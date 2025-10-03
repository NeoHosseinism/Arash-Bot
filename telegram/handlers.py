"""
Telegram bot handlers
"""
import base64
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramHandlers:
    """Telegram message handlers"""
    
    def __init__(self, bot_client):
        self.bot_client = bot_client
        self.max_file_size = settings.max_image_size_bytes
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        chat = update.effective_chat
        
        try:
            response = await self.bot_client.send_message(
                user_id=str(user.id),
                chat_id=str(chat.id),
                message_id=str(update.message.message_id),
                text="/start"
            )
            
            await update.message.reply_text(
                response["data"]["response"],
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in start command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ متأسفم، خطایی رخ داد. لطفاً بعداً تلاش کنید."
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user = update.effective_user
        chat = update.effective_chat
        
        try:
            response = await self.bot_client.send_message(
                user_id=str(user.id),
                chat_id=str(chat.id),
                message_id=str(update.message.message_id),
                text="/help"
            )
            
            await update.message.reply_text(
                response["data"]["response"],
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in help command: {e}", exc_info=True)
            await update.message.reply_text(
                "❌ متأسفم، خطایی رخ داد. لطفاً بعداً تلاش کنید."
            )
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        
        try:
            response = await self.bot_client.send_message(
                user_id=str(user.id),
                chat_id=str(chat.id),
                message_id=str(message.message_id),
                text=message.text
            )
            
            await message.reply_text(
                response["data"]["response"],
                parse_mode="Markdown"
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                await message.reply_text(
                    "⚠️ محدودیت سرعت. لطفاً کمی صبر کنید."
                )
            else:
                await message.reply_text(
                    "❌ متأسفم، خطایی در پردازش پیام شما رخ داد. لطفاً دوباره تلاش کنید."
                )
        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)
            await message.reply_text(
                "❌ متأسفم، خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages"""
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        
        # Validate photo exists
        if not message.photo:
            await message.reply_text("❌ هیچ تصویری در پیام یافت نشد.")
            return
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        
        try:
            # Get the largest photo
            photo = message.photo[-1]
            
            # Check file size
            if photo.file_size and photo.file_size > self.max_file_size:
                await message.reply_text(
                    f"❌ تصویر خیلی بزرگ است. حداکثر حجم {settings.MAX_IMAGE_SIZE_MB}MB است.\n"
                    f"حجم تصویر شما: {photo.file_size / (1024*1024):.1f}MB"
                )
                return
            
            # Download photo
            file = await context.bot.get_file(photo.file_id)
            photo_bytes = await file.download_as_bytearray()
            
            # Convert to base64
            photo_base64 = base64.b64encode(photo_bytes).decode('utf-8')
            
            # Get caption if any
            caption = message.caption or "این تصویر را توضیح بده؟"
            
            # Send to bot service
            response = await self.bot_client.send_message(
                user_id=str(user.id),
                chat_id=str(chat.id),
                message_id=str(message.message_id),
                text=caption,
                image_data=photo_base64,
                mime_type="image/jpeg"
            )
            
            # Send response
            await message.reply_text(
                response["data"]["response"],
                parse_mode="Markdown"
            )
            
        except httpx.TimeoutException:
            logger.error(f"Timeout processing photo from user {user.id}")
            await message.reply_text(
                "⏱️ درخواست به پایان زمان رسید. ممکن است تصویر خیلی بزرگ باشد. لطفاً دوباره تلاش کنید."
            )
        except Exception as e:
            logger.error(f"Error handling photo: {e}", exc_info=True)
            await message.reply_text(
                "❌ نتوانستم تصویر را پردازش کنم. لطفاً دوباره تلاش کنید."
            )
    
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle document messages"""
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        document = message.document
        
        # Check if it's an image document
        if document.mime_type and document.mime_type.startswith("image/"):
            await context.bot.send_chat_action(chat_id=chat.id, action="typing")
            
            # Check file size
            if document.file_size and document.file_size > self.max_file_size:
                await message.reply_text(
                    f"❌ فایل خیلی بزرگ است. حداکثر حجم {settings.MAX_IMAGE_SIZE_MB}MB است.\n"
                    f"حجم فایل شما: {document.file_size / (1024*1024):.1f}MB"
                )
                return
            
            try:
                # Download document
                file = await context.bot.get_file(document.file_id)
                file_bytes = await file.download_as_bytearray()
                
                # Convert to base64
                file_base64 = base64.b64encode(file_bytes).decode('utf-8')
                
                # Get caption if any
                caption = message.caption or "این تصویر را توضیح بده؟"
                
                # Send to bot service
                response = await self.bot_client.send_message(
                    user_id=str(user.id),
                    chat_id=str(chat.id),
                    message_id=str(message.message_id),
                    text=caption,
                    image_data=file_base64,
                    mime_type=document.mime_type
                )
                
                await message.reply_text(
                    response["data"]["response"],
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error handling document: {e}", exc_info=True)
                await message.reply_text(
                    "❌ نتوانستم فایل را پردازش کنم. لطفاً دوباره تلاش کنید."
                )
        else:
            await message.reply_text(
                "❌ متأسفم، فعلاً فقط می‌توانم فایل‌های تصویری را پردازش کنم."
            )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
        
        # Send error message to user
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ خطایی در پردازش درخواست شما رخ داد. لطفاً بعداً تلاش کنید."
            )