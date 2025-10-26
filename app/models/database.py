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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import OperationalError, ProgrammingError

logger = logging.getLogger(__name__)

Base = declarative_base()


class AccessLevel(str, Enum):
    """Access levels for API keys"""

    ADMIN = "admin"  # Full access, can manage teams and keys
    TEAM_LEAD = "team_lead"  # Can manage team members and view usage
    USER = "user"  # Basic access, can only use the service


class Team(Base):
    """Team model for organizing users and tracking usage"""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    monthly_quota = Column(Integer, nullable=True)  # Requests per month, None = unlimited
    daily_quota = Column(Integer, nullable=True)  # Requests per day, None = unlimited
    is_active = Column(Boolean, default=True, nullable=False)
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
    access_level = Column(String(50), nullable=False, default=AccessLevel.USER.value)

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
        Initialize database connection.

        Args:
            database_url: Database connection string. If None, reads from environment.
        """
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "sqlite:///./arash_api.db")

        logger.info(f"Initializing database connection: {database_url.split('@')[-1] if '@' in database_url else database_url}")

        # Configure engine based on database type
        engine_args = {}
        if database_url.startswith("sqlite"):
            engine_args["connect_args"] = {"check_same_thread": False}
        elif database_url.startswith("postgresql"):
            # PostgreSQL-specific settings for better performance
            engine_args["pool_size"] = 10
            engine_args["max_overflow"] = 20
            engine_args["pool_pre_ping"] = True  # Verify connections before using them
            engine_args["pool_recycle"] = 3600  # Recycle connections after 1 hour

        try:
            self.engine = create_engine(database_url, **engine_args)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self.database_url = database_url
            logger.info("Database engine created successfully")
        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
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
        Create all database tables if they don't exist.
        Handles scenarios where tables may already exist.

        Args:
            force: If True, drop and recreate all tables (use with caution!)
        """
        try:
            if force:
                logger.warning("Dropping all existing tables (force=True)")
                Base.metadata.drop_all(bind=self.engine)

            # Check which tables already exist
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()

            if existing_tables:
                logger.info(f"Found existing tables: {', '.join(existing_tables)}")
            else:
                logger.info("No existing tables found, creating new schema")

            # Create all tables (will skip existing ones)
            Base.metadata.create_all(bind=self.engine)

            # Verify tables were created
            new_tables = inspect(self.engine).get_table_names()
            created_tables = set(new_tables) - set(existing_tables)

            if created_tables:
                logger.info(f"Created new tables: {', '.join(created_tables)}")
            else:
                logger.info("All tables already exist")

            logger.info("Database schema ready")

        except OperationalError as e:
            logger.error(f"Operational error creating tables: {e}")
            raise
        except ProgrammingError as e:
            logger.error(f"Programming error creating tables: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating tables: {e}")
            raise

    def test_connection(self) -> bool:
        """
        Test if database connection is working.

        Returns:
            True if connection works, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
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
    Get or create the global database instance.

    Args:
        database_url: Database connection string. If None, reads from environment.

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(database_url)
        # Test connection
        if _db_instance.test_connection():
            # Create tables if they don't exist
            _db_instance.create_tables()
        else:
            logger.error("Database connection failed - API key management will not be available")
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
