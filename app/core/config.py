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
    ENVIRONMENT: str = "dev"  # dev, stage, prod - Controls database selection and optimizations
    AI_SERVICE_URL: str
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
    TELEGRAM_COMMANDS: str = "start,help,status,clear,model,models"
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

    # Logging Configuration (per environment - application behavior)
    LOG_LEVEL_DEV: str = "DEBUG"
    LOG_LEVEL_STAGE: str = "INFO"
    LOG_LEVEL_PROD: str = "WARNING"
    LOG_FILE: str = "logs/arash_api_service.log"

    # Features Configuration
    ENABLE_IMAGE_PROCESSING: bool = True
    MAX_IMAGE_SIZE_MB: int = 20

    # API Docs - controlled by ENVIRONMENT (application behavior)
    ENABLE_API_DOCS_DEV: bool = True
    ENABLE_API_DOCS_STAGE: bool = True
    ENABLE_API_DOCS_PROD: bool = False

    # Database Configuration (Generic - set by DevOps per deployment)
    # DevOps sets these in K8s ConfigMap/Secret for each environment
    # Each deployment only has the credentials it needs (security)
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "arash_user"
    DB_PASSWORD: str = "change_me_in_production"
    DB_NAME: str = "arash_db"

    # Redis Configuration (Generic - set by DevOps per deployment)
    REDIS_URL: Optional[str] = None

    # CORS Configuration (per environment - application behavior)
    CORS_ORIGINS_DEV: str = "*"
    CORS_ORIGINS_STAGE: str = "*"
    CORS_ORIGINS_PROD: str = "https://arash-api.irisaprime.ir"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 3000  # Changed from 8001 to 3000 for K8s

    # Telegram Bot Integration
    RUN_TELEGRAM_BOT: bool = True
    
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
    def cors_origins(self) -> str:
        """Get CORS origins based on ENVIRONMENT"""
        env_map = {
            "dev": self.CORS_ORIGINS_DEV,
            "development": self.CORS_ORIGINS_DEV,
            "stage": self.CORS_ORIGINS_STAGE,
            "staging": self.CORS_ORIGINS_STAGE,
            "prod": self.CORS_ORIGINS_PROD,
            "production": self.CORS_ORIGINS_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.CORS_ORIGINS_DEV)

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list"""
        origins = self.cors_origins
        if origins == "*":
            return ["*"]
        return [origin.strip() for origin in origins.split(",") if origin.strip()]
    
    @property
    def max_image_size_bytes(self) -> int:
        """Get max image size in bytes"""
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024
    
    @property
    def database_url(self) -> str:
        """Build async database URL for SQLAlchemy from generic parameters"""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def sync_database_url(self) -> str:
        """Build synchronous database URL for Alembic migrations from generic parameters"""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def log_level(self) -> str:
        """Get log level based on ENVIRONMENT"""
        env_map = {
            "dev": self.LOG_LEVEL_DEV,
            "development": self.LOG_LEVEL_DEV,
            "stage": self.LOG_LEVEL_STAGE,
            "staging": self.LOG_LEVEL_STAGE,
            "prod": self.LOG_LEVEL_PROD,
            "production": self.LOG_LEVEL_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.LOG_LEVEL_DEV)

    @property
    def enable_api_docs(self) -> bool:
        """Get API docs enabled status based on ENVIRONMENT"""
        env_map = {
            "dev": self.ENABLE_API_DOCS_DEV,
            "development": self.ENABLE_API_DOCS_DEV,
            "stage": self.ENABLE_API_DOCS_STAGE,
            "staging": self.ENABLE_API_DOCS_STAGE,
            "prod": self.ENABLE_API_DOCS_PROD,
            "production": self.ENABLE_API_DOCS_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.ENABLE_API_DOCS_DEV)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT.lower() in ("prod", "production")

    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT.lower() in ("dev", "development")

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.ENVIRONMENT.lower() in ("stage", "staging")

    @property
    def enable_debug_features(self) -> bool:
        """Enable debug features in development"""
        return self.is_development


# Global settings instance
# This will raise validation errors if required fields are missing from .env
settings = Settings()   # type: ignore[call-arg]


def get_settings() -> Settings:
    """Get settings instance (for dependency injection)"""
    return settings