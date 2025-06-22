#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path
from typing import Optional

from config import ConfigParser
from systems.arch import ArchSystem
from systems.debian import DebianSystem
from utils.logger import get_logger


def create_system(name: str, config: dict):
    """Factory function to create system instances"""
    system_type = config['type']
    if system_type == 'arch':
        return ArchSystem(name, config)
    elif system_type == 'debian':
        return DebianSystem(name, config)
    else:
        raise ValueError(f"Unknown system type: {system_type}")


def main():
    parser = argparse.ArgumentParser(description="Update all systems")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--system", help="Update specific system only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--log-file", help="Log to file")
    parser.add_argument("--only", help="Update only specific components (comma-separated)")
    
    args = parser.parse_args()
    
    try:
        config_parser = ConfigParser(args.config)
        config = config_parser.load_config()
        
        update_settings = config_parser.get_update_settings()
        log_level = "DEBUG" if args.verbose else update_settings.get('log_level', 'INFO')
        
        logger = get_logger(log_level, args.log_file)
        logger.info("Starting updall")
        
        systems_config = config_parser.get_systems()
        
        if args.system:
            if args.system not in systems_config:
                logger.error(f"System '{args.system}' not found in config")
                sys.exit(1)
            systems_to_update = {args.system: systems_config[args.system]}
        else:
            systems_to_update = systems_config
        
        for system_name, system_config in systems_to_update.items():            
            try:
                system = create_system(system_name, system_config)
                
                if args.only:
                    update_types = [t.strip() for t in args.only.split(',')]
                    system.update_types = [t for t in system.update_types if t in update_types]
                
                if args.dry_run:
                    logger.info(f"[DRY RUN] Would update {system_name} with: {system.update_types}")
                    for update_type in system.update_types:
                        commands = system.get_commands_for_update_type(update_type)
                        for cmd, opts in commands:
                            final_cmd = system.prepare_command(cmd, opts.get('needs_sudo', False), 
                                                             opts.get('handles_sudo_internally', False))
                            logger.info(f"[DRY RUN] Would run: {final_cmd}")
                else:
                    results = system.run_updates()
                    
                    # Print summary results
                    print(f"\n=== Update Results for {system_name} ===")
                    for update_type, result in results.items():
                        status_symbol = "✓" if result.get('success', False) else "✗"
                        print(f"{status_symbol} {update_type}: {result.get('status', 'unknown')}")
                        
                        if not result.get('success', False) and 'error' in result:
                            print(f"  Error: {result['error']}")
                
            except Exception as e:
                logger.error(f"Failed to update system {system_name}: {e}")
                continue
        
        logger.info("Updall completed")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()