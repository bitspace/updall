from typing import List, Tuple, Dict, Any
from .base import BaseSystem


class DebianSystem(BaseSystem):
    def get_package_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get Debian-specific update commands (all need sudo)"""
        return [
            ("apt update", {"needs_sudo": True, "handles_sudo_internally": False}),
            ("apt upgrade -y", {"needs_sudo": True, "handles_sudo_internally": False}),
            ("apt autoremove -y", {"needs_sudo": True, "handles_sudo_internally": False}),
            ("apt autoclean", {"needs_sudo": True, "handles_sudo_internally": False})
        ]