# Updall Systemd Integration

This directory contains systemd service and timer files for automating updall execution.

## Files

- `updall.service`: Main service that updates all configured systems
- `updall.timer`: Timer to run daily updates automatically  
- `updall@.service`: Template service for updating specific systems
- `README.md`: This documentation

## Installation

The systemd files are automatically installed when using the installation script with the `--service` option:

```bash
sudo ./install.sh --system --service
```

Manual installation:

```bash
sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

## Usage

### Enable Automatic Daily Updates

```bash
# Enable and start the timer
sudo systemctl enable updall.timer
sudo systemctl start updall.timer

# Check timer status
systemctl status updall.timer
systemctl list-timers updall.timer
```

### Manual Updates

```bash
# Update all systems
sudo systemctl start updall.service

# Update specific system
sudo systemctl start updall@laptop.service
sudo systemctl start updall@home_server.service
```

### Monitoring

```bash
# View recent logs
journalctl -u updall.service -f

# View logs for specific system
journalctl -u updall@laptop.service -f

# View timer logs
journalctl -u updall.timer -f
```

## Timer Schedule

The default timer runs daily at 3:00 AM with up to 1 hour randomization delay. This helps:

- Distribute load across different times
- Avoid all systems updating simultaneously
- Ensure updates happen during low-usage hours

To modify the schedule, edit `updall.timer` and change the `OnCalendar` value:

```ini
# Examples:
OnCalendar=*-*-* 02:00:00        # Daily at 2 AM
OnCalendar=Mon *-*-* 03:00:00    # Weekly on Monday at 3 AM  
OnCalendar=*-*-01 03:00:00       # Monthly on 1st at 3 AM
```

## Security Features

The service files include several security hardening measures:

- **Process isolation**: `PrivateTmp=true`, `ProtectHome=true`
- **System protection**: `ProtectSystem=strict`, `ProtectKernelTunables=true`
- **Resource limits**: Memory and task limits to prevent resource exhaustion
- **Network restrictions**: Limited address families
- **Privilege restrictions**: `NoNewPrivileges=true`, `RestrictSUIDSGID=true`

## Configuration

The service expects:

- Main binary: `/usr/local/bin/updall`
- Configuration: `/etc/updall/config.yaml`
- Log directory: `/var/log/updall/`
- Python modules: `/etc/updall/`

Ensure these paths exist and have proper permissions before enabling the service.

## Troubleshooting

### Service fails to start

1. Check configuration file exists and is valid:

   ```bash
   sudo updall --config /etc/updall/config.yaml --dry-run
   ```

2. Check permissions:

   ```bash
   ls -la /etc/updall/config.yaml
   ls -la /usr/local/bin/updall
   ```

3. Check service logs:

   ```bash
   journalctl -u updall.service --no-pager
   ```

### Timer not running

1. Check timer status:

   ```bash
   systemctl status updall.timer
   systemctl list-timers updall.timer
   ```

2. Check if timer is enabled:

   ```bash
   systemctl is-enabled updall.timer
   ```

3. Manually trigger timer:

   ```bash
   sudo systemctl start updall.service
   ```

### Updates failing

1. Test manually:

   ```bash
   sudo updall --config /etc/updall/config.yaml --validate-only
   ```

2. Check network connectivity and SSH keys
3. Verify sudo configuration for package managers
4. Check available disk space

## Customization

### Custom Configuration Location

To use a different config file, modify the `ExecStart` line in the service file:

```ini
ExecStart=/usr/local/bin/updall --config /path/to/custom/config.yaml --report summary
```

### Additional Options

Add command-line options to the `ExecStart` line:

```ini
# Enable verbose logging
ExecStart=/usr/local/bin/updall --config /etc/updall/config.yaml --verbose --report summary

# Update only specific components
ExecStart=/usr/local/bin/updall --config /etc/updall/config.yaml --only rust,node --report summary
```

### Environment Variables

Add environment variables to the service file:

```ini
[Service]
Environment="UPDATE_SUDO_PASS_FILE=/etc/updall/sudo.pass"
Environment="CUSTOM_VAR=value"
```
