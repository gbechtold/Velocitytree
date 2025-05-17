"""
Velocitytree: A Python tool to streamline developer workflows.

Manages project structure, context, and integrates AI assistance.
"""

__version__ = "0.1.0"
__author__ = "Guntram Bechtold"
__license__ = "MIT"

from .core import TreeFlattener, ContextManager
from .cli import main

__all__ = ["TreeFlattener", "ContextManager", "main"]