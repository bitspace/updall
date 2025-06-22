from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import os
import subprocess
import time
import pexpect
from utils.ssh import SSHConnection


class BaseSystem(ABC):
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.hostname = config['hostname']
        self.update_types = config['updates']
        self.ssh_config = config.get('ssh')
        self.sudo_method = config.get('sudo_method', 'password')
        self.sudo_password = None
        self.is_local = self._is_local_system()
        
        if self.sudo_method == 'password':
            env_var = config.get('sudo_password_env', 'UPDATE_SUDO_PASS')
            self.sudo_password = os.environ.get(env_var)
    
    def _is_local_system(self) -> bool:
        """Determine if this system should be executed locally"""
        return (self.ssh_config is None or 
                self.hostname in ['localhost', '127.0.0.1'] or
                self.hostname == os.uname().nodename)
    
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
    
    def create_ssh_connection(self) -> Optional[SSHConnection]:
        """Create SSH connection if needed"""
        if self.is_local or not self.ssh_config:
            return None
        
        return SSHConnection(
            hostname=self.hostname,
            username=self.ssh_config['user'],
            key_file=self.ssh_config['key_file'],
            sudo_password=self.sudo_password
        )
    
    def execute_command(self, command: str, needs_sudo: bool = False, 
                       handles_sudo_internally: bool = False, 
                       timeout: int = 3600,
                       ssh_connection: Optional[SSHConnection] = None) -> Tuple[int, str, str]:
        """
        Execute command locally or remotely based on system configuration
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if self.is_local:
            return self.execute_command_local(command, needs_sudo, handles_sudo_internally, timeout)
        else:
            return self.execute_command_remote(command, needs_sudo, handles_sudo_internally, ssh_connection)
    
    def execute_command_local(self, command: str, needs_sudo: bool = False, 
                             handles_sudo_internally: bool = False, 
                             timeout: int = 3600) -> Tuple[int, str, str]:
        """
        Execute command locally with proper sudo handling
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if handles_sudo_internally and self.sudo_password:
            return self._execute_with_pexpect(command, timeout)
        elif needs_sudo and not handles_sudo_internally:
            final_command = self.wrap_with_sudo(command)
            return self._execute_with_subprocess(final_command, timeout)
        else:
            return self._execute_with_subprocess(command, timeout)
    
    def _execute_with_subprocess(self, command: str, timeout: int) -> Tuple[int, str, str]:
        """Execute command using subprocess"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 124, "", f"Command timed out after {timeout} seconds"
        except Exception as e:
            return 1, "", str(e)
    
    def _execute_with_pexpect(self, command: str, timeout: int) -> Tuple[int, str, str]:
        """Execute command using pexpect for interactive sudo handling"""
        try:
            child = pexpect.spawn(command, timeout=timeout)
            output = ""
            
            while True:
                try:
                    index = child.expect([
                        pexpect.TIMEOUT,
                        pexpect.EOF,
                        r'\[sudo\] password.*:',
                        r'Password.*:',
                        r'.*'
                    ], timeout=10)
                    
                    if index == 0:  # TIMEOUT
                        output += child.before.decode() if child.before else ""
                        continue
                    elif index == 1:  # EOF
                        output += child.before.decode() if child.before else ""
                        break
                    elif index in [2, 3]:  # sudo password prompt
                        if self.sudo_password:
                            child.sendline(self.sudo_password)
                            output += child.before.decode() if child.before else ""
                        else:
                            child.close()
                            return 1, output, "Sudo password required but not provided"
                    else:  # Regular output
                        output += child.before.decode() if child.before else ""
                        output += child.after.decode() if child.after else ""
                
                except pexpect.TIMEOUT:
                    continue
                except pexpect.EOF:
                    break
            
            exit_code = child.exitstatus if child.exitstatus is not None else 0
            child.close()
            return exit_code, output, ""
            
        except Exception as e:
            return 1, "", str(e)
    
    def execute_command_remote(self, command: str, needs_sudo: bool = False,
                              handles_sudo_internally: bool = False,
                              ssh_connection: Optional[SSHConnection] = None) -> Tuple[int, str, str]:
        """
        Execute command remotely via SSH
        
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if ssh_connection is None:
            return 1, "", "No SSH connection provided for remote execution"
        
        try:
            return ssh_connection.execute_command(
                command,
                use_sudo=needs_sudo,
                sudo_method=self.sudo_method,
                interactive_sudo=handles_sudo_internally
            )
        except Exception as e:
            return 1, "", f"Remote command execution failed: {e}"
    
    def run_updates(self) -> Dict[str, Any]:
        """Run updates for this system"""
        from utils.logger import get_logger
        logger = get_logger()
        
        results = {}
        start_time = time.time()
        ssh_connection = None
        
        logger.log_system_start(self.name)
        
        # Create SSH connection if needed
        if not self.is_local:
            try:
                ssh_connection = self.create_ssh_connection()
                if ssh_connection:
                    logger.info(f"Establishing SSH connection to {self.hostname}")
                    ssh_connection.connect()
                    logger.info(f"Successfully connected to {self.hostname}")
            except Exception as e:
                logger.error(f"Failed to connect to {self.hostname}: {e}")
                return {
                    'connection_error': {
                        'status': 'failed',
                        'error': f"SSH connection failed: {e}",
                        'success': False
                    }
                }
        
        try:
            for update_type in self.update_types:
                logger.log_update_type_start(update_type)
                
                try:
                    commands = self.get_commands_for_update_type(update_type)
                    update_results = []
                    success = True
                    
                    for command, options in commands:
                        logger.log_command_start(command)
                        cmd_start_time = time.time()
                        
                        exit_code, stdout, stderr = self.execute_command(
                            command,
                            options.get('needs_sudo', False),
                            options.get('handles_sudo_internally', False),
                            ssh_connection=ssh_connection
                        )
                        
                        cmd_duration = time.time() - cmd_start_time
                        logger.log_command_complete(command, exit_code, cmd_duration)
                        
                        cmd_result = {
                            'command': command,
                            'exit_code': exit_code,
                            'stdout': stdout,
                            'stderr': stderr,
                            'duration': cmd_duration,
                            'success': exit_code == 0
                        }
                        
                        update_results.append(cmd_result)
                        
                        if exit_code != 0:
                            success = False
                            logger.error(f"Command failed: {command} (exit code: {exit_code})")
                            if stderr:
                                logger.error(f"Error output: {stderr}")
                    
                    results[update_type] = {
                        'status': 'success' if success else 'failed',
                        'commands': update_results,
                        'success': success
                    }
                    
                    logger.log_update_type_complete(update_type, success)
                    
                except Exception as e:
                    logger.error(f"Failed to execute {update_type} updates: {e}")
                    results[update_type] = {
                        'status': 'error',
                        'error': str(e),
                        'success': False
                    }
        
        finally:
            # Clean up SSH connection
            if ssh_connection:
                try:
                    ssh_connection.close()
                    logger.debug(f"Closed SSH connection to {self.hostname}")
                except Exception as e:
                    logger.warning(f"Error closing SSH connection: {e}")
        
        total_duration = time.time() - start_time
        logger.log_system_complete(self.name, total_duration)
        
        return results