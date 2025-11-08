"""
Database models for API key management and usage tracking.
Note: Chat history is NOT stored here - it's handled by the AI service.
This database only stores API keys, teams, and usage statistics.
"""

import os
from datetime import datetime
from enum import Enum
from typing import Optional
import logging

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

Base = declarative_base()


class AccessLevel(str, Enum):
    """
    Access levels for API keys - Two-tier system

    ADMIN: Super admins (internal team developers)
        - Full access to ALL /api/v1/admin/* endpoints
        - Can create teams, API keys, view all usage, etc.
        - These are the service owners

    TEAM: External teams (clients using the service)
        - Can ONLY access /api/v1/chat endpoint
        - Cannot access ANY admin endpoints
        - These are the clients using the chatbot service
    """

    ADMIN = "admin"  # Super admins (internal team) - full access to admin endpoints
    TEAM = "team"    # External teams (clients) - can only use chat service


class Team(Base):
    """Team model for organizing users and tracking usage"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    monthly_quota = Column(Integer, nullable=True)  # Requests per month, None = unlimited
    daily_quota = Column(Integer, nullable=True)  # Requests per day, None = unlimited
    is_active = Column(Boolean, default=True, nullable=False)

    # Webhook configuration for each team
    webhook_url = Column(String(2048), nullable=True)  # URL to send callbacks to
    webhook_secret = Column(String(255), nullable=True)  # Secret for HMAC signing
    webhook_enabled = Column(Boolean, default=False, nullable=False)  # Enable/disable webhook

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    api_keys = relationship("APIKey", back_populates="team", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team(id={self.id}, name='{self.name}')>"


class APIKey(Base):
    """API Key model for authentication and authorization"""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 hash
    key_prefix = Column(String(16), nullable=False)  # First 8 chars for identification
    name = Column(String(255), nullable=False)  # Friendly name for the key
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    access_level = Column(String(50), nullable=False, default=AccessLevel.TEAM.value)

    # Quota management
    monthly_quota = Column(Integer, nullable=True)  # Overrides team quota if set
    daily_quota = Column(Integer, nullable=True)  # Overrides team quota if set

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_by = Column(String(255), nullable=True)  # User who created this key
    description = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # None = never expires

    # Relationships
    team = relationship("Team", back_populates="api_keys")
    usage_logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<APIKey(id={self.id}, prefix='{self.key_prefix}', team_id={self.team_id})>"

    @property
    def is_expired(self) -> bool:
        """Check if the API key has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at


class UsageLog(Base):
    """Usage log for tracking API requests and resource consumption"""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    # Request details
    session_id = Column(String(64), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    model_used = Column(String(255), nullable=False)  # Friendly model name

    # Usage metrics
    request_count = Column(Integer, default=1, nullable=False)
    tokens_used = Column(Integer, nullable=True)  # If available from AI service
    estimated_cost = Column(Float, nullable=True)  # If cost tracking is implemented

    # Response metadata
    success = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    error_message = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")
    team = relationship("Team", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog(id={self.id}, api_key_id={self.api_key_id}, model='{self.model_used}')>"


# Database session management
class Database:
    """Database connection and session management with PostgreSQL support"""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection (PostgreSQL only).

        Args:
            database_url: PostgreSQL connection string. If None, builds from config settings
                         (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).

        Raises:
            ValueError: If database_url is not provided or is not PostgreSQL
        """
        if database_url is None:
            # Build URL from config settings (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
            from app.core.config import settings
            database_url = settings.sync_database_url

        if not database_url:
            raise ValueError(
                "Database configuration is required. "
                "Please set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME in environment variables."
            )

        # Validate PostgreSQL URL
        if not database_url.startswith("postgresql"):
            raise ValueError(
                f"Only PostgreSQL is supported. "
                f"DATABASE_URL must start with 'postgresql://' or 'postgresql+psycopg2://'"
            )

        # Hide password in logs
        log_url = database_url.split('@')[-1] if '@' in database_url else database_url
        logger.info(f"Initializing PostgreSQL connection: {log_url}")

        # PostgreSQL-specific settings for better performance
        engine_args = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,  # Verify connections before using them
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }

        try:
            self.engine = create_engine(database_url, **engine_args)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.database_url = database_url
            logger.info("[OK] PostgreSQL engine created successfully")
        except Exception as e:
            logger.error(f"[ERROR] Failed to create PostgreSQL engine: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            inspector = inspect(self.engine)
            return table_name in inspector.get_table_names()
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False

    def create_tables(self, force: bool = False):
        """
        DEPRECATED: Use Alembic migrations instead.

        This method is kept for backward compatibility with scripts but should not be used.
        Database schema should be managed through Alembic migrations.

        To initialize database with migrations:
            from app.core.database_init import initialize_database
            initialize_database()

        To create a new migration:
            alembic revision --autogenerate -m "description"

        To apply migrations:
            alembic upgrade head

        Args:
            force: Not used (kept for compatibility)
        """
        print("[WARNING] create_tables() is deprecated - use Alembic migrations")
        print("[INFO] Run: alembic upgrade head")
        logger.warning("create_tables() is deprecated - use Alembic migrations instead")
        logger.info("To initialize database, use: from app.core.database_init import initialize_database")

    def test_connection(self) -> bool:
        """
        Test if PostgreSQL connection is working.

        Returns:
            True if connection works, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                print("[OK] PostgreSQL connection successful")
                logger.info(f"PostgreSQL connection test successful: {version}")
            return True
        except Exception as e:
            print(f"[ERROR] PostgreSQL connection failed: {e}")
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False

    def get_session(self):
        """Get a database session (generator for dependency injection)"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_database(database_url: Optional[str] = None) -> Database:
    """
    Get or create the global PostgreSQL database instance.

    Args:
        database_url: PostgreSQL connection string. If None, builds from config settings
                     (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).

    Returns:
        Database instance

    Raises:
        ValueError: If database configuration is not set or is not PostgreSQL
    """
    global _db_instance
    if _db_instance is None:
        print("=" * 60)
        print("Initializing Database Connection")
        print("=" * 60)
        _db_instance = Database(database_url)
        # Test connection
        if _db_instance.test_connection():
            print("[OK] Database connection established")
            logger.info("Database connection established")
            # Note: Database schema is managed by Alembic migrations
            # Run migrations on startup using: from app.core.database_init import initialize_database
        else:
            print("[ERROR] Database connection failed - API key management will not be available")
            logger.error("PostgreSQL connection failed - API key management will not be available")
        print("=" * 60)
    return _db_instance


def get_db_session():
    """Dependency for getting database sessions in FastAPI"""
    db = get_database()
    return next(db.get_session())


# Future: Chat history models would go here
# Currently NOT implemented as chat history is handled by AI service
# When implementing end-to-end chat history, add models here:
#
# class ChatHistory(Base):
#     __tablename__ = "chat_history"
#     id = Column(Integer, primary_key=True)
#     session_id = Column(String(64), index=True)
#     role = Column(String(20))  # "user" or "assistant"
#     content = Column(Text)
#     timestamp = Column(DateTime, default=datetime.utcnow)
#     ...additional fields...
