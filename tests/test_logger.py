"""
Tests for logging utilities
"""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.utils.logger import ColoredFormatter, StructuredLogger, get_structured_logger, setup_logging


@pytest.fixture
def mock_record():
    """Create a mock log record"""
    record = Mock(spec=logging.LogRecord)
    record.name = "test_logger"
    record.levelname = "INFO"
    record.getMessage.return_value = "Test message"
    record.created = 1234567890.123
    record.msecs = 123.456
    record.exc_info = None
    return record


class TestColoredFormatter:
    """Tests for ColoredFormatter"""

    def test_formatter_initialization(self):
        """Test formatter is initialized correctly"""
        formatter = ColoredFormatter(use_colors=False)
        assert formatter is not None
        assert formatter.use_colors is False

    def test_should_use_colors_no_color_env(self):
        """Test NO_COLOR environment variable disables colors"""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            formatter = ColoredFormatter(use_colors=True)
            assert formatter.use_colors is False

    def test_should_use_colors_explicit_false(self):
        """Test explicit false setting"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=True)
            assert formatter.use_colors is False

    def test_should_use_colors_explicit_true(self):
        """Test explicit true setting"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "true"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=True)
            assert formatter.use_colors is True

    def test_should_use_colors_docker_env(self):
        """Test colors disabled in Docker"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "auto"
            mock_settings.NO_COLOR = "0"
            with patch("os.path.exists", return_value=True):
                formatter = ColoredFormatter(use_colors=True)
                assert formatter.use_colors is False

    def test_colorize_without_colors(self):
        """Test colorization when colors are disabled"""
        formatter = ColoredFormatter(use_colors=False)
        result = formatter._colorize("test", "info")
        assert result == "test"
        assert "\033[" not in result

    def test_colorize_with_colors(self):
        """Test colorization when colors are enabled"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "true"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=True)
            result = formatter._colorize("test", "info")
            assert result != "test"
            assert "\033[" in result

    def test_format_timestamp_utc(self, mock_record):
        """Test UTC timestamp formatting"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "utc"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=False)

            result = formatter._format_timestamp_utc(mock_record)
            assert "UTC" in result
            assert "2009-02-13" in result

    def test_format_timestamp_utc_microseconds(self, mock_record):
        """Test UTC timestamp with microsecond precision"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "utc"
            mock_settings.LOG_TIMESTAMP_PRECISION = 6
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=False)

            result = formatter._format_timestamp_utc(mock_record)
            assert "UTC" in result
            assert "." in result

    def test_format_timestamp_ir(self, mock_record):
        """Test Iranian timestamp formatting"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "ir"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            formatter = ColoredFormatter(use_colors=False)

            result = formatter._format_timestamp_ir(mock_record)
            assert " IR" in result
            assert "[" in result

    def test_format_level(self):
        """Test level formatting"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            assert "[info]" in formatter._format_level("INFO")
            assert "[error]" in formatter._format_level("ERROR")
            assert "[warn]" in formatter._format_level("WARNING")
            assert "[debug]" in formatter._format_level("DEBUG")

    def test_format_context_from_name(self, mock_record):
        """Test context extraction from logger name"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            mock_record.name = "app.api.routes"
            result = formatter._format_context(mock_record)
            assert "api.routes" in result

    def test_format_context_custom(self, mock_record):
        """Test custom context attribute"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            mock_record.context = "custom.context"
            result = formatter._format_context(mock_record)
            assert "custom.context" in result

    def test_format_context_root_logger(self, mock_record):
        """Test context for root logger"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            mock_record.name = "root"
            result = formatter._format_context(mock_record)
            assert result == ""

    def test_colorize_message_error(self):
        """Test message colorization for error level"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "true"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=True)

            result = formatter._colorize_message("Error message", "ERROR")
            assert "\033[" in result

    def test_colorize_message_info_no_color(self):
        """Test message colorization for non-error levels"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_COLOR = "true"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=True)

            result = formatter._colorize_message("Info message", "INFO")
            assert result == "Info message"

    def test_format_record_no_timestamp(self, mock_record):
        """Test formatting with no timestamp"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            result = formatter.format(mock_record)
            assert "Test message" in result
            assert "[info]" in result
            assert "UTC" not in result
            assert " IR" not in result

    def test_format_record_utc_timestamp(self, mock_record):
        """Test formatting with UTC timestamp"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "utc"
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            result = formatter.format(mock_record)
            assert "UTC" in result
            assert "Test message" in result

    def test_format_record_ir_timestamp(self, mock_record):
        """Test formatting with Iranian timestamp"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "ir"
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            result = formatter.format(mock_record)
            assert " IR" in result
            assert "Test message" in result

    def test_format_record_both_timestamps(self, mock_record):
        """Test formatting with both UTC and IR timestamps"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "both"
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            result = formatter.format(mock_record)
            assert "UTC" in result
            assert " IR" in result
            assert "Test message" in result

    def test_format_record_with_exception(self, mock_record):
        """Test formatting with exception info"""
        with patch("app.utils.logger.settings") as mock_settings:
            mock_settings.LOG_TIMESTAMP = "none"
            mock_settings.LOG_COLOR = "false"
            mock_settings.NO_COLOR = "0"
            mock_settings.LOG_TIMESTAMP_PRECISION = 3
            formatter = ColoredFormatter(use_colors=False)

            try:
                raise ValueError("Test exception")
            except ValueError:
                import sys

                mock_record.exc_info = sys.exc_info()

            result = formatter.format(mock_record)
            assert "Test message" in result
            assert "ValueError" in result or "Traceback" in result


class TestStructuredLogger:
    """Tests for StructuredLogger"""

    def test_format_kvs_basic(self):
        """Test basic key-value formatting"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        result = structured._format_kvs(user_id="123", count=5)
        assert "user_id=123" in result
        assert "count=5" in result

    def test_format_kvs_with_spaces(self):
        """Test key-value formatting with values containing spaces"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        result = structured._format_kvs(message="Hello world")
        assert 'message="Hello world"' in result

    def test_format_kvs_key_normalization(self):
        """Test key normalization (snake_case)"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        result = structured._format_kvs(**{"user-id": "123", "User Name": "test"})
        assert "user_id=123" in result
        assert "user_name=test" in result

    def test_debug_no_kwargs(self):
        """Test debug logging without kwargs"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        structured.debug("Test message")
        mock_logger.debug.assert_called_once()
        args = mock_logger.debug.call_args
        assert "Test message" in args[0][0]

    def test_debug_with_kwargs(self):
        """Test debug logging with kwargs"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        structured.debug("Test message", user_id="123")
        mock_logger.debug.assert_called_once()
        args = mock_logger.debug.call_args
        assert "Test message" in args[0][0]
        assert "user_id=123" in args[0][0]

    def test_info_with_context(self):
        """Test info logging with context"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        structured.info("Test message", context="api.routes")
        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args.kwargs
        assert call_kwargs["extra"]["context"] == "api.routes"

    def test_warning(self):
        """Test warning logging"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        structured.warning("Warning message", level="high")
        mock_logger.warning.assert_called_once()
        args = mock_logger.warning.call_args
        assert "Warning message" in args[0][0]
        assert "level=high" in args[0][0]

    def test_error(self):
        """Test error logging"""
        mock_logger = Mock(spec=logging.Logger)
        structured = StructuredLogger(mock_logger)

        structured.error("Error message", error_code=500)
        mock_logger.error.assert_called_once()
        args = mock_logger.error.call_args
        assert "Error message" in args[0][0]
        assert "error_code=500" in args[0][0]


class TestSetupLogging:
    """Tests for setup_logging function"""

    @patch("app.utils.logger.logging.getLogger")
    @patch("app.utils.logger.logging.FileHandler")
    @patch("app.utils.logger.logging.StreamHandler")
    @patch("app.utils.logger.Path.mkdir")
    def test_setup_logging_creates_handlers(
        self, mock_mkdir, mock_stream_handler, mock_file_handler, mock_get_logger
    ):
        """Test that setup_logging creates console and file handlers"""
        mock_root_logger = Mock()
        mock_root_logger.handlers = []
        mock_get_logger.return_value = mock_root_logger

        setup_logging()

        mock_root_logger.addHandler.assert_called()
        assert mock_root_logger.addHandler.call_count == 2

    @patch("app.utils.logger.logging.getLogger")
    @patch("app.utils.logger.logging.FileHandler")
    @patch("app.utils.logger.logging.StreamHandler")
    @patch("app.utils.logger.Path.mkdir")
    def test_setup_logging_clears_existing_handlers(
        self, mock_mkdir, mock_stream_handler, mock_file_handler, mock_get_logger
    ):
        """Test that setup_logging clears existing handlers"""
        mock_root_logger = Mock()
        mock_handlers = MagicMock()
        mock_handlers.__iter__ = Mock(return_value=iter([Mock(), Mock()]))
        mock_root_logger.handlers = mock_handlers
        mock_get_logger.return_value = mock_root_logger

        setup_logging()

        mock_handlers.clear.assert_called_once()


class TestGetStructuredLogger:
    """Tests for get_structured_logger function"""

    def test_get_structured_logger(self):
        """Test get_structured_logger returns StructuredLogger instance"""
        logger = get_structured_logger("test_module")

        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == "test_module"
