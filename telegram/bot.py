"""
Telegram Bot Setup
"""
import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from telegram.client import BotServiceClient
from telegram.handlers import TelegramHandlers
from app.core.config import settings
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot manager"""
    
    def __init__(self, service_url: str = "http://localhost:8001"):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.webhook_url = settings.TELEGRAM_WEBHOOK_URL
        self.bot_client = BotServiceClient(service_url)
        self.handlers = TelegramHandlers(self.bot_client)
        self.application = None
    
    def setup(self):
        """Setup bot application"""
        logger.info("Setting up Telegram bot...")
        
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add command handlers
        self.application.add_handler(
            CommandHandler("start", self.handlers.start_command)
        )
        self.application.add_handler(
            CommandHandler("help", self.handlers.help_command)
        )
        self.application.add_handler(
            CommandHandler("status", self.handlers.handle_text_message)
        )
        self.application.add_handler(
            CommandHandler("translate", self.handlers.handle_text_message)
        )
        
        # Add message handlers
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handlers.handle_text_message
            )
        )
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.handlers.handle_photo)
        )
        self.application.add_handler(
            MessageHandler(filters.Document.IMAGE, self.handlers.handle_document)
        )
        
        # Add error handler
        self.application.add_error_handler(self.handlers.error_handler)
        
        logger.info("Telegram bot setup complete")
    
    def run(self):
        """Run the bot"""
        if not self.application:
            self.setup()
        
        if self.webhook_url:
            # Use webhook mode
            logger.info(f"Starting bot in webhook mode: {self.webhook_url}")
            self.application.run_webhook(
                listen="0.0.0.0",
                port=8443,
                url_path=self.token,
                webhook_url=f"{self.webhook_url}/{self.token}"
            )
        else:
            # Use polling mode
            logger.info("Starting bot in polling mode...")
            logger.info(f"Bot service URL: {self.bot_client.service_url}")
            logger.info(f"Model: {settings.TELEGRAM_MODEL}")
            logger.info(f"Rate limit: {settings.TELEGRAM_RATE_LIMIT}/min")
            logger.info("=" * 60)
            self.application.run_polling(drop_pending_updates=True)


def main():
    """Main entry point"""
    try:
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\nBot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()