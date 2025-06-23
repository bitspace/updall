import pytest
import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

from utils.logger import UpdallLogger


class TestUpdallLogger:
    """Test UpdallLogger functionality"""

    def test_init_with_file_and_console(self):
        """Test logger initialization with both file and console output"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name
        
        try:
            logger = UpdallLogger(log_file=log_file, console_output=True, log_level='INFO')
            
            assert logger.logger.level == logging.INFO
            assert len(logger.logger.handlers) == 2  # File and console handlers
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_init_console_only(self):
        """Test logger initialization with console output only"""
        logger = UpdallLogger(console_output=True, log_level='DEBUG')
        
        assert logger.logger.level == logging.DEBUG
        assert len(logger.logger.handlers) == 1  # Console handler only

    def test_init_file_only(self):
        """Test logger initialization with file output only"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name
        
        try:
            logger = UpdallLogger(log_file=log_file, console_output=False, log_level='WARNING')
            
            assert logger.logger.level == logging.WARNING
            assert len(logger.logger.handlers) == 1  # File handler only
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_init_no_output(self):
        """Test logger initialization with no output (should default to console)"""
        logger = UpdallLogger(console_output=False, log_level='ERROR')
        
        assert logger.logger.level == logging.ERROR
        assert len(logger.logger.handlers) >= 1  # Should have at least one handler

    def test_log_levels(self):
        """Test different log levels"""
        logger = UpdallLogger(console_output=True, log_level='DEBUG')
        
        # Test that all log level methods exist and are callable
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'warning')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'critical')
        
        # Mock the underlying logger to test calls
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.debug("Test debug message")
            mock_debug.assert_called_once_with("Test debug message")

    def test_log_system_start(self):
        """Test logging system start"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_system_start("test_system", "localhost")
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "test_system" in call_args
            assert "localhost" in call_args

    def test_log_system_complete(self):
        """Test logging system completion"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_system_complete("test_system", True, 150.5)
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "test_system" in call_args
            assert "2m 30s" in call_args  # Duration formatting

    def test_log_system_complete_failure(self):
        """Test logging system completion with failure"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'error') as mock_error:
            logger.log_system_complete("test_system", False, 75.0)
            mock_error.assert_called()
            call_args = mock_error.call_args[0][0]
            assert "test_system" in call_args
            assert "1m 15s" in call_args

    def test_log_update_type_start(self):
        """Test logging update type start"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_update_type_start("rust")
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "rust" in call_args.lower()

    def test_log_update_type_complete(self):
        """Test logging update type completion"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_update_type_complete("rust", True, 2, 30.5)
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "rust" in call_args.lower()
            assert "2" in call_args  # Command count
            assert "30s" in call_args  # Duration

    def test_log_update_type_complete_failure(self):
        """Test logging update type completion with failure"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.log_update_type_complete("node", False, 1, 15.2)
            mock_warning.assert_called()
            call_args = mock_warning.call_args[0][0]
            assert "node" in call_args.lower()

    def test_log_command_start(self):
        """Test logging command start"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.log_command_start("rustup update")
            mock_debug.assert_called()
            call_args = mock_debug.call_args[0][0]
            assert "rustup update" in call_args

    def test_log_command_complete_success(self):
        """Test logging command completion success"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.log_command_complete("rustup update", 0, 5.5)
            mock_debug.assert_called()
            call_args = mock_debug.call_args[0][0]
            assert "rustup update" in call_args
            assert "5s" in call_args

    def test_log_command_complete_failure(self):
        """Test logging command completion failure"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.log_command_complete("npm update -g", 1, 3.2)
            mock_warning.assert_called()
            call_args = mock_warning.call_args[0][0]
            assert "npm update -g" in call_args
            assert "exit code 1" in call_args

    def test_format_duration_seconds(self):
        """Test duration formatting for seconds"""
        logger = UpdallLogger(console_output=True)
        
        assert logger.format_duration(45.5) == "45s"
        assert logger.format_duration(1.2) == "1s"
        assert logger.format_duration(0.8) == "0s"

    def test_format_duration_minutes(self):
        """Test duration formatting for minutes"""
        logger = UpdallLogger(console_output=True)
        
        assert logger.format_duration(65.0) == "1m 5s"
        assert logger.format_duration(125.7) == "2m 5s"
        assert logger.format_duration(60.0) == "1m 0s"

    def test_format_duration_hours(self):
        """Test duration formatting for hours"""
        logger = UpdallLogger(console_output=True)
        
        assert logger.format_duration(3665.0) == "1h 1m 5s"
        assert logger.format_duration(7200.0) == "2h 0m 0s"
        assert logger.format_duration(3600.0) == "1h 0m 0s"

    def test_file_logging_actual_output(self):
        """Test that file logging actually writes to file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name
        
        try:
            logger = UpdallLogger(log_file=log_file, console_output=False, log_level='INFO')
            
            # Log some messages
            logger.info("Test info message")
            logger.warning("Test warning message")
            logger.error("Test error message")
            
            # Force flush handlers
            for handler in logger.logger.handlers:
                handler.flush()
            
            # Read the log file
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert "Test info message" in content
            assert "Test warning message" in content
            assert "Test error message" in content
            assert "INFO" in content
            assert "WARNING" in content
            assert "ERROR" in content
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_log_file_creation_in_directory(self):
        """Test log file creation in specific directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'subdir', 'test.log')
            
            # Directory doesn't exist yet
            assert not os.path.exists(os.path.dirname(log_file))
            
            logger = UpdallLogger(log_file=log_file, console_output=False)
            logger.info("Test message")
            
            # Directory should be created
            assert os.path.exists(os.path.dirname(log_file))
            assert os.path.exists(log_file)

    def test_console_formatter(self):
        """Test console output formatting"""
        logger = UpdallLogger(console_output=True, log_level='DEBUG')
        
        # Find console handler
        console_handler = None
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
                console_handler = handler
                break
        
        assert console_handler is not None
        assert console_handler.formatter is not None

    def test_file_formatter(self):
        """Test file output formatting"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            log_file = f.name
        
        try:
            logger = UpdallLogger(log_file=log_file, console_output=False)
            
            # Find file handler
            file_handler = None
            for handler in logger.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    file_handler = handler
                    break
            
            assert file_handler is not None
            assert file_handler.formatter is not None
            
        finally:
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_log_exception(self):
        """Test logging exceptions with stack trace"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'error') as mock_error:
            try:
                raise ValueError("Test exception")
            except ValueError as e:
                logger.log_exception("Test operation failed", e)
            
            mock_error.assert_called()
            # Should include both the message and exception info
            call_args = mock_error.call_args
            assert "Test operation failed" in str(call_args)

    def test_context_logging(self):
        """Test logging with context information"""
        logger = UpdallLogger(console_output=True)
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.log_with_context("System update started", {
                'system': 'laptop',
                'hostname': 'localhost',
                'update_types': ['rust', 'node']
            })
            
            mock_info.assert_called()
            call_args = mock_info.call_args[0][0]
            assert "System update started" in call_args
            assert "laptop" in call_args
            assert "localhost" in call_args

    def test_log_level_filtering(self):
        """Test that log level filtering works correctly"""
        logger = UpdallLogger(console_output=True, log_level='WARNING')
        
        with patch.object(logger.logger, 'handle') as mock_handle:
            # These should not be handled due to log level
            logger.debug("Debug message")
            logger.info("Info message")
            
            # These should be handled
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Should only have 2 calls (warning and error)
            assert mock_handle.call_count == 2

    def test_multiple_logger_instances(self):
        """Test that multiple logger instances work independently"""
        logger1 = UpdallLogger(console_output=True, log_level='INFO')
        logger2 = UpdallLogger(console_output=True, log_level='ERROR')
        
        # Should have different loggers
        assert logger1.logger != logger2.logger
        assert logger1.logger.level != logger2.logger.level

    def test_logger_name_uniqueness(self):
        """Test that logger names are unique for different instances"""
        logger1 = UpdallLogger(console_output=True)
        logger2 = UpdallLogger(console_output=True)
        
        # Logger names should be different to avoid conflicts
        assert logger1.logger.name != logger2.logger.name