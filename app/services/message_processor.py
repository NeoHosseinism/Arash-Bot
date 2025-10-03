"""
Message processor with platform-aware logic
"""
import logging
from typing import Dict, Any

from app.models.schemas import IncomingMessage, BotResponse
from app.models.session import ChatSession
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.command_processor import command_processor
from app.services.openrouter_client import openrouter_client
from app.core.constants import MESSAGES_FA, MessageType

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes messages with platform-aware logic"""
    
    async def process_message(self, message: IncomingMessage) -> BotResponse:
        """Process incoming message"""
        
        try:
            # Get or create session
            session = session_manager.get_or_create_session(
                platform=message.platform,
                user_id=message.user_id,
                chat_id=message.chat_id
            )
            
            # Check authentication if required
            if platform_manager.requires_auth(message.platform):
                if not message.auth_token or not platform_manager.validate_auth(
                    message.platform, message.auth_token
                ):
                    return BotResponse(
                        success=False,
                        error="authentication_failed",
                        response=MESSAGES_FA["error_auth_failed"]
                    )
            
            # Check rate limit
            if not session_manager.check_rate_limit(message.platform, message.user_id):
                rate_limit = platform_manager.get_rate_limit(message.platform)
                return BotResponse(
                    success=False,
                    error="rate_limit",
                    response=MESSAGES_FA["error_rate_limit"].format(rate_limit=rate_limit)
                )
            
            # Process command or message
            if message.text and command_processor.is_command(message.text):
                response_text = await self._handle_command(session, message.text)
            else:
                response_text = await self._handle_chat(session, message)
            
            # Update session
            session.message_count += 1
            session.update_activity()
            
            return BotResponse(
                success=True,
                response=response_text,
                data={
                    "session_id": session.session_id,
                    "platform": session.platform,
                    "model": session.current_model,
                    "message_count": session.message_count
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return BotResponse(
                success=False,
                error="processing_error",
                response=MESSAGES_FA["error_processing"]
            )
    
    async def _handle_command(self, session: ChatSession, text: str) -> str:
        """Handle command"""
        return await command_processor.process_command(session, text)
    
    async def _handle_chat(self, session: ChatSession, message: IncomingMessage) -> str:
        """Handle chat message"""
        try:
            # Prepare files if any
            files = []
            if message.attachments:
                for att in message.attachments:
                    if att.type == MessageType.IMAGE and att.data:
                        files.append({
                            "Data": att.data,
                            "MIMEType": att.mime_type or "image/jpeg"
                        })
            
            # Get max history for platform
            max_history = platform_manager.get_max_history(session.platform)
            
            # Send to OpenRouter with session's current model
            response = await openrouter_client.send_chat_request(
                session_id=session.session_id,
                query=message.text or "این تصویر را توضیح بده؟",
                history=session.get_recent_history(max_history),
                pipeline=session.current_model,
                files=files
            )
            
            # Update history
            session.add_message("user", message.text or "[تصویر/پیوست]")
            session.add_message("assistant", response["Response"])
            
            # Trim history if exceeds platform limit
            if len(session.history) > max_history * 2:
                session.history = session.history[-max_history * 2:]
            
            return response["Response"]
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            return MESSAGES_FA["error_processing"]


# Global instance
message_processor = MessageProcessor()