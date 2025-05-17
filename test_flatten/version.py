"""
Version information for Velocitytree.
"""

from . import __version__, __author__, __license__
from .utils import get_system_info, get_git_info


def version_info() -> str:
    """Get detailed version information."""
    info = f"""Velocitytree v{__version__}
Author: {__author__}
License: {__license__}

System Information:
"""
    
    # Add system info
    system_info = get_system_info()
    for key, value in system_info.items():
        info += f"  {key}: {value}\n"
    
    # Add git info if available
    git_info = get_git_info()
    if git_info:
        info += "\nGit Information:\n"
        info += f"  Branch: {git_info.get('branch', 'unknown')}\n"
        info += f"  Commit: {git_info.get('commit', 'unknown')}\n"
    
    return info