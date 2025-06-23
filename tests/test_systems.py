import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from systems.base import BaseSystem
from systems.arch import ArchSystem
from systems.debian import DebianSystem


class TestBaseSystem:
    """Test BaseSystem abstract class functionality"""

    def test_init_local_system(self, arch_system_config):
        """Test initialization of local system"""
        system = ArchSystem('test_laptop', arch_system_config)
        
        assert system.name == 'test_laptop'
        assert system.hostname == 'localhost'
        assert system.is_local is True
        assert system.update_types == ['system_packages', 'rust', 'node']
        assert system.sudo_method == 'password'

    def test_init_remote_system(self, debian_system_config):
        """Test initialization of remote system"""
        system = DebianSystem('test_server', debian_system_config)
        
        assert system.name == 'test_server'
        assert system.hostname == 'server.example.com'
        assert system.is_local is False
        assert system.ssh_config is not None
        assert system.ssh_config['user'] == 'admin'

    def test_is_local_system_detection(self):
        """Test local system detection logic"""
        # Test localhost
        config = {'hostname': 'localhost', 'type': 'arch', 'updates': []}
        system = ArchSystem('test', config)
        assert system.is_local is True
        
        # Test 127.0.0.1
        config = {'hostname': '127.0.0.1', 'type': 'arch', 'updates': []}
        system = ArchSystem('test', config)
        assert system.is_local is True
        
        # Test current hostname
        with patch('os.uname') as mock_uname:
            mock_uname.return_value.nodename = 'current-host'
            config = {'hostname': 'current-host', 'type': 'arch', 'updates': []}
            system = ArchSystem('test', config)
            assert system.is_local is True
        
        # Test remote hostname
        config = {'hostname': 'remote.example.com', 'type': 'arch', 'updates': []}
        system = ArchSystem('test', config)
        assert system.is_local is False

    @patch.dict(os.environ, {'UPDATE_SUDO_PASS': 'test_password'})
    def test_sudo_password_from_env(self, arch_system_config):
        """Test sudo password loading from environment"""
        system = ArchSystem('test', arch_system_config)
        assert system.sudo_password == 'test_password'

    def test_sudo_password_not_set(self, arch_system_config):
        """Test when sudo password is not set in environment"""
        with patch.dict(os.environ, {}, clear=True):
            system = ArchSystem('test', arch_system_config)
            assert system.sudo_password is None

    def test_wrap_with_sudo_nopasswd(self, arch_system_config):
        """Test wrapping command with sudo (nopasswd method)"""
        arch_system_config['sudo_method'] = 'nopasswd'
        system = ArchSystem('test', arch_system_config)
        
        wrapped = system.wrap_with_sudo('apt update')
        assert wrapped == 'sudo apt update'

    def test_wrap_with_sudo_password(self, arch_system_config):
        """Test wrapping command with sudo (password method)"""
        system = ArchSystem('test', arch_system_config)
        system.sudo_password = 'test_password'
        
        wrapped = system.wrap_with_sudo('apt update')
        assert wrapped == "echo 'test_password' | sudo -S apt update"

    def test_prepare_command_no_sudo(self, arch_system_config):
        """Test preparing command without sudo"""
        system = ArchSystem('test', arch_system_config)
        
        cmd = system.prepare_command('rustup update', needs_sudo=False)
        assert cmd == 'rustup update'

    def test_prepare_command_with_sudo(self, arch_system_config):
        """Test preparing command with sudo"""
        arch_system_config['sudo_method'] = 'nopasswd'
        system = ArchSystem('test', arch_system_config)
        
        cmd = system.prepare_command('apt update', needs_sudo=True)
        assert cmd == 'sudo apt update'

    def test_prepare_command_handles_sudo_internally(self, arch_system_config):
        """Test preparing command that handles sudo internally"""
        system = ArchSystem('test', arch_system_config)
        
        cmd = system.prepare_command('paru -S package', needs_sudo=True, handles_sudo_internally=True)
        assert cmd == 'paru -S package'

    def test_get_commands_for_update_type_rust(self, arch_system_config):
        """Test getting commands for rust update type"""
        system = ArchSystem('test', arch_system_config)
        
        commands = system.get_commands_for_update_type('rust')
        assert len(commands) == 2
        assert commands[0][0] == 'rustup update'
        assert commands[1][0] == 'cargo install-update -a'
        assert all(not cmd[1]['needs_sudo'] for cmd in commands)

    def test_get_commands_for_update_type_invalid(self, arch_system_config):
        """Test getting commands for invalid update type"""
        system = ArchSystem('test', arch_system_config)
        
        with pytest.raises(ValueError, match="Unknown update type: invalid"):
            system.get_commands_for_update_type('invalid')

    def test_create_ssh_connection_local(self, arch_system_config):
        """Test SSH connection creation for local system"""
        system = ArchSystem('test', arch_system_config)
        
        ssh_conn = system.create_ssh_connection()
        assert ssh_conn is None

    def test_create_ssh_connection_remote(self, debian_system_config):
        """Test SSH connection creation for remote system"""
        system = DebianSystem('test', debian_system_config)
        
        with patch('systems.base.SSHConnection') as mock_ssh:
            ssh_conn = system.create_ssh_connection()
            mock_ssh.assert_called_once_with(
                hostname='server.example.com',
                username='admin',
                key_file='~/.ssh/id_rsa',
                sudo_password=None
            )


class TestArchSystem:
    """Test ArchSystem specific functionality"""

    def test_get_package_update_commands(self, arch_system_config):
        """Test getting Arch package update commands"""
        system = ArchSystem('test', arch_system_config)
        
        commands = system.get_package_update_commands()
        assert len(commands) == 2
        assert commands[0][0] == 'paru -Syu --noconfirm'
        assert commands[1][0] == 'paru -Sua --noconfirm'
        
        # Check that both commands need sudo but handle it internally
        for cmd, opts in commands:
            assert opts['needs_sudo'] is True
            assert opts['handles_sudo_internally'] is True

    def test_inheritance_from_base(self, arch_system_config):
        """Test that ArchSystem properly inherits from BaseSystem"""
        system = ArchSystem('test', arch_system_config)
        
        # Should have all base system methods
        assert hasattr(system, 'get_rust_update_commands')
        assert hasattr(system, 'get_node_update_commands')
        assert hasattr(system, 'get_sdkman_update_commands')
        assert hasattr(system, 'get_gcloud_update_commands')
        
        # Test inherited methods work
        rust_commands = system.get_rust_update_commands()
        assert len(rust_commands) > 0
        assert rust_commands[0][0] == 'rustup update'


class TestDebianSystem:
    """Test DebianSystem specific functionality"""

    def test_get_package_update_commands(self, debian_system_config):
        """Test getting Debian package update commands"""
        system = DebianSystem('test', debian_system_config)
        
        commands = system.get_package_update_commands()
        assert len(commands) == 4
        expected_commands = ['apt update', 'apt upgrade -y', 'apt autoremove -y', 'apt autoclean']
        
        for i, (cmd, opts) in enumerate(commands):
            assert cmd == expected_commands[i]
            assert opts['needs_sudo'] is True
            assert opts['handles_sudo_internally'] is False

    def test_inheritance_from_base(self, debian_system_config):
        """Test that DebianSystem properly inherits from BaseSystem"""
        system = DebianSystem('test', debian_system_config)
        
        # Should have all base system methods
        assert hasattr(system, 'get_rust_update_commands')
        assert hasattr(system, 'get_node_update_commands')
        assert hasattr(system, 'get_sdkman_update_commands')
        
        # Test inherited methods work
        node_commands = system.get_node_update_commands()
        assert len(node_commands) > 0
        assert node_commands[0][0] == 'npm update -g'


class TestBaseSystemCommandExecution:
    """Test command execution functionality in BaseSystem"""

    @patch('subprocess.run')
    def test_execute_with_subprocess_success(self, mock_run, arch_system_config):
        """Test successful subprocess execution"""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Success output"
        mock_run.return_value.stderr = ""
        
        system = ArchSystem('test', arch_system_config)
        exit_code, stdout, stderr = system._execute_with_subprocess('echo test', 60)
        
        assert exit_code == 0
        assert stdout == "Success output"
        assert stderr == ""
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_execute_with_subprocess_failure(self, mock_run, arch_system_config):
        """Test failed subprocess execution"""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "Error output"
        
        system = ArchSystem('test', arch_system_config)
        exit_code, stdout, stderr = system._execute_with_subprocess('false', 60)
        
        assert exit_code == 1
        assert stderr == "Error output"

    @patch('subprocess.run')
    def test_execute_with_subprocess_timeout(self, mock_run, arch_system_config):
        """Test subprocess execution timeout"""
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired('test', 60)
        
        system = ArchSystem('test', arch_system_config)
        exit_code, stdout, stderr = system._execute_with_subprocess('sleep 100', 60)
        
        assert exit_code == 124
        assert "timed out" in stderr

    @patch('pexpect.spawn')
    def test_execute_with_pexpect_success(self, mock_spawn, arch_system_config):
        """Test successful pexpect execution"""
        mock_child = Mock()
        mock_child.expect.return_value = 1  # EOF
        mock_child.before = b"Success output"
        mock_child.after = b""
        mock_child.exitstatus = 0
        mock_spawn.return_value = mock_child
        
        system = ArchSystem('test', arch_system_config)
        system.sudo_password = 'test_pass'
        
        exit_code, stdout, stderr = system._execute_with_pexpect('paru -S package', 60)
        
        assert exit_code == 0
        assert "Success output" in stdout

    @patch('pexpect.spawn')
    def test_execute_with_pexpect_sudo_prompt(self, mock_spawn, arch_system_config):
        """Test pexpect execution with sudo prompt"""
        mock_child = Mock()
        mock_child.expect.side_effect = [2, 1]  # First sudo prompt, then EOF
        mock_child.before = b"[sudo] password:"
        mock_child.after = b""
        mock_child.exitstatus = 0
        mock_spawn.return_value = mock_child
        
        system = ArchSystem('test', arch_system_config)
        system.sudo_password = 'test_pass'
        
        exit_code, stdout, stderr = system._execute_with_pexpect('paru -S package', 60)
        
        mock_child.sendline.assert_called_with('test_pass')
        assert exit_code == 0

    def test_execute_command_local_system(self, arch_system_config):
        """Test execute_command routing for local system"""
        system = ArchSystem('test', arch_system_config)
        
        with patch.object(system, 'execute_command_local') as mock_local:
            mock_local.return_value = (0, "output", "")
            
            result = system.execute_command('test command')
            
            mock_local.assert_called_once_with('test command', False, False, 3600)
            assert result == (0, "output", "")

    def test_execute_command_remote_system(self, debian_system_config):
        """Test execute_command routing for remote system"""
        system = DebianSystem('test', debian_system_config)
        
        with patch.object(system, 'execute_command_remote') as mock_remote:
            mock_remote.return_value = (0, "output", "")
            mock_ssh = Mock()
            
            result = system.execute_command('test command', ssh_connection=mock_ssh)
            
            mock_remote.assert_called_once_with('test command', False, False, mock_ssh)
            assert result == (0, "output", "")