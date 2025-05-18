"""
Velocitytree: AI-powered development assistant.

Features continuous monitoring, drift detection, smart documentation,
and intelligent suggestions to streamline developer workflows.
"""

__version__ = "2.0.0"
__author__ = "Guntram Bechtold"
__license__ = "MIT"

from .core import TreeFlattener, ContextManager
from .cli import main

__all__ = ["TreeFlattener", "ContextManager", "main"]