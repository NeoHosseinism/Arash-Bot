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

    # Logging Configuration (per environment)
    LOG_LEVEL_DEV: str = "DEBUG"
    LOG_LEVEL_STAGE: str = "INFO"
    LOG_LEVEL_PROD: str = "WARNING"
    LOG_FILE: str = "logs/arash_api_service.log"

    # Features Configuration (per environment)
    ENABLE_IMAGE_PROCESSING: bool = True
    MAX_IMAGE_SIZE_MB: int = 20

    # API Docs - can be disabled per environment
    ENABLE_API_DOCS_DEV: bool = True
    ENABLE_API_DOCS_STAGE: bool = True
    ENABLE_API_DOCS_PROD: bool = False

    # Database Configuration (Environment-based - Complete per-env configuration)
    # All database parameters can be different per environment

    # Development Environment Database
    DB_HOST_DEV: str = "localhost"
    DB_PORT_DEV: int = 5432
    DB_USER_DEV: str = "arash_user"
    DB_PASSWORD_DEV: str = "dev_password"
    DB_NAME_DEV: str = "arash_dev"

    # Staging Environment Database
    DB_HOST_STAGE: str = "localhost"
    DB_PORT_STAGE: int = 5432
    DB_USER_STAGE: str = "arash_user"
    DB_PASSWORD_STAGE: str = "stage_password"
    DB_NAME_STAGE: str = "arash_stage"

    # Production Environment Database
    DB_HOST_PROD: str = "localhost"
    DB_PORT_PROD: int = 5432
    DB_USER_PROD: str = "arash_user"
    DB_PASSWORD_PROD: str = "prod_password"
    DB_NAME_PROD: str = "arash_prod"

    # Redis Configuration (per environment)
    REDIS_URL_DEV: Optional[str] = None
    REDIS_URL_STAGE: Optional[str] = None
    REDIS_URL_PROD: Optional[str] = None

    # CORS Configuration (per environment)
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
    def db_host(self) -> str:
        """Get database host based on ENVIRONMENT"""
        env_map = {
            "dev": self.DB_HOST_DEV,
            "development": self.DB_HOST_DEV,
            "stage": self.DB_HOST_STAGE,
            "staging": self.DB_HOST_STAGE,
            "prod": self.DB_HOST_PROD,
            "production": self.DB_HOST_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.DB_HOST_DEV)

    @property
    def db_port(self) -> int:
        """Get database port based on ENVIRONMENT"""
        env_map = {
            "dev": self.DB_PORT_DEV,
            "development": self.DB_PORT_DEV,
            "stage": self.DB_PORT_STAGE,
            "staging": self.DB_PORT_STAGE,
            "prod": self.DB_PORT_PROD,
            "production": self.DB_PORT_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.DB_PORT_DEV)

    @property
    def db_user(self) -> str:
        """Get database user based on ENVIRONMENT"""
        env_map = {
            "dev": self.DB_USER_DEV,
            "development": self.DB_USER_DEV,
            "stage": self.DB_USER_STAGE,
            "staging": self.DB_USER_STAGE,
            "prod": self.DB_USER_PROD,
            "production": self.DB_USER_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.DB_USER_DEV)

    @property
    def db_password(self) -> str:
        """Get database password based on ENVIRONMENT"""
        env_map = {
            "dev": self.DB_PASSWORD_DEV,
            "development": self.DB_PASSWORD_DEV,
            "stage": self.DB_PASSWORD_STAGE,
            "staging": self.DB_PASSWORD_STAGE,
            "prod": self.DB_PASSWORD_PROD,
            "production": self.DB_PASSWORD_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.DB_PASSWORD_DEV)

    @property
    def db_name(self) -> str:
        """Get database name based on ENVIRONMENT"""
        env_map = {
            "dev": self.DB_NAME_DEV,
            "development": self.DB_NAME_DEV,
            "stage": self.DB_NAME_STAGE,
            "staging": self.DB_NAME_STAGE,
            "prod": self.DB_NAME_PROD,
            "production": self.DB_NAME_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.DB_NAME_DEV)

    @property
    def database_url(self) -> str:
        """Build async database URL for SQLAlchemy from environment-specific parameters"""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def sync_database_url(self) -> str:
        """Build synchronous database URL for Alembic migrations from environment-specific parameters"""
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> Optional[str]:
        """Get Redis URL based on ENVIRONMENT"""
        env_map = {
            "dev": self.REDIS_URL_DEV,
            "development": self.REDIS_URL_DEV,
            "stage": self.REDIS_URL_STAGE,
            "staging": self.REDIS_URL_STAGE,
            "prod": self.REDIS_URL_PROD,
            "production": self.REDIS_URL_PROD,
        }
        return env_map.get(self.ENVIRONMENT.lower(), self.REDIS_URL_DEV)

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