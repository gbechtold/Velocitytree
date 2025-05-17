"""Language-specific code analysis adapters."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import ModuleAnalysis, LanguageSupport


class BaseLanguageAdapter(ABC):
    """Base class for language-specific analyzers."""
    
    @abstractmethod
    def analyze_module(self, file_path: str, content: str) -> ModuleAnalysis:
        """Analyze a module/file and return analysis results.
        
        Args:
            file_path: Path to the file being analyzed
            content: File content as string
            
        Returns:
            Module analysis results
        """
        pass
    
    @abstractmethod
    def can_analyze(self, file_path: str) -> bool:
        """Check if this adapter can analyze the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if this adapter can handle the file
        """
        pass


# Import specific adapters
from .python_adapter import PythonAdapter


# Registry of available adapters
ADAPTERS = {
    LanguageSupport.PYTHON: PythonAdapter
}


def get_language_adapter(language: LanguageSupport) -> Optional[BaseLanguageAdapter]:
    """Get the appropriate language adapter.
    
    Args:
        language: Programming language
        
    Returns:
        Language adapter instance or None if not available
    """
    adapter_class = ADAPTERS.get(language)
    if adapter_class:
        return adapter_class()
    return None