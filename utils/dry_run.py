from typing import Dict, Any, List, Tuple
import subprocess
from updaters.rust import RustUpdater
from updaters.node import NodeUpdater
from updaters.sdkman import SdkmanUpdater
from updaters.gcloud import GcloudUpdater


class DryRunValidator:
    """Enhanced dry-run mode with validation and detailed output"""
    
    def __init__(self, logger):
        self.logger = logger
        self.validation_results = {}
    
    def validate_system_requirements(self, system_name: str, system_config: Dict[str, Any],
                                   update_types: List[str]) -> Dict[str, Any]:
        """Validate system requirements and tool availability"""
        results = {
            'system_name': system_name,
            'reachable': False,
            'tools_available': {},
            'missing_tools': [],
            'warnings': [],
            'estimated_duration': 0
        }
        
        # Check system reachability
        if system_config.get('ssh'):
            results['reachable'] = self._check_ssh_connectivity(
                system_config['hostname'], 
                system_config['ssh']
            )
        else:
            results['reachable'] = True  # Local system
        
        # Check tool availability for each update type
        for update_type in update_types:
            if update_type == 'rust':
                available = RustUpdater.check_availability()
                results['tools_available']['rust'] = available
                if not available:
                    results['missing_tools'].append('rustup')
                    results['warnings'].append("Rust toolchain not installed")
                else:
                    version = RustUpdater.get_version_info()
                    if version:
                        results['tools_available']['rust_version'] = version
                results['estimated_duration'] += 30 if available else 0
                
            elif update_type == 'node':
                available = NodeUpdater.check_availability()
                results['tools_available']['node'] = available
                if not available:
                    results['missing_tools'].append('npm')
                    results['warnings'].append("Node.js/npm not installed")
                else:
                    version = NodeUpdater.get_version_info()
                    if version:
                        results['tools_available']['node_version'] = version
                    # Check for outdated packages
                    outdated = NodeUpdater.get_outdated_packages()
                    if outdated:
                        results['warnings'].append(f"{len(outdated)} npm packages need updates")
                results['estimated_duration'] += 60 if available else 0
                
            elif update_type == 'sdkman':
                available = SdkmanUpdater.check_availability()
                results['tools_available']['sdkman'] = available
                if not available:
                    results['missing_tools'].append('sdkman')
                    results['warnings'].append("SDKman not installed")
                else:
                    version = SdkmanUpdater.get_version_info()
                    if version:
                        results['tools_available']['sdkman_version'] = version
                results['estimated_duration'] += 45 if available else 0
                
            elif update_type == 'gcloud':
                available = GcloudUpdater.check_availability()
                results['tools_available']['gcloud'] = available
                if not available:
                    results['missing_tools'].append('gcloud')
                    results['warnings'].append("Google Cloud SDK not installed")
                else:
                    version = GcloudUpdater.get_version_info()
                    if version:
                        results['tools_available']['gcloud_version'] = version
                results['estimated_duration'] += 90 if available else 0
                
            elif update_type == 'system_packages':
                if system_config['type'] == 'arch':
                    available = self._check_command_availability('paru')
                    if not available:
                        available = self._check_command_availability('pacman')
                        if available:
                            results['warnings'].append("Using pacman instead of paru")
                    results['tools_available']['package_manager'] = available
                    results['estimated_duration'] += 120 if available else 0
                elif system_config['type'] == 'debian':
                    available = self._check_command_availability('apt')
                    results['tools_available']['package_manager'] = available
                    results['estimated_duration'] += 180 if available else 0
        
        return results
    
    def _check_ssh_connectivity(self, hostname: str, ssh_config: Dict[str, Any]) -> bool:
        """Check if SSH connection is possible"""
        try:
            # Simple connectivity test
            result = subprocess.run([
                'ssh', 
                '-o', 'BatchMode=yes',
                '-o', 'ConnectTimeout=5',
                '-o', 'StrictHostKeyChecking=no',
                f"{ssh_config['user']}@{hostname}",
                'echo "test"'
            ], capture_output=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False
    
    def _check_command_availability(self, command: str) -> bool:
        """Check if a command is available"""
        try:
            subprocess.run(['which', command], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def generate_dry_run_report(self, system_results: Dict[str, Dict[str, Any]]) -> str:
        """Generate comprehensive dry-run report"""
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("           DRY RUN VALIDATION REPORT")
        report_lines.append("=" * 60)
        
        total_systems = len(system_results)
        ready_systems = 0
        total_duration = 0
        
        for system_name, results in system_results.items():
            report_lines.append(f"\n[{system_name}]")
            
            # System reachability
            reachable_symbol = "✓" if results['reachable'] else "✗"
            report_lines.append(f"  {reachable_symbol} System reachable: {'Yes' if results['reachable'] else 'No'}")
            
            # Tool availability
            missing_tools = results.get('missing_tools', [])
            if missing_tools:
                report_lines.append(f"  ⚠  Missing tools: {', '.join(missing_tools)}")
            else:
                report_lines.append("  ✓ All required tools available")
            
            # Version information
            tools_available = results.get('tools_available', {})
            for tool, info in tools_available.items():
                if tool.endswith('_version') and info:
                    tool_name = tool.replace('_version', '')
                    report_lines.append(f"     {tool_name}: {info}")
            
            # Warnings
            warnings = results.get('warnings', [])
            for warning in warnings:
                report_lines.append(f"  ⚠  {warning}")
            
            # Estimated duration
            duration = results.get('estimated_duration', 0)
            if duration > 0:
                report_lines.append(f"  ⏱  Estimated duration: {self._format_duration(duration)}")
                total_duration += duration
            
            if results['reachable'] and not missing_tools:
                ready_systems += 1
        
        # Summary
        report_lines.append("\n" + "-" * 60)
        report_lines.append(f"Summary: {ready_systems}/{total_systems} systems ready for updates")
        if total_duration > 0:
            report_lines.append(f"Total estimated duration: {self._format_duration(total_duration)}")
        
        if ready_systems < total_systems:
            report_lines.append(f"⚠  {total_systems - ready_systems} system(s) have issues that need attention")
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}m {secs}s" if secs > 0 else f"{minutes}m"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m" if minutes > 0 else f"{hours}h"
    
    def validate_commands(self, system, update_types: List[str]) -> List[Tuple[str, Dict[str, Any]]]:
        """Validate and return commands that would be executed"""
        all_commands = []
        
        for update_type in update_types:
            try:
                commands = system.get_commands_for_update_type(update_type)
                for cmd, opts in commands:
                    final_cmd = system.prepare_command(
                        cmd, 
                        opts.get('needs_sudo', False),
                        opts.get('handles_sudo_internally', False)
                    )
                    all_commands.append((final_cmd, {
                        'update_type': update_type,
                        'original_command': cmd,
                        'needs_sudo': opts.get('needs_sudo', False),
                        'handles_sudo_internally': opts.get('handles_sudo_internally', False)
                    }))
            except Exception as e:
                self.logger.warning(f"Could not get commands for {update_type}: {e}")
        
        return all_commands