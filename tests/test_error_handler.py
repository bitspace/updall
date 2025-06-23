import pytest
import time
from unittest.mock import Mock, patch

from utils.error_handler import (
    ErrorHandler, UpdallError, ConfigurationError, ConnectionError,
    CommandExecutionError, PackageManagerError, handle_exception
)


class TestErrorClasses:
    """Test custom error classes"""

    def test_updall_error_inheritance(self):
        """Test that custom errors inherit from UpdallError"""
        assert issubclass(ConfigurationError, UpdallError)
        assert issubclass(ConnectionError, UpdallError)
        assert issubclass(CommandExecutionError, UpdallError)
        assert issubclass(PackageManagerError, UpdallError)

    def test_error_instantiation(self):
        """Test error instantiation with messages"""
        config_error = ConfigurationError("Config file not found")
        assert str(config_error) == "Config file not found"
        
        conn_error = ConnectionError("SSH connection failed")
        assert str(conn_error) == "SSH connection failed"


class TestErrorHandler:
    """Test ErrorHandler class functionality"""

    def test_init_with_logger(self, mock_logger):
        """Test ErrorHandler initialization with logger"""
        handler = ErrorHandler(mock_logger)
        assert handler.logger == mock_logger
        assert handler.max_retries == 3
        assert handler.retry_delay == 5

    def test_init_without_logger(self):
        """Test ErrorHandler initialization without logger"""
        handler = ErrorHandler()
        assert handler.logger is not None
        assert hasattr(handler.logger, 'info')

    def test_handle_config_error_file_not_found(self, mock_logger):
        """Test handling configuration file not found error"""
        handler = ErrorHandler(mock_logger)
        error = FileNotFoundError("Config file not found")
        
        result = handler.handle_config_error(error, "/test/config.yaml")
        
        assert result['error_type'] == 'configuration'
        assert result['recoverable'] is True
        assert any('Create config file' in suggestion for suggestion in result['suggestions'])
        mock_logger.error.assert_called_once()

    def test_handle_config_error_yaml_syntax(self, mock_logger):
        """Test handling YAML syntax error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("YAML syntax error")
        
        result = handler.handle_config_error(error, "/test/config.yaml")
        
        assert result['error_type'] == 'configuration'
        assert any('YAML syntax' in suggestion for suggestion in result['suggestions'])

    def test_handle_config_error_missing_field(self, mock_logger):
        """Test handling missing required field error"""
        handler = ErrorHandler(mock_logger)
        error = ValueError("Missing required field 'hostname'")
        
        result = handler.handle_config_error(error, "/test/config.yaml")
        
        assert result['error_type'] == 'configuration'
        assert any('required fields' in suggestion for suggestion in result['suggestions'])

    def test_handle_connection_error_name_resolution(self, mock_logger):
        """Test handling DNS name resolution error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("name resolution failed")
        
        result = handler.handle_connection_error(error, "test.example.com")
        
        assert result['error_type'] == 'connection'
        assert result['hostname'] == "test.example.com"
        assert result['error_count'] == 1
        assert any('hostname' in suggestion for suggestion in result['suggestions'])

    def test_handle_connection_error_connection_refused(self, mock_logger):
        """Test handling connection refused error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("connection refused")
        
        result = handler.handle_connection_error(error, "test.example.com")
        
        assert result['error_type'] == 'connection'
        assert any('SSH daemon' in suggestion for suggestion in result['suggestions'])

    def test_handle_connection_error_authentication(self, mock_logger):
        """Test handling SSH authentication error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("authentication failed")
        
        result = handler.handle_connection_error(error, "test.example.com")
        
        assert result['error_type'] == 'connection'
        assert any('SSH key' in suggestion for suggestion in result['suggestions'])

    def test_handle_connection_error_timeout(self, mock_logger):
        """Test handling connection timeout error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("connection timeout")
        
        result = handler.handle_connection_error(error, "test.example.com")
        
        assert result['error_type'] == 'connection'
        assert any('network connectivity' in suggestion for suggestion in result['suggestions'])

    def test_handle_connection_error_counter(self, mock_logger):
        """Test connection error counter increment"""
        handler = ErrorHandler(mock_logger)
        hostname = "test.example.com"
        
        # First error
        result1 = handler.handle_connection_error(Exception("error 1"), hostname)
        assert result1['error_count'] == 1
        assert result1['recoverable'] is True
        
        # Second error
        result2 = handler.handle_connection_error(Exception("error 2"), hostname)
        assert result2['error_count'] == 2
        assert result2['recoverable'] is True
        
        # Third error - should still be recoverable
        result3 = handler.handle_connection_error(Exception("error 3"), hostname)
        assert result3['error_count'] == 3
        assert result3['recoverable'] is False

    def test_handle_command_error_command_not_found(self, mock_logger):
        """Test handling command not found error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("rustup: command not found")
        
        result = handler.handle_command_error(error, "rustup update", "test_system")
        
        assert result['error_type'] == 'command_execution'
        assert result['command'] == "rustup update"
        assert result['system_name'] == "test_system"
        assert any('Install Rust' in suggestion for suggestion in result['suggestions'])

    def test_handle_command_error_permission_denied(self, mock_logger):
        """Test handling permission denied error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("permission denied")
        
        result = handler.handle_command_error(error, "apt update", "test_system")
        
        assert result['error_type'] == 'command_execution'
        assert any('sudo configuration' in suggestion for suggestion in result['suggestions'])

    def test_handle_command_error_package_lock(self, mock_logger):
        """Test handling package manager lock error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("package database is locked")
        
        result = handler.handle_command_error(error, "apt update", "test_system")
        
        assert result['error_type'] == 'command_execution'
        assert any('package manager' in suggestion for suggestion in result['suggestions'])

    def test_handle_command_error_network(self, mock_logger):
        """Test handling network-related command error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("network unreachable")
        
        result = handler.handle_command_error(error, "apt update", "test_system")
        
        assert result['error_type'] == 'command_execution'
        assert any('internet connectivity' in suggestion for suggestion in result['suggestions'])

    def test_handle_package_manager_error_paru_lock(self, mock_logger):
        """Test handling paru database lock error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("database lock file exists")
        
        result = handler.handle_package_manager_error(error, "paru", "test_system")
        
        assert result['error_type'] == 'package_manager'
        assert result['package_manager'] == "paru"
        assert any('db.lck' in suggestion for suggestion in result['suggestions'])

    def test_handle_package_manager_error_apt_lock(self, mock_logger):
        """Test handling apt lock error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("Could not get lock /var/lib/dpkg/lock")
        
        result = handler.handle_package_manager_error(error, "apt", "test_system")
        
        assert result['error_type'] == 'package_manager'
        assert any('apt/dpkg' in suggestion for suggestion in result['suggestions'])

    def test_handle_package_manager_error_signature(self, mock_logger):
        """Test handling package signature error"""
        handler = ErrorHandler(mock_logger)
        error = Exception("signature verification failed")
        
        result = handler.handle_package_manager_error(error, "apt", "test_system")
        
        assert result['error_type'] == 'package_manager'
        assert any('keys' in suggestion for suggestion in result['suggestions'])

    def test_get_recovery_action_connection(self, mock_logger):
        """Test getting recovery action for connection error"""
        handler = ErrorHandler(mock_logger)
        error_info = {'error_type': 'connection', 'recoverable': True}
        
        action = handler.get_recovery_action(error_info)
        assert action == "retry_connection"

    def test_get_recovery_action_command(self, mock_logger):
        """Test getting recovery action for command error"""
        handler = ErrorHandler(mock_logger)
        error_info = {'error_type': 'command_execution', 'recoverable': True}
        
        action = handler.get_recovery_action(error_info)
        assert action == "skip_command"

    def test_get_recovery_action_package_manager_lock(self, mock_logger):
        """Test getting recovery action for package manager lock"""
        handler = ErrorHandler(mock_logger)
        error_info = {
            'error_type': 'package_manager',
            'error_message': 'database lock file exists',
            'recoverable': True
        }
        
        action = handler.get_recovery_action(error_info)
        assert action == "wait_and_retry"

    def test_get_recovery_action_not_recoverable(self, mock_logger):
        """Test getting recovery action for non-recoverable error"""
        handler = ErrorHandler(mock_logger)
        error_info = {'error_type': 'connection', 'recoverable': False}
        
        action = handler.get_recovery_action(error_info)
        assert action is None

    def test_log_error_summary_empty(self, mock_logger):
        """Test logging error summary with no errors"""
        handler = ErrorHandler(mock_logger)
        
        handler.log_error_summary([])
        
        # Should not log anything for empty error list
        mock_logger.error.assert_not_called()

    def test_log_error_summary_with_errors(self, mock_logger):
        """Test logging error summary with errors"""
        handler = ErrorHandler(mock_logger)
        errors = [
            {'error_type': 'connection'},
            {'error_type': 'connection'},
            {'error_type': 'command_execution'}
        ]
        
        handler.log_error_summary(errors)
        
        # Should log summary information
        assert mock_logger.error.call_count >= 2
        assert mock_logger.info.call_count >= 1

    def test_with_retry_decorator_success(self, mock_logger):
        """Test retry decorator with successful function"""
        handler = ErrorHandler(mock_logger)
        
        @handler.with_retry(max_retries=2, delay=0.1)
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"

    def test_with_retry_decorator_eventual_success(self, mock_logger):
        """Test retry decorator with eventual success"""
        handler = ErrorHandler(mock_logger)
        call_count = 0
        
        @handler.with_retry(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        with patch('time.sleep'):  # Speed up test
            result = eventually_successful_function()
        
        assert result == "success"
        assert call_count == 2

    def test_with_retry_decorator_all_attempts_fail(self, mock_logger):
        """Test retry decorator when all attempts fail"""
        handler = ErrorHandler(mock_logger)
        
        @handler.with_retry(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def always_failing_function():
            raise ValueError("Persistent error")
        
        with patch('time.sleep'):  # Speed up test
            with pytest.raises(ValueError, match="Persistent error"):
                always_failing_function()

    def test_with_retry_decorator_non_retryable_exception(self, mock_logger):
        """Test retry decorator with non-retryable exception"""
        handler = ErrorHandler(mock_logger)
        
        @handler.with_retry(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def function_with_different_error():
            raise TypeError("Different error type")
        
        # Should not retry TypeError, only ValueError
        with pytest.raises(TypeError, match="Different error type"):
            function_with_different_error()


class TestHandleExceptionDecorator:
    """Test the handle_exception decorator"""

    def test_handle_exception_decorator_success(self, mock_logger):
        """Test decorator with successful function"""
        @handle_exception
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"

    def test_handle_exception_decorator_with_exception(self, mock_logger):
        """Test decorator with function that raises exception"""
        with patch('utils.error_handler.logging.getLogger') as mock_get_logger:
            mock_get_logger.return_value = mock_logger
            
            @handle_exception
            def failing_function():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                failing_function()
            
            # Should log the error
            mock_logger.error.assert_called_once()
            mock_logger.debug.assert_called_once()