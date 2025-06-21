import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class UpdallLogger:
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger("updall")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        if not self.logger.handlers:
            self._setup_handlers(log_file)
    
    def _setup_handlers(self, log_file: Optional[str]):
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str):
        self.logger.info(message)
    
    def warning(self, message: str):
        self.logger.warning(message)
    
    def error(self, message: str):
        self.logger.error(message)
    
    def debug(self, message: str):
        self.logger.debug(message)
    
    def log_system_start(self, system_name: str):
        self.info(f"Starting updates for system: {system_name}")
    
    def log_system_complete(self, system_name: str, duration: float):
        self.info(f"Completed updates for system: {system_name} in {duration:.2f}s")
    
    def log_command_start(self, command: str):
        self.debug(f"Executing command: {command}")
    
    def log_command_complete(self, command: str, exit_code: int, duration: float):
        if exit_code == 0:
            self.debug(f"Command completed successfully: {command} ({duration:.2f}s)")
        else:
            self.error(f"Command failed with exit code {exit_code}: {command} ({duration:.2f}s)")
    
    def log_update_type_start(self, update_type: str):
        self.info(f"Starting {update_type} updates")
    
    def log_update_type_complete(self, update_type: str, success: bool):
        if success:
            self.info(f"Successfully completed {update_type} updates")
        else:
            self.error(f"Failed to complete {update_type} updates")


def get_logger(log_level: str = "INFO", log_file: Optional[str] = None) -> UpdallLogger:
    """Get a configured logger instance"""
    return UpdallLogger(log_level, log_file)