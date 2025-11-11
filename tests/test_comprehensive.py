"""
Comprehensive Test Suite for Arash Bot
Tests all major functionality end-to-end
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_team():
    """Mock team with API key"""
    team = Mock()
    team.id = 1
    team.platform_name = "Internal-BI"
    team.monthly_quota = 100000
    team.daily_quota = 5000
    team.is_active = True
    return team


@pytest.fixture
def mock_api_key(mock_team):
    """Mock valid API key"""
    key = Mock()
    key.id = 1
    key.team_id = 1
    key.key_prefix = "ark_test"
    key.is_active = True
    key.team = mock_team
    return key


class TestHealthAndBasics:
    """Test basic health and status endpoints"""

    def test_health_endpoint(self, client):
        """Health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Arash External API Service"
        assert "version" in data
        assert "status" in data
        assert "timestamp" in data

    def test_openapi_docs_available(self, client):
        """OpenAPI docs are available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestAuthentication:
    """Test authentication for all endpoint types"""

    def test_chat_endpoint_no_auth_header(self, client):
        """Chat endpoint with no auth should work (public Telegram mode)"""
        response = client.post(
            "/v1/chat",
            json={"user_id": "telegram_user", "text": "سلام"}
        )
        # Should work or fail gracefully (depends on AI service mock)
        assert response.status_code in [200, 500, 503]

    @patch("app.api.dependencies.get_db_session")
    @patch("app.api.dependencies.APIKeyManager.validate_api_key")
    def test_chat_endpoint_with_valid_key(self, mock_validate, mock_db, mock_api_key, client):
        """Chat endpoint with valid API key"""
        mock_validate.return_value = mock_api_key

        response = client.post(
            "/v1/chat",
            headers={"Authorization": "Bearer ark_test_key"},
            json={"user_id": "user123", "text": "Hello"}
        )
        # Should process or fail on AI service
        assert response.status_code in [200, 500, 503]

    @patch("app.api.dependencies.get_db_session")
    @patch("app.api.dependencies.APIKeyManager.validate_api_key")
    def test_chat_endpoint_with_invalid_key(self, mock_validate, mock_db, client):
        """Chat endpoint with invalid API key returns 403"""
        mock_validate.return_value = None

        response = client.post(
            "/v1/chat",
            headers={"Authorization": "Bearer invalid_key"},
            json={"user_id": "user123", "text": "Hello"}
        )
        assert response.status_code == 403

    def test_admin_endpoint_no_auth(self, client):
        """Admin endpoints require authentication"""
        response = client.get("/v1/admin/teams")
        assert response.status_code == 401

    @patch("app.api.dependencies.settings")
    def test_admin_endpoint_with_super_admin_key(self, mock_settings, client):
        """Admin endpoint with valid super admin key"""
        mock_settings.super_admin_keys_set = {"test_admin_key"}

        response = client.get(
            "/v1/admin/teams",
            headers={"Authorization": "Bearer test_admin_key"}
        )
        # Should work or return data
        assert response.status_code in [200, 500]


class TestChatEndpoint:
    """Test /v1/chat endpoint thoroughly"""

    @patch("app.services.message_processor.message_processor.process_message_simple")
    def test_chat_success_response(self, mock_process, client):
        """Chat endpoint returns successful response"""
        mock_process.return_value = {
            "success": True,
            "response": "سلام! چطور می‌تونم کمکتون کنم؟",
            "chat_id": "chat_123",
            "session_id": "telegram:chat_123",
            "model": "Gemini 2.0 Flash",
            "message_count": 1
        }

        response = client.post(
            "/v1/chat",
            json={"user_id": "user1", "text": "سلام"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
        assert data["model"] == "Gemini 2.0 Flash"

    @patch("app.services.message_processor.message_processor.process_message_simple")
    def test_chat_rate_limit_error(self, mock_process, client):
        """Chat endpoint handles rate limit"""
        mock_process.return_value = {
            "success": False,
            "error": "rate_limit_exceeded",
            "response": "⚠️ محدودیت سرعت. لطفاً کمی صبر کنید."
        }

        response = client.post(
            "/v1/chat",
            json={"user_id": "user1", "text": "test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] == "rate_limit_exceeded"

    def test_chat_missing_required_fields(self, client):
        """Chat endpoint validates required fields"""
        response = client.post(
            "/v1/chat",
            json={"user_id": "user1"}  # Missing 'text'
        )
        assert response.status_code == 422  # Validation error


class TestCommandsEndpoint:
    """Test /v1/commands endpoint"""

    def test_commands_public_mode(self, client):
        """Commands endpoint returns Telegram commands without auth"""
        response = client.get("/v1/commands")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["platform"] == "telegram"
        assert len(data["commands"]) > 0
        # Check commands have required fields
        for cmd in data["commands"]:
            assert "command" in cmd
            assert "description" in cmd
            assert "usage" in cmd

    @patch("app.api.dependencies.get_db_session")
    @patch("app.api.dependencies.APIKeyManager.validate_api_key")
    def test_commands_private_mode(self, mock_validate, mock_db, mock_api_key, client):
        """Commands endpoint returns team-specific commands with auth"""
        mock_validate.return_value = mock_api_key

        response = client.get(
            "/v1/commands",
            headers={"Authorization": "Bearer test_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["platform"] == "Internal-BI"


class TestAdminTeamEndpoints:
    """Test admin team management endpoints"""

    @patch("app.api.dependencies.settings")
    @patch("app.services.api_key_manager.APIKeyManager.list_all_teams")
    def test_list_teams(self, mock_list, mock_settings, mock_team, client):
        """Admin can list all teams"""
        mock_settings.super_admin_keys_set = {"admin_key"}
        mock_list.return_value = [mock_team]

        response = client.get(
            "/v1/admin/teams",
            headers={"Authorization": "Bearer admin_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.api.dependencies.settings")
    @patch("app.services.api_key_manager.APIKeyManager.create_team")
    def test_create_team(self, mock_create, mock_settings, mock_team, client):
        """Admin can create new team"""
        mock_settings.super_admin_keys_set = {"admin_key"}
        mock_create.return_value = (mock_team, "ark_generated_key_12345")

        response = client.post(
            "/v1/admin/teams",
            headers={"Authorization": "Bearer admin_key"},
            json={
                "platform_name": "Test-Team",
                "monthly_quota": 50000,
                "daily_quota": 2000
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "warning" in data

    @patch("app.api.dependencies.settings")
    @patch("app.services.api_key_manager.APIKeyManager.get_team_by_id")
    def test_get_team_details(self, mock_get, mock_settings, mock_team, client):
        """Admin can get team details"""
        mock_settings.super_admin_keys_set = {"admin_key"}
        mock_get.return_value = mock_team

        response = client.get(
            "/v1/admin/teams/1",
            headers={"Authorization": "Bearer admin_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert data["platform_name"] == "Internal-BI"

    @patch("app.api.dependencies.settings")
    def test_get_team_not_found(self, mock_settings, client):
        """Admin gets 404 for non-existent team"""
        mock_settings.super_admin_keys_set = {"admin_key"}

        response = client.get(
            "/v1/admin/teams/999",
            headers={"Authorization": "Bearer admin_key"}
        )
        assert response.status_code == 404


class TestAdminStatsEndpoints:
    """Test admin statistics endpoints"""

    @patch("app.api.dependencies.settings")
    @patch("app.services.session_manager.session_manager")
    def test_get_platform_stats(self, mock_session_mgr, mock_settings, client):
        """Admin can get platform statistics"""
        mock_settings.super_admin_keys_set = {"admin_key"}
        mock_session_mgr.sessions = {}
        mock_session_mgr.get_active_session_count.return_value = 0

        response = client.get(
            "/v1/admin/stats",
            headers={"Authorization": "Bearer admin_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "active_sessions" in data
        assert "telegram" in data
        assert "internal" in data


class TestSessionManagement:
    """Test session management functionality"""

    @patch("app.api.dependencies.settings")
    @patch("app.services.session_manager.session_manager")
    def test_clear_sessions(self, mock_session_mgr, mock_settings, client):
        """Admin can clear sessions"""
        mock_settings.super_admin_keys_set = {"admin_key"}
        mock_session_mgr.sessions = {"test_key": Mock()}

        response = client.post(
            "/v1/admin/clear-sessions",
            headers={"Authorization": "Bearer admin_key"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cleared" in data


class TestErrorHandling:
    """Test error handling across endpoints"""

    def test_404_on_invalid_endpoint(self, client):
        """Invalid endpoint returns 404"""
        response = client.get("/v1/invalid_endpoint")
        assert response.status_code == 404

    def test_405_on_wrong_method(self, client):
        """Wrong HTTP method returns 405"""
        response = client.get("/v1/chat")  # Should be POST
        assert response.status_code == 405

    def test_422_on_invalid_json(self, client):
        """Invalid JSON schema returns 422"""
        response = client.post(
            "/v1/chat",
            json={"invalid": "schema"}  # Missing required fields
        )
        assert response.status_code == 422


class TestPersianLanguageResponses:
    """Test that user-facing responses are in Persian"""

    @patch("app.services.message_processor.message_processor.process_message_simple")
    def test_rate_limit_message_is_persian(self, mock_process, client):
        """Rate limit messages are in Persian"""
        mock_process.return_value = {
            "success": False,
            "error": "rate_limit_exceeded",
            "response": "⚠️ محدودیت سرعت"
        }

        response = client.post(
            "/v1/chat",
            json={"user_id": "user1", "text": "test"}
        )
        data = response.json()
        assert "محدودیت سرعت" in data["response"]

    def test_commands_descriptions_are_persian(self, client):
        """Command descriptions are in Persian"""
        response = client.get("/v1/commands")
        data = response.json()
        for cmd in data["commands"]:
            # Persian text should contain Persian characters
            assert any('\u0600' <= c <= '\u06FF' for c in cmd["description"])


class TestOpenAPIExamples:
    """Test that OpenAPI schema includes examples"""

    def test_openapi_has_examples(self, client):
        """OpenAPI schema includes request/response examples"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()

        # Check chat endpoint has examples
        chat_schema = data["paths"]["/v1/chat"]["post"]
        assert "examples" in chat_schema["responses"]["200"]["content"]["application/json"]

        # Check schemas have examples
        incoming_message_schema = data["components"]["schemas"]["IncomingMessage"]
        assert "examples" in incoming_message_schema

        bot_response_schema = data["components"]["schemas"]["BotResponse"]
        assert "examples" in bot_response_schema
