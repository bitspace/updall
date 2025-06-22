from typing import List, Tuple, Dict, Any, Optional
import subprocess


class GcloudUpdater:
    """Handle Google Cloud SDK updates"""
    
    @staticmethod
    def get_update_commands() -> List[Tuple[str, Dict[str, Any]]]:
        """Get Google Cloud SDK update commands"""
        return [
            ("gcloud components update --quiet", {"needs_sudo": False})
        ]
    
    @staticmethod
    def check_availability() -> bool:
        """Check if Google Cloud SDK is available"""
        try:
            subprocess.run(["gcloud", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_version_info() -> Optional[Dict[str, str]]:
        """Get current Google Cloud SDK version info"""
        try:
            result = subprocess.run(["gcloud", "--version"], 
                                  capture_output=True, text=True, check=True)
            
            version_info = {}
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'Google Cloud SDK' in line:
                    version_info['sdk'] = line
                elif 'bq' in line and line.startswith('bq'):
                    version_info['bq'] = line
                elif 'gsutil' in line and line.startswith('gsutil'):
                    version_info['gsutil'] = line
                elif 'gcloud' in line and line.startswith('gcloud'):
                    version_info['gcloud'] = line
            
            return version_info
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    @staticmethod
    def get_installed_components() -> List[str]:
        """Get list of installed gcloud components"""
        try:
            result = subprocess.run(["gcloud", "components", "list", "--only-local-state"], 
                                  capture_output=True, text=True, check=True)
            
            components = []
            lines = result.stdout.split('\n')
            in_components_section = False
            
            for line in lines:
                line = line.strip()
                if 'COMPONENT NAME' in line:
                    in_components_section = True
                    continue
                elif in_components_section and line and not line.startswith('-'):
                    parts = line.split()
                    if parts and 'Installed' in line:
                        components.append(parts[0])
            
            return components
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
    
    @staticmethod
    def parse_update_output(stdout: str) -> Dict[str, Any]:
        """Parse gcloud components update output to extract useful information"""
        info = {
            'updated_components': [],
            'already_up_to_date': False,
            'new_version': None,
            'errors': []
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            if 'updated' in line.lower() and 'component' in line.lower():
                info['updated_components'].append(line)
            elif 'up to date' in line.lower() or 'already at latest' in line.lower():
                info['already_up_to_date'] = True
            elif 'version' in line.lower() and ('updated to' in line.lower() or 'installing' in line.lower()):
                info['new_version'] = line
            elif 'error' in line.lower() or 'failed' in line.lower():
                info['errors'].append(line)
        
        return info