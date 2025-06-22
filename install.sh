#!/bin/bash

# Updall Installation Script
# Installs updall system update utility with proper file placement

set -e

# Configuration
INSTALL_DIR="/usr/local/bin"
CONFIG_DIR="/etc/updall"
LOG_DIR="/var/log/updall"
SERVICE_DIR="/etc/systemd/system"
USER_CONFIG_DIR="$HOME/.config/updall"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_info "Checking system requirements..."
    
    # Check if running as root for system installation
    if [[ $EUID -ne 0 && "$1" == "--system" ]]; then
        print_error "System installation requires root privileges"
        print_info "Run with sudo: sudo $0 --system"
        exit 1
    fi
    
    # Check Python 3
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check Python version
    python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 7) else 1)'; then
        print_success "Python $python_version detected"
    else
        print_error "Python 3.7+ is required (found $python_version)"
        exit 1
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_warning "pip3 not found, will attempt to install dependencies manually"
    fi
}

install_dependencies() {
    print_info "Installing Python dependencies..."
    
    # Try to install with pip first
    if command -v pip3 &> /dev/null; then
        if pip3 install --user -r requirements.txt; then
            print_success "Dependencies installed via pip"
            return
        else
            print_warning "pip installation failed, trying system packages"
        fi
    fi
    
    # Fallback to system packages
    if command -v pacman &> /dev/null; then
        # Arch Linux
        print_info "Installing dependencies via pacman..."
        sudo pacman -S --needed python-paramiko python-yaml python-pexpect
    elif command -v apt &> /dev/null; then
        # Debian/Ubuntu
        print_info "Installing dependencies via apt..."
        sudo apt update
        sudo apt install -y python3-paramiko python3-yaml python-pexpect
    else
        print_error "Unable to install dependencies automatically"
        print_info "Please install manually: paramiko, PyYAML, pexpect"
        exit 1
    fi
}

install_system() {
    print_info "Installing updall system-wide..."
    
    # Create directories
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    # Copy main script
    cp updall.py "$INSTALL_DIR/updall"
    chmod +x "$INSTALL_DIR/updall"
    
    # Copy Python modules
    cp -r systems updaters utils config.py "$CONFIG_DIR/"
    
    # Copy default config if it doesn't exist
    if [[ ! -f "$CONFIG_DIR/config.yaml" ]]; then
        cp config.yaml "$CONFIG_DIR/config.yaml.example"
        print_info "Example config copied to $CONFIG_DIR/config.yaml.example"
        print_warning "Please create $CONFIG_DIR/config.yaml based on the example"
    fi
    
    # Set ownership and permissions
    chown -R root:root "$CONFIG_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 644 "$CONFIG_DIR"/*.py
    chmod -R 755 "$CONFIG_DIR"/*/
    chmod 600 "$CONFIG_DIR/config.yaml.example"
    
    # Create log directory with proper permissions
    chown root:root "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    print_success "System installation completed"
    print_info "Updall installed to: $INSTALL_DIR/updall"
    print_info "Config directory: $CONFIG_DIR"
    print_info "Log directory: $LOG_DIR"
}

install_user() {
    print_info "Installing updall for user..."
    
    # Create user directories
    mkdir -p "$USER_CONFIG_DIR"
    mkdir -p "$HOME/.local/bin"
    
    # Copy main script
    cp updall.py "$HOME/.local/bin/updall"
    chmod +x "$HOME/.local/bin/updall"
    
    # Copy Python modules to user config
    cp -r systems updaters utils config.py "$USER_CONFIG_DIR/"
    
    # Copy default config if it doesn't exist
    if [[ ! -f "$USER_CONFIG_DIR/config.yaml" ]]; then
        cp config.yaml "$USER_CONFIG_DIR/config.yaml"
        print_info "Default config copied to $USER_CONFIG_DIR/config.yaml"
        print_warning "Please edit $USER_CONFIG_DIR/config.yaml for your systems"
    fi
    
    # Update PATH information
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        print_warning "Add $HOME/.local/bin to your PATH:"
        print_info "echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    fi
    
    print_success "User installation completed"
    print_info "Updall installed to: $HOME/.local/bin/updall"
    print_info "Config directory: $USER_CONFIG_DIR"
}

install_systemd_service() {
    print_info "Installing systemd service and timer..."
    
    # Create service file
    cat > "$SERVICE_DIR/updall.service" << 'EOF'
[Unit]
Description=System Update Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/local/bin/updall --config /etc/updall/config.yaml --report summary
StandardOutput=journal
StandardError=journal
TimeoutStartSec=3600

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/updall /tmp
PrivateTmp=true
EOF

    # Create timer file
    cat > "$SERVICE_DIR/updall.timer" << 'EOF'
[Unit]
Description=Daily System Updates
Requires=network-online.target

[Timer]
OnCalendar=daily
Persistent=true
RandomizedDelaySec=1h

[Install]
WantedBy=timers.target
EOF

    # Set permissions
    chmod 644 "$SERVICE_DIR/updall.service"
    chmod 644 "$SERVICE_DIR/updall.timer"
    
    # Reload systemd
    systemctl daemon-reload
    
    print_success "Systemd service installed"
    print_info "Enable with: systemctl enable updall.timer"
    print_info "Start with: systemctl start updall.timer"
    print_info "Check status: systemctl status updall.timer"
}

create_sample_config() {
    print_info "Creating sample configuration..."
    
    local config_file="$1"
    
    cat > "$config_file" << 'EOF'
systems:
  laptop:
    hostname: localhost
    type: arch
    sudo_method: password
    updates:
      - system_packages
      - rust
      - node
      - sdkman
      - gcloud

  # Example remote Arch system
  # home_server:
  #   hostname: server.example.com
  #   type: arch
  #   ssh:
  #     user: admin
  #     key_file: ~/.ssh/id_rsa
  #   sudo_method: password
  #   updates:
  #     - system_packages
  #     - rust
  #     - node

  # Example Debian system
  # vps:
  #   hostname: vps.example.com
  #   type: debian
  #   ssh:
  #     user: root
  #     key_file: ~/.ssh/id_rsa
  #   sudo_method: nopasswd
  #   updates:
  #     - system_packages
  #     - rust

update_settings:
  parallel: false
  timeout: 3600
  log_level: INFO
  sudo_password_env: UPDATE_SUDO_PASS
EOF

    print_success "Sample configuration created at $config_file"
}

uninstall() {
    print_info "Uninstalling updall..."
    
    # Stop and disable timer
    if systemctl is-enabled updall.timer &> /dev/null; then
        systemctl disable updall.timer
        systemctl stop updall.timer
    fi
    
    # Remove files
    rm -f "$INSTALL_DIR/updall"
    rm -rf "$CONFIG_DIR"
    rm -rf "$LOG_DIR"
    rm -f "$SERVICE_DIR/updall.service"
    rm -f "$SERVICE_DIR/updall.timer"
    
    # User installation
    rm -f "$HOME/.local/bin/updall"
    rm -rf "$USER_CONFIG_DIR"
    
    systemctl daemon-reload
    
    print_success "Updall uninstalled"
}

show_help() {
    cat << 'EOF'
Updall Installation Script

USAGE:
    ./install.sh [OPTIONS]

OPTIONS:
    --system        Install system-wide (requires root)
    --user          Install for current user only (default)
    --service       Install systemd service and timer (requires --system)
    --uninstall     Remove updall installation
    --help          Show this help message

EXAMPLES:
    ./install.sh --user                    # User installation
    sudo ./install.sh --system             # System installation
    sudo ./install.sh --system --service   # System + systemd service
    sudo ./install.sh --uninstall          # Uninstall

NOTES:
    - User installation installs to ~/.local/bin/updall
    - System installation installs to /usr/local/bin/updall
    - Config files are placed in ~/.config/updall (user) or /etc/updall (system)
    - Systemd service runs daily updates automatically
EOF
}

main() {
    local install_type="user"
    local install_service=false
    local do_uninstall=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --system)
                install_type="system"
                shift
                ;;
            --user)
                install_type="user"
                shift
                ;;
            --service)
                install_service=true
                shift
                ;;
            --uninstall)
                do_uninstall=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Handle uninstall
    if [[ "$do_uninstall" == true ]]; then
        uninstall
        exit 0
    fi
    
    print_info "Starting updall installation..."
    
    # Check requirements
    check_requirements "$install_type"
    
    # Install dependencies
    install_dependencies
    
    # Perform installation
    if [[ "$install_type" == "system" ]]; then
        install_system
        
        if [[ "$install_service" == true ]]; then
            install_systemd_service
        fi
    else
        install_user
    fi
    
    print_success "Installation completed successfully!"
    
    # Show next steps
    echo
    print_info "Next steps:"
    if [[ "$install_type" == "system" ]]; then
        print_info "1. Edit /etc/updall/config.yaml for your systems"
        print_info "2. Test with: updall --dry-run"
        if [[ "$install_service" == true ]]; then
            print_info "3. Enable timer: systemctl enable updall.timer"
            print_info "4. Start timer: systemctl start updall.timer"
        fi
    else
        print_info "1. Edit ~/.config/updall/config.yaml for your systems"
        print_info "2. Test with: updall --dry-run"
        print_info "3. Add ~/.local/bin to PATH if needed"
    fi
}

# Run main function with all arguments
main "$@"