"""Test the code analyzer functionality."""

import pytest
import tempfile
import shutil
from pathlib import Path

from velocitytree.code_analysis import CodeAnalyzer, AnalysisResult
from velocitytree.code_analysis.models import (
    Severity,
    IssueCategory,
    LanguageSupport,
    PatternType
)


class TestCodeAnalyzer:
    """Test the CodeAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a code analyzer instance."""
        return CodeAnalyzer()
    
    @pytest.fixture
    def sample_python_code(self):
        """Sample Python code for testing."""
        return '''
"""Sample module for testing code analysis."""

import os
import sys
from typing import List, Optional

# Global variable
GLOBAL_CONFIG = {"debug": True}


class SampleClass:
    """A sample class with various methods."""
    
    def __init__(self, name: str):
        self.name = name
        self._instance = None  # Singleton pattern hint
    
    def get_instance(self):
        """Get singleton instance."""
        if not self._instance:
            self._instance = SampleClass("default")
        return self._instance
    
    def complex_method(self, data: List[int]) -> Optional[int]:
        """A method with high complexity."""
        result = 0
        
        for item in data:
            if item > 0:
                if item % 2 == 0:
                    result += item
                else:
                    result -= item
            elif item < 0:
                if item % 3 == 0:
                    result *= 2
                else:
                    result //= 2
        
        if result > 100:
            return result
        elif result < -100:
            return -result
        else:
            return None


def simple_function(x: int, y: int) -> int:
    """A simple function with docstring."""
    return x + y


def function_without_docstring(x, y):
    # This function lacks documentation
    return x * y


def long_function(data: List[int]) -> int:
    """This function is intentionally long for testing."""
    result = 0
    
    # Many lines of code...
    for i in range(50):
        result += i
        
    for item in data:
        result += item
        
    if result > 1000:
        result = 1000
    elif result < 0:
        result = 0
        
    # More processing...
    for i in range(50):
        result -= i
        
    return result
'''
    
    @pytest.fixture
    def temp_python_file(self, sample_python_code):
        """Create a temporary Python file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(sample_python_code)
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        temp_path.unlink()
    
    def test_analyze_file(self, analyzer, temp_python_file):
        """Test analyzing a single file."""
        result = analyzer.analyze_file(temp_python_file)
        
        assert result is not None
        assert result.file_path == str(temp_python_file)
        assert result.language == LanguageSupport.PYTHON
        
        # Check detected imports
        assert "os" in result.imports
        assert "sys" in result.imports
        assert "typing.List" in result.imports
        
        # Check functions
        assert len(result.functions) == 3
        function_names = [f.name for f in result.functions]
        assert "simple_function" in function_names
        assert "function_without_docstring" in function_names
        assert "long_function" in function_names
        
        # Check classes
        assert len(result.classes) == 1
        assert result.classes[0].name == "SampleClass"
        assert len(result.classes[0].methods) == 3
        
        # Check global variables
        assert "GLOBAL_CONFIG" in result.global_variables
    
    def test_complexity_calculation(self, analyzer, temp_python_file):
        """Test complexity metric calculation."""
        result = analyzer.analyze_file(temp_python_file)
        
        # Check that metrics were calculated
        assert result.metrics is not None
        assert result.metrics.lines_of_code > 0
        assert result.metrics.cyclomatic_complexity > 0
        assert result.metrics.maintainability_index > 0
        
        # Find the complex method
        sample_class = result.classes[0]
        complex_method = next(m for m in sample_class.methods if m.name == "complex_method")
        assert complex_method.complexity > 5  # High complexity
    
    def test_issue_detection(self, analyzer, temp_python_file):
        """Test issue detection."""
        result = analyzer.analyze_file(temp_python_file)
        
        # Should detect missing docstring
        docstring_issues = [i for i in result.issues 
                           if i.rule_id == "missing-docstring"]
        assert len(docstring_issues) > 0
        
        # Should detect long function
        long_function_issues = [i for i in result.issues 
                               if i.rule_id == "long-function"]
        assert len(long_function_issues) > 0
        
        # Should detect high complexity
        complexity_issues = [i for i in result.issues 
                            if i.rule_id == "high-complexity"]
        assert len(complexity_issues) > 0
    
    def test_pattern_detection(self, analyzer, temp_python_file):
        """Test pattern detection."""
        result = analyzer.analyze_file(temp_python_file)
        
        # Should detect singleton pattern
        singleton_patterns = [p for p in result.patterns 
                             if p.name == "Singleton"]
        assert len(singleton_patterns) > 0
        assert singleton_patterns[0].pattern_type == PatternType.DESIGN_PATTERN
    
    def test_analyze_directory(self, analyzer, sample_python_code):
        """Test analyzing a directory."""
        # Create temporary directory with multiple files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create multiple Python files
            (temp_path / "file1.py").write_text(sample_python_code)
            (temp_path / "file2.py").write_text("def test(): pass")
            (temp_path / "subdir").mkdir()
            (temp_path / "subdir" / "file3.py").write_text("class Test: pass")
            
            # Analyze directory
            result = analyzer.analyze_directory(temp_path)
            
            assert isinstance(result, AnalysisResult)
            assert result.files_analyzed == 3
            assert LanguageSupport.PYTHON in result.language_breakdown
            assert result.language_breakdown[LanguageSupport.PYTHON] == 3
            assert len(result.modules) == 3
    
    def test_cache_functionality(self, analyzer, temp_python_file):
        """Test that caching works correctly."""
        # First analysis
        result1 = analyzer.analyze_file(temp_python_file)
        
        # Second analysis should use cache
        result2 = analyzer.analyze_file(temp_python_file)
        
        # Results should be the same
        assert result1.file_path == result2.file_path
        assert len(result1.functions) == len(result2.functions)
        
        # Modify file and analyze again
        with open(temp_python_file, 'a') as f:
            f.write("\ndef new_function(): pass")
        
        result3 = analyzer.analyze_file(temp_python_file)
        
        # Should detect the new function
        assert len(result3.functions) == len(result1.functions) + 1
    
    def test_syntax_error_handling(self, analyzer):
        """Test handling of syntax errors."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("def broken_function(\n    pass")  # Syntax error
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            
            # Should still return a result
            assert result is not None
            
            # Should have syntax error issue
            syntax_errors = [i for i in result.issues 
                            if i.rule_id == "syntax-error"]
            assert len(syntax_errors) > 0
            assert syntax_errors[0].severity == Severity.ERROR
        finally:
            temp_path.unlink()
    
    def test_analyze_changes(self, analyzer):
        """Test analyzing changes between file versions."""
        old_content = """
def simple_function(x, y):
    return x + y
"""
        
        new_content = """
def simple_function(x, y, z):
    # More complex now
    if z:
        return x + y + z
    else:
        return x + y
"""
        
        old_analysis, new_analysis, suggestions = analyzer.analyze_changes(
            old_content, new_content, "test.py"
        )
        
        # Should detect increased complexity
        assert new_analysis.functions[0].complexity > old_analysis.functions[0].complexity
        
        # Should generate suggestions
        assert len(suggestions) > 0
        complexity_suggestions = [s for s in suggestions 
                                if "Complexity" in s.title]
        assert len(complexity_suggestions) > 0
    
    def test_language_detection(self, analyzer):
        """Test language detection from file extension."""
        # Test various extensions
        test_cases = [
            ("test.py", LanguageSupport.PYTHON),
            ("test.js", LanguageSupport.JAVASCRIPT),
            ("test.ts", LanguageSupport.TYPESCRIPT),
            ("test.java", LanguageSupport.JAVA),
            ("test.cpp", LanguageSupport.CPP),
            ("test.go", LanguageSupport.GO),
            ("test.rs", LanguageSupport.RUST),
            ("test.rb", LanguageSupport.RUBY),
        ]
        
        for filename, expected_language in test_cases:
            detected = analyzer._detect_language(Path(filename))
            assert detected == expected_language
    
    def test_unsupported_file_type(self, analyzer):
        """Test handling of unsupported file types."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file")
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            assert result is None  # Should return None for unsupported files
        finally:
            temp_path.unlink()