"""
Session Management Tests

Tests for:
- Session creation and management
- Team isolation at session level
- Session key generation
- Session history management
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.session import ChatSession
from app.services.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """Create fresh session manager for each test"""
    # Mock the database to avoid needing a real database in tests
    with patch("app.services.session_manager.get_db_session") as mock_db:
        mock_db.return_value = MagicMock()
        mock_db.return_value.query.return_value.filter.return_value.scalar.return_value = 0
        mock_db.return_value.query.return_value.filter.return_value.all.return_value = []
        yield SessionManager()


class TestSessionCreation:
    """Test session creation"""

    def test_create_session_with_team_id(self, session_manager):
        """Test creating session with team_id"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        assert session is not None
        assert session.platform == "internal"
        assert session.user_id == "user1"
        assert session.team_id == 100
        assert session.api_key_id == 1
        assert session.api_key_prefix == "sk_test_"

    def test_create_session_without_team_id(self, session_manager):
        """Test creating session without team_id (Telegram bot)"""
        session = session_manager.get_or_create_session(
            platform="telegram",
            user_id="tg_user1",
            team_id=None,
            api_key_id=None,
            api_key_prefix=None,
        )

        assert session is not None
        assert session.platform == "telegram"
        assert session.team_id is None
        assert session.api_key_id is None


class TestSessionKeyGeneration:
    """Test session key generation for team isolation"""

    def test_session_key_format_with_team(self, session_manager):
        """Test session key format includes team_id"""
        key = session_manager.get_session_key(
            platform="internal", user_id="user123", team_id=100
        )

        assert key == "internal:100:user123"

    def test_session_key_format_without_team(self, session_manager):
        """Test session key format without team_id"""
        key = session_manager.get_session_key(
            platform="telegram", user_id="user123", team_id=None
        )

        assert key == "telegram:user123"

    def test_session_key_collision_prevention(self, session_manager):
        """Test that different teams with same user_id get different keys"""
        key_team_1 = session_manager.get_session_key("internal", "user123", team_id=1)
        key_team_2 = session_manager.get_session_key("internal", "user123", team_id=2)

        assert key_team_1 != key_team_2
        assert key_team_1 == "internal:1:user123"
        assert key_team_2 == "internal:2:user123"


class TestSessionIsolation:
    """Test team isolation at session level"""

    def test_different_teams_cannot_share_sessions(self, session_manager):
        """Test that sessions are isolated by team_id"""
        # Team 1 creates session for user123
        session_team_1 = session_manager.get_or_create_session(
            platform="internal",
            user_id="user123",
            team_id=1,
            api_key_id=10,
            api_key_prefix="sk_team1_",
        )

        # Team 2 creates session for same user123
        session_team_2 = session_manager.get_or_create_session(
            platform="internal",
            user_id="user123",
            team_id=2,
            api_key_id=20,
            api_key_prefix="sk_team2_",
        )

        # Sessions must be different
        assert session_team_1.session_id != session_team_2.session_id
        assert session_team_1.team_id == 1
        assert session_team_2.team_id == 2
        assert session_team_1.api_key_id == 10
        assert session_team_2.api_key_id == 20

    def test_get_sessions_by_team(self, session_manager):
        """Test filtering sessions by team_id"""
        # Create sessions for team 100
        session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_t100_",
        )

        session_manager.get_or_create_session(
            platform="internal",
            user_id="user2",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_t100_",
        )

        # Create session for team 200
        session_manager.get_or_create_session(
            platform="internal",
            user_id="user3",
            team_id=200,
            api_key_id=2,
            api_key_prefix="sk_t200_",
        )

        # Get sessions for team 100
        team_100_sessions = session_manager.get_sessions_by_team(100)
        assert len(team_100_sessions) == 2
        for session in team_100_sessions:
            assert session.team_id == 100

        # Get sessions for team 200
        team_200_sessions = session_manager.get_sessions_by_team(200)
        assert len(team_200_sessions) == 1
        assert team_200_sessions[0].team_id == 200


class TestSessionRetrieval:
    """Test session retrieval"""

    def test_get_existing_session(self, session_manager):
        """Test retrieving existing session"""
        # Create session
        session1 = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Retrieve same session (same user, platform, team)
        session2 = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Should be the same session
        assert session1.session_id == session2.session_id

    def test_get_session_by_id(self, session_manager):
        """Test getting session by session_id"""
        # Create session
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Retrieve by session_id
        retrieved = session_manager.get_session_by_id(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_nonexistent_session(self, session_manager):
        """Test getting session that doesn't exist"""
        retrieved = session_manager.get_session_by_id("nonexistent_session_id")
        assert retrieved is None


class TestSessionDeletion:
    """Test session deletion"""

    def test_delete_session_with_team_id(self, session_manager):
        """Test deleting session with team_id"""
        # Create session
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Delete session
        success = session_manager.delete_session(
            platform="internal", user_id="user1", team_id=100
        )

        assert success is True

        # Verify deleted
        retrieved = session_manager.get_session_by_id(session.session_id)
        assert retrieved is None

    def test_delete_session_without_team_id(self, session_manager):
        """Test deleting session without team_id (Telegram)"""
        # Create session
        session_manager.get_or_create_session(
            platform="telegram",
            user_id="tg_user",
            team_id=None,
            api_key_id=None,
            api_key_prefix=None,
        )

        # Delete session
        success = session_manager.delete_session(
            platform="telegram", user_id="tg_user", team_id=None
        )

        assert success is True


class TestSessionHistory:
    """Test session history management"""

    def test_add_message_to_history(self, session_manager):
        """Test adding messages to session history"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Add user message
        session.add_message("user", "Hello")
        assert len(session.history) == 1
        assert session.history[0]["role"] == "user"
        assert session.history[0]["content"] == "Hello"

        # Add assistant message
        session.add_message("assistant", "Hi there!")
        assert len(session.history) == 2
        assert session.history[1]["role"] == "assistant"
        assert session.history[1]["content"] == "Hi there!"

    def test_history_max_limit(self, session_manager):
        """Test that history respects max_history limit"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Add more messages than max_history
        for i in range(10):
            session.add_message("user", f"Message {i}")

        # History should be limited when retrieving recent history
        max_history = 5
        history = session.get_recent_history(max_messages=max_history)
        assert len(history) <= max_history

    def test_clear_history(self, session_manager):
        """Test clearing session history"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Add messages
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi")
        assert len(session.history) == 2

        # Clear history
        session.clear_history()
        assert len(session.history) == 0


class TestSessionExpiration:
    """Test session expiration"""

    def test_session_is_not_expired(self, session_manager):
        """Test that recent session is not expired"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Recent session should not be expired
        assert session.is_expired(timeout_minutes=30) is False

    def test_session_is_expired(self, session_manager):
        """Test that old session is expired"""
        session = session_manager.get_or_create_session(
            platform="internal",
            user_id="user1",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        # Manually set last_activity to 2 hours ago
        session.last_activity = datetime.utcnow() - timedelta(hours=2)

        # Should be expired with 30 min timeout
        assert session.is_expired(timeout_minutes=30) is True


class TestChatSession:
    """Test ChatSession model"""

    def test_session_model_creation(self):
        """Test creating ChatSession model"""
        session = ChatSession(
            session_id="test_123",
            platform="internal",
            platform_config={"type": "private", "model": "gpt-4"},
            user_id="user1",
            current_model="gpt-4",
            team_id=100,
            api_key_id=1,
            api_key_prefix="sk_test_",
        )

        assert session.session_id == "test_123"
        assert session.platform == "internal"
        assert session.team_id == 100
        assert session.api_key_id == 1

    def test_session_model_without_team(self):
        """Test ChatSession without team (Telegram bot)"""
        session = ChatSession(
            session_id="tg_123",
            platform="telegram",
            platform_config={"type": "private", "model": "gemini-2.0-flash"},
            user_id="tg_user",
            current_model="gemini-2.0-flash",
            team_id=None,
            api_key_id=None,
            api_key_prefix=None,
        )

        assert session.platform == "telegram"
        assert session.team_id is None
        assert session.api_key_id is None

    def test_session_get_uptime_seconds(self):
        """Test getting session uptime in seconds"""
        import time

        session = ChatSession(
            session_id="uptime_test",
            platform="internal",
            platform_config={"type": "private", "model": "gpt-4"},
            user_id="user1",
            current_model="gpt-4",
        )

        # Wait a small amount
        time.sleep(0.1)

        uptime = session.get_uptime_seconds()
        assert uptime >= 0.1
        assert uptime < 1.0  # Should be less than 1 second


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
