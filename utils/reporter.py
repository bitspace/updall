from typing import Dict, Any, List
from datetime import datetime
import time


class UpdateReporter:
    """Generate unified update reports"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.system_results = {}
    
    def set_start_time(self):
        """Record the start time of updates"""
        self.start_time = datetime.now()
    
    def set_end_time(self):
        """Record the end time of updates"""
        self.end_time = datetime.now()
    
    def add_system_result(self, system_name: str, results: Dict[str, Any]):
        """Add results for a system"""
        self.system_results[system_name] = results
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive summary report"""
        if not self.start_time:
            self.start_time = datetime.now()
        if not self.end_time:
            self.end_time = datetime.now()
        
        duration = self.end_time - self.start_time
        
        report_lines = []
        report_lines.append("=" * 50)
        report_lines.append("         System Update Report")
        report_lines.append("=" * 50)
        report_lines.append(f"Started:   {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Completed: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Duration:  {self._format_duration(duration.total_seconds())}")
        report_lines.append("")
        
        total_systems = len(self.system_results)
        successful_systems = 0
        failed_systems = 0
        
        for system_name, results in self.system_results.items():
            report_lines.append(f"[{system_name}]")
            
            system_success = True
            if 'connection_error' in results:
                report_lines.append(f"  ✗ Connection failed: {results['connection_error'].get('error', 'Unknown error')}")
                system_success = False
                failed_systems += 1
            else:
                for update_type, result in results.items():
                    if update_type == 'connection_error':
                        continue
                    
                    success = result.get('success', False)
                    status_symbol = "✓" if success else "✗"
                    
                    # Generate detailed status message
                    status_msg = self._generate_update_status(update_type, result)
                    report_lines.append(f"  {status_symbol} {status_msg}")
                    
                    if not success:
                        system_success = False
                
                if system_success:
                    successful_systems += 1
                else:
                    failed_systems += 1
            
            report_lines.append("")
        
        # Add summary statistics
        report_lines.append("-" * 50)
        report_lines.append(f"Summary: {successful_systems}/{total_systems} systems updated successfully")
        if failed_systems > 0:
            report_lines.append(f"Failed:  {failed_systems} system(s) had errors")
        report_lines.append("=" * 50)
        
        return "\n".join(report_lines)
    
    def _generate_update_status(self, update_type: str, result: Dict[str, Any]) -> str:
        """Generate detailed status message for an update type"""
        if not result.get('success', False):
            if 'error' in result:
                return f"{update_type}: Error - {result['error']}"
            else:
                return f"{update_type}: Failed"
        
        # Success case - try to extract meaningful info from commands
        commands = result.get('commands', [])
        if not commands:
            return f"{update_type}: Success"
        
        # Analyze command outputs for more detailed reporting
        total_duration = sum(cmd.get('duration', 0) for cmd in commands)
        
        if update_type == 'system_packages':
            return self._parse_package_update_status(commands, total_duration)
        elif update_type == 'rust':
            return self._parse_rust_update_status(commands, total_duration)
        elif update_type == 'node':
            return self._parse_node_update_status(commands, total_duration)
        elif update_type == 'sdkman':
            return self._parse_sdkman_update_status(commands, total_duration)
        elif update_type == 'gcloud':
            return self._parse_gcloud_update_status(commands, total_duration)
        else:
            return f"{update_type}: Success ({self._format_duration(total_duration)})"
    
    def _parse_package_update_status(self, commands: List[Dict], duration: float) -> str:
        """Parse package manager update status"""
        from updaters.package_manager import PackageManagerUpdater
        
        updated_packages = 0
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            if 'paru' in cmd.get('command', ''):
                info = PackageManagerUpdater.parse_paru_output(stdout)
                updated_packages += info['total_packages']
            elif 'apt' in cmd.get('command', ''):
                info = PackageManagerUpdater.parse_apt_output(stdout)
                updated_packages += info['total_packages']
        
        if updated_packages > 0:
            return f"System packages: {updated_packages} packages updated ({self._format_duration(duration)})"
        else:
            return f"System packages: Already up to date ({self._format_duration(duration)})"
    
    def _parse_rust_update_status(self, commands: List[Dict], duration: float) -> str:
        """Parse Rust update status"""
        from updaters.rust import RustUpdater
        
        updates_found = False
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            info = RustUpdater.parse_update_output(stdout)
            if info['updated_components'] or not info['already_up_to_date']:
                updates_found = True
                break
        
        if updates_found:
            return f"Rust: Updated ({self._format_duration(duration)})"
        else:
            return f"Rust: Already up to date ({self._format_duration(duration)})"
    
    def _parse_node_update_status(self, commands: List[Dict], duration: float) -> str:
        """Parse Node.js update status"""
        from updaters.node import NodeUpdater
        
        updates_found = False
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            info = NodeUpdater.parse_update_output(stdout)
            if info['updated_packages']:
                updates_found = True
                break
        
        package_count = 0
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            info = NodeUpdater.parse_update_output(stdout)
            package_count += len(info['updated_packages'])
        
        if updates_found and package_count > 0:
            return f"Node.js: {package_count} packages updated ({self._format_duration(duration)})"
        elif updates_found:
            return f"Node.js: Updated ({self._format_duration(duration)})"
        else:
            return f"Node.js: Already up to date ({self._format_duration(duration)})"
    
    def _parse_sdkman_update_status(self, commands: List[Dict], duration: float) -> str:
        """Parse SDKman update status"""
        from updaters.sdkman import SdkmanUpdater
        
        updates_found = False
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            info = SdkmanUpdater.parse_update_output(stdout)
            if info['candidates_updated'] or info['selfupdate_success']:
                updates_found = True
                break
        
        if updates_found:
            return f"SDKman: Updated ({self._format_duration(duration)})"
        else:
            return f"SDKman: Already up to date ({self._format_duration(duration)})"
    
    def _parse_gcloud_update_status(self, commands: List[Dict], duration: float) -> str:
        """Parse Google Cloud SDK update status"""
        from updaters.gcloud import GcloudUpdater
        
        updates_found = False
        for cmd in commands:
            stdout = cmd.get('stdout', '')
            info = GcloudUpdater.parse_update_output(stdout)
            if info['updated_components']:
                updates_found = True
                break
        
        if updates_found:
            return f"Google Cloud SDK: Updated ({self._format_duration(duration)})"
        else:
            return f"Google Cloud SDK: Already up to date ({self._format_duration(duration)})"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in a human-readable way"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def generate_json_report(self) -> Dict[str, Any]:
        """Generate a JSON-formatted report"""
        if not self.start_time:
            self.start_time = datetime.now()
        if not self.end_time:
            self.end_time = datetime.now()
        
        duration = self.end_time - self.start_time
        
        return {
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'systems': self.system_results,
            'summary': {
                'total_systems': len(self.system_results),
                'successful_systems': sum(1 for results in self.system_results.values() 
                                        if not any(not result.get('success', True) 
                                                 for result in results.values())),
                'failed_systems': sum(1 for results in self.system_results.values() 
                                    if any(not result.get('success', True) 
                                         for result in results.values()))
            }
        }