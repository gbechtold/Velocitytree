"""
Utility functions for Velocitytree.
"""

import os
import sys
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from functools import lru_cache
import colorama
from rich.logging import RichHandler

# Initialize colorama for cross-platform color support
colorama.init()


# Configure logging with Rich handler
def setup_logger(name: str = "velocitytree", level: str = "INFO") -> logging.Logger:
    """Set up a logger with Rich formatting."""
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Create Rich handler
    handler = RichHandler(
        show_time=True,
        show_path=False,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True
    )
    
    # Set format
    handler.setFormatter(logging.Formatter("%(message)s"))
    
    # Add handler and set level
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    return logger


# Global logger instance
logger = setup_logger()


def get_file_info(path: Path) -> Dict[str, Any]:
    """Get detailed information about a file."""
    try:
        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "extension": path.suffix.lower(),
            "is_symlink": path.is_symlink(),
            "is_hidden": path.name.startswith('.'),
            "permissions": oct(stat.st_mode)[-3:],
        }
    except Exception as e:
        logger.error(f"Error getting file info for {path}: {e}")
        return {}


def calculate_file_hash(path: Path, algorithm: str = "md5") -> str:
    """Calculate hash of a file."""
    hash_func = getattr(hashlib, algorithm)()
    
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        return hash_func.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {path}: {e}")
        return ""


def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def get_project_root() -> Path:
    """Find the project root directory."""
    current = Path.cwd()
    
    # Look for common project markers
    markers = [
        '.git',
        '.velocitytree.yaml',
        '.velocitytree.yml',
        '.velocitytree.toml',
        'pyproject.toml',
        'setup.py',
        'package.json',
        'Cargo.toml',
        'go.mod',
    ]
    
    for parent in [current] + list(current.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent
    
    return current


@lru_cache(maxsize=128)
def is_binary_file(path: Path) -> bool:
    """Check if a file is binary."""
    try:
        with open(path, 'rb') as f:
            chunk = f.read(1024)
        
        # Check for null bytes
        if b'\x00' in chunk:
            return True
        
        # Check if file is mostly printable
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = chunk.translate(None, text_chars)
        
        return len(non_text) > len(chunk) * 0.3
    except Exception:
        return True


def run_command(
    command: Union[str, List[str]],
    cwd: Optional[Path] = None,
    capture_output: bool = True,
    check: bool = True
) -> subprocess.CompletedProcess:
    """Run a shell command."""
    if isinstance(command, str):
        command = command.split()
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(command)}")
        logger.error(f"Exit code: {e.returncode}")
        if e.stdout:
            logger.error(f"stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"stderr: {e.stderr}")
        raise


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_git_info() -> Dict[str, Any]:
    """Get information about the current git repository."""
    try:
        # Check if we're in a git repository
        result = run_command("git rev-parse --git-dir", capture_output=True, check=False)
        if result.returncode != 0:
            return {}
        
        info = {
            "branch": run_command("git branch --show-current").stdout.strip(),
            "commit": run_command("git rev-parse HEAD").stdout.strip()[:8],
            "status": run_command("git status --porcelain").stdout.strip(),
            "remotes": run_command("git remote -v").stdout.strip(),
        }
        
        # Get last commit info
        commit_info = run_command(
            "git log -1 --pretty=format:%H%n%an%n%ae%n%at%n%s"
        ).stdout.strip().split('\n')
        
        if len(commit_info) >= 5:
            info["last_commit"] = {
                "hash": commit_info[0],
                "author": commit_info[1],
                "email": commit_info[2],
                "timestamp": commit_info[3],
                "message": commit_info[4],
            }
        
        return info
    except Exception as e:
        logger.debug(f"Error getting git info: {e}")
        return {}


def create_backup(path: Path, suffix: str = ".bak") -> Path:
    """Create a backup of a file."""
    backup_path = path.with_suffix(path.suffix + suffix)
    
    # Find a unique backup name
    if backup_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f"{path.suffix}.{timestamp}{suffix}")
    
    try:
        import shutil
        shutil.copy2(path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def parse_gitignore(gitignore_path: Path) -> List[str]:
    """Parse a .gitignore file and return patterns."""
    patterns = []
    
    try:
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    except Exception as e:
        logger.error(f"Error parsing gitignore: {e}")
    
    return patterns


def is_url(text: str) -> bool:
    """Check if a string is a valid URL."""
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(text) is not None


def get_python_version() -> str:
    """Get the current Python version."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    import platform
    
    return {
        "platform": platform.platform(),
        "python_version": get_python_version(),
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to be filesystem-safe."""
    import re
    
    # Replace invalid characters
    sanitized = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Replace multiple underscores with single
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized or "unnamed"


class ProgressReporter:
    """Simple progress reporter for operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        if self.current > 0:
            rate = self.current / elapsed
            eta = (self.total - self.current) / rate if rate > 0 else 0
        else:
            eta = 0
        
        logger.info(
            f"{self.description}: {self.current}/{self.total} "
            f"({percentage:.1f}%) - ETA: {eta:.1f}s"
        )
    
    def finish(self):
        """Mark progress as complete."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(
            f"{self.description}: Completed {self.total} items "
            f"in {elapsed:.1f} seconds"
        )