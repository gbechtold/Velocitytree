"""
IDE integration modules for VelocityTree.
Provides language server protocol (LSP) support and IDE-specific plugins.
"""

from .lsp_server import VelocityTreeLanguageServer
from .vscode_extension import VSCodeExtension
from .feedback_ui import FeedbackUIProvider

__all__ = [
    'VelocityTreeLanguageServer',
    'VSCodeExtension', 
    'FeedbackUIProvider'
]