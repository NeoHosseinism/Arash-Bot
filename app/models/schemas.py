"""
Pydantic models for request/response schemas with OpenAPI examples
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from app.core.constants import MessageType, Platform


class MessageAttachment(BaseModel):
    """Message attachment model"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "image",
                    "url": "https://example.com/image.jpg",
                    "file_id": "file_12345",
                    "mime_type": "image/jpeg",
                    "file_size": 102400
                }
            ]
        }
    )

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
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "user_12345",
                    "text": "سلام، چطور می‌تونم مدل رو عوض کنم؟",
                    "chat_id": "chat_67890"
                },
                {
                    "user_id": "telegram_987654",
                    "text": "What is the weather like today?"
                }
            ]
        }
    )

    user_id: str = Field(..., description="Unique user identifier", examples=["user_12345", "telegram_987654"])
    text: str = Field(..., description="Message text content", examples=["سلام!", "Hello, how can I help?"])
    chat_id: Optional[str] = Field(None, description="Chat ID for continuing conversation (auto-generated if not provided)", examples=["chat_67890", None])


class BotResponse(BaseModel):
    """
    Bot response model for chat endpoint.

    Use chat_id to continue conversations. Each API key can only access
    conversations started with that specific API key.
    """
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "response": "برای تغییر مدل، از دستور /model استفاده کنید. مدل‌های موجود: Gemini Flash، DeepSeek v3، GPT-5",
                    "chat_id": "chat_67890",
                    "model": "Gemini 2.0 Flash",
                    "message_count": 3
                },
                {
                    "success": False,
                    "error": "rate_limit_exceeded",
                    "response": "⚠️ محدودیت سرعت. لطفاً قبل از ارسال پیام بعدی کمی صبر کنید.\n\nمحدودیت: 20 پیام در دقیقه"
                }
            ]
        }
    )

    success: bool = Field(..., examples=[True, False])
    response: Optional[str] = Field(None, examples=["سلام! چطور می‌تونم کمکتون کنم؟"])
    chat_id: Optional[str] = Field(None, examples=["chat_67890"])
    model: Optional[str] = Field(None, examples=["Gemini 2.0 Flash", "DeepSeek v3", "GPT-5 Chat"])
    message_count: Optional[int] = Field(None, examples=[1, 5, 10])
    error: Optional[str] = Field(None, examples=["rate_limit_exceeded", "ai_service_unavailable"])


class PlatformConfigResponse(BaseModel):
    """Platform configuration response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "private",
                    "available_models": ["Gemini 2.0 Flash", "GPT-5 Chat", "DeepSeek v3"],
                    "rate_limit": 60,
                    "commands": ["start", "help", "model", "models", "clear", "status"],
                    "max_history": 30,
                    "features": {"model_switching": True, "requires_auth": True}
                }
            ]
        }
    )

    type: str = Field(..., examples=["public", "private"])
    model: Optional[str] = Field(None, examples=["Gemini 2.0 Flash"])
    available_models: Optional[List[str]] = Field(None, examples=[["Gemini 2.0 Flash", "GPT-5 Chat", "DeepSeek v3"]])
    rate_limit: int = Field(..., examples=[20, 60])
    commands: List[str] = Field(..., examples=[["start", "help", "model", "clear"]])
    max_history: int = Field(..., examples=[10, 30])
    features: Dict[str, bool] = Field(..., examples=[{"model_switching": True, "requires_auth": True}])


class SessionStatusResponse(BaseModel):
    """Session status response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "chat_id": "chat_67890",
                    "platform": "Internal-BI",
                    "platform_type": "private",
                    "current_model": "Gemini 2.0 Flash",
                    "message_count": 5,
                    "history_length": 10,
                    "last_activity": "2025-01-15T14:30:00",
                    "uptime_seconds": 3600.5,
                    "rate_limit": 60,
                    "is_admin": False
                }
            ]
        }
    )

    chat_id: str = Field(..., examples=["chat_67890"])
    platform: str = Field(..., examples=["telegram", "Internal-BI"])
    platform_type: str = Field(..., examples=["public", "private"])
    current_model: str = Field(..., examples=["Gemini 2.0 Flash"])
    message_count: int = Field(..., examples=[5])
    history_length: int = Field(..., examples=[10])
    last_activity: datetime
    uptime_seconds: float = Field(..., examples=[3600.5])
    rate_limit: int = Field(..., examples=[60])
    is_admin: bool = Field(..., examples=[False])


class SessionListResponse(BaseModel):
    """Session list response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total": 2,
                    "authenticated": True,
                    "sessions": [
                        {
                            "chat_id": "chat_67890",
                            "platform": "Internal-BI",
                            "message_count": 5,
                            "last_activity": "2025-01-15T14:30:00"
                        }
                    ]
                }
            ]
        }
    )

    total: int = Field(..., examples=[2])
    authenticated: bool = Field(..., examples=[True, False])
    sessions: List[Dict[str, Any]]


class StatsResponse(BaseModel):
    """Statistics response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "total_sessions": 150,
                    "active_sessions": 25,
                    "telegram": {
                        "sessions": 10,
                        "model": "Gemini 2.0 Flash"
                    },
                    "internal": {
                        "sessions": 15,
                        "teams": 5
                    },
                    "uptime_seconds": 86400.0
                }
            ]
        }
    )

    total_sessions: int = Field(..., examples=[150])
    active_sessions: int = Field(..., examples=[25])
    telegram: Dict[str, Any]
    internal: Dict[str, Any]
    uptime_seconds: float = Field(..., examples=[86400.0])


class HealthCheckResponse(BaseModel):
    """Health check response"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "service": "Arash External API Service",
                    "version": "1.1.0",
                    "status": "healthy",
                    "platforms": {
                        "telegram": {
                            "type": "public",
                            "model": "Gemini 2.0 Flash",
                            "rate_limit": 20
                        },
                        "internal": {
                            "type": "private",
                            "models": ["Gemini 2.0 Flash", "GPT-5 Chat", "DeepSeek v3"],
                            "rate_limit": 60
                        }
                    },
                    "active_sessions": 25,
                    "timestamp": "2025-01-15T14:30:00"
                }
            ]
        }
    )

    service: str = Field(..., examples=["Arash External API Service"])
    version: str = Field(..., examples=["1.1.0"])
    status: str = Field(..., examples=["healthy", "degraded"])
    platforms: Dict[str, Dict[str, Any]]
    active_sessions: int = Field(..., examples=[25])
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response model"""
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": False,
                    "error": "Authentication required",
                    "detail": "No valid API key provided",
                    "timestamp": "2025-01-15T14:30:00"
                },
                {
                    "success": False,
                    "error": "Invalid API key",
                    "detail": "The provided API key is invalid or has been revoked",
                    "timestamp": "2025-01-15T14:30:00"
                }
            ]
        }
    )

    success: bool = Field(False, examples=[False])
    error: str = Field(..., examples=["Authentication required", "Invalid API key", "Team not found"])
    detail: Optional[str] = Field(None, examples=["No valid API key provided"])
    timestamp: datetime = Field(default_factory=datetime.utcnow)