"""
Pytest configuration and shared fixtures
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_user_message():
    """Sample user message for testing"""
    return {
        "platform": "telegram",
        "user_id": "test_user_123",
        "chat_id": "test_chat_456",
        "message_id": "test_msg_789",
        "text": "سلام، این یک تست است",
        "type": "text"
    }


@pytest.fixture
def sample_session_data():
    """Sample session data for testing"""
    return {
        "session_id": "test_session_abc",
        "platform": "telegram",
        "user_id": "test_user_123",
        "chat_id": "test_chat_456",
        "current_model": "google/gemini-2.0-flash-001"
    }


@pytest.fixture
def mock_ai_service_response():
    """Mock AI service API response"""
    return {
        "Response": "این یک پاسخ تستی است",
        "SessionId": "test_session",
        "Model": "google/gemini-2.0-flash-001"
    }


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "ai_service: marks tests that require AI service"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers automatically based on test location
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        if "ai_service" in item.nodeid:
            item.add_marker(pytest.mark.ai_service)