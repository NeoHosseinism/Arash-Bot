"""
Pydantic models for request/response schemas
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.core.constants import MessageType, Platform


class MessageAttachment(BaseModel):
    """Message attachment model"""
    type: MessageType
    url: Optional[str] = None
    file_id: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    data: Optional[str] = None  # Base64 encoded data

    @field_validator("data")
    @classmethod
    def validate_base64(cls, v):
        """Validate base64 data format"""
        if v and not v.replace("+", "").replace("/", "").replace("=", "").isalnum():
            raise ValueError("Invalid base64 data")
        return v


class IncomingMessage(BaseModel):
    """
    Simplified incoming message for chat endpoint.

    Changes from previous version:
    - Removed platform (auto-detected from API key's team.platform_name)
    - Removed message_id (auto-generated internally)
    - Removed type (text-only in this version)
    - Removed attachments (text-only in this version)
    - Removed metadata (not needed)
    - Made chat_id optional (auto-generated if not provided for new conversations)
    """
    user_id: str = Field(..., description="Unique user identifier")
    text: str = Field(..., description="Message text content")
    chat_id: Optional[str] = Field(None, description="Chat ID for continuing conversation (auto-generated if not provided)")


class BotResponse(BaseModel):
    """
    Bot response model for chat endpoint.

    Includes chat_id so clients can continue conversation.
    """
    success: bool
    response: Optional[str] = None
    chat_id: Optional[str] = None  # Chat ID for continuing conversation
    session_id: Optional[str] = None  # Internal session ID (platform:team:chat)
    model: Optional[str] = None  # AI model used
    message_count: Optional[int] = None  # Total messages in session
    error: Optional[str] = None


class PlatformConfigResponse(BaseModel):
    """Platform configuration response"""
    type: str
    model: Optional[str] = None
    available_models: Optional[List[str]] = None
    rate_limit: int
    commands: List[str]
    max_history: int
    features: Dict[str, bool]


class SessionStatusResponse(BaseModel):
    """Session status response"""
    session_id: str
    platform: str
    platform_type: str
    current_model: str
    message_count: int
    history_length: int
    last_activity: datetime
    uptime_seconds: float
    rate_limit: int
    is_admin: bool


class SessionListResponse(BaseModel):
    """Session list response"""
    total: int
    authenticated: bool
    sessions: List[Dict[str, Any]]


class StatsResponse(BaseModel):
    """Statistics response"""
    total_sessions: int
    active_sessions: int
    telegram: Dict[str, Any]
    internal: Dict[str, Any]
    uptime_seconds: float


class HealthCheckResponse(BaseModel):
    """Health check response"""
    service: str
    version: str
    status: str
    platforms: Dict[str, Dict[str, Any]]
    active_sessions: int
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)