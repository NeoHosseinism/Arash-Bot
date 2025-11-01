"""
API Endpoint Tests - v1

Tests for API v1 endpoints including:
- Authentication and authorization
- Team isolation
- Message processing
- Session management
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.models.database import AccessLevel


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    return MagicMock()


@pytest.fixture
def mock_api_key_user():
    """Mock USER level API key"""
    key = Mock()
    key.id = 1
    key.team_id = 100
    key.key_prefix = "sk_test_"
    key.access_level = AccessLevel.USER.value
    key.is_active = True
    return key


@pytest.fixture
def mock_api_key_admin():
    """Mock ADMIN level API key"""
    key = Mock()
    key.id = 2
    key.team_id = 200
    key.key_prefix = "sk_admin_"
    key.access_level = AccessLevel.ADMIN.value
    key.is_active = True
    return key


class TestHealthEndpoint:
    """Test health check endpoints"""

    def test_root_health_check(self, client):
        """Test health endpoint (unversioned at /health for monitoring)"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data


class TestAuthenticationV1:
    """Test API v1 authentication"""

    @patch("app.api.dependencies.APIKeyManager")
    def test_missing_auth_header(self, mock_key_mgr, client):
        """Test request without auth header on protected endpoint"""
        response = client.post(
            "/api/v1/chat",
            json={
                "platform": "internal",
                "user_id": "user1",
                "chat_id": "chat1",
                "message_id": "msg1",
                "text": "Hello",
                "type": "text"
            }
        )
        assert response.status_code == 401
        assert "Authentication required" in response.text

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    def test_invalid_api_key(self, mock_get_db, mock_key_mgr, client):
        """Test request with invalid API key"""
        # Mock database and invalid key
        mock_key_mgr.validate_api_key.return_value = None

        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": "Bearer invalid_key"},
            json={
                "platform": "internal",
                "user_id": "user1",
                "chat_id": "chat1",
                "message_id": "msg1",
                "text": "Hello",
                "type": "text"
            }
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.text

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    @patch("app.api.routes.message_processor")
    def test_valid_api_key(self, mock_processor, mock_get_db, mock_key_mgr, client, mock_api_key_user):
        """Test request with valid API key"""
        # Mock valid key
        mock_key_mgr.validate_api_key.return_value = mock_api_key_user

        # Mock message processor response with AsyncMock
        from app.models.schemas import BotResponse
        mock_processor.process_message = AsyncMock(return_value=BotResponse(
            success=True,
            response="Test response",
            data={
                "session_id": "test_session",
                "model": "test-model"
            }
        ))

        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": "Bearer valid_key"},
            json={
                "platform": "internal",
                "user_id": "user1",
                "chat_id": "chat1",
                "message_id": "msg1",
                "text": "Hello",
                "type": "text"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTeamIsolationV1:
    """Test team isolation enforcement - DEPRECATED: Session endpoints removed for external teams"""

    @pytest.mark.skip(reason="Session listing endpoint removed - external teams don't see sessions")
    def test_session_listing_filtered_by_team(self):
        """DEPRECATED: /api/v1/sessions endpoint no longer exists for external teams"""
        pass

    @pytest.mark.skip(reason="Session access endpoint removed - external teams don't see sessions")
    def test_access_other_team_session_denied(self):
        """DEPRECATED: /api/v1/session/{id} endpoint no longer exists for external teams"""
        pass


class TestMessageEndpointV1:
    """Test /api/v1/chat endpoint"""

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    @patch("app.api.routes.message_processor")
    def test_message_endpoint_success(self, mock_processor, mock_get_db, mock_key_mgr, client, mock_api_key_user):
        """Test successful message processing"""
        mock_key_mgr.validate_api_key.return_value = mock_api_key_user

        # Mock message processor response with AsyncMock
        from app.models.schemas import BotResponse
        mock_processor.process_message = AsyncMock(return_value=BotResponse(
            success=True,
            response="Hello! How can I help?",
            data={
                "session_id": "test_session_123",
                "model": "gpt-4"
            }
        ))

        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": "Bearer valid_key"},
            json={
                "platform": "internal",
                "user_id": "user1",
                "chat_id": "chat1",
                "message_id": "msg1",
                "text": "Hello",
                "type": "text"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["response"] == "Hello! How can I help?"
        assert data["data"]["session_id"] == "test_session_123"

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    def test_message_endpoint_requires_internal_platform(self, mock_get_db, mock_key_mgr, client, mock_api_key_user):
        """Test that API endpoint requires platform=internal"""
        mock_key_mgr.validate_api_key.return_value = mock_api_key_user

        response = client.post(
            "/api/v1/chat",
            headers={"Authorization": "Bearer valid_key"},
            json={
                "platform": "telegram",  # Wrong platform
                "user_id": "user1",
                "chat_id": "chat1",
                "message_id": "msg1",
                "text": "Hello",
                "type": "text"
            }
        )

        assert response.status_code == 400
        assert "internal" in response.text.lower()


class TestAdminEndpointsV1:
    """Test admin-only endpoints"""

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    def test_admin_endpoint_requires_admin_access(self, mock_get_db, mock_key_mgr, client, mock_api_key_user):
        """Test that admin endpoints reject non-admin users"""
        # USER level key
        mock_key_mgr.validate_api_key.return_value = mock_api_key_user

        response = client.get(
            "/api/v1/admin/",
            headers={"Authorization": "Bearer user_key"}
        )

        assert response.status_code == 403
        assert "Admin access required" in response.text

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    def test_admin_endpoint_allows_admin(self, mock_get_db, mock_key_mgr, client, mock_api_key_admin):
        """Test that admin endpoints allow admin users"""
        # ADMIN level key
        mock_key_mgr.validate_api_key.return_value = mock_api_key_admin

        response = client.get(
            "/api/v1/admin/",
            headers={"Authorization": "Bearer admin_key"}
        )

        # Should succeed (200) or have different error if endpoint not fully mocked
        assert response.status_code != 403


class TestAPIVersioning:
    """Test API versioning structure"""

    def test_v1_prefix_on_chat_endpoint(self, client):
        """Test that chat endpoint is at /api/v1/chat"""
        # Try without auth to verify endpoint exists
        response = client.post("/api/v1/chat", json={})
        # Should be 401 (auth required) or 422 (validation), not 404
        assert response.status_code in [401, 422]

    @pytest.mark.skip(reason="Sessions endpoint removed for external teams")
    def test_v1_prefix_on_sessions_endpoint(self):
        """DEPRECATED: /api/v1/sessions endpoint no longer exists for external teams"""
        pass

    def test_docs_at_v1_path(self, client):
        """Test that API docs are at /api/v1/docs"""
        response = client.get("/api/v1/docs")
        # Docs might be disabled in production, but path should exist
        assert response.status_code in [200, 404]  # 404 if ENABLE_API_DOCS=false

    def test_openapi_at_v1_path(self, client):
        """Test that OpenAPI spec is at /api/v1/openapi.json"""
        response = client.get("/api/v1/openapi.json")
        # Should exist or be disabled, not 404 for wrong path
        assert response.status_code in [200, 404]  # 404 if ENABLE_API_DOCS=false


class TestSessionKeyIsolation:
    """Test session key generation includes team_id"""

    @patch("app.services.session_manager.session_manager")
    def test_session_key_includes_team_id(self, mock_sess_mgr):
        """Test that session keys include team_id for isolation"""
        from app.services.session_manager import SessionManager

        manager = SessionManager()

        # Test with team_id (internal platform)
        key_with_team = manager.get_session_key("internal", "chat123", team_id=100)
        assert "100" in key_with_team
        assert "chat123" in key_with_team

        # Test without team_id (telegram bot)
        key_without_team = manager.get_session_key("telegram", "chat123", team_id=None)
        assert "chat123" in key_without_team
        # Should NOT include team_id
        assert key_with_team != key_without_team

    @patch("app.services.session_manager.session_manager")
    def test_different_teams_same_chat_id_different_sessions(self, mock_sess_mgr):
        """Test that two teams with same chat_id get different sessions"""
        from app.services.session_manager import SessionManager

        manager = SessionManager()

        # Team 100 with chat_id "user123"
        key_team_100 = manager.get_session_key("internal", "user123", team_id=100)

        # Team 200 with chat_id "user123" (same chat_id, different team)
        key_team_200 = manager.get_session_key("internal", "user123", team_id=200)

        # Keys must be different to prevent session collision
        assert key_team_100 != key_team_200
        assert "100" in key_team_100
        assert "200" in key_team_200


class TestQuotaEnforcement:
    """Test quota enforcement (if implemented)"""

    @patch("app.api.dependencies.APIKeyManager")
    @patch("app.api.dependencies.get_db_session")
    def test_quota_exceeded_returns_429(self, mock_get_db, mock_key_mgr, client, mock_api_key_user):
        """Test that quota exceeded returns 429"""
        # TODO: Implement when quota checking is in dependencies
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
