"""Claude integration for enhanced AI capabilities."""

from .provider import LocalClaudeProvider, ClaudeConfig
from .streaming import ContextStreamer, StreamConfig
from .prompts import PromptManager, PromptTemplate
from .cache import ResponseCache

__all__ = [
    'LocalClaudeProvider',
    'ClaudeConfig',
    'ContextStreamer',
    'StreamConfig',
    'PromptManager',
    'PromptTemplate',
    'ResponseCache',
]