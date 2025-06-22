from typing import List, Tuple, Dict, Any, Optional
import subprocess
import re


class PackageManagerUpdater:
    """Handle package manager updates for different distributions"""
    
    @staticmethod
    def parse_paru_output(stdout: str) -> Dict[str, Any]:
        """Parse paru output to extract useful information"""
        info = {
            'packages_updated': [],
            'aur_packages_updated': [],
            'already_up_to_date': False,
            'total_packages': 0,
            'total_download_size': None,
            'errors': []
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check for package updates
            if ' -> ' in line and ('upgraded' in line or 'installed' in line):
                info['packages_updated'].append(line)
            elif 'AUR' in line and 'updated' in line:
                info['aur_packages_updated'].append(line)
            elif 'up to date' in line.lower() or 'nothing to do' in line.lower():
                info['already_up_to_date'] = True
            elif 'Total Download Size:' in line:
                info['total_download_size'] = line.split(':')[1].strip()
            elif 'error' in line.lower() or 'failed' in line.lower():
                info['errors'].append(line)
        
        info['total_packages'] = len(info['packages_updated']) + len(info['aur_packages_updated'])
        return info
    
    @staticmethod
    def parse_apt_output(stdout: str) -> Dict[str, Any]:
        """Parse apt output to extract useful information"""
        info = {
            'packages_updated': [],
            'packages_installed': [],
            'packages_removed': [],
            'already_up_to_date': False,
            'total_packages': 0,
            'download_size': None,
            'errors': []
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            
            # Parse apt upgrade output
            if 'upgraded,' in line:
                # Extract numbers from "X upgraded, Y newly installed, Z to remove"
                match = re.search(r'(\d+) upgraded', line)
                if match:
                    info['total_packages'] = int(match.group(1))
            elif line.startswith('Get:') and 'http' in line:
                # Package download lines
                info['packages_updated'].append(line)
            elif 'up to date' in line.lower() or '0 upgraded' in line:
                info['already_up_to_date'] = True
            elif 'Need to get' in line:
                info['download_size'] = line
            elif 'error' in line.lower() or 'failed' in line.lower():
                info['errors'].append(line)
        
        return info
    
    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """Get system information for reporting"""
        info = {}
        
        try:
            # Get OS release information
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('PRETTY_NAME='):
                        info['os'] = line.split('=')[1].strip().strip('"')
                        break
        except FileNotFoundError:
            info['os'] = 'Unknown'
        
        try:
            # Get hostname
            result = subprocess.run(['hostname'], capture_output=True, text=True, check=True)
            info['hostname'] = result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            info['hostname'] = 'Unknown'
        
        return info