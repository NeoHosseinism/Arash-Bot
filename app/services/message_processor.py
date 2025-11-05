"""
Message processor with platform-aware logic
"""
import logging
from typing import Dict, Any, Optional
import asyncio

from app.models.schemas import IncomingMessage, BotResponse
from app.models.session import ChatSession
from app.models.database import Team, get_db_session
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.command_processor import command_processor
from app.services.ai_client import ai_client
from app.services.webhook_client import webhook_client
from app.core.constants import MESSAGES_FA, MessageType

logger = logging.getLogger(__name__)


class MessageProcessor:
    """Processes messages with platform-aware logic"""
    
    async def process_message(self, message: IncomingMessage) -> BotResponse:
        """Process incoming message with team isolation"""

        try:
            # Extract team info from metadata (set by API endpoint)
            team_id = message.metadata.get("team_id")
            api_key_id = message.metadata.get("api_key_id")
            api_key_prefix = message.metadata.get("api_key_prefix")

            # Get or create session with team isolation
            session = session_manager.get_or_create_session(
                platform=message.platform,
                user_id=message.user_id,
                chat_id=message.chat_id,
                team_id=team_id,
                api_key_id=api_key_id,
                api_key_prefix=api_key_prefix
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

            # Prepare response
            bot_response = BotResponse(
                success=True,
                response=response_text,
                data={
                    "session_id": session.session_id,
                    "platform": session.platform,
                    "model": session.current_model,
                    "message_count": session.message_count
                }
            )

            # Send webhook asynchronously (don't block response)
            if team_id:
                asyncio.create_task(self._send_webhook(
                    team_id=team_id,
                    message=message,
                    response=bot_response
                ))

            return bot_response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return BotResponse(
                success=False,
                error="processing_error",
                response=MESSAGES_FA["error_processing"]
            )

    async def _send_webhook(
        self,
        team_id: int,
        message: IncomingMessage,
        response: BotResponse
    ) -> None:
        """
        Send webhook callback to team (runs in background)

        Args:
            team_id: Team ID
            message: Original incoming message
            response: Bot response
        """
        try:
            # Get team from database
            db = get_db_session()
            team = db.query(Team).filter(Team.id == team_id).first()

            if not team:
                logger.warning(f"Team {team_id} not found for webhook")
                return

            # Prepare message data for webhook
            message_data = {
                "platform": message.platform,
                "user_id": message.user_id,
                "chat_id": message.chat_id,
                "message_id": message.message_id,
                "text": message.text,
                "type": message.type.value if hasattr(message.type, 'value') else str(message.type),
                "timestamp": message.timestamp.isoformat() if message.timestamp else None
            }

            # Prepare response data for webhook
            response_data = {
                "success": response.success,
                "response": response.response,
                "data": response.data,
                "error": response.error
            }

            # Send webhook
            await webhook_client.send_message_callback(
                team=team,
                message_data=message_data,
                response_data=response_data
            )

        except Exception as e:
            logger.error(f"Error sending webhook for team {team_id}: {e}", exc_info=True)
    
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
            
            # Send to AI service with session's current model
            try:
                response = await ai_client.send_chat_request(
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

            except Exception as ai_service_error:
                logger.error(f"AI service error: {ai_service_error}")

                # Return fallback message when AI service is unavailable
                return (
                    "⚠️ متأسفم، سرویس هوش مصنوعی در حال حاضر در دسترس نیست.\n\n"
                    f"پیام شما: {message.text}\n\n"
                    "لطفاً چند لحظه دیگر دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.\n\n"
                    f"جزئیات خطا: سرویس هوش مصنوعی پاسخ نمی‌دهد."
                )
            
        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            return MESSAGES_FA["error_processing"]


# Global instance
message_processor = MessageProcessor()