"""
Command processor with platform-aware access control
"""
from typing import List, Tuple, Optional
import logging

from app.models.session import ChatSession
from app.services.platform_manager import platform_manager
from app.core.constants import MESSAGES_FA, COMMAND_DESCRIPTIONS, MODEL_ALIASES

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Processes bot commands with platform-aware access control"""
    
    def __init__(self):
        self.commands = {
            "start": self.handle_start,
            "help": self.handle_help,
            "status": self.handle_status,
            "clear": self.handle_clear,
            "model": self.handle_model,
            "models": self.handle_models,
            "summarize": self.handle_summarize,
            "translate": self.handle_translate,
            "settings": self.handle_settings,
        }
    
    def is_command(self, text: str) -> bool:
        """Check if text is a command"""
        if not text:
            return False
        return text.startswith("/") or text.startswith("!")
    
    def parse_command(self, text: str) -> Tuple[Optional[str], List[str]]:
        """Parse command and arguments"""
        if not self.is_command(text):
            return None, []
        
        text = text.lstrip("/!").strip()
        parts = text.split()
        
        if not parts:
            return None, []
        
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        return command, args
    
    def can_use_command(self, command: str, platform: str) -> bool:
        """Check if platform can use command"""
        allowed_commands = platform_manager.get_allowed_commands(platform)
        return command in allowed_commands
    
    async def process_command(self, session: ChatSession, text: str) -> str:
        """Process command and return response"""
        command, args = self.parse_command(text)
        
        if not command:
            return MESSAGES_FA["command_unknown"].format(command="")
        
        # Check if command is allowed for platform
        if not self.can_use_command(command, session.platform):
            allowed = platform_manager.get_allowed_commands(session.platform)
            commands_list = "\n".join([f"• /{c}" for c in allowed])
            return MESSAGES_FA["command_not_available_platform"].format(
                command=command,
                platform=session.platform.title(),
                commands=commands_list
            )
        
        # Execute command
        if command in self.commands:
            handler = self.commands[command]
            try:
                return await handler(session, args)
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}", exc_info=True)
                return f"❌ خطا در اجرای دستور: {str(e)}"
        
        return MESSAGES_FA["command_unknown"].format(command=command)
    
    async def handle_start(self, session: ChatSession, args: List[str]) -> str:
        """Handle /start command"""
        config = platform_manager.get_config(session.platform)
        
        if session.platform == "internal":
            welcome = MESSAGES_FA["welcome_internal"].format(model=session.current_model)
            if session.is_admin:
                welcome += MESSAGES_FA["welcome_internal_admin"]
            return welcome
        else:
            return MESSAGES_FA["welcome_telegram"].format(
                model=session.current_model,
                rate_limit=config.rate_limit
            )
    
    async def handle_help(self, session: ChatSession, args: List[str]) -> str:
        """Handle /help command"""
        allowed_commands = platform_manager.get_allowed_commands(session.platform)
        config = platform_manager.get_config(session.platform)
        
        help_text = "📚 **دستورات موجود:**\n\n"
        for cmd in allowed_commands:
            if cmd in COMMAND_DESCRIPTIONS:
                help_text += f"/{cmd} - {COMMAND_DESCRIPTIONS[cmd]}\n"
        
        help_text += "\n📊 **اطلاعات پلتفرم:**\n"
        if session.platform == "internal":
            help_text += f"• پلتفرم: داخلی (خصوصی)\n"
            help_text += f"• تغییر مدل: ✅ فعال\n"
            help_text += f"• مدل فعلی: {session.current_model}\n"
            help_text += f"• محدودیت سرعت: {config.rate_limit} پیام/دقیقه\n"
            help_text += f"• حداکثر تاریخچه: {config.max_history} پیام\n"
        else:
            help_text += f"• پلتفرم: تلگرام\n"
            help_text += f"• مدل: {config.model} (ثابت)\n"
            help_text += f"• محدودیت سرعت: {config.rate_limit} پیام/دقیقه\n"
            help_text += f"• حداکثر تاریخچه: {config.max_history} پیام\n"
        
        return help_text
    
    async def handle_status(self, session: ChatSession, args: List[str]) -> str:
        """Handle /status command"""
        config = platform_manager.get_config(session.platform)
        uptime = session.get_uptime_seconds()
        
        status_text = (
            f"📊 **وضعیت نشست:**\n\n"
            f"• پلتفرم: {session.platform.title()}\n"
            f"• نوع: {'خصوصی (داخلی)' if config.type == 'private' else 'عمومی'}\n"
            f"• شناسه نشست: {session.session_id[:8]}...\n"
            f"• مدل فعلی: {session.current_model}\n"
            f"• تعداد پیام‌ها: {session.message_count}\n"
            f"• تاریخچه: {len(session.history)}/{config.max_history}\n"
            f"• مدت فعالیت: {uptime:.0f} ثانیه\n"
            f"• محدودیت سرعت: {config.rate_limit}/دقیقه\n"
        )
        
        if session.is_admin:
            status_text += "• نقش: ادمین 👑\n"
        
        return status_text
    
    async def handle_clear(self, session: ChatSession, args: List[str]) -> str:
        """Handle /clear command (private only)"""
        if not platform_manager.can_switch_models(session.platform):
            return MESSAGES_FA["command_not_available_telegram"].format(command="clear")
        
        session.clear_history()
        return MESSAGES_FA["session_cleared"]
    
    async def handle_model(self, session: ChatSession, args: List[str]) -> str:
        """Handle /model command (private only)"""
        if session.platform != "internal":
            return MESSAGES_FA["model_switch_not_available"].format(model=session.current_model)
        
        available_models = platform_manager.get_available_models(session.platform)
        
        if not args:
            return (
                f"**مدل فعلی:** {session.current_model}\n\n"
                f"**مدل‌های موجود:**\n" +
                "\n".join([f"• {m}" for m in available_models]) +
                f"\n\nبرای تغییر مدل از `/model [نام]` استفاده کنید"
            )
        
        model = args[0].lower()
        
        # Check model aliases
        if model in MODEL_ALIASES:
            model = MODEL_ALIASES[model]
        
        if not platform_manager.is_model_available(session.platform, model):
            return (
                MESSAGES_FA["model_invalid"].format(model=model) + "\n\n"
                f"**مدل‌های موجود:**\n" +
                "\n".join([f"• {m}" for m in available_models])
            )
        
        session.current_model = model
        return MESSAGES_FA["model_switched"].format(model=model)
    
    async def handle_models(self, session: ChatSession, args: List[str]) -> str:
        """Handle /models command"""
        config = platform_manager.get_config(session.platform)
        
        if session.platform != "internal":
            return (
                f"📌 **پلتفرم تلگرام:**\n\n"
                f"مدل ثابت: **{config.model}**\n\n"
                f"تغییر مدل فقط برای کاربران داخلی امکان‌پذیر است."
            )
        
        available_models = platform_manager.get_available_models(session.platform)
        models_text = "🤖 **مدل‌های موجود:**\n\n"
        
        for model in available_models:
            if model == session.current_model:
                models_text += f"• **{model}** ← فعلی\n"
            else:
                models_text += f"• {model}\n"
        
        models_text += f"\n💡 از `/model [نام]` برای تغییر استفاده کنید"
        
        # Add aliases info
        models_text += "\n\n**نام‌های مستعار (aliases):**\n"
        models_text += "• claude, sonnet → Claude Sonnet 4\n"
        models_text += "• gpt, gpt5 → GPT-5\n"
        models_text += "• gpt4, gpt-4 → GPT-4.1\n"
        models_text += "• mini → GPT-4o Mini\n"
        models_text += "• web, search → GPT-4o Search\n"
        models_text += "• gemini → Gemini 2.5 Flash\n"
        models_text += "• grok → Grok 4\n"
        models_text += "• deepseek → DeepSeek v3\n"
        models_text += "• llama → Llama 4 Maverick\n"
        
        return models_text
    
    async def handle_summarize(self, session: ChatSession, args: List[str]) -> str:
        """Handle /summarize command (private only)"""
        if session.platform != "internal":
            return MESSAGES_FA["internal_only"]
        
        if not session.history:
            return MESSAGES_FA["session_no_history"]
        
        return "📝 خلاصه‌سازی گفت‌وگو در حال پردازش است..."
    
    async def handle_translate(self, session: ChatSession, args: List[str]) -> str:
        """Handle /translate command"""
        if "translate" not in platform_manager.get_allowed_commands(session.platform):
            return "❌ ترجمه برای این پلتفرم در دسترس نیست."
        
        if len(args) < 2:
            return (
                "**استفاده:** `/translate [زبان] [متن]`\n\n"
                "**مثال:** `/translate english سلام دنیا`"
            )
        
        language = args[0]
        text = " ".join(args[1:])
        
        return f"🌐 در حال ترجمه به {language}: *{text}*\n(این به سرویس OpenRouter ارسال می‌شود)"
    
    async def handle_settings(self, session: ChatSession, args: List[str]) -> str:
        """Handle /settings command (private only)"""
        if session.platform != "internal":
            return MESSAGES_FA["internal_only"]
        
        settings_text = (
            "⚙️ **تنظیمات کاربر:**\n\n"
            f"• شناسه کاربر: {session.user_id}\n"
            f"• پلتفرم: {session.platform}\n"
            f"• مدل پیش‌فرض: {session.current_model}\n"
            f"• وضعیت ادمین: {'بله' if session.is_admin else 'خیر'}\n\n"
            "امکان سفارشی‌سازی تنظیمات به زودی..."
        )
        
        return settings_text


# Global instance
command_processor = CommandProcessor()