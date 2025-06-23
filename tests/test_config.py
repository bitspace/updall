import pytest
import tempfile
import os
from unittest.mock import patch, mock_open

from config import ConfigParser


class TestConfigParser:
    """Test configuration parsing and validation"""

    def test_load_valid_config(self, temp_config_file, sample_config):
        """Test loading a valid configuration file"""
        parser = ConfigParser(temp_config_file)
        config = parser.load_config()
        
        assert 'systems' in config
        assert 'update_settings' in config
        assert len(config['systems']) == 2
        assert 'laptop' in config['systems']
        assert 'server' in config['systems']

    def test_config_file_not_found(self):
        """Test handling of missing config file"""
        parser = ConfigParser('/nonexistent/config.yaml')
        
        with pytest.raises(FileNotFoundError):
            parser.load_config()

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(Exception):  # YAML parsing error
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_missing_systems_section(self):
        """Test validation when systems section is missing"""
        config_content = """
update_settings:
  log_level: INFO
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="Config must contain 'systems' section"):
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_invalid_system_config(self):
        """Test validation of invalid system configuration"""
        config_content = """
systems:
  invalid_system:
    hostname: localhost
    # Missing required 'type' and 'updates' fields
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="missing required field"):
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_invalid_system_type(self):
        """Test validation of invalid system type"""
        config_content = """
systems:
  invalid_system:
    hostname: localhost
    type: invalid_type
    updates: [rust]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="invalid type"):
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_get_systems(self, temp_config_file):
        """Test getting systems configuration"""
        parser = ConfigParser(temp_config_file)
        systems = parser.get_systems()
        
        assert isinstance(systems, dict)
        assert 'laptop' in systems
        assert 'server' in systems
        assert systems['laptop']['type'] == 'arch'
        assert systems['server']['type'] == 'debian'

    def test_get_system_config(self, temp_config_file):
        """Test getting specific system configuration"""
        parser = ConfigParser(temp_config_file)
        
        laptop_config = parser.get_system_config('laptop')
        assert laptop_config['hostname'] == 'localhost'
        assert laptop_config['type'] == 'arch'

    def test_get_nonexistent_system_config(self, temp_config_file):
        """Test getting configuration for nonexistent system"""
        parser = ConfigParser(temp_config_file)
        
        with pytest.raises(ValueError, match="System 'nonexistent' not found"):
            parser.get_system_config('nonexistent')

    def test_get_update_settings(self, temp_config_file):
        """Test getting update settings"""
        parser = ConfigParser(temp_config_file)
        settings = parser.get_update_settings()
        
        assert settings['timeout'] == 3600
        assert settings['log_level'] == 'INFO'
        assert not settings['parallel']

    def test_get_update_settings_defaults(self):
        """Test getting update settings with defaults when section missing"""
        config_content = """
systems:
  laptop:
    hostname: localhost
    type: arch
    updates: [rust]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            settings = parser.get_update_settings()
            
            assert isinstance(settings, dict)
            # Should return empty dict when section missing
            assert len(settings) == 0
        finally:
            os.unlink(temp_path)

    @patch.dict(os.environ, {'UPDATE_SUDO_PASS': 'test_password'})
    def test_get_sudo_password_from_env(self, temp_config_file):
        """Test getting sudo password from environment variable"""
        parser = ConfigParser(temp_config_file)
        laptop_config = parser.get_system_config('laptop')
        
        password = parser.get_sudo_password(laptop_config)
        assert password == 'test_password'

    def test_get_sudo_password_no_env(self, temp_config_file):
        """Test getting sudo password when not in environment"""
        parser = ConfigParser(temp_config_file)
        laptop_config = parser.get_system_config('laptop')
        
        with patch.dict(os.environ, {}, clear=True):
            password = parser.get_sudo_password(laptop_config)
            assert password is None

    def test_get_sudo_password_nopasswd_method(self, temp_config_file):
        """Test getting sudo password when method is nopasswd"""
        parser = ConfigParser(temp_config_file)
        server_config = parser.get_system_config('server')
        
        password = parser.get_sudo_password(server_config)
        assert password is None

    def test_find_default_config_current_dir(self):
        """Test finding default config in current directory"""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = lambda: str(self).endswith('config.yaml')
            
            parser = ConfigParser()
            assert parser.config_path.name == 'config.yaml'

    def test_find_default_config_user_dir(self):
        """Test finding default config in user config directory"""
        with patch('pathlib.Path.exists') as mock_exists:
            def exists_side_effect():
                path_str = str(self)
                return '.config/updall/config.yaml' in path_str
            
            mock_exists.side_effect = exists_side_effect
            
            parser = ConfigParser()
            assert '.config/updall/config.yaml' in str(parser.config_path)

    def test_validation_with_non_dict_config(self):
        """Test validation when config is not a dictionary"""
        config_content = "- invalid_list_config"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="Config must be a dictionary"):
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_validation_with_non_dict_systems(self):
        """Test validation when systems is not a dictionary"""
        config_content = """
systems: invalid_string
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="'systems' must be a dictionary"):
                parser.load_config()
        finally:
            os.unlink(temp_path)

    def test_validation_with_non_list_updates(self):
        """Test validation when updates is not a list"""
        config_content = """
systems:
  test_system:
    hostname: localhost
    type: arch
    updates: invalid_string
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        try:
            parser = ConfigParser(temp_path)
            with pytest.raises(ValueError, match="updates must be a list"):
                parser.load_config()
        finally:
            os.unlink(temp_path)