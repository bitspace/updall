import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
import time


class UpdallError(Exception):
    """Base exception for updall errors"""
    pass


class ConfigurationError(UpdallError):
    """Configuration-related errors"""
    pass


class ConnectionError(UpdallError):
    """Network/SSH connection errors"""
    pass


class CommandExecutionError(UpdallError):
    """Command execution errors"""
    pass


class PackageManagerError(UpdallError):
    """Package manager specific errors"""
    pass


class ErrorHandler:
    """Centralized error handling and recovery"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_counts = {}
        self.max_retries = 3
        self.retry_delay = 5
    
    def with_retry(self, max_retries: int = None, delay: int = None, 
                   exceptions: tuple = None):
        """Decorator for automatic retry with exponential backoff"""
        if max_retries is None:
            max_retries = self.max_retries
        if delay is None:
            delay = self.retry_delay
        if exceptions is None:
            exceptions = (ConnectionError, CommandExecutionError)
        
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_retries:
                            wait_time = delay * (2 ** attempt)  # Exponential backoff
                            self.logger.warning(
                                f"Attempt {attempt + 1} failed: {e}. "
                                f"Retrying in {wait_time}s..."
                            )
                            time.sleep(wait_time)
                        else:
                            self.logger.error(
                                f"All {max_retries + 1} attempts failed. "
                                f"Final error: {e}"
                            )
                
                raise last_exception
            return wrapper
        return decorator
    
    def handle_config_error(self, error: Exception, config_path: str) -> Dict[str, Any]:
        """Handle configuration errors with helpful suggestions"""
        self.logger.error(f"Configuration error in {config_path}: {error}")
        
        suggestions = []
        error_msg = str(error).lower()
        
        if "not found" in error_msg:
            suggestions.append(f"Create config file at {config_path}")
            suggestions.append("Use --config to specify a different config file")
        elif "yaml" in error_msg or "syntax" in error_msg:
            suggestions.append("Check YAML syntax in config file")
            suggestions.append("Ensure proper indentation and no tabs")
        elif "missing" in error_msg or "required" in error_msg:
            suggestions.append("Check required fields in config file")
            suggestions.append("See config.yaml example for reference")
        
        return {
            'error_type': 'configuration',
            'error_message': str(error),
            'suggestions': suggestions,
            'recoverable': True
        }
    
    def handle_connection_error(self, error: Exception, hostname: str) -> Dict[str, Any]:
        """Handle SSH connection errors with recovery suggestions"""
        self.logger.error(f"Connection error to {hostname}: {error}")
        
        suggestions = []
        error_msg = str(error).lower()
        
        if "name resolution" in error_msg or "unknown host" in error_msg:
            suggestions.append(f"Check if hostname '{hostname}' is correct")
            suggestions.append("Verify DNS resolution or /etc/hosts entry")
        elif "connection refused" in error_msg:
            suggestions.append(f"Check if SSH daemon is running on {hostname}")
            suggestions.append("Verify SSH port (default 22) is open")
        elif "authentication" in error_msg or "permission denied" in error_msg:
            suggestions.append("Check SSH key permissions (should be 600)")
            suggestions.append("Verify SSH key is authorized on remote host")
            suggestions.append("Try ssh-copy-id to setup key authentication")
        elif "timeout" in error_msg:
            suggestions.append("Check network connectivity to host")
            suggestions.append("Increase connection timeout in config")
        
        # Increment error count for this host
        self.error_counts[hostname] = self.error_counts.get(hostname, 0) + 1
        
        return {
            'error_type': 'connection',
            'error_message': str(error),
            'hostname': hostname,
            'error_count': self.error_counts[hostname],
            'suggestions': suggestions,
            'recoverable': self.error_counts[hostname] < 3
        }
    
    def handle_command_error(self, error: Exception, command: str, 
                           system_name: str) -> Dict[str, Any]:
        """Handle command execution errors with context-aware suggestions"""
        self.logger.error(f"Command error on {system_name}: {command} - {error}")
        
        suggestions = []
        error_msg = str(error).lower()
        
        if "command not found" in error_msg or "no such file" in error_msg:
            if "rustup" in command:
                suggestions.append("Install Rust: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
            elif "npm" in command:
                suggestions.append("Install Node.js and npm")
            elif "sdk" in command:
                suggestions.append("Install SDKman: curl -s 'https://get.sdkman.io' | bash")
            elif "gcloud" in command:
                suggestions.append("Install Google Cloud SDK")
            elif "paru" in command:
                suggestions.append("Install paru AUR helper")
            else:
                suggestions.append(f"Install required tool for command: {command}")
        elif "permission denied" in error_msg:
            suggestions.append("Check sudo configuration")
            suggestions.append("Verify user has required permissions")
        elif "lock" in error_msg or "locked" in error_msg:
            suggestions.append("Another package manager instance is running")
            suggestions.append("Wait for other package operations to complete")
        elif "network" in error_msg or "download" in error_msg:
            suggestions.append("Check internet connectivity")
            suggestions.append("Verify package repository URLs")
        
        return {
            'error_type': 'command_execution',
            'error_message': str(error),
            'command': command,
            'system_name': system_name,
            'suggestions': suggestions,
            'recoverable': "command not found" not in error_msg
        }
    
    def handle_package_manager_error(self, error: Exception, package_manager: str,
                                   system_name: str) -> Dict[str, Any]:
        """Handle package manager specific errors"""
        self.logger.error(f"Package manager error ({package_manager}) on {system_name}: {error}")
        
        suggestions = []
        error_msg = str(error).lower()
        
        if package_manager == "paru":
            if "database lock" in error_msg:
                suggestions.append("Remove /var/lib/pacman/db.lck if no pacman is running")
            elif "signature" in error_msg:
                suggestions.append("Update archlinux-keyring: sudo pacman -S archlinux-keyring")
            elif "conflict" in error_msg:
                suggestions.append("Resolve package conflicts manually")
        elif package_manager == "apt":
            if "lock" in error_msg:
                suggestions.append("Wait for apt/dpkg to finish")
                suggestions.append("Remove /var/lib/dpkg/lock* if no apt is running")
            elif "signature" in error_msg:
                suggestions.append("Update package keys: sudo apt-key update")
            elif "space" in error_msg:
                suggestions.append("Free up disk space")
        
        return {
            'error_type': 'package_manager',
            'error_message': str(error),
            'package_manager': package_manager,
            'system_name': system_name,
            'suggestions': suggestions,
            'recoverable': "lock" in error_msg or "space" in error_msg
        }
    
    def get_recovery_action(self, error_info: Dict[str, Any]) -> Optional[str]:
        """Get suggested recovery action for an error"""
        if not error_info.get('recoverable', False):
            return None
        
        error_type = error_info.get('error_type')
        
        if error_type == 'connection':
            return "retry_connection"
        elif error_type == 'command_execution':
            return "skip_command"
        elif error_type == 'package_manager':
            if "lock" in error_info.get('error_message', '').lower():
                return "wait_and_retry"
            return "skip_update"
        
        return None
    
    def log_error_summary(self, errors: list):
        """Log a summary of all errors encountered"""
        if not errors:
            return
        
        self.logger.error(f"Encountered {len(errors)} error(s) during execution:")
        
        error_types = {}
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in error_types.items():
            self.logger.error(f"  {error_type}: {count} error(s)")
        
        self.logger.info("Check logs above for detailed error information and suggestions")


def handle_exception(func: Callable):
    """Decorator for comprehensive exception handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Unhandled exception in {func.__name__}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            raise
    return wrapper