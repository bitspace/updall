from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import os


class BaseSystem(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.hostname = config['hostname']
        self.update_types = config['updates']
        self.ssh_config = config.get('ssh')
        self.sudo_method = config.get('sudo_method', 'password')
        self.sudo_password = None
        
        if self.sudo_method == 'password':
            env_var = config.get('sudo_password_env', 'UPDATE_SUDO_PASS')
            self.sudo_password = os.environ.get(env_var)
    
    @abstractmethod
    def get_package_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Return list of (command, options) tuples"""
        pass
    
    def get_rust_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Rust toolchain updates (user-level, no sudo needed)"""
        return [
            ("rustup update", {"needs_sudo": False}),
            ("cargo install-update -a", {"needs_sudo": False})
        ]
    
    def get_node_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Node.js global package updates (user-level, no sudo)"""
        return [
            ("npm update -g", {"needs_sudo": False})
        ]
    
    def get_sdkman_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """SDKman updates (user-level, no sudo needed)"""
        return [
            ("sdk selfupdate", {"needs_sudo": False}),
            ("sdk update", {"needs_sudo": False}),
            ("sdk upgrade", {"needs_sudo": False})
        ]
    
    def get_gcloud_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Google Cloud SDK updates (user-level, no sudo needed)"""
        return [
            ("gcloud components update", {"needs_sudo": False})
        ]
    
    def wrap_with_sudo(self, command: str) -> str:
        """Wrap command with sudo based on configuration"""
        if self.sudo_method == 'nopasswd':
            return f"sudo {command}"
        elif self.sudo_method == 'password' and self.sudo_password:
            return f"echo '{self.sudo_password}' | sudo -S {command}"
        else:
            return f"sudo {command}"
    
    def prepare_command(self, command: str, needs_sudo: bool, 
                       handles_sudo_internally: bool = False) -> str:
        """
        Prepare command with appropriate sudo handling
        
        Args:
            command: Base command to run
            needs_sudo: Whether command needs elevated privileges
            handles_sudo_internally: Whether command handles sudo itself (like paru)
        """
        if not needs_sudo or handles_sudo_internally:
            return command
        return self.wrap_with_sudo(command)
    
    def get_commands_for_update_type(self, update_type: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Get commands for a specific update type"""
        method_map = {
            'system_packages': self.get_package_update_commands,
            'rust': self.get_rust_update_commands,
            'node': self.get_node_update_commands,
            'sdkman': self.get_sdkman_update_commands,
            'gcloud': self.get_gcloud_update_commands
        }
        
        if update_type not in method_map:
            raise ValueError(f"Unknown update type: {update_type}")
        
        return method_map[update_type]()
    
    def run_updates(self) -> Dict[str, Any]:
        """Run updates for this system - to be implemented by concrete classes"""
        results = {}
        for update_type in self.update_types:
            results[update_type] = {"status": "pending"}
        return results