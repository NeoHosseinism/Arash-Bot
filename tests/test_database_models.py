"""
Tests for Database models and database management

Tests SQLAlchemy models (Team, APIKey, UsageLog) and Database class
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.database import Base, Team, APIKey, UsageLog, Database


class TestTeamModel:
    """Tests for Team model"""

    def test_team_repr(self):
        """Test Team __repr__ method (line 58 coverage)"""
        team = Team(
            id=1,
            name="Test Team",
            platform_name="test-platform"
        )

        repr_str = repr(team)

        assert "Team" in repr_str
        assert "test-platform" in repr_str
        assert "id=1" in repr_str


class TestAPIKeyModel:
    """Tests for APIKey model"""

    def test_api_key_repr(self):
        """Test APIKey __repr__ method (line 99 coverage)"""
        api_key = APIKey(
            id=10,
            key_prefix="ak_test_",
            team_id=5
        )

        repr_str = repr(api_key)

        assert "APIKey" in repr_str
        assert "id=10" in repr_str
        assert "ak_test_" in repr_str
        assert "team_id=5" in repr_str

    def test_api_key_is_expired_no_expiry(self):
        """Test is_expired when expires_at is None (lines 104-105 coverage)"""
        api_key = APIKey(
            id=10,
            key_prefix="ak_test_",
            team_id=5,
            expires_at=None
        )

        assert api_key.is_expired is False

    def test_api_key_is_expired_future_date(self):
        """Test is_expired with future expiry date (line 106 coverage)"""
        from datetime import timedelta

        future_date = datetime.utcnow() + timedelta(days=30)
        api_key = APIKey(
            id=10,
            key_prefix="ak_test_",
            team_id=5,
            expires_at=future_date
        )

        assert api_key.is_expired is False

    def test_api_key_is_expired_past_date(self):
        """Test is_expired with past expiry date (line 106 coverage)"""
        from datetime import timedelta

        past_date = datetime.utcnow() - timedelta(days=1)
        api_key = APIKey(
            id=10,
            key_prefix="ak_test_",
            team_id=5,
            expires_at=past_date
        )

        assert api_key.is_expired is True


class TestUsageLogModel:
    """Tests for UsageLog model"""

    def test_usage_log_repr(self):
        """Test UsageLog __repr__ method (line 141 coverage)"""
        usage_log = UsageLog(
            id=100,
            api_key_id=20,
            model_used="gpt-4"
        )

        repr_str = repr(usage_log)

        assert "UsageLog" in repr_str
        assert "id=100" in repr_str
        assert "api_key_id=20" in repr_str
        assert "gpt-4" in repr_str


class TestDatabaseClass:
    """Tests for Database class"""

    @patch("app.core.config.settings")
    def test_database_init_missing_url(self, mock_settings):
        """Test Database init with missing database URL (line 166 coverage)"""
        # No database URL provided
        mock_settings.sync_database_url = None

        with pytest.raises(ValueError) as exc_info:
            Database()

        assert "Database configuration is required" in str(exc_info.value)

    def test_database_init_invalid_url_not_postgresql(self):
        """Test Database init with non-PostgreSQL URL (line 173 coverage)"""
        # SQLite URL instead of PostgreSQL
        invalid_url = "sqlite:///test.db"

        with pytest.raises(ValueError) as exc_info:
            Database(database_url=invalid_url)

        assert "PostgreSQL" in str(exc_info.value)

    @patch("app.models.database.create_engine")
    def test_database_init_engine_creation_error(self, mock_create_engine):
        """Test Database init with engine creation error (lines 195-197 coverage)"""
        # Simulate engine creation failure
        mock_create_engine.side_effect = Exception("Database connection failed")

        valid_url = "postgresql://user:pass@localhost/testdb"

        with pytest.raises(Exception) as exc_info:
            Database(database_url=valid_url)

        assert "Database connection failed" in str(exc_info.value)

    @patch("app.models.database.inspect")
    def test_table_exists_with_exception(self, mock_inspect):
        """Test table_exists with exception (lines 209-214 coverage)"""
        # Create a real SQLite database for testing
        test_url = "postgresql://test:test@localhost/test"

        with patch("app.models.database.create_engine") as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            db = Database(database_url=test_url)

            # Simulate inspection error
            mock_inspect.side_effect = Exception("Inspection failed")

            result = db.table_exists("test_table")

            assert result is False

    def test_create_tables_deprecated_warning(self):
        """Test create_tables shows deprecation warning (lines 236-237 coverage)"""
        test_url = "postgresql://test:test@localhost/test"

        with patch("app.models.database.create_engine") as mock_create:
            mock_engine = Mock()
            mock_create.return_value = mock_engine

            db = Database(database_url=test_url)

            # Call deprecated method
            with patch("app.models.database.logger") as mock_logger:
                db.create_tables()

                # Verify warning was logged
                assert mock_logger.warning.called
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "deprecated" in warning_msg

    def test_test_connection_failure(self):
        """Test test_connection when connection fails (lines 254-256 coverage)"""
        test_url = "postgresql://test:test@localhost/test"

        with patch("app.models.database.create_engine") as mock_create:
            mock_engine = Mock()

            # Simulate connection failure
            mock_engine.connect.side_effect = Exception("Connection refused")

            mock_create.return_value = mock_engine

            db = Database(database_url=test_url)

            result = db.test_connection()

            assert result is False


class TestGetDatabaseInstance:
    """Tests for get_database() global function"""

    @patch("app.models.database._db_instance", None)
    @patch("app.core.config.settings")
    @patch("app.models.database.create_engine")
    def test_get_database_connection_failure(self, mock_create, mock_settings):
        """Test get_database when connection fails (line 297 coverage)"""
        mock_settings.sync_database_url = "postgresql://test:test@localhost/test"

        mock_engine = Mock()

        # Simulate successful engine creation but failed connection test
        mock_engine.connect.side_effect = Exception("Connection failed")

        mock_create.return_value = mock_engine

        # Import here to avoid caching issues
        from app.models.database import get_database

        # Reset singleton
        import app.models.database
        app.models.database._db_instance = None

        with patch("app.models.database.logger") as mock_logger:
            db = get_database()

            # Verify error was logged
            assert mock_logger.error.called
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert any("connection failed" in str(call).lower() for call in error_calls)

            # Should still return instance even if test fails
            assert db is not None
