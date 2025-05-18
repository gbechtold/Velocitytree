"""Test smart template selection."""

import pytest
import tempfile
from pathlib import Path

from velocitytree.documentation import TemplateSelector, TemplateManager
from velocitytree.documentation.models import (
    DocTemplate,
    DocType,
    DocFormat,
    DocStyle,
    DocConfig,
)
from velocitytree.code_analysis.analyzer import CodeAnalyzer
from velocitytree.code_analysis.models import ModuleAnalysis


@pytest.fixture
def template_manager():
    """Create a template manager instance."""
    return TemplateManager()


@pytest.fixture
def template_selector(template_manager):
    """Create a template selector instance."""
    return TemplateSelector(template_manager)


@pytest.fixture
def code_analyzer():
    """Create a code analyzer instance."""
    return CodeAnalyzer()


class TestTemplateSelector:
    """Test the smart template selector."""
    
    def test_select_module_template(self, template_selector, code_analyzer):
        """Test selecting template for a module."""
        # Create a sample module
        code = '''
"""Sample module for testing."""

def main():
    """Main function."""
    print("Hello, world!")
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Select template
            template = template_selector.select_template(
                source=analysis,
                doc_type=DocType.MODULE,
                config=DocConfig(),
            )
            
            assert template is not None
            assert template.doc_type == DocType.MODULE
            assert template.format == DocFormat.MARKDOWN
            
        finally:
            temp_path.unlink()
            
    def test_detect_api_module(self, template_selector, code_analyzer):
        """Test detecting API modules."""
        # Create an API module
        code = '''
"""API module for testing."""

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/users', methods=['GET'])
def get_users():
    """Get all users."""
    return jsonify({"users": []})
    
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user."""
    return jsonify({"user": {"id": user_id}})
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Check API detection
            assert template_selector._is_api_module(analysis)
            
            # Select template
            template = template_selector.select_template(
                source=analysis,
                doc_type=DocType.MODULE,
                config=DocConfig(),
            )
            
            # Should still get module template but with API considerations
            assert template.doc_type == DocType.MODULE
            
        finally:
            temp_path.unlink()
            
    def test_detect_cli_tool(self, template_selector, code_analyzer):
        """Test detecting CLI tools."""
        # Create a CLI tool
        code = '''
"""CLI tool for testing."""

import click

@click.command()
@click.option('--count', default=1, help='Number of greetings.')
@click.option('--name', prompt='Your name', help='The person to greet.')
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")
        
if __name__ == '__main__':
    hello()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Check CLI detection
            assert template_selector._is_cli_tool(analysis)
            
        finally:
            temp_path.unlink()
            
    def test_detect_test_file(self, template_selector, code_analyzer):
        """Test detecting test files."""
        # Create a test file
        code = '''
"""Test file for testing."""

import pytest

def test_addition():
    """Test addition function."""
    assert 1 + 1 == 2
    
def test_subtraction():
    """Test subtraction function."""
    assert 5 - 3 == 2
    
class TestMath:
    """Test math operations."""
    
    def test_multiplication(self):
        """Test multiplication."""
        assert 2 * 3 == 6
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', prefix='test_', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Check test detection
            assert template_selector._is_test_file(analysis)
            
        finally:
            temp_path.unlink()
            
    def test_detect_docstring_style(self, template_selector):
        """Test detecting documentation style."""
        # Google style
        google_docstring = """Brief description.
        
        Args:
            param1: Description of param1.
            param2: Description of param2.
            
        Returns:
            Description of return value.
        """
        assert template_selector._detect_docstring_style(google_docstring) == DocStyle.GOOGLE
        
        # NumPy style
        numpy_docstring = """
        Brief description.
        
        Parameters
        ----------
        param1 : int
            Description of param1
        param2 : str
            Description of param2
            
        Returns
        -------
        bool
            Description of return value
        """
        assert template_selector._detect_docstring_style(numpy_docstring) == DocStyle.NUMPY
        
        # Sphinx style
        sphinx_docstring = """
        Brief description.
        
        :param param1: Description of param1
        :param param2: Description of param2
        :return: Description of return value
        :rtype: bool
        """
        assert template_selector._detect_docstring_style(sphinx_docstring) == DocStyle.SPHINX
        
    def test_template_scoring(self, template_selector, template_manager, code_analyzer):
        """Test template scoring mechanism."""
        # Create a sample module
        code = '''
"""Sample module with Google style docstring."""

def example_function(param1, param2):
    """Example function.
    
    Args:
        param1: First parameter
        param2: Second parameter
        
    Returns:
        Combined result
    """
    return param1 + param2
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Get a template
            template = template_manager.get_template(
                doc_type=DocType.MODULE,
                format=DocFormat.MARKDOWN,
                style=DocStyle.GOOGLE,
            )
            
            # Score the template
            score = template_selector._score_template(
                template=template,
                source=analysis,
                context={},
            )
            
            assert score.score > 0
            assert 'type_match' in score.reasoning
            assert 'style_match' in score.reasoning
            
        finally:
            temp_path.unlink()
            
    def test_suggest_improvements(self, template_selector, template_manager, code_analyzer):
        """Test improvement suggestions."""
        # Create an API module
        code = '''
"""API module with NumPy style docstring."""

from flask import Flask

app = Flask(__name__)

@app.route('/api/v1/status')
def get_status():
    """
    Get API status.
    
    Returns
    -------
    dict
        Status information
    """
    return {"status": "ok"}
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Get a non-API template
            template = template_manager.get_template(
                doc_type=DocType.MODULE,
                format=DocFormat.MARKDOWN,
                style=DocStyle.GOOGLE,
            )
            
            # Get suggestions
            suggestions = template_selector.suggest_improvements(
                template=template,
                source=analysis,
            )
            
            # Should suggest API template and style mismatch
            assert len(suggestions) > 0
            assert any('API' in s for s in suggestions)
            assert any('style' in s.lower() for s in suggestions)
            
        finally:
            temp_path.unlink()
            
    def test_get_template_context(self, template_selector, template_manager, code_analyzer):
        """Test extracting template context."""
        # Create a module with version
        code = '''
"""Example module for testing context extraction."""

__version__ = "1.0.0"
__author__ = "Test Author"

import os
import sys
from typing import List

def example_function(items: List[str]) -> str:
    """Process a list of items."""
    return ", ".join(items)
    
class ExampleClass:
    """Example class for testing."""
    
    def __init__(self, name: str):
        """Initialize with name."""
        self.name = name
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Analyze the module
            analysis = code_analyzer.analyze_file(temp_path)
            
            # Get a template
            template = template_manager.get_template(
                doc_type=DocType.MODULE,
                format=DocFormat.MARKDOWN,
            )
            
            # Get context
            context = template_selector.get_template_context(
                source=analysis,
                template=template,
            )
            
            assert 'module_name' in context
            assert 'module_description' in context
            assert 'imports' in context
            assert context['module_name'] == Path(temp_path).stem
            assert 'os' in context['imports']
            
        finally:
            temp_path.unlink()
            
    def test_custom_template_preference(self, template_selector, template_manager):
        """Test preference for custom templates."""
        # Create a custom template
        custom_template = DocTemplate(
            name="custom_test_module",
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
            style=DocStyle.GOOGLE,
            content="# Custom Template",
            placeholders=[],
            required_fields=[],
        )
        
        # Save the custom template
        template_manager.templates[custom_template.name] = custom_template
        
        # Create a regular template
        regular_template = template_manager.get_template(
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
        )
        
        # Score both templates
        mock_analysis = type('MockAnalysis', (), {'docstring': 'Test'})()
        
        custom_score = template_selector._score_template(
            template=custom_template,
            source=mock_analysis,
            context={},
        )
        
        regular_score = template_selector._score_template(
            template=regular_template,
            source=mock_analysis,
            context={},
        )
        
        # Custom template should have bonus points
        assert custom_score.score >= regular_score.score