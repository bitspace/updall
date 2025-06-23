import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import paramiko

from utils.ssh import SSHConnection
from utils.error_handler import ConnectionError


class TestSSHConnection:
    """Test SSHConnection functionality"""

    def test_init_with_password(self):
        """Test SSHConnection initialization with sudo password"""
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa', 'sudo_password')
        
        assert conn.hostname == 'test.example.com'
        assert conn.username == 'testuser'
        assert conn.key_file == '~/.ssh/id_rsa'
        assert conn.sudo_password == 'sudo_password'
        assert conn.client is None

    def test_init_without_password(self):
        """Test SSHConnection initialization without sudo password"""
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        assert conn.hostname == 'test.example.com'
        assert conn.username == 'testuser'
        assert conn.key_file == '~/.ssh/id_rsa'
        assert conn.sudo_password is None
        assert conn.client is None

    @patch('paramiko.SSHClient')
    def test_connect_success(self, mock_ssh_client):
        """Test successful SSH connection"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        result = conn.connect()
        
        assert result is True
        assert conn.client == mock_client
        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname='test.example.com',
            username='testuser',
            key_filename='~/.ssh/id_rsa',
            timeout=30
        )

    @patch('paramiko.SSHClient')
    def test_connect_failure(self, mock_ssh_client):
        """Test SSH connection failure"""
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_client.return_value = mock_client
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        result = conn.connect()
        
        assert result is False
        assert conn.client is None

    @patch('paramiko.SSHClient')
    def test_connect_with_retries(self, mock_ssh_client):
        """Test SSH connection with retry logic"""
        mock_client = Mock()
        # Fail first two attempts, succeed on third
        mock_client.connect.side_effect = [
            paramiko.SSHException("Connection failed"),
            paramiko.SSHException("Connection failed"),
            None  # Success
        ]
        mock_ssh_client.return_value = mock_client
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        with patch('time.sleep'):  # Speed up test
            result = conn.connect(max_retries=3, retry_delay=0.1)
        
        assert result is True
        assert mock_client.connect.call_count == 3

    @patch('paramiko.SSHClient')
    def test_connect_max_retries_exceeded(self, mock_ssh_client):
        """Test SSH connection when max retries exceeded"""
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.SSHException("Connection failed")
        mock_ssh_client.return_value = mock_client
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        with patch('time.sleep'):  # Speed up test
            result = conn.connect(max_retries=2, retry_delay=0.1)
        
        assert result is False
        assert mock_client.connect.call_count == 2

    def test_execute_command_simple_success(self, mock_ssh_client):
        """Test executing simple command successfully"""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"Success output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.client = mock_client
        
        exit_code, stdout, stderr = conn.execute_command('echo "hello"')
        
        assert exit_code == 0
        assert stdout == "Success output"
        assert stderr == ""
        mock_client.exec_command.assert_called_once_with('echo "hello"')

    def test_execute_command_with_sudo_nopasswd(self, mock_ssh_client):
        """Test executing command with sudo (nopasswd method)"""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"Sudo command output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.client = mock_client
        
        exit_code, stdout, stderr = conn.execute_command(
            'apt update',
            use_sudo=True,
            sudo_method='nopasswd'
        )
        
        assert exit_code == 0
        assert stdout == "Sudo command output"
        mock_client.exec_command.assert_called_once_with('sudo apt update')

    def test_execute_command_with_sudo_password(self, mock_ssh_client):
        """Test executing command with sudo password"""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"Sudo with password output"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa', 'test_password')
        conn.client = mock_client
        
        exit_code, stdout, stderr = conn.execute_command(
            'apt update',
            use_sudo=True,
            sudo_method='password'
        )
        
        assert exit_code == 0
        assert stdout == "Sudo with password output"
        mock_client.exec_command.assert_called_once_with('sudo -S apt update', get_pty=True)
        mock_stdin.write.assert_called_once_with('test_password\n')

    def test_execute_command_interactive_sudo(self, mock_ssh_client):
        """Test executing command with interactive sudo (like paru)"""
        mock_client = Mock()
        mock_channel = Mock()
        
        # Simulate interactive session
        mock_channel.recv_ready.side_effect = [True, True, False]
        mock_channel.recv.side_effect = [
            b"[sudo] password for user:",
            b"Package installation complete",
            b""
        ]
        mock_channel.exit_status_ready.side_effect = [False, False, True]
        mock_channel.recv_exit_status.return_value = 0
        
        mock_client.invoke_shell.return_value = mock_channel
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa', 'test_password')
        conn.client = mock_client
        
        with patch('time.sleep'):  # Speed up test
            exit_code, stdout, stderr = conn.execute_command(
                'paru -S package',
                use_sudo=False,
                interactive_sudo=True
            )
        
        assert exit_code == 0
        assert "[sudo] password for user:" in stdout
        assert "Package installation complete" in stdout
        mock_channel.send.assert_called_with('test_password\n')

    def test_execute_command_timeout(self, mock_ssh_client):
        """Test command execution timeout"""
        mock_client = Mock()
        mock_channel = Mock()
        
        # Simulate command that never completes
        mock_channel.recv_ready.return_value = False
        mock_channel.exit_status_ready.return_value = False
        
        mock_client.invoke_shell.return_value = mock_channel
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa', 'test_password')
        conn.client = mock_client
        
        with patch('time.sleep'):  # Speed up test
            exit_code, stdout, stderr = conn.execute_command(
                'sleep 1000',
                interactive_sudo=True,
                timeout=1  # Very short timeout for test
            )
        
        # Should timeout and return appropriate exit code
        assert exit_code == 124  # Standard timeout exit code
        assert "timed out" in stderr

    def test_execute_command_failure(self, mock_ssh_client):
        """Test command execution failure"""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"Command failed"
        mock_stdout.channel.recv_exit_status.return_value = 1
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.client = mock_client
        
        exit_code, stdout, stderr = conn.execute_command('false')
        
        assert exit_code == 1
        assert stdout == ""
        assert stderr == "Command failed"

    def test_execute_command_no_client(self):
        """Test command execution when not connected"""
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        with pytest.raises(ConnectionError, match="Not connected to SSH server"):
            conn.execute_command('echo test')

    def test_close_connection(self, mock_ssh_client):
        """Test closing SSH connection"""
        mock_client = Mock()
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.client = mock_client
        
        conn.close()
        
        mock_client.close.assert_called_once()
        assert conn.client is None

    def test_close_no_connection(self):
        """Test closing when no connection exists"""
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        
        # Should not raise error
        conn.close()
        assert conn.client is None

    def test_context_manager_success(self, mock_ssh_client):
        """Test using SSHConnection as context manager successfully"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        with SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa') as conn:
            assert conn.client == mock_client
            mock_client.connect.assert_called_once()
        
        # Should close connection on exit
        mock_client.close.assert_called_once()

    @patch('paramiko.SSHClient')
    def test_context_manager_connection_failure(self, mock_ssh_client):
        """Test context manager when connection fails"""
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_client.return_value = mock_client
        
        with pytest.raises(ConnectionError, match="Failed to connect"):
            with SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa') as conn:
                pass

    def test_context_manager_exception_during_use(self, mock_ssh_client):
        """Test context manager when exception occurs during use"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        try:
            with SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa') as conn:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should still close connection even when exception occurs
        mock_client.close.assert_called_once()

    def test_execute_command_with_environment(self, mock_ssh_client):
        """Test executing command with environment variables"""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()
        
        mock_stdout.read.return_value = b"Environment set"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.client = mock_client
        
        exit_code, stdout, stderr = conn.execute_command(
            'echo $TEST_VAR',
            environment={'TEST_VAR': 'test_value'}
        )
        
        assert exit_code == 0
        # Should prefix command with environment variables
        expected_cmd = 'TEST_VAR=test_value echo $TEST_VAR'
        mock_client.exec_command.assert_called_once_with(expected_cmd)

    def test_get_connection_info(self):
        """Test getting connection information"""
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa', 'password')
        
        info = conn.get_connection_info()
        
        assert info['hostname'] == 'test.example.com'
        assert info['username'] == 'testuser'
        assert info['key_file'] == '~/.ssh/id_rsa'
        assert info['has_sudo_password'] is True
        assert info['connected'] is False

    def test_get_connection_info_connected(self, mock_ssh_client):
        """Test getting connection info when connected"""
        mock_client = Mock()
        mock_ssh_client.return_value = mock_client
        
        conn = SSHConnection('test.example.com', 'testuser', '~/.ssh/id_rsa')
        conn.connect()
        
        info = conn.get_connection_info()
        
        assert info['connected'] is True