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
    """Incoming message from messenger platform"""
    platform: str  # Allow string for flexibility
    user_id: str
    chat_id: str
    message_id: str
    text: Optional[str] = None
    type: MessageType = MessageType.TEXT
    attachments: List[MessageAttachment] = Field(default_factory=list)
    reply_to_message_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    auth_token: Optional[str] = None  # For internal platform authentication


class BotResponse(BaseModel):
    """Bot response model"""
    success: bool
    response: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
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