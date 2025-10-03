"""
Platform configuration manager
"""
from typing import List, Dict, Any
from app.core.config import settings
from app.core.constants import Platform, PlatformType
import logging

logger = logging.getLogger(__name__)


class PlatformConfig:
    """Platform configuration"""
    
    def __init__(
        self,
        type: str,
        model: str,
        available_models: List[str] = None,
        rate_limit: int = 30,
        commands: List[str] = None,
        allow_model_switch: bool = False,
        requires_auth: bool = False,
        api_key: str = None,
        max_history: int = 20
    ):
        self.type = type
        self.model = model
        self.available_models = available_models or [model]
        self.rate_limit = rate_limit
        self.commands = commands or []
        self.allow_model_switch = allow_model_switch
        self.requires_auth = requires_auth
        self.api_key = api_key
        self.max_history = max_history
    
    def dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "model": self.model,
            "available_models": self.available_models,
            "rate_limit": self.rate_limit,
            "commands": self.commands,
            "allow_model_switch": self.allow_model_switch,
            "requires_auth": self.requires_auth,
            "max_history": self.max_history
        }


class PlatformManager:
    """Manages platform-specific configurations and access control"""
    
    def __init__(self):
        self.configs: Dict[str, PlatformConfig] = {}
        self._load_configurations()
    
    def _load_configurations(self):
        """Load platform configurations from settings"""
        
        # Telegram configuration (PUBLIC)
        self.configs[Platform.TELEGRAM] = PlatformConfig(
            type=PlatformType.PUBLIC,
            model=settings.TELEGRAM_MODEL,
            available_models=[settings.TELEGRAM_MODEL],
            rate_limit=settings.TELEGRAM_RATE_LIMIT,
            commands=settings.telegram_commands_list,
            allow_model_switch=False,
            requires_auth=False,
            max_history=settings.TELEGRAM_MAX_HISTORY
        )
        
        # Internal configuration (PRIVATE)
        self.configs[Platform.INTERNAL] = PlatformConfig(
            type=PlatformType.PRIVATE,
            model=settings.INTERNAL_DEFAULT_MODEL,
            available_models=settings.internal_models_list,
            rate_limit=settings.INTERNAL_RATE_LIMIT,
            commands=["start", "help", "status", "clear", "model", "models", 
                     "settings", "summarize", "translate"],
            allow_model_switch=True,
            requires_auth=True,
            api_key=settings.INTERNAL_API_KEY,
            max_history=settings.INTERNAL_MAX_HISTORY
        )
        
        logger.info("Platform configurations loaded successfully")
        logger.info(f"  - Telegram: {self.configs[Platform.TELEGRAM].model}")
        logger.info(f"  - Internal: {len(self.configs[Platform.INTERNAL].available_models)} models")
    
    def get_config(self, platform: str) -> PlatformConfig:
        """Get configuration for a platform"""
        # Normalize platform name
        platform = platform.lower()
        
        # Return config if exists, otherwise default to telegram (public)
        if platform in self.configs:
            return self.configs[platform]
        
        logger.warning(f"Unknown platform: {platform}, defaulting to Telegram")
        return self.configs[Platform.TELEGRAM]
    
    def is_private_platform(self, platform: str) -> bool:
        """Check if platform is private"""
        config = self.get_config(platform)
        return config.type == PlatformType.PRIVATE
    
    def can_switch_models(self, platform: str) -> bool:
        """Check if platform allows model switching"""
        config = self.get_config(platform)
        return config.allow_model_switch
    
    def get_available_models(self, platform: str) -> List[str]:
        """Get available models for platform"""
        config = self.get_config(platform)
        return config.available_models
    
    def get_default_model(self, platform: str) -> str:
        """Get default model for platform"""
        config = self.get_config(platform)
        return config.model
    
    def get_rate_limit(self, platform: str) -> int:
        """Get rate limit for platform"""
        config = self.get_config(platform)
        return config.rate_limit
    
    def get_allowed_commands(self, platform: str) -> List[str]:
        """Get allowed commands for platform"""
        config = self.get_config(platform)
        return config.commands
    
    def get_max_history(self, platform: str) -> int:
        """Get maximum history length for platform"""
        config = self.get_config(platform)
        return config.max_history
    
    def requires_auth(self, platform: str) -> bool:
        """Check if platform requires authentication"""
        config = self.get_config(platform)
        return config.requires_auth
    
    def validate_auth(self, platform: str, token: str) -> bool:
        """Validate authentication for platform"""
        config = self.get_config(platform)
        if not config.requires_auth:
            return True
        return config.api_key and token == config.api_key
    
    def is_admin(self, platform: str, user_id: str) -> bool:
        """Check if user is admin for platform"""
        if platform == Platform.TELEGRAM:
            return user_id in settings.telegram_admin_users_set
        elif platform == Platform.INTERNAL:
            return user_id in settings.internal_admin_users_set
        return False
    
    def is_model_available(self, platform: str, model: str) -> bool:
        """Check if model is available for platform"""
        available_models = self.get_available_models(platform)
        return model in available_models


# Global instance
platform_manager = PlatformManager()