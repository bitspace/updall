from typing import List, Tuple, Dict, Any
from .base import BaseSystem


class ArchSystem(BaseSystem):
    def get_package_update_commands(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Get Arch-specific update commands
        paru handles sudo internally and should NOT be run with sudo
        """
        return [
            ("paru -Syu --noconfirm", {"needs_sudo": True, "handles_sudo_internally": True}),
            ("paru -Sua --noconfirm", {"needs_sudo": True, "handles_sudo_internally": True})
        ]