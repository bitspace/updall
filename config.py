import yaml
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


class ConfigParser:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = self._find_default_config()
        self.config_path = Path(config_path)
        self._config = None
    
    def _find_default_config(self) -> str:
        possible_paths = [
            "config.yaml",
            "~/.config/updall/config.yaml",
            "/etc/updall/config.yaml"
        ]
        
        for path in possible_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists():
                return str(expanded_path)
        
        return "config.yaml"
    
    def load_config(self) -> Dict[str, Any]:
        if self._config is not None:
            return self._config
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            self._config = yaml.safe_load(f)
        
        self._validate_config()
        return self._config
    
    def _validate_config(self):
        if not isinstance(self._config, dict):
            raise ValueError("Config must be a dictionary")
        
        if 'systems' not in self._config:
            raise ValueError("Config must contain 'systems' section")
        
        systems = self._config['systems']
        if not isinstance(systems, dict):
            raise ValueError("'systems' must be a dictionary")
        
        for system_name, system_config in systems.items():
            self._validate_system_config(system_name, system_config)
    
    def _validate_system_config(self, name: str, config: Dict[str, Any]):
        required_fields = ['hostname', 'type', 'updates']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"System '{name}' missing required field: {field}")
        
        if config['type'] not in ['arch', 'debian']:
            raise ValueError(f"System '{name}' has invalid type: {config['type']}")
        
        if not isinstance(config['updates'], list):
            raise ValueError(f"System '{name}' updates must be a list")
    
    def get_systems(self) -> Dict[str, Dict[str, Any]]:
        config = self.load_config()
        return config['systems']
    
    def get_system_config(self, system_name: str) -> Dict[str, Any]:
        systems = self.get_systems()
        if system_name not in systems:
            raise ValueError(f"System '{system_name}' not found in config")
        return systems[system_name]
    
    def get_update_settings(self) -> Dict[str, Any]:
        config = self.load_config()
        return config.get('update_settings', {})
    
    def get_sudo_password(self, system_config: Dict[str, Any]) -> Optional[str]:
        if system_config.get('sudo_method') != 'password':
            return None
        
        env_var = system_config.get('sudo_password_env', 'UPDATE_SUDO_PASS')
        return os.environ.get(env_var)