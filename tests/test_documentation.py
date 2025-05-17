"""Test documentation generation system."""

import pytest
import tempfile
from pathlib import Path

from velocitytree.documentation import DocGenerator, DocFormat, DocStyle
from velocitytree.documentation.models import (
    DocType,
    DocumentationResult,
    DocConfig,
    FunctionDoc,
    ClassDoc,
    ModuleDoc,
)
from velocitytree.documentation.templates import TemplateManager


@pytest.fixture
def doc_generator():
    """Create a documentation generator instance."""
    return DocGenerator()


@pytest.fixture
def template_manager():
    """Create a template manager instance."""
    return TemplateManager()


@pytest.fixture
def sample_python_file():
    """Create a sample Python file for testing."""
    code = '''
"""Sample module for testing documentation generation.

This module contains sample classes and functions to test
the documentation generator.
"""

from typing import List, Optional

__version__ = "1.0.0"


def add_numbers(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        Sum of a and b
        
    Examples:
        >>> add_numbers(2, 3)
        5
        >>> add_numbers(-1, 1)
        0
    """
    return a + b


def complex_function(data: List[dict], 
                    threshold: float = 0.5,
                    validate: bool = True) -> Optional[dict]:
    """Process complex data with multiple parameters.
    
    This function demonstrates a more complex signature with
    optional parameters and type hints.
    
    Args:
        data: List of dictionaries to process
        threshold: Minimum threshold value (default: 0.5)
        validate: Whether to validate input (default: True)
        
    Returns:
        Processed result or None if no valid data
        
    Raises:
        ValueError: If data is empty
        TypeError: If data is not a list
        
    Notes:
        This function uses advanced processing algorithms
        that may be computationally expensive for large datasets.
    """
    if not data:
        raise ValueError("Data cannot be empty")
        
    if not isinstance(data, list):
        raise TypeError("Data must be a list")
        
    # Complex processing logic here
    return data[0] if data else None


class Calculator:
    """A simple calculator class.
    
    This class provides basic arithmetic operations.
    
    Attributes:
        history: List of previous calculations
        precision: Number of decimal places for results
    """
    
    def __init__(self, precision: int = 2):
        """Initialize calculator.
        
        Args:
            precision: Number of decimal places (default: 2)
        """
        self.history: List[str] = []
        self.precision = precision
        
    def add(self, a: float, b: float) -> float:
        """Add two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Sum of a and b
            
        Examples:
            >>> calc = Calculator()
            >>> calc.add(1.5, 2.5)
            4.0
        """
        result = round(a + b, self.precision)
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def multiply(self, a: float, b: float) -> float:
        """Multiply two numbers.
        
        Args:
            a: First number
            b: Second number
            
        Returns:
            Product of a and b
        """
        result = round(a * b, self.precision)
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def get_history(self) -> List[str]:
        """Get calculation history.
        
        Returns:
            List of previous calculations
        """
        return self.history.copy()
        
    def _internal_method(self):
        """Internal method that should not be documented."""
        pass


class AdvancedCalculator(Calculator):
    """An advanced calculator with more operations.
    
    Inherits from Calculator and adds advanced mathematical operations.
    """
    
    def power(self, base: float, exponent: float) -> float:
        """Calculate power of a number.
        
        Args:
            base: Base number
            exponent: Exponent
            
        Returns:
            base raised to the power of exponent
        """
        result = round(base ** exponent, self.precision)
        self.history.append(f"{base} ^ {exponent} = {result}")
        return result


# Module-level constant
PI = 3.14159
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        return Path(f.name)


class TestDocGenerator:
    """Test the documentation generator."""
    
    def test_generate_module_documentation(self, doc_generator, sample_python_file):
        """Test generating module documentation."""
        result = doc_generator.generate_documentation(
            sample_python_file,
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
        )
        
        assert isinstance(result, DocumentationResult)
        assert result.format == DocFormat.MARKDOWN
        assert "Sample module for testing" in result.content
        assert "add_numbers" in result.content
        assert "Calculator" in result.content
        
    def test_generate_function_documentation(self, doc_generator, sample_python_file):
        """Test generating function documentation."""
        result = doc_generator.generate_documentation(
            sample_python_file,
            doc_type=DocType.FUNCTION,
            format=DocFormat.MARKDOWN,
        )
        
        assert "add_numbers" in result.content
        assert "complex_function" in result.content
        assert "Args:" in result.content or "Parameters:" in result.content
        assert "Returns:" in result.content
        
    def test_generate_class_documentation(self, doc_generator, sample_python_file):
        """Test generating class documentation."""
        result = doc_generator.generate_documentation(
            sample_python_file,
            doc_type=DocType.CLASS,
            format=DocFormat.MARKDOWN,
        )
        
        assert "Calculator" in result.content
        assert "AdvancedCalculator" in result.content
        assert "Methods" in result.content
        assert "Attributes" in result.content
        
    def test_generate_api_documentation(self, doc_generator, sample_python_file):
        """Test generating API reference documentation."""
        result = doc_generator.generate_documentation(
            sample_python_file,
            doc_type=DocType.API,
            format=DocFormat.MARKDOWN,
        )
        
        assert "API" in result.content
        assert "Functions" in result.content
        assert "Classes" in result.content
        
    def test_different_formats(self, doc_generator, sample_python_file):
        """Test generating documentation in different formats."""
        formats = [
            DocFormat.MARKDOWN,
            DocFormat.HTML,
            DocFormat.JSON,
            DocFormat.YAML,
        ]
        
        for format in formats:
            result = doc_generator.generate_documentation(
                sample_python_file,
                format=format,
            )
            
            assert result.format == format
            assert len(result.content) > 0
            
    def test_documentation_quality_check(self, doc_generator, sample_python_file):
        """Test documentation quality checking."""
        result = doc_generator.generate_documentation(
            sample_python_file,
            doc_type=DocType.MODULE,
        )
        
        # Should have some quality issues (missing docstrings for some items)
        assert len(result.issues) > 0
        assert result.quality_score < 100
        assert result.completeness_score > 0
        
    def test_parse_google_docstring(self, doc_generator):
        """Test parsing Google-style docstring."""
        docstring = """Calculate something complex.
        
        This function does complex calculations.
        
        Args:
            data: Input data
            threshold: Minimum threshold value
            
        Returns:
            Calculated result
            
        Raises:
            ValueError: If data is invalid
            
        Examples:
            >>> calculate(data, 0.5)
            42
            
        Notes:
            This is computationally expensive.
        """
        
        parsed = doc_generator._parse_google_docstring(docstring)
        
        assert parsed['description'].startswith("Calculate something complex")
        assert 'data' in parsed['parameters']
        assert 'threshold' in parsed['parameters']
        assert parsed['returns'] == "Calculated result"
        assert "ValueError" in parsed['raises'][0]
        assert len(parsed['examples']) > 0
        assert parsed['notes'] == "This is computationally expensive."
        
    def test_custom_config(self, sample_python_file):
        """Test documentation generation with custom config."""
        config = DocConfig(
            format=DocFormat.RST,
            style=DocStyle.NUMPY,
            include_private=True,
            include_examples=False,
        )
        
        doc_generator = DocGenerator(config)
        result = doc_generator.generate_documentation(sample_python_file)
        
        assert result.format == DocFormat.RST
        # Private methods should be included
        assert "_internal_method" in result.content or config.include_private


class TestTemplateManager:
    """Test the template manager."""
    
    def test_builtin_templates(self, template_manager):
        """Test built-in templates are loaded."""
        templates = template_manager.list_templates()
        
        assert len(templates) > 0
        assert any(t.name == "module_markdown" for t in templates)
        assert any(t.name == "function_markdown" for t in templates)
        assert any(t.name == "class_markdown" for t in templates)
        
    def test_get_template(self, template_manager):
        """Test getting templates by criteria."""
        template = template_manager.get_template(
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
        )
        
        assert template is not None
        assert template.doc_type == DocType.MODULE
        assert template.format == DocFormat.MARKDOWN
        
    def test_render_template(self, template_manager):
        """Test rendering a template."""
        template = template_manager.get_template(
            doc_type=DocType.FUNCTION,
            format=DocFormat.MARKDOWN,
        )
        
        context = {
            'function_name': 'test_function',
            'function_signature': 'test_function(a, b)',
            'description': 'Test function description',
            'parameters': '- a: First parameter\n- b: Second parameter',
            'returns': 'Test result',
            'raises': 'None',
            'examples': 'test_function(1, 2)',
            'see_also': 'other_function',
        }
        
        rendered = template_manager.render_template(template, context)
        
        assert 'test_function' in rendered
        assert 'Test function description' in rendered
        assert 'First parameter' in rendered
        
    def test_save_custom_template(self, template_manager, tmp_path):
        """Test saving a custom template."""
        template_manager.template_dir = tmp_path
        
        template = template_manager.templates["module_markdown"]
        template.name = "custom_module"
        
        template_manager.save_template(template)
        
        # Verify file was created
        template_file = tmp_path / "custom_module.yaml"
        assert template_file.exists()
        
        # Verify template is in manager
        assert "custom_module" in template_manager.templates
        
    def test_template_validation(self, template_manager):
        """Test template validation with required fields."""
        template = template_manager.get_template(
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
        )
        
        # Missing required fields should raise error
        with pytest.raises(ValueError):
            template_manager.render_template(
                template,
                context={},
                strict=True,
            )
            
        # With required fields should work
        context = {
            'module_name': 'test_module',
            'module_description': 'Test description',
        }
        
        rendered = template_manager.render_template(template, context)
        assert 'test_module' in rendered


class TestFunctionDoc:
    """Test function documentation model."""
    
    def test_function_doc_creation(self):
        """Test creating function documentation."""
        func_doc = FunctionDoc(
            name="test_function",
            signature="test_function(a: int, b: int) -> int",
            description="Test function that adds numbers",
            parameters={
                "a": "First number",
                "b": "Second number",
            },
            returns="Sum of a and b",
            examples=["test_function(1, 2) # Returns 3"],
        )
        
        assert func_doc.name == "test_function"
        assert len(func_doc.parameters) == 2
        assert func_doc.returns == "Sum of a and b"
        assert len(func_doc.examples) == 1


class TestClassDoc:
    """Test class documentation model."""
    
    def test_class_doc_creation(self):
        """Test creating class documentation."""
        method_doc = FunctionDoc(
            name="add",
            signature="add(self, a: int, b: int) -> int",
            description="Add two numbers",
            parameters={
                "a": "First number",
                "b": "Second number",
            },
            returns="Sum of a and b",
        )
        
        class_doc = ClassDoc(
            name="Calculator",
            description="A simple calculator class",
            attributes={
                "precision": "Number of decimal places",
            },
            methods=[method_doc],
        )
        
        assert class_doc.name == "Calculator"
        assert len(class_doc.attributes) == 1
        assert len(class_doc.methods) == 1
        assert class_doc.methods[0].name == "add"


def test_end_to_end_documentation(doc_generator, sample_python_file):
    """Test end-to-end documentation generation."""
    # Generate documentation
    result = doc_generator.generate_documentation(
        sample_python_file,
        doc_type=DocType.MODULE,
        format=DocFormat.MARKDOWN,
    )
    
    # Verify content
    assert result.metadata.title == "sample_python_file"
    assert result.quality_score > 0
    assert result.completeness_score > 0
    
    # Check for expected sections
    content = result.content
    assert "## Functions" in content
    assert "## Classes" in content
    assert "add_numbers" in content
    assert "Calculator" in content
    assert "__version__" in content or "1.0.0" in content
    
    # Verify generation time
    assert result.generation_time > 0