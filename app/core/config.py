"""
Configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Core Configuration
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    OPENROUTER_SERVICE_URL: str = Field(..., env="OPENROUTER_SERVICE_URL")
    SESSION_TIMEOUT_MINUTES: int = Field(default=30, env="SESSION_TIMEOUT_MINUTES")
    
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_DEFAULT_MODEL: str = Field(default="google/gemini-2.0-flash-001", env="TELEGRAM_DEFAULT_MODEL")
    TELEGRAM_MODELS: str = Field(
        default="google/gemini-2.0-flash-001,google/gemini-2.5-flash,deepseek/deepseek-chat-v3-0324,openai/gpt-4o-mini,google/gemma-3-1b-it",
        env="TELEGRAM_MODELS"
    )
    TELEGRAM_RATE_LIMIT: int = Field(default=20, env="TELEGRAM_RATE_LIMIT")
    TELEGRAM_MAX_HISTORY: int = Field(default=10, env="TELEGRAM_MAX_HISTORY")
    TELEGRAM_COMMANDS: str = Field(default="start,help,status,translate,model,models", env="TELEGRAM_COMMANDS")
    TELEGRAM_ADMIN_USERS: str = Field(default="", env="TELEGRAM_ADMIN_USERS")
    TELEGRAM_WEBHOOK_URL: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")
    
    # Internal Configuration
    INTERNAL_DEFAULT_MODEL: str = Field(default="openai/gpt-5-chat", env="INTERNAL_DEFAULT_MODEL")
    INTERNAL_MODELS: str = Field(..., env="INTERNAL_MODELS")
    INTERNAL_RATE_LIMIT: int = Field(default=60, env="INTERNAL_RATE_LIMIT")
    INTERNAL_MAX_HISTORY: int = Field(default=30, env="INTERNAL_MAX_HISTORY")
    INTERNAL_API_KEY: str = Field(..., env="INTERNAL_API_KEY")
    INTERNAL_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="INTERNAL_WEBHOOK_SECRET")
    INTERNAL_ADMIN_USERS: str = Field(default="", env="INTERNAL_ADMIN_USERS")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="logs/bot_service.log", env="LOG_FILE")
    
    # Features
    ENABLE_IMAGE_PROCESSING: bool = Field(default=True, env="ENABLE_IMAGE_PROCESSING")
    MAX_IMAGE_SIZE_MB: int = Field(default=20, env="MAX_IMAGE_SIZE_MB")
    
    # Database (Optional)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # API Server
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8001, env="API_PORT")
    ENABLE_API_DOCS: bool = Field(default=True, env="ENABLE_API_DOCS")
    CORS_ORIGINS: str = Field(default="*", env="CORS_ORIGINS")
    
    @validator("TELEGRAM_BOT_TOKEN")
    def validate_telegram_token(cls, v):
        """Validate Telegram bot token format"""
        if not v or v == "your_telegram_bot_token_here":
            raise ValueError("TELEGRAM_BOT_TOKEN must be set to a valid token")
        if ":" not in v:
            raise ValueError("Invalid Telegram bot token format")
        return v
    
    @validator("INTERNAL_API_KEY")
    def validate_api_key(cls, v):
        """Validate API key strength"""
        if not v or v == "your_secure_random_api_key_here":
            raise ValueError("INTERNAL_API_KEY must be set to a secure key")
        if len(v) < 32:
            raise ValueError("INTERNAL_API_KEY must be at least 32 characters")
        return v
    
    @validator("LOG_FILE")
    def create_log_directory(cls, v):
        """Ensure log directory exists"""
        log_path = Path(v)
        log_path.parent.mkdir(parents=True, exist_ok=True)
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
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings