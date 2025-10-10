"""
Configuration management using Pydantic Settings V2
"""
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import json


class Settings(BaseSettings):
    """Application settings with validation - Pydantic V2"""
    
    # Core Configuration
    ENVIRONMENT: str = "development"
    OPENROUTER_SERVICE_URL: str
    SESSION_TIMEOUT_MINUTES: int = 30
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_DEFAULT_MODEL: str = "google/gemini-2.0-flash-001"
    TELEGRAM_MODELS: str = (
        "google/gemini-2.0-flash-001,google/gemini-2.5-flash,"
        "deepseek/deepseek-chat-v3-0324,openai/gpt-4o-mini,google/gemma-3-1b-it"
    )
    TELEGRAM_RATE_LIMIT: int = 20
    TELEGRAM_MAX_HISTORY: int = 10
    TELEGRAM_COMMANDS: str = "start,help,status,translate,model,models"
    TELEGRAM_ADMIN_USERS: str = ""
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    
    # Internal Configuration
    INTERNAL_DEFAULT_MODEL: str = "openai/gpt-5-chat"
    INTERNAL_MODELS: str
    INTERNAL_RATE_LIMIT: int = 60
    INTERNAL_MAX_HISTORY: int = 30
    INTERNAL_API_KEY: str
    INTERNAL_WEBHOOK_SECRET: Optional[str] = None
    INTERNAL_ADMIN_USERS: str = ""
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/arash_bot_service.log"
    
    # Features
    ENABLE_IMAGE_PROCESSING: bool = True
    MAX_IMAGE_SIZE_MB: int = 20
    
    # Database (Optional)
    REDIS_URL: Optional[str] = None
    DATABASE_URL: Optional[str] = None
    
    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    ENABLE_API_DOCS: bool = True
    CORS_ORIGINS: str = "*"
    
    # Pydantic V2 model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env file
    )
    
    @field_validator("TELEGRAM_BOT_TOKEN")
    @classmethod
    def validate_telegram_token(cls, v: str) -> str:
        """Validate Telegram bot token format"""
        if not v or v == "your_telegram_bot_token_here":
            raise ValueError("TELEGRAM_BOT_TOKEN must be set to a valid token")
        if ":" not in v:
            raise ValueError("Invalid Telegram bot token format")
        return v
    
    @field_validator("INTERNAL_API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key strength"""
        if not v or v == "your_secure_random_api_key_here":
            raise ValueError("INTERNAL_API_KEY must be set to a secure key")
        if len(v) < 32:
            raise ValueError("INTERNAL_API_KEY must be at least 32 characters")
        return v
    
    @field_validator("LOG_FILE")
    @classmethod
    def create_log_directory(cls, v: str) -> str:
        """Ensure log directory exists"""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @field_validator("INTERNAL_MODELS")
    @classmethod
    def validate_internal_models(cls, v: str) -> str:
        """Validate INTERNAL_MODELS is valid JSON array or comma-separated string"""
        if not v:
            raise ValueError("INTERNAL_MODELS cannot be empty")
        
        # Try parsing as JSON first
        if v.strip().startswith('['):
            try:
                models = json.loads(v)
                if not isinstance(models, list):
                    raise ValueError("INTERNAL_MODELS JSON must be an array")
                if not models:
                    raise ValueError("INTERNAL_MODELS array cannot be empty")
                return v
            except json.JSONDecodeError as e:
                raise ValueError(f"INTERNAL_MODELS invalid JSON: {e}")
        
        # Otherwise treat as comma-separated
        if not any(c in v for c in [',', '/']):
            raise ValueError("INTERNAL_MODELS must be JSON array or comma-separated list")
        
        return v
    
    @property
    def telegram_commands_list(self) -> List[str]:
        """Get Telegram commands as list"""
        return [cmd.strip() for cmd in self.TELEGRAM_COMMANDS.split(",") if cmd.strip()]
    
    @property
    def telegram_models_list(self) -> List[str]:
        """Get Telegram models as list"""
        return [model.strip() for model in self.TELEGRAM_MODELS.split(",") if model.strip()]
    
    @property
    def telegram_admin_users_set(self) -> set:
        """Get Telegram admin users as set"""
        return {user.strip() for user in self.TELEGRAM_ADMIN_USERS.split(",") if user.strip()}
    
    @property
    def internal_models_list(self) -> List[str]:
        """Get internal models as list"""
        # Handle JSON array format
        if self.INTERNAL_MODELS.strip().startswith('['):
            try:
                return json.loads(self.INTERNAL_MODELS)
            except json.JSONDecodeError:
                pass
        
        # Handle comma-separated format
        return [model.strip() for model in self.INTERNAL_MODELS.split(",") if model.strip()]
    
    @property
    def internal_admin_users_set(self) -> set:
        """Get internal admin users as set"""
        return {user.strip() for user in self.INTERNAL_ADMIN_USERS.split(",") if user.strip()}
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @property
    def max_image_size_bytes(self) -> int:
        """Get max image size in bytes"""
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


# Global settings instance
# This will raise validation errors if required fields are missing from .env
settings = Settings()   # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings