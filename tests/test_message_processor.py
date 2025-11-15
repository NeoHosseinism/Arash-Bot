"""
Tests for Message Processor service
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.models.schemas import BotResponse, IncomingMessage
from app.models.session import ChatSession
from app.services.message_processor import MessageProcessor, message_processor


@pytest.fixture
def mock_session():
    """Mock chat session"""
    session = Mock(spec=ChatSession)
    session.session_id = "test_session_123"
    session.platform = "test-platform"
    session.current_model = "test-model"
    session.current_model_friendly = "Test Model"  # Add friendly name
    session.message_count = 5
    session.history = []
    session.platform_config = {"rate_limit": 60, "max_history": 10}
    session.get_recent_history = Mock(return_value=[])

    # Team isolation fields
    session.team_id = 1
    session.api_key_id = 1
    session.api_key_prefix = "ak_test"
    session.user_id = "user123"

    # Make add_message increment count like the real implementation
    def add_message_side_effect(role, content):
        session.message_count += 1

    session.add_message = Mock(side_effect=add_message_side_effect)
    session.update_activity = Mock()
    return session


@pytest.fixture
def processor():
    """Create message processor instance"""
    return MessageProcessor()


class TestProcessMessageSimple:
    """Tests for process_message_simple method"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_message_success(
        self, mock_db, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test successful simple message processing"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        # Mock DB query for message_count reload
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 7  # 5 initial + 2 new
        mock_db.return_value.query.return_value = mock_query

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Test response"

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            assert result.success is True
            assert result.response == "Test response"
            assert result.model == "Test Model"  # Friendly name
            # message_count reloaded from DB
            assert result.message_count == 7

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_message_permission_denied(
        self, mock_db, mock_session_mgr, processor
    ):
        """Test permission denied when API key doesn't own user's conversation"""
        mock_session_mgr.get_or_create_session.side_effect = PermissionError(
            "Access denied"
        )

        result = await processor.process_message_simple(
            platform_name="Internal-BI",
            team_id=1,
            api_key_id=1,
            api_key_prefix="ak_test",
            user_id="user123",
            text="Hello",
        )

        assert result.success is False
        assert result.error == "access_denied"
        assert "دسترسی رد شد" in result.response

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_message_rate_limit(
        self, mock_db, mock_tracker, mock_session_mgr, processor, mock_session
    ):
        """Test rate limit exceeded"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = False

        result = await processor.process_message_simple(
            platform_name="Internal-BI",
            team_id=1,
            api_key_id=1,
            api_key_prefix="ak_test",
            user_id="user123",
            text="Hello",
        )

        assert result.success is False
        assert result.error == "rate_limit_exceeded"
        assert "محدودیت سرعت" in result.response

        mock_tracker.log_usage.assert_called_once()
        call_kwargs = mock_tracker.log_usage.call_args.kwargs
        assert call_kwargs["success"] is False
        assert call_kwargs["error_message"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_command(
        self, mock_db, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test command processing"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = True

        with patch.object(
            processor, "_handle_command", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Command response"

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="/help",
            )

            assert result.success is True
            assert result.response == "Command response"
            mock_handle.assert_called_once_with(mock_session, "/help")

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_message_with_exception(
        self, mock_db, mock_tracker, mock_session_mgr, processor, mock_session
    ):
        """Test exception handling during message processing"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.side_effect = Exception("Test error")

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            assert result.success is False
            assert result.error == "processing_error"
            assert "خطایی در پردازش" in result.response

            mock_tracker.log_usage.assert_called_once()
            call_kwargs = mock_tracker.log_usage.call_args.kwargs
            assert call_kwargs["success"] is False
            assert "Test error" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_logs_success(
        self, mock_db, mock_tracker, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test that successful requests are logged for authenticated teams"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Response"

            await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            mock_tracker.log_usage.assert_called_once()
            call_kwargs = mock_tracker.log_usage.call_args.kwargs
            assert call_kwargs["success"] is True
            assert call_kwargs["team_id"] == 1
            assert call_kwargs["api_key_id"] == 1

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_process_simple_no_logging_without_team(
        self, mock_db, mock_tracker, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test that Telegram (no team) requests are not logged"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Response"

            await processor.process_message_simple(
                platform_name="telegram",
                team_id=None,
                api_key_id=None,
                api_key_prefix=None,
                user_id="user123",
                text="Hello",
            )

            mock_tracker.log_usage.assert_not_called()


class TestHandleChatSimple:
    """Tests for _handle_chat_simple method"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    @patch("app.services.message_processor.ai_client")
    async def test_handle_chat_simple_success(
        self, mock_ai_client, mock_platform_mgr, processor, mock_session
    ):
        """Test successful chat handling"""
        mock_platform_mgr.get_max_history.return_value = 10
        mock_ai_client.send_chat_request = AsyncMock(
            return_value={"Response": "AI response", "SessionId": "session123"}
        )

        mock_db = Mock()
        result = await processor._handle_chat_simple(mock_session, "Hello AI", mock_db)

        assert result == "AI response"
        mock_session.add_message.assert_any_call("user", "Hello AI")
        mock_session.add_message.assert_any_call("assistant", "AI response")

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    @patch("app.services.message_processor.ai_client")
    async def test_handle_chat_simple_ai_service_error(
        self, mock_ai_client, mock_platform_mgr, processor, mock_session
    ):
        """Test AI service error handling"""
        mock_platform_mgr.get_max_history.return_value = 10
        mock_ai_client.send_chat_request = AsyncMock(
            side_effect=Exception("AI service down")
        )

        mock_db = Mock()
        result = await processor._handle_chat_simple(mock_session, "Hello", mock_db)

        assert "سرویس هوش مصنوعی" in result
        assert "در دسترس نیست" in result

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    @patch("app.services.message_processor.ai_client")
    async def test_handle_chat_simple_trims_history(
        self, mock_ai_client, mock_platform_mgr, processor, mock_session
    ):
        """Test that history is trimmed when it exceeds max"""
        mock_platform_mgr.get_max_history.return_value = 5
        mock_ai_client.send_chat_request = AsyncMock(
            return_value={"Response": "AI response"}
        )

        mock_session.history = ["msg"] * 20

        mock_db = Mock()
        await processor._handle_chat_simple(mock_session, "Hello", mock_db)

        assert len(mock_session.history) == 10

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    async def test_handle_chat_simple_general_exception(
        self, mock_platform_mgr, processor, mock_session
    ):
        """Test general exception handling"""
        mock_platform_mgr.get_max_history.side_effect = Exception("Unexpected error")

        mock_db = Mock()
        result = await processor._handle_chat_simple(mock_session, "Hello", mock_db)

        assert "خطایی در پردازش" in result


class TestHandleCommand:
    """Tests for _handle_command method"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.command_processor")
    async def test_handle_command(self, mock_cmd_proc, processor, mock_session):
        """Test command handling delegates to command processor"""
        mock_cmd_proc.process_command = AsyncMock(return_value="Command result")

        result = await processor._handle_command(mock_session, "/help")

        assert result == "Command result"
        mock_cmd_proc.process_command.assert_called_once_with(mock_session, "/help")


class TestDatabasePersistence:
    """Tests for database message persistence in _handle_chat_simple"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    @patch("app.services.message_processor.ai_client")
    @patch("app.models.database.Message")
    async def test_handle_chat_simple_persists_to_db(
        self, mock_message_class, mock_ai_client, mock_platform_mgr, processor, mock_session
    ):
        """Test that messages are persisted to database successfully"""
        mock_platform_mgr.get_max_history.return_value = 10
        mock_ai_client.send_chat_request = AsyncMock(
            return_value={"Response": "AI response"}
        )

        # Mock database session
        mock_db = Mock()
        mock_db.add = Mock()
        mock_db.commit = Mock()

        # Mock Message class
        mock_user_msg = Mock()
        mock_assistant_msg = Mock()
        mock_message_class.side_effect = [mock_user_msg, mock_assistant_msg]

        result = await processor._handle_chat_simple(mock_session, "Test message", mock_db)

        assert result == "AI response"

        # Verify messages were added to DB
        assert mock_db.add.call_count == 2
        mock_db.add.assert_any_call(mock_user_msg)
        mock_db.add.assert_any_call(mock_assistant_msg)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.message_processor.platform_manager")
    @patch("app.services.message_processor.ai_client")
    @patch("app.models.database.Message")
    async def test_handle_chat_simple_db_error_continues(
        self, mock_message_class, mock_ai_client, mock_platform_mgr, processor, mock_session
    ):
        """Test that DB errors don't break the flow - in-memory history intact"""
        mock_platform_mgr.get_max_history.return_value = 10
        mock_ai_client.send_chat_request = AsyncMock(
            return_value={"Response": "AI response"}
        )

        # Mock database session that fails on commit
        mock_db = Mock()
        mock_db.commit.side_effect = Exception("Database connection lost")
        mock_db.rollback = Mock()

        result = await processor._handle_chat_simple(mock_session, "Test message", mock_db)

        # Should still return AI response even though DB failed
        assert result == "AI response"

        # Verify rollback was called
        mock_db.rollback.assert_called_once()

        # In-memory history should still be updated
        mock_session.add_message.assert_any_call("user", "Test message")
        mock_session.add_message.assert_any_call("assistant", "AI response")


class TestErrorLoggingEdgeCases:
    """Tests for error logging edge cases in process_message_simple"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_error_logging_when_session_retrieval_fails(
        self, mock_db, mock_tracker, mock_session_mgr, processor
    ):
        """Test error logging when session retrieval fails during error handling"""
        # First call succeeds, but throws exception later
        mock_session_mgr.get_or_create_session.side_effect = Exception("Fatal error")

        result = await processor.process_message_simple(
            platform_name="Internal-BI",
            team_id=1,
            api_key_id=1,
            api_key_prefix="ak_test",
            user_id="user123",
            text="Hello",
        )

        assert result.success is False
        assert result.error == "processing_error"

        # Should still attempt to log (even though it may fail internally)
        # The error handler has a try-except that catches session retrieval failures

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.UsageTracker")
    @patch("app.services.message_processor.get_db_session")
    async def test_error_logging_handles_session_not_found(
        self, mock_db, mock_tracker, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test error logging when session can't be found during error recovery"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        # Simulate error during message processing
        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.side_effect = Exception("Processing failed")

            # When trying to get session for logging, return None
            mock_session_mgr.get_session.return_value = None

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            assert result.success is False

            # Should still log with "unknown" model
            mock_tracker.log_usage.assert_called_once()
            call_kwargs = mock_tracker.log_usage.call_args.kwargs
            assert call_kwargs["model_used"] == "unknown"
            assert call_kwargs["session_id"] == "unknown"


class TestProcessMessageSimpleEdgeCases:
    """Additional edge case tests for process_message_simple"""

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.get_db_session")
    async def test_message_count_reload_from_db(
        self, mock_db, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test that message_count is correctly reloaded from database"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        # Mock DB query to return specific message count
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 42  # Specific count
        mock_db.return_value.query.return_value = mock_query

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Response"

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            # Verify message_count was reloaded from DB
            assert result.message_count == 42

    @pytest.mark.asyncio
    @patch("app.services.message_processor.session_manager")
    @patch("app.services.message_processor.command_processor")
    @patch("app.services.message_processor.get_db_session")
    async def test_message_count_defaults_to_zero_if_none(
        self, mock_db, mock_cmd_proc, mock_session_mgr, processor, mock_session
    ):
        """Test that message_count defaults to 0 if DB returns None"""
        mock_session_mgr.get_or_create_session.return_value = mock_session
        mock_session_mgr.check_rate_limit.return_value = True
        mock_cmd_proc.is_command.return_value = False

        # Mock DB query to return None
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = None  # No messages yet
        mock_db.return_value.query.return_value = mock_query

        with patch.object(
            processor, "_handle_chat_simple", new_callable=AsyncMock
        ) as mock_handle:
            mock_handle.return_value = "Response"

            result = await processor.process_message_simple(
                platform_name="Internal-BI",
                team_id=1,
                api_key_id=1,
                api_key_prefix="ak_test",
                user_id="user123",
                text="Hello",
            )

            # Should default to 0
            assert result.message_count == 0


class TestGlobalInstance:
    """Tests for global message_processor instance"""

    def test_global_instance_exists(self):
        """Test that global instance is created"""
        assert message_processor is not None
        assert isinstance(message_processor, MessageProcessor)
