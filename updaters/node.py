from typing import List, Tuple, Dict, Any, Optional
import subprocess
import json


class NodeUpdater:
    """Handle Node.js and npm updates"""
    
    @staticmethod
    def get_update_commands() -> List[Tuple[str, Dict[str, Any]]]:
        """Get Node.js update commands"""
        return [
            ("npm update -g", {"needs_sudo": False})
        ]
    
    @staticmethod
    def check_availability() -> bool:
        """Check if Node.js and npm are available"""
        try:
            subprocess.run(["npm", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_version_info() -> Optional[Dict[str, str]]:
        """Get current Node.js and npm versions"""
        try:
            node_result = subprocess.run(["node", "--version"], 
                                       capture_output=True, text=True, check=True)
            npm_result = subprocess.run(["npm", "--version"], 
                                      capture_output=True, text=True, check=True)
            return {
                'node': node_result.stdout.strip(),
                'npm': npm_result.stdout.strip()
            }
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    @staticmethod
    def get_outdated_packages() -> List[str]:
        """Get list of outdated global packages"""
        try:
            result = subprocess.run(["npm", "outdated", "-g", "--json"], 
                                  capture_output=True, text=True, check=True)
            if result.stdout.strip():
                outdated = json.loads(result.stdout)
                return list(outdated.keys())
            return []
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
            return []
    
    @staticmethod
    def parse_update_output(stdout: str) -> Dict[str, Any]:
        """Parse npm update output to extract useful information"""
        info = {
            'updated_packages': [],
            'already_up_to_date': False,
            'errors': []
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            if 'updated' in line.lower():
                info['updated_packages'].append(line)
            elif 'up to date' in line.lower() or 'already at latest' in line.lower():
                info['already_up_to_date'] = True
            elif 'error' in line.lower() or 'warn' in line.lower():
                info['errors'].append(line)
        
        return info