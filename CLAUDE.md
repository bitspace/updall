# Multi-System Update Utility Design

## Project Overview

A centralized update management utility that executes OS and software updates across multiple Linux systems (Arch, Debian) with support for various package managers and development tools.

## Core Requirements

### MVP Features
- Single command execution from laptop to update all systems
- Remote update capability for servers
- Support for multiple package managers (paru/pacman, apt)
- Update tracking with timestamps
- Basic error handling and reporting

### Supported Update Types
1. **System Packages**
   - Arch: paru (handles sudo internally)
   - Debian: apt (requires sudo)
2. **Development Tools** (all user-level, no sudo needed)
   - Rust: rustup & cargo-update
   - Node.js: npm global packages
   - SDKman: Java/Kotlin/Scala SDKs
   - Google Cloud SDK

## Architecture Design

### Option 1: Python-Based Solution (Recommended for MVP)

```
updall/
├── updall.py              # Main entry point
├── config.yaml             # System configurations
├── systems/
│   ├── __init__.py
│   ├── base.py            # Base system class
│   ├── arch.py            # Arch-specific updates
│   └── debian.py          # Debian-specific updates
├── updaters/
│   ├── __init__.py
│   ├── package_manager.py # Package manager abstractions
│   ├── rust.py            # Rust toolchain updates
│   ├── node.py            # Node.js updates
│   ├── sdkman.py          # SDKman updates
│   └── gcloud.py          # Google Cloud SDK updates
├── utils/
│   ├── __init__.py
│   ├── ssh.py             # SSH connection handling
│   ├── logger.py          # Logging utilities
│   └── reporter.py        # Update reports
└── requirements.txt
```

### Option 2: Ansible-Based Solution

```
ansible-updall/
├── ansible.cfg
├── inventory.yml
├── updall.yml          # Main playbook
├── group_vars/
│   ├── arch.yml
│   └── debian.yml
├── roles/
│   ├── common/
│   ├── arch-updates/
│   ├── debian-updates/
│   ├── rust-updates/
│   ├── node-updates/
│   ├── sdkman-updates/
│   └── gcloud-updates/
└── templates/
    └── updall-report.j2
```

## Implementation Details

### Python Solution Components

#### 1. Configuration File (config.yaml)
```yaml
systems:
  laptop:
    hostname: strider.bitspace.org
    type: arch
    sudo_method: password  # or 'nopasswd' if configured
    updates:
      - system_packages
      - rust
      - node
      - sdkman
      - gcloud
  
  home_server:
    hostname: sleipnir.bitspace.org
    type: arch
    ssh:
      user: chris
      key_file: ~/.ssh/id_rsa
    sudo_method: password  # Recommended for automation
    updates:
      - system_packages
      - rust
      - node
      - sdkman
  
  vps:
    hostname: ssdnode.bitspace.org
    type: debian
    ssh:
      user: chris
      key_file: ~/.ssh/id_rsa
    sudo_method: password  # Recommended for automation
    updates:
      - system_packages
      - rust
      - node
      - sdkman

update_settings:
  parallel: false
  timeout: 3600
  log_level: INFO
  sudo_password_env: UPDATE_SUDO_PASS  # Optional: env var for sudo password
```

#### 2. Base System Class
```python
# systems/base.py
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
        
        # Get sudo password from environment if needed
        if self.sudo_method == 'password':
            env_var = config.get('sudo_password_env', 'UPDATE_SUDO_PASS')
            self.sudo_password = os.environ.get(env_var)
    
    @abstractmethod
    def get_package_update_commands(self) -> List[Tuple[str, bool]]:
        """
        Return list of (command, needs_sudo) tuples
        """
        pass
    
    def wrap_with_sudo(self, command: str) -> str:
        """Wrap command with sudo based on configuration"""
        if self.sudo_method == 'nopasswd':
            return f"sudo {command}"
        elif self.sudo_method == 'password' and self.sudo_password:
            # Use echo with pipe for non-interactive sudo
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
    
    def run_updates(self) -> Dict[str, Any]:
        results = {}
        for update_type in self.update_types:
            # Execute update and store results
            pass
        return results
```

#### 3. SSH Connection Handler
```python
# utils/ssh.py
import paramiko
from typing import Optional, Tuple
import time
import select

class SSHConnection:
    def __init__(self, hostname: str, username: str, key_file: str, 
                 sudo_password: Optional[str] = None):
        self.hostname = hostname
        self.username = username
        self.key_file = key_file
        self.sudo_password = sudo_password
        self.client = None
    
    def connect(self) -> bool:
        # Establish SSH connection
        pass
    
    def execute_command(self, command: str, use_sudo: bool = False,
                       sudo_method: str = 'nopasswd', 
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
        if interactive_sudo and self.sudo_password:
            # For commands like paru that handle sudo internally
            # Use expect-style interaction
            channel = self.client.invoke_shell()
            channel.send(f"{command}\n")
            
            output = ""
            while True:
                if channel.recv_ready():
                    data = channel.recv(1024).decode()
                    output += data
                    
                    # Look for sudo password prompt
                    if "[sudo] password" in data or "Password:" in data:
                        channel.send(f"{self.sudo_password}\n")
                
                if channel.exit_status_ready():
                    break
                
                time.sleep(0.1)
            
            exit_code = channel.recv_exit_status()
            return exit_code, output, ""
            
        elif use_sudo and not interactive_sudo:
            if sudo_method == 'password' and self.sudo_password:
                # Use stdin to provide password
                stdin, stdout, stderr = self.client.exec_command(
                    f"sudo -S {command}", get_pty=True
                )
                stdin.write(f"{self.sudo_password}\n")
                stdin.flush()
            else:
                # Assume NOPASSWD is configured
                stdin, stdout, stderr = self.client.exec_command(
                    f"sudo {command}"
                )
        else:
            stdin, stdout, stderr = self.client.exec_command(command)
        
        # Wait for command completion
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, stdout.read().decode(), stderr.read().decode()
    
    def close(self):
        # Close SSH connection
        pass
```

### Ansible Solution Components

#### 1. Main Playbook (updall.yml)
```yaml
---
- name: Update all systems
  hosts: all
  gather_facts: yes
  
  pre_tasks:
    - name: Record start time
      set_fact:
        update_start_time: "{{ ansible_date_time.iso8601 }}"
  
  roles:
    - role: arch-updates
      when: ansible_distribution == "Archlinux"
    
    - role: debian-updates
      when: ansible_distribution == "Debian"
    
    - role: rust-updates
      when: "'rust' in update_types"
    
    - role: node-updates
      when: "'node' in update_types"
    
    - role: sdkman-updates
      when: "'sdkman' in update_types"
    
    - role: gcloud-updates
      when: "'gcloud' in update_types and inventory_hostname == 'laptop'"
  
  post_tasks:
    - name: Generate update report
      template:
        src: updall-report.j2
        dest: "/tmp/updall-report-{{ inventory_hostname }}.txt"
```

## Error Handling Strategy

### 1. Command Execution Errors
- Capture exit codes and stderr
- Log detailed error information
- Continue with other updates unless critical

### 2. Connection Errors
- Retry logic for SSH connections
- Fallback to local execution for laptop
- Alert on persistent connection failures

### 3. Update Conflicts
- Check for package manager locks
- Handle interactive prompts programmatically
- Implement rollback for failed updates

## Scheduling and Automation

### 1. Cron Integration
```bash
# Daily updates at 3 AM
0 3 * * * /usr/local/bin/updall --config /etc/updall/config.yaml --log /var/log/updall/daily.log
```

### 2. Systemd Timer (Recommended)
```ini
# /etc/systemd/system/updall.service
[Unit]
Description=System Update Service
After=network-online.target

[Service]
Type=oneshot
# Run as user with sudo privileges
User=chris
# Pass sudo password via environment if needed
Environment="UPDATE_SUDO_PASS_FILE=/etc/updall/sudo.pass"
ExecStartPre=/bin/bash -c 'export UPDATE_SUDO_PASS=$(cat $UPDATE_SUDO_PASS_FILE)'
ExecStart=/usr/local/bin/updall --config /etc/updall/config.yaml
StandardOutput=journal
StandardError=journal

# /etc/systemd/system/updall.timer
[Unit]
Description=Daily System Updates
Requires=network-online.target

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
```

## MVP Implementation Steps

1. **Phase 1: Core Framework**
   - Set up project structure
   - Implement configuration parser
   - Create base system classes
   - Add logging infrastructure

2. **Phase 2: Local Updates**
   - Implement Arch system updates
   - Add Rust toolchain updates
   - Test on laptop locally

3. **Phase 3: Remote Capability**
   - Add SSH connection handling
   - Implement remote command execution
   - Add error handling for network issues

4. **Phase 4: Multi-System Support**
   - Add Debian system support
   - Implement all update types
   - Create unified reporting

5. **Phase 5: Production Ready**
   - Add comprehensive error handling
   - Implement dry-run mode
   - Create installation script
   - Add systemd service files

## Command Line Interface

```bash
# Update all systems
updall

# Update specific system
updall --system laptop

# Dry run mode
updall --dry-run

# Custom config file
updall --config ~/.config/updall/custom.yaml

# Verbose output
updall --verbose

# Update only specific components
updall --only rust,node

# Provide sudo password interactively
updall --ask-sudo-pass

# Use sudo password from environment
UPDATE_SUDO_PASS='password' updall
```

## Example Output Format

```
=== System Update Report ===
Started: 2024-01-20 03:00:00

[strider - Arch Linux]
✓ System packages: 15 packages updated
✓ Rust: Updated to 1.75.0
✓ Cargo crates: 3 crates updated
✓ Node.js: 5 global packages updated
✓ SDKman: 2 SDKs updated
✓ Google Cloud SDK: Updated to 456.0.0

[sleipnir - Arch Linux]
✓ System packages: 8 packages updated
✓ Rust: Already up to date
✗ Node.js: npm error - see logs
✓ SDKman: 1 SDK updated

[ssdnode - Debian 12]
✓ System packages: 23 packages updated
✓ Rust: Updated to 1.75.0
✓ Node.js: 3 global packages updated
✓ SDKman: Already up to date

Completed: 2024-01-20 03:15:42
Total duration: 15m 42s
```

## Future Enhancements

1. **Web Dashboard**
   - Real-time update status
   - Historical update logs
   - System health metrics

2. **Notification System**
   - Email reports
   - Slack/Discord webhooks
   - Mobile push notifications

3. **Advanced Features**
   - Automatic rollback on failure
   - Update scheduling per system
   - Dependency resolution
   - Security update prioritization

4. **Container Support**
   - Docker image updates
   - Kubernetes deployment updates
   - Container registry cleanup

## Security Considerations

1. **SSH Key Management**
   - Use dedicated update keys
   - Implement key rotation
   - Restrict key permissions

2. **Privilege Escalation**
   - Configure NOPASSWD sudo for specific update commands only
   - Example sudoers configuration:
     ```
     username ALL=(ALL) NOPASSWD: /usr/bin/paru, /usr/bin/apt update, /usr/bin/apt upgrade, /usr/bin/apt autoremove, /usr/bin/npm update -g
     ```
   - For password-based sudo:
     - Store password in environment variable
     - Use secure password input methods
     - Clear password from memory after use
   - Log all privileged operations

3. **Network Security**
   - Use SSH jump hosts if needed
   - Implement IP whitelisting
   - Use VPN for remote updates

### Example Implementation: Arch System Class

```python
# systems/arch.py
from typing import List, Tuple, Dict, Any
from .base import BaseSystem

class ArchSystem(BaseSystem):
    def get_package_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Get Arch-specific update commands
        Returns list of (command, options) tuples where options dict contains:
        - needs_sudo: whether command needs elevated privileges
        - handles_sudo_internally: whether command manages sudo itself
        """
        # paru handles sudo internally and should NOT be run with sudo
        return [
            ("paru", {"needs_sudo": True, "handles_sudo_internally": True}),
            ("paru -Sua", {"needs_sudo": True, "handles_sudo_internally": True})
        ]
    
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
    
    def execute_updates(self, connection=None):
        """Execute updates with proper handling for paru's interactive sudo"""
        results = {}
        
        for update_type in self.update_types:
            if update_type == "system_packages":
                for cmd, opts in self.get_package_update_commands():
                    if opts.get("handles_sudo_internally") and self.sudo_password:
                        # For paru, we need to handle interactive sudo prompt
                        if connection:  # Remote execution
                            exit_code, stdout, stderr = connection.execute_command(
                                cmd, 
                                use_sudo=False,  # Don't wrap with sudo
                                interactive_sudo=True  # Handle sudo prompt
                            )
                        else:  # Local execution
                            # Use expect or pexpect for local paru execution
                            import pexpect
                            child = pexpect.spawn(cmd)
                            child.expect('[sudo] password.*:')
                            child.sendline(self.sudo_password)
                            child.expect(pexpect.EOF)
                            stdout = child.before.decode()
                            exit_code = child.exitstatus
                    else:
                        # Regular command execution
                        final_cmd = self.prepare_command(cmd, opts.get("needs_sudo", False))
                        # Execute final_cmd...
```

### Example Implementation: Debian System Class

```python
# systems/debian.py
from typing import List, Tuple, Dict, Any
from .base import BaseSystem

class DebianSystem(BaseSystem):
    def get_package_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get Debian-specific update commands (all need sudo)"""
        return [
            ("apt update", {"needs_sudo": True, "handles_sudo_internally": False}),
            ("apt upgrade -y", {"needs_sudo": True, "handles_sudo_internally": False}),
            ("apt autoremove -y", {"needs_sudo": True, "handles_sudo_internally": False})
        ]
    
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
```