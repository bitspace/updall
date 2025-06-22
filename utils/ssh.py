import paramiko
import socket
import time
from typing import Optional, Tuple
from pathlib import Path


class SSHConnection:
    def __init__(self, hostname: str, username: str, key_file: str, 
                 sudo_password: Optional[str] = None, port: int = 22,
                 connect_timeout: int = 30, command_timeout: int = 3600):
        self.hostname = hostname
        self.username = username
        self.key_file = Path(key_file).expanduser()
        self.sudo_password = sudo_password
        self.port = port
        self.connect_timeout = connect_timeout
        self.command_timeout = command_timeout
        self.client = None
        self.connected = False
    
    def connect(self, max_retries: int = 3, retry_delay: int = 5) -> bool:
        """
        Establish SSH connection with retry logic
        
        Args:
            max_retries: Maximum number of connection attempts
            retry_delay: Delay between retry attempts in seconds
            
        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                self.client = paramiko.SSHClient()
                self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                # Load private key
                if not self.key_file.exists():
                    raise FileNotFoundError(f"SSH key file not found: {self.key_file}")
                
                private_key = paramiko.RSAKey.from_private_key_file(str(self.key_file))
                
                # Connect with timeout
                self.client.connect(
                    hostname=self.hostname,
                    port=self.port,
                    username=self.username,
                    pkey=private_key,
                    timeout=self.connect_timeout,
                    banner_timeout=self.connect_timeout
                )
                
                # Test connection with a simple command
                stdin, stdout, stderr = self.client.exec_command('echo "test"', timeout=10)
                test_result = stdout.read().decode().strip()
                
                if test_result == "test":
                    self.connected = True
                    return True
                else:
                    raise Exception("Connection test failed")
                    
            except (paramiko.AuthenticationException, 
                    paramiko.SSHException, 
                    socket.error, 
                    FileNotFoundError,
                    Exception) as e:
                
                if self.client:
                    self.client.close()
                    self.client = None
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                else:
                    self.connected = False
                    raise ConnectionError(f"Failed to connect to {self.hostname} after {max_retries} attempts: {e}")
        
        return False
    
    def execute_command(self, command: str, use_sudo: bool = False,
                       sudo_method: str = 'password', 
                       interactive_sudo: bool = False) -> Tuple[int, str, str]:
        """
        Execute command with optional sudo support
        
        Args:
            command: Command to execute
            use_sudo: Whether to run with sudo
            sudo_method: 'nopasswd' or 'password'
            interactive_sudo: Whether command handles sudo internally (like paru)
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to remote host")
        
        try:
            if interactive_sudo and self.sudo_password:
                return self._execute_interactive_sudo(command)
            elif use_sudo and not interactive_sudo:
                return self._execute_with_sudo(command, sudo_method)
            else:
                return self._execute_simple(command)
                
        except Exception as e:
            return 1, "", f"Command execution failed: {e}"
    
    def _execute_simple(self, command: str) -> Tuple[int, str, str]:
        """Execute simple command without sudo"""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=self.command_timeout)
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode()
        stderr_data = stderr.read().decode()
        
        return exit_code, stdout_data, stderr_data
    
    def _execute_with_sudo(self, command: str, sudo_method: str) -> Tuple[int, str, str]:
        """Execute command with sudo using password or nopasswd"""
        if sudo_method == 'password' and self.sudo_password:
            # Use sudo -S to read password from stdin
            full_command = f"sudo -S {command}"
            stdin, stdout, stderr = self.client.exec_command(
                full_command, 
                get_pty=True,
                timeout=self.command_timeout
            )
            stdin.write(f"{self.sudo_password}\n")
            stdin.flush()
        else:
            # Assume NOPASSWD is configured
            full_command = f"sudo {command}"
            stdin, stdout, stderr = self.client.exec_command(
                full_command,
                timeout=self.command_timeout
            )
        
        exit_code = stdout.channel.recv_exit_status()
        stdout_data = stdout.read().decode()
        stderr_data = stderr.read().decode()
        
        return exit_code, stdout_data, stderr_data
    
    def _execute_interactive_sudo(self, command: str) -> Tuple[int, str, str]:
        """
        Execute command with interactive sudo (for commands like paru)
        Uses shell interaction to handle sudo prompts
        """
        channel = self.client.invoke_shell()
        
        # Send command
        channel.send(f"{command}\n")
        
        output = ""
        start_time = time.time()
        
        while True:
            # Check for timeout
            if time.time() - start_time > self.command_timeout:
                channel.close()
                return 124, output, "Command timed out"
            
            # Check if channel is ready to receive data
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8', errors='ignore')
                output += data
                
                # Look for sudo password prompts
                if any(prompt in data.lower() for prompt in [
                    '[sudo] password',
                    'password:',
                    'password for'
                ]):
                    if self.sudo_password:
                        channel.send(f"{self.sudo_password}\n")
                    else:
                        channel.close()
                        return 1, output, "Sudo password required but not provided"
            
            # Check if command is complete
            if channel.exit_status_ready():
                # Read any remaining output
                while channel.recv_ready():
                    data = channel.recv(4096).decode('utf-8', errors='ignore')
                    output += data
                
                exit_code = channel.recv_exit_status()
                channel.close()
                return exit_code, output, ""
            
            time.sleep(0.1)
    
    def test_connection(self) -> bool:
        """Test if the connection is still alive"""
        if not self.connected or not self.client:
            return False
        
        try:
            transport = self.client.get_transport()
            if transport and transport.is_active():
                # Send a simple test command
                stdin, stdout, stderr = self.client.exec_command('echo "alive"', timeout=5)
                result = stdout.read().decode().strip()
                return result == "alive"
            else:
                return False
        except Exception:
            return False
    
    def close(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None
        self.connected = False
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()