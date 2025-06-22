from typing import List, Tuple, Dict, Any, Optional
import subprocess
import os


class SdkmanUpdater:
    """Handle SDKman updates for Java/Kotlin/Scala SDKs"""
    
    @staticmethod
    def get_update_commands() -> List[Tuple[str, Dict[str, Any]]]:
        """Get SDKman update commands"""
        return [
            ("sdk selfupdate", {"needs_sudo": False}),
            ("sdk update", {"needs_sudo": False}),
            ("sdk upgrade", {"needs_sudo": False})
        ]
    
    @staticmethod
    def check_availability() -> bool:
        """Check if SDKman is available"""
        sdkman_dir = os.path.expanduser("~/.sdkman")
        sdk_script = os.path.join(sdkman_dir, "bin", "sdkman-init.sh")
        return os.path.exists(sdk_script)
    
    @staticmethod
    def get_version_info() -> Optional[str]:
        """Get current SDKman version"""
        try:
            # SDKman requires sourcing its init script
            cmd = 'source ~/.sdkman/bin/sdkman-init.sh && sdk version'
            result = subprocess.run(cmd, shell=True, 
                                  capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    
    @staticmethod
    def get_installed_candidates() -> List[str]:
        """Get list of installed SDK candidates"""
        try:
            cmd = 'source ~/.sdkman/bin/sdkman-init.sh && sdk list'
            result = subprocess.run(cmd, shell=True, 
                                  capture_output=True, text=True, check=True)
            
            candidates = []
            lines = result.stdout.split('\n')
            for line in lines:
                if 'installed' in line.lower():
                    # Extract candidate name from the line
                    parts = line.split()
                    if parts:
                        candidates.append(parts[0])
            return candidates
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []
    
    @staticmethod
    def parse_update_output(stdout: str) -> Dict[str, Any]:
        """Parse SDKman update output to extract useful information"""
        info = {
            'selfupdate_success': False,
            'candidates_updated': [],
            'upgrades_available': [],
            'already_up_to_date': False
        }
        
        lines = stdout.split('\n')
        for line in lines:
            line = line.strip()
            if 'successfully updated' in line.lower():
                info['selfupdate_success'] = True
            elif 'upgrade available' in line.lower():
                info['upgrades_available'].append(line)
            elif 'updated' in line.lower():
                info['candidates_updated'].append(line)
            elif 'up to date' in line.lower() or 'latest' in line.lower():
                info['already_up_to_date'] = True
        
        return info