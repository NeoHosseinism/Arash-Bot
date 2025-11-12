"""
Message processor with platform-aware logic
"""
import logging
import time
from typing import Dict, Any, Optional
import asyncio

from app.models.schemas import IncomingMessage, BotResponse
from app.models.session import ChatSession
from app.models.database import Team, get_db_session
from app.services.session_manager import session_manager
from app.services.platform_manager import platform_manager
from app.services.command_processor import command_processor
from app.services.ai_client import ai_client
from app.services.usage_tracker import UsageTracker
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

            return bot_response

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return BotResponse(
                success=False,
                error="processing_error",
                response=MESSAGES_FA["error_processing"]
            )

    async def process_message_simple(
        self,
        platform_name: str,
        team_id: Optional[int],
        api_key_id: Optional[int],
        api_key_prefix: Optional[str],
        user_id: str,
        chat_id: str,
        message_id: str,
        text: str,
    ) -> BotResponse:
        """
        Process message with simplified interface (text-only, no webhooks).

        Args:
            platform_name: Platform name (e.g., "telegram", "Internal-BI")
            team_id: Team ID (None for Telegram, required for authenticated platforms)
            api_key_id: API key ID (None for Telegram)
            api_key_prefix: API key prefix (None for Telegram)
            user_id: User ID
            chat_id: Chat ID (auto-generated if not provided by client)
            message_id: Message ID (auto-generated)
            text: Message text

        Returns:
            BotResponse with chat_id for continuation
        """
        start_time = time.time()
        db = get_db_session()

        try:
            # Get or create session with platform_name
            # This will raise PermissionError if API key doesn't own the chat_id
            try:
                session = session_manager.get_or_create_session(
                    platform=platform_name,  # Now using platform_name instead of "internal"
                    user_id=user_id,
                    chat_id=chat_id,
                    team_id=team_id,
                    api_key_id=api_key_id,
                    api_key_prefix=api_key_prefix
                )
            except PermissionError as e:
                # API key doesn't own this chat - return 403 error
                return BotResponse(
                    success=False,
                    error="access_denied",
                    response=f"❌ دسترسی رد شد. این مکالمه متعلق به API key دیگری است.\n\nAccess denied. This chat belongs to a different API key.",
                    chat_id=chat_id,
                )

            # Check rate limit (use platform_name for rate limiting)
            if not session_manager.check_rate_limit(platform_name, user_id):
                # Get rate limit for this platform from session config
                rate_limit = session.platform_config.get("rate_limit", 60)

                # Log rate limit failure (only for authenticated teams)
                if team_id and api_key_id:
                    response_time_ms = int((time.time() - start_time) * 1000)
                    UsageTracker.log_usage(
                        db=db,
                        api_key_id=api_key_id,
                        team_id=team_id,
                        session_id=chat_id,
                        platform=platform_name,
                        model_used=session.current_model,
                        success=False,
                        response_time_ms=response_time_ms,
                        error_message="rate_limit_exceeded",
                    )

                return BotResponse(
                    success=False,
                    error="rate_limit_exceeded",
                    response=f"⚠️ محدودیت سرعت. لطفاً قبل از ارسال پیام بعدی کمی صبر کنید.\n\nمحدودیت: {rate_limit} پیام در دقیقه",
                    chat_id=chat_id,
                )

            # Process command or message
            if text and command_processor.is_command(text):
                response_text = await self._handle_command(session, text)
            else:
                response_text = await self._handle_chat_simple(session, text)

            # Update session
            session.message_count += 1
            session.update_activity()

            # Log successful usage (only for authenticated teams)
            if team_id and api_key_id:
                response_time_ms = int((time.time() - start_time) * 1000)
                UsageTracker.log_usage(
                    db=db,
                    api_key_id=api_key_id,
                    team_id=team_id,
                    session_id=chat_id,
                    platform=platform_name,
                    model_used=session.current_model,
                    success=True,
                    response_time_ms=response_time_ms,
                )

            # Return simplified response with chat_id (NO session_id)
            return BotResponse(
                success=True,
                response=response_text,
                chat_id=chat_id,  # Only chat_id needed for continuation
                model=session.current_model,
                message_count=session.message_count,
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

            # Log error (only for authenticated teams)
            if team_id and api_key_id:
                response_time_ms = int((time.time() - start_time) * 1000)
                try:
                    # Get model from session if available
                    session = session_manager.get_or_create_session(
                        platform=platform_name,
                        user_id=user_id,
                        chat_id=chat_id,
                        team_id=team_id,
                        api_key_id=api_key_id,
                        api_key_prefix=api_key_prefix
                    )
                    UsageTracker.log_usage(
                        db=db,
                        api_key_id=api_key_id,
                        team_id=team_id,
                        session_id=chat_id,
                        platform=platform_name,
                        model_used=session.current_model,
                        success=False,
                        response_time_ms=response_time_ms,
                        error_message=str(e),
                    )
                except:
                    pass  # Don't fail on logging errors

            return BotResponse(
                success=False,
                error="processing_error",
                response="❌ متأسفم، خطایی در پردازش پیام شما رخ داد. لطفاً دوباره تلاش کنید.",
                chat_id=chat_id,
            )

    async def _handle_chat_simple(self, session: ChatSession, text: str) -> str:
        """Handle chat message (simplified, text-only)"""
        try:
            # Get max history for platform
            max_history = platform_manager.get_max_history(session.platform)

            # Send to AI service with session's current model
            try:
                response = await ai_client.send_chat_request(
                    session_id=session.session_id,
                    query=text,
                    history=session.get_recent_history(max_history),
                    pipeline=session.current_model,
                    files=[],  # No files in simplified version
                )

                # Update history
                session.add_message("user", text)
                session.add_message("assistant", response["Response"])

                # Trim history if exceeds platform limit
                if len(session.history) > max_history * 2:
                    session.history = session.history[-max_history * 2:]

                return response["Response"]

            except Exception as ai_service_error:
                logger.error(f"AI service error: {ai_service_error}")
                return (
                    "متأسفم، سرویس هوش مصنوعی در حال حاضر در دسترس نیست. "
                    "لطفاً چند لحظه دیگر دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
                )

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            return "خطایی در پردازش پیام شما رخ داد. لطفاً دوباره تلاش کنید."

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