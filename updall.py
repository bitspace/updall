#!/usr/bin/env python3

import argparse
import sys
import os
import getpass
from pathlib import Path
from typing import Optional

from config import ConfigParser
from systems.arch import ArchSystem
from systems.debian import DebianSystem
from utils.logger import get_logger
from utils.reporter import UpdateReporter
from utils.error_handler import ErrorHandler, handle_exception
from utils.dry_run import DryRunValidator


def create_system(name: str, config: dict):
    """Factory function to create system instances"""
    system_type = config['type']
    if system_type == 'arch':
        return ArchSystem(name, config)
    elif system_type == 'debian':
        return DebianSystem(name, config)
    else:
        raise ValueError(f"Unknown system type: {system_type}")


@handle_exception
def main():
    parser = argparse.ArgumentParser(description="Update all systems")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--system", help="Update specific system only")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--log-file", help="Log to file")
    parser.add_argument("--only", help="Update only specific components (comma-separated)")
    parser.add_argument("--report", choices=['summary', 'json'], help="Generate detailed report")
    parser.add_argument("--ask-sudo-pass", action="store_true", help="Prompt for sudo password interactively")
    parser.add_argument("--validate-only", action="store_true", help="Only validate systems without running updates")
    
    args = parser.parse_args()
    
    try:
        config_parser = ConfigParser(args.config)
        config = config_parser.load_config()
        
        update_settings = config_parser.get_update_settings()
        log_level = "DEBUG" if args.verbose else update_settings.get('log_level', 'INFO')
        
        logger = get_logger(log_level, args.log_file)
        error_handler = ErrorHandler(logger)
        
        # Handle interactive sudo password
        if args.ask_sudo_pass:
            try:
                sudo_password = getpass.getpass("Enter sudo password: ")
                os.environ['UPDATE_SUDO_PASS'] = sudo_password
                logger.debug("Sudo password set from interactive prompt")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                sys.exit(1)
        
        logger.info("Starting updall")
        
        # Initialize reporter and dry-run validator
        reporter = UpdateReporter()
        reporter.set_start_time()
        dry_run_validator = DryRunValidator(logger)
        
        systems_config = config_parser.get_systems()
        
        if args.system:
            if args.system not in systems_config:
                logger.error(f"System '{args.system}' not found in config")
                sys.exit(1)
            systems_to_update = {args.system: systems_config[args.system]}
        else:
            systems_to_update = systems_config
        
        # Validation mode - just check system readiness
        if args.validate_only:
            validation_results = {}
            for system_name, system_config in systems_to_update.items():
                try:
                    system = create_system(system_name, system_config)
                    if args.only:
                        update_types = [t.strip() for t in args.only.split(',')]
                        system.update_types = [t for t in system.update_types if t in update_types]
                    
                    validation_results[system_name] = dry_run_validator.validate_system_requirements(
                        system_name, system_config, system.update_types
                    )
                except Exception as e:
                    validation_results[system_name] = {
                        'system_name': system_name,
                        'error': str(e),
                        'reachable': False,
                        'tools_available': {},
                        'missing_tools': [],
                        'warnings': [f"System creation failed: {e}"],
                        'estimated_duration': 0
                    }
            
            print(dry_run_validator.generate_dry_run_report(validation_results))
            return

        for system_name, system_config in systems_to_update.items():            
            try:
                system = create_system(system_name, system_config)
                
                if args.only:
                    update_types = [t.strip() for t in args.only.split(',')]
                    system.update_types = [t for t in system.update_types if t in update_types]
                
                if args.dry_run:
                    # Enhanced dry-run with validation
                    validation_result = dry_run_validator.validate_system_requirements(
                        system_name, system_config, system.update_types
                    )
                    
                    print(f"\n=== DRY RUN: {system_name} ===")
                    print(f"System reachable: {'✓' if validation_result['reachable'] else '✗'}")
                    
                    if validation_result['missing_tools']:
                        print(f"Missing tools: {', '.join(validation_result['missing_tools'])}")
                    
                    if validation_result['warnings']:
                        for warning in validation_result['warnings']:
                            print(f"⚠  {warning}")
                    
                    print(f"Update types: {system.update_types}")
                    
                    commands = dry_run_validator.validate_commands(system, system.update_types)
                    print("Commands to execute:")
                    for cmd, info in commands:
                        sudo_info = " (sudo)" if info['needs_sudo'] else ""
                        print(f"  {info['update_type']}: {cmd}{sudo_info}")
                    
                    if validation_result['estimated_duration'] > 0:
                        duration = dry_run_validator._format_duration(validation_result['estimated_duration'])
                        print(f"Estimated duration: {duration}")
                else:
                    results = system.run_updates()
                    reporter.add_system_result(system_name, results)
                    
                    # Print simple status if not generating detailed report
                    if not args.report:
                        print(f"\n=== Update Results for {system_name} ===")
                        for update_type, result in results.items():
                            status_symbol = "✓" if result.get('success', False) else "✗"
                            print(f"{status_symbol} {update_type}: {result.get('status', 'unknown')}")
                            
                            if not result.get('success', False) and 'error' in result:
                                print(f"  Error: {result['error']}")
                
            except Exception as e:
                logger.error(f"Failed to update system {system_name}: {e}")
                # Add error to reporter
                reporter.add_system_result(system_name, {
                    'system_error': {
                        'status': 'failed',
                        'error': str(e),
                        'success': False
                    }
                })
                continue
        
        reporter.set_end_time()
        
        # Generate and display report if requested
        if args.report and not args.dry_run:
            if args.report == 'summary':
                print("\n" + reporter.generate_summary_report())
            elif args.report == 'json':
                import json
                print(json.dumps(reporter.generate_json_report(), indent=2))
        
        logger.info("Updall completed")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()