"""
Session manager with rate limiting
"""
import hashlib
import time
from typing import Dict, List
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from app.models.session import ChatSession
from app.services.platform_manager import platform_manager
from app.core.config import settings
from app.core.name_mapping import get_friendly_platform_name, mask_session_id

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages chat sessions with platform-aware configuration"""
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self.rate_limits: Dict[str, List[float]] = defaultdict(list)
    
    def get_session_key(self, platform: str, chat_id: str) -> str:
        """Generate unique session key"""
        return f"{platform}:{chat_id}"
    
    def get_or_create_session(
        self,
        platform: str,
        user_id: str,
        chat_id: str,
        team_id: int | None = None,
        api_key_id: int | None = None,
        api_key_prefix: str | None = None
    ) -> ChatSession:
        """Get existing session or create new one with platform-specific config and team isolation"""
        key = self.get_session_key(platform, chat_id)

        if key not in self.sessions:
            # Get platform configuration
            config = platform_manager.get_config(platform)

            self.sessions[key] = ChatSession(
                session_id=hashlib.md5(key.encode()).hexdigest(),
                platform=platform,
                platform_config=config.dict(),
                user_id=user_id,
                chat_id=chat_id,
                current_model=config.model,
                is_admin=platform_manager.is_admin(platform, user_id),
                # Team isolation - CRITICAL for security
                team_id=team_id,
                api_key_id=api_key_id,
                api_key_prefix=api_key_prefix
            )

            friendly_platform = get_friendly_platform_name(platform)
            masked_id = mask_session_id(self.sessions[key].session_id)
            team_info = f" (team: {team_id}, key: {api_key_prefix})" if team_id else ""
            logger.info(f"Created new session for {friendly_platform} (session: {masked_id}){team_info}")
        else:
            # Update last activity
            self.sessions[key].update_activity()

        return self.sessions[key]
    
    def get_session(self, platform: str, chat_id: str) -> ChatSession:
        """Get existing session"""
        key = self.get_session_key(platform, chat_id)
        return self.sessions.get(key)
    
    def delete_session(self, platform: str, chat_id: str) -> bool:
        """Delete a session"""
        key = self.get_session_key(platform, chat_id)
        if key in self.sessions:
            del self.sessions[key]
            logger.info(f"Deleted session: {key}")
            return True
        return False
    
    def check_rate_limit(self, platform: str, user_id: str) -> bool:
        """Check if user exceeded rate limit for their platform"""
        now = time.time()
        minute_ago = now - 60
        rate_limit = platform_manager.get_rate_limit(platform)
        
        key = f"{platform}:{user_id}"
        
        # Clean old entries
        self.rate_limits[key] = [
            t for t in self.rate_limits[key] if t > minute_ago
        ]
        
        # Check limit
        if len(self.rate_limits[key]) >= rate_limit:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        # Add current request
        self.rate_limits[key].append(now)
        return True
    
    def get_rate_limit_remaining(self, platform: str, user_id: str) -> int:
        """Get remaining rate limit for user"""
        now = time.time()
        minute_ago = now - 60
        rate_limit = platform_manager.get_rate_limit(platform)
        
        key = f"{platform}:{user_id}"
        
        # Clean old entries
        self.rate_limits[key] = [
            t for t in self.rate_limits[key] if t > minute_ago
        ]
        
        return max(0, rate_limit - len(self.rate_limits[key]))
    
    def clear_old_sessions(self):
        """Clear expired sessions"""
        timeout_minutes = settings.SESSION_TIMEOUT_MINUTES
        timeout = datetime.now() - timedelta(minutes=timeout_minutes)
        
        keys_to_remove = [
            key for key, session in self.sessions.items()
            if session.last_activity < timeout
        ]
        
        for key in keys_to_remove:
            del self.sessions[key]
        
        if keys_to_remove:
            logger.info(f"Cleaned {len(keys_to_remove)} expired sessions")
        
        return len(keys_to_remove)
    
    def clear_rate_limits(self):
        """Clear old rate limit entries"""
        now = time.time()
        minute_ago = now - 60
        
        for key in list(self.rate_limits.keys()):
            self.rate_limits[key] = [
                t for t in self.rate_limits[key] if t > minute_ago
            ]
            
            # Remove empty entries
            if not self.rate_limits[key]:
                del self.rate_limits[key]
    
    def get_all_sessions(self, platform: str = None) -> List[ChatSession]:
        """Get all sessions, optionally filtered by platform"""
        if platform:
            return [
                session for session in self.sessions.values()
                if session.platform == platform
            ]
        return list(self.sessions.values())
    
    def get_session_count(self, platform: str = None) -> int:
        """Get count of sessions"""
        if platform:
            return len([s for s in self.sessions.values() if s.platform == platform])
        return len(self.sessions)
    
    def get_active_session_count(self, minutes: int = 5) -> int:
        """Get count of recently active sessions"""
        threshold = datetime.now() - timedelta(minutes=minutes)
        return len([
            s for s in self.sessions.values()
            if s.last_activity > threshold
        ])

    def get_sessions_by_team(self, team_id: int) -> List[ChatSession]:
        """Get all sessions for a specific team (for team isolation)"""
        return [
            session for session in self.sessions.values()
            if session.team_id == team_id
        ]

    def get_session_count_by_team(self, team_id: int) -> int:
        """Get count of sessions for a specific team"""
        return len(self.get_sessions_by_team(team_id))


# Global instance
session_manager = SessionManager()