"""
Chat session model
"""
from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ChatSession(BaseModel):
    """Chat session model"""
    session_id: str
    platform: str
    platform_config: Dict[str, Any]
    user_id: str
    chat_id: str
    current_model: str
    history: List[Dict[str, str]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    is_admin: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.history.append({
            "role": role,
            "content": content
        })
        self.message_count += 1
        self.last_activity = datetime.now()
    
    def clear_history(self):
        """Clear conversation history"""
        self.history.clear()
        self.message_count = 0
    
    def get_recent_history(self, max_messages: int) -> List[Dict[str, str]]:
        """Get recent history up to max_messages"""
        return self.history[-max_messages:] if self.history else []
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.now()
    
    def get_uptime_seconds(self) -> float:
        """Get session uptime in seconds"""
        return (datetime.now() - self.created_at).total_seconds()
    
    def is_expired(self, timeout_minutes: int) -> bool:
        """Check if session is expired"""
        from datetime import timedelta
        timeout = datetime.now() - timedelta(minutes=timeout_minutes)
        return self.last_activity < timeout