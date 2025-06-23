import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        'systems': {
            'laptop': {
                'hostname': 'localhost',
                'type': 'arch',
                'sudo_method': 'password',
                'updates': ['system_packages', 'rust', 'node']
            },
            'server': {
                'hostname': 'server.example.com',
                'type': 'debian',
                'ssh': {
                    'user': 'admin',
                    'key_file': '~/.ssh/id_rsa'
                },
                'sudo_method': 'nopasswd',
                'updates': ['system_packages', 'rust']
            }
        },
        'update_settings': {
            'parallel': False,
            'timeout': 3600,
            'log_level': 'INFO',
            'sudo_password_env': 'UPDATE_SUDO_PASS'
        }
    }


@pytest.fixture
def sample_config_yaml():
    """Sample YAML configuration content"""
    return """
systems:
  laptop:
    hostname: localhost
    type: arch
    sudo_method: password
    updates:
      - system_packages
      - rust
      - node
  
  server:
    hostname: server.example.com
    type: debian
    ssh:
      user: admin
      key_file: ~/.ssh/id_rsa
    sudo_method: nopasswd
    updates:
      - system_packages
      - rust

update_settings:
  parallel: false
  timeout: 3600
  log_level: INFO
  sudo_password_env: UPDATE_SUDO_PASS
"""


@pytest.fixture
def temp_config_file(sample_config_yaml):
    """Create a temporary config file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(sample_config_yaml)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.log_system_start = Mock()
    logger.log_system_complete = Mock()
    logger.log_command_start = Mock()
    logger.log_command_complete = Mock()
    logger.log_update_type_start = Mock()
    logger.log_update_type_complete = Mock()
    return logger


@pytest.fixture
def mock_ssh_client():
    """Mock SSH client for testing"""
    client = Mock()
    client.connect = Mock()
    client.exec_command = Mock()
    client.invoke_shell = Mock()
    client.close = Mock()
    client.get_transport = Mock()
    return client


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing"""
    result = Mock()
    result.returncode = 0
    result.stdout = "mock output"
    result.stderr = ""
    return result


@pytest.fixture
def arch_system_config():
    """Configuration for Arch system testing"""
    return {
        'hostname': 'localhost',
        'type': 'arch',
        'sudo_method': 'password',
        'updates': ['system_packages', 'rust', 'node']
    }


@pytest.fixture
def debian_system_config():
    """Configuration for Debian system testing"""
    return {
        'hostname': 'server.example.com',
        'type': 'debian',
        'ssh': {
            'user': 'admin',
            'key_file': '~/.ssh/id_rsa'
        },
        'sudo_method': 'nopasswd',
        'updates': ['system_packages', 'rust']
    }


@pytest.fixture
def mock_pexpect_spawn():
    """Mock pexpect.spawn for testing"""
    spawn = Mock()
    spawn.expect = Mock(return_value=1)  # EOF
    spawn.sendline = Mock()
    spawn.before = b"mock output"
    spawn.after = b""
    spawn.exitstatus = 0
    spawn.close = Mock()
    return spawn


@pytest.fixture
def sample_command_results():
    """Sample command execution results"""
    return [
        {
            'command': 'rustup update',
            'exit_code': 0,
            'stdout': 'info: syncing channel updates\ninfo: checking for self-update',
            'stderr': '',
            'duration': 1.5,
            'success': True
        },
        {
            'command': 'cargo install-update -a',
            'exit_code': 0,
            'stdout': 'No packages need updating.',
            'stderr': '',
            'duration': 2.3,
            'success': True
        }
    ]


@pytest.fixture
def sample_update_results():
    """Sample system update results"""
    return {
        'rust': {
            'status': 'success',
            'commands': [
                {
                    'command': 'rustup update',
                    'exit_code': 0,
                    'stdout': 'Updated successfully',
                    'stderr': '',
                    'duration': 1.5,
                    'success': True
                }
            ],
            'success': True
        },
        'node': {
            'status': 'success', 
            'commands': [
                {
                    'command': 'npm update -g',
                    'exit_code': 0,
                    'stdout': 'Updated 3 packages',
                    'stderr': '',
                    'duration': 5.2,
                    'success': True
                }
            ],
            'success': True
        }
    }


@pytest.fixture
def mock_os_environ(monkeypatch):
    """Mock os.environ for testing"""
    env = {'HOME': '/home/testuser'}
    
    def mock_get(key, default=None):
        return env.get(key, default)
    
    monkeypatch.setattr(os.environ, 'get', mock_get)
    return env


@pytest.fixture
def temp_ssh_key():
    """Create a temporary SSH key file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("-----BEGIN OPENSSH PRIVATE KEY-----\ntest_key_content\n-----END OPENSSH PRIVATE KEY-----")
        key_path = f.name
    
    yield key_path
    
    # Cleanup
    if os.path.exists(key_path):
        os.unlink(key_path)