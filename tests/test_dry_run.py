import pytest
import os
from unittest.mock import Mock, patch, mock_open
import subprocess

from utils.dry_run import DryRunValidator
from utils.error_handler import UpdallError


class TestDryRunValidator:
    """Test DryRunValidator functionality"""

    def test_init_with_logger(self, mock_logger):
        """Test DryRunValidator initialization with logger"""
        validator = DryRunValidator(mock_logger)
        assert validator.logger == mock_logger
        assert validator.validation_errors == []
        assert validator.validation_warnings == []

    def test_init_without_logger(self):
        """Test DryRunValidator initialization without logger"""
        validator = DryRunValidator()
        assert validator.logger is not None
        assert hasattr(validator.logger, 'info')

    def test_validate_system_local_success(self, mock_logger, arch_system_config):
        """Test validation of local system success"""
        validator = DryRunValidator(mock_logger)
        
        with patch('os.uname') as mock_uname:
            mock_uname.return_value.nodename = 'localhost'
            result = validator.validate_system('test_laptop', arch_system_config)
        
        assert result['valid'] is True
        assert result['system_name'] == 'test_laptop'
        assert result['is_local'] is True
        assert len(result['errors']) == 0

    def test_validate_system_remote_success(self, mock_logger, debian_system_config):
        """Test validation of remote system success"""
        validator = DryRunValidator(mock_logger)
        
        with patch('socket.gethostbyname', return_value='192.168.1.100'):
            with patch('os.path.exists', return_value=True):
                result = validator.validate_system('test_server', debian_system_config)
        
        assert result['valid'] is True
        assert result['system_name'] == 'test_server'
        assert result['is_local'] is False
        assert len(result['errors']) == 0

    def test_validate_system_hostname_resolution_failure(self, mock_logger, debian_system_config):
        """Test validation when hostname resolution fails"""
        validator = DryRunValidator(mock_logger)
        
        with patch('socket.gethostbyname', side_effect=Exception("Name resolution failed")):
            result = validator.validate_system('test_server', debian_system_config)
        
        assert result['valid'] is False
        assert any('hostname resolution' in error for error in result['errors'])

    def test_validate_system_missing_ssh_key(self, mock_logger, debian_system_config):
        """Test validation when SSH key file is missing"""
        validator = DryRunValidator(mock_logger)
        
        with patch('socket.gethostbyname', return_value='192.168.1.100'):
            with patch('os.path.exists', return_value=False):
                result = validator.validate_system('test_server', debian_system_config)
        
        assert result['valid'] is False
        assert any('SSH key file' in error for error in result['errors'])

    def test_validate_system_invalid_update_type(self, mock_logger, arch_system_config):
        """Test validation with invalid update type"""
        validator = DryRunValidator(mock_logger)
        arch_system_config['updates'] = ['invalid_update_type']
        
        result = validator.validate_system('test_laptop', arch_system_config)
        
        assert result['valid'] is False
        assert any('invalid update type' in error for error in result['errors'])

    def test_check_ssh_connectivity_success(self, mock_logger):
        """Test successful SSH connectivity check"""
        validator = DryRunValidator(mock_logger)
        
        with patch('utils.dry_run.SSHConnection') as mock_ssh:
            mock_connection = Mock()
            mock_connection.connect.return_value = True
            mock_connection.execute_command.return_value = (0, "connection test", "")
            mock_ssh.return_value = mock_connection
            
            result = validator.check_ssh_connectivity('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        assert result['reachable'] is True
        assert result['ssh_working'] is True
        assert len(result['errors']) == 0

    def test_check_ssh_connectivity_connection_failure(self, mock_logger):
        """Test SSH connectivity check with connection failure"""
        validator = DryRunValidator(mock_logger)
        
        with patch('utils.dry_run.SSHConnection') as mock_ssh:
            mock_connection = Mock()
            mock_connection.connect.return_value = False
            mock_ssh.return_value = mock_connection
            
            result = validator.check_ssh_connectivity('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        assert result['reachable'] is False
        assert result['ssh_working'] is False
        assert len(result['errors']) > 0

    def test_check_ssh_connectivity_command_failure(self, mock_logger):
        """Test SSH connectivity check with command execution failure"""
        validator = DryRunValidator(mock_logger)
        
        with patch('utils.dry_run.SSHConnection') as mock_ssh:
            mock_connection = Mock()
            mock_connection.connect.return_value = True
            mock_connection.execute_command.return_value = (1, "", "Permission denied")
            mock_ssh.return_value = mock_connection
            
            result = validator.check_ssh_connectivity('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        assert result['reachable'] is True
        assert result['ssh_working'] is False
        assert any('command execution failed' in error for error in result['errors'])

    @patch('subprocess.run')
    def test_check_tool_availability_available(self, mock_run, mock_logger):
        """Test tool availability check when tool is available"""
        validator = DryRunValidator(mock_logger)
        mock_run.return_value.returncode = 0
        
        result = validator.check_tool_availability('rustup')
        
        assert result['available'] is True
        assert result['tool'] == 'rustup'
        mock_run.assert_called_once_with(['rustup', '--version'], capture_output=True, check=True)

    @patch('subprocess.run')
    def test_check_tool_availability_not_available(self, mock_run, mock_logger):
        """Test tool availability check when tool is not available"""
        validator = DryRunValidator(mock_logger)
        mock_run.side_effect = FileNotFoundError()
        
        result = validator.check_tool_availability('nonexistent-tool')
        
        assert result['available'] is False
        assert result['tool'] == 'nonexistent-tool'

    @patch('subprocess.run')
    def test_check_tool_availability_error(self, mock_run, mock_logger):
        """Test tool availability check when command returns error"""
        validator = DryRunValidator(mock_logger)
        mock_run.side_effect = subprocess.CalledProcessError(1, 'tool')
        
        result = validator.check_tool_availability('problematic-tool')
        
        assert result['available'] is False
        assert result['tool'] == 'problematic-tool'

    def test_check_sudo_configuration_nopasswd(self, mock_logger):
        """Test sudo configuration check for nopasswd method"""
        validator = DryRunValidator(mock_logger)
        system_config = {'sudo_method': 'nopasswd'}
        
        result = validator.check_sudo_configuration(system_config)
        
        assert result['method'] == 'nopasswd'
        assert result['password_required'] is False

    def test_check_sudo_configuration_password_with_env(self, mock_logger):
        """Test sudo configuration check for password method with environment variable"""
        validator = DryRunValidator(mock_logger)
        system_config = {'sudo_method': 'password', 'sudo_password_env': 'TEST_SUDO_PASS'}
        
        with patch.dict(os.environ, {'TEST_SUDO_PASS': 'test_password'}):
            result = validator.check_sudo_configuration(system_config)
        
        assert result['method'] == 'password'
        assert result['password_required'] is True
        assert result['password_available'] is True

    def test_check_sudo_configuration_password_without_env(self, mock_logger):
        """Test sudo configuration check for password method without environment variable"""
        validator = DryRunValidator(mock_logger)
        system_config = {'sudo_method': 'password', 'sudo_password_env': 'MISSING_SUDO_PASS'}
        
        with patch.dict(os.environ, {}, clear=True):
            result = validator.check_sudo_configuration(system_config)
        
        assert result['method'] == 'password'
        assert result['password_required'] is True
        assert result['password_available'] is False
        assert len(result['warnings']) > 0

    def test_validate_update_requirements_rust(self, mock_logger):
        """Test validation of Rust update requirements"""
        validator = DryRunValidator(mock_logger)
        
        with patch.object(validator, 'check_tool_availability') as mock_check:
            mock_check.side_effect = [
                {'available': True, 'tool': 'rustup'},
                {'available': True, 'tool': 'cargo'}
            ]
            
            result = validator.validate_update_requirements(['rust'])
        
        assert result['valid'] is True
        assert 'rust' in result['update_types']
        assert result['update_types']['rust']['requirements_met'] is True

    def test_validate_update_requirements_missing_tool(self, mock_logger):
        """Test validation when required tool is missing"""
        validator = DryRunValidator(mock_logger)
        
        with patch.object(validator, 'check_tool_availability') as mock_check:
            mock_check.return_value = {'available': False, 'tool': 'rustup'}
            
            result = validator.validate_update_requirements(['rust'])
        
        assert result['valid'] is False
        assert 'rust' in result['update_types']
        assert result['update_types']['rust']['requirements_met'] is False
        assert len(result['update_types']['rust']['missing_tools']) > 0

    def test_generate_summary_all_valid(self, mock_logger):
        """Test generating summary when all validations pass"""
        validator = DryRunValidator(mock_logger)
        
        systems_results = [
            {'valid': True, 'system_name': 'system1', 'errors': [], 'warnings': []},
            {'valid': True, 'system_name': 'system2', 'errors': [], 'warnings': []}
        ]
        
        summary = validator.generate_summary(systems_results)
        
        assert summary['overall_valid'] is True
        assert summary['total_systems'] == 2
        assert summary['valid_systems'] == 2
        assert summary['invalid_systems'] == 0
        assert summary['total_errors'] == 0
        assert summary['total_warnings'] == 0

    def test_generate_summary_with_errors(self, mock_logger):
        """Test generating summary when some validations fail"""
        validator = DryRunValidator(mock_logger)
        
        systems_results = [
            {'valid': True, 'system_name': 'system1', 'errors': [], 'warnings': ['warning1']},
            {'valid': False, 'system_name': 'system2', 'errors': ['error1', 'error2'], 'warnings': []}
        ]
        
        summary = validator.generate_summary(systems_results)
        
        assert summary['overall_valid'] is False
        assert summary['total_systems'] == 2
        assert summary['valid_systems'] == 1
        assert summary['invalid_systems'] == 1
        assert summary['total_errors'] == 2
        assert summary['total_warnings'] == 1

    def test_generate_recommendations_ssh_issues(self, mock_logger):
        """Test generating recommendations for SSH connectivity issues"""
        validator = DryRunValidator(mock_logger)
        
        systems_results = [
            {
                'valid': False,
                'system_name': 'remote_system',
                'errors': ['SSH connection failed', 'SSH key file not found'],
                'warnings': []
            }
        ]
        
        recommendations = validator.generate_recommendations(systems_results)
        
        assert any('SSH' in rec for rec in recommendations)
        assert any('key' in rec for rec in recommendations)

    def test_generate_recommendations_tool_missing(self, mock_logger):
        """Test generating recommendations for missing tools"""
        validator = DryRunValidator(mock_logger)
        
        systems_results = [
            {
                'valid': False,
                'system_name': 'system1',
                'errors': ['Tool rustup not available'],
                'warnings': []
            }
        ]
        
        recommendations = validator.generate_recommendations(systems_results)
        
        assert any('rustup' in rec for rec in recommendations)
        assert any('install' in rec.lower() for rec in recommendations)

    def test_validate_all_systems_success(self, mock_logger, temp_config_file):
        """Test validation of all systems when all pass"""
        validator = DryRunValidator(mock_logger)
        
        systems_config = {
            'laptop': {
                'hostname': 'localhost',
                'type': 'arch',
                'sudo_method': 'nopasswd',
                'updates': ['rust']
            }
        }
        
        with patch.object(validator, 'validate_system') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'system_name': 'laptop',
                'errors': [],
                'warnings': []
            }
            
            result = validator.validate_all_systems(systems_config)
        
        assert result['overall_valid'] is True
        assert len(result['systems']) == 1

    def test_validate_all_systems_with_failures(self, mock_logger):
        """Test validation of all systems when some fail"""
        validator = DryRunValidator(mock_logger)
        
        systems_config = {
            'laptop': {
                'hostname': 'localhost',
                'type': 'arch',
                'sudo_method': 'nopasswd',
                'updates': ['rust']
            },
            'server': {
                'hostname': 'unreachable.example.com',
                'type': 'debian',
                'ssh': {'user': 'admin', 'key_file': '~/.ssh/missing_key'},
                'sudo_method': 'password',
                'updates': ['rust']
            }
        }
        
        def mock_validate_side_effect(name, config):
            if name == 'laptop':
                return {'valid': True, 'system_name': name, 'errors': [], 'warnings': []}
            else:
                return {'valid': False, 'system_name': name, 'errors': ['SSH failed'], 'warnings': []}
        
        with patch.object(validator, 'validate_system', side_effect=mock_validate_side_effect):
            result = validator.validate_all_systems(systems_config)
        
        assert result['overall_valid'] is False
        assert len(result['systems']) == 2
        assert result['summary']['valid_systems'] == 1
        assert result['summary']['invalid_systems'] == 1