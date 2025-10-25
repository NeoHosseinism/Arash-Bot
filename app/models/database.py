"""
Database models for API key management and usage tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

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
    """Database connection and session management"""

    def __init__(self, database_url: str = "sqlite:///./arash_bot.db"):
        """
        Initialize database connection.

        Args:
            database_url: Database connection string
        """
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        """Get a database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


# Global database instance
_db_instance: Optional[Database] = None


def get_database(database_url: str = "sqlite:///./arash_bot.db") -> Database:
    """
    Get or create the global database instance.

    Args:
        database_url: Database connection string

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(database_url)
        _db_instance.create_tables()
    return _db_instance


def get_db_session():
    """Dependency for getting database sessions in FastAPI"""
    db = get_database()
    return next(db.get_session())
