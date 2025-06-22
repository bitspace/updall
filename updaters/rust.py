from typing import List, Tuple, Dict, Any, Optional
import subprocess


class RustUpdater:
    """Handle Rust toolchain updates"""
    
    @staticmethod
    def get_update_commands() -> List[Tuple[str, Dict[str, Any]]]:
        """Get Rust update commands"""
        return [
            ("rustup update", {"needs_sudo": False}),
            ("cargo install-update -a", {"needs_sudo": False})
        ]
    
    @staticmethod
    def check_availability() -> bool:
        """Check if Rust tools are available"""
        try:
            subprocess.run(["rustup", "--version"], 
                         capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_version_info() -> Optional[str]:
        """Get current Rust version"""
        try:
            result = subprocess.run(["rustc", "--version"], 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    @staticmethod
    def parse_update_output(stdout: str) -> Dict[str, Any]:
        """Parse rustup update output to extract useful information"""
        info = {
            'updated_components': [],
            'already_up_to_date': False,
            'version': None
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            if 'updated' in line.lower():
                info['updated_components'].append(line)
            elif 'up to date' in line.lower():
                info['already_up_to_date'] = True
            elif line.startswith('rustc'):
                info['version'] = line
        
        return info