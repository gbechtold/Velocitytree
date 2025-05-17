"""Test complexity metrics calculation."""

import pytest
import tempfile
from pathlib import Path

from velocitytree.code_analysis import CodeAnalyzer
from velocitytree.code_analysis.metrics import (
    ComplexityCalculator,
    HalsteadMetrics,
    CognitiveComplexityVisitor,
    HalsteadVisitor
)
from velocitytree.code_analysis.models import LanguageSupport


class TestComplexityMetrics:
    """Test the complexity metrics calculation."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a code analyzer instance."""
        return CodeAnalyzer()
    
    @pytest.fixture
    def calculator(self):
        """Create a complexity calculator instance."""
        return ComplexityCalculator()
    
    def test_cyclomatic_complexity_simple(self, calculator):
        """Test cyclomatic complexity for simple function."""
        code = '''
def simple_function(x):
    return x + 1
'''
        import ast
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        complexity = calculator.calculate_cyclomatic_complexity(func_node)
        assert complexity == 1  # Base complexity
    
    def test_cyclomatic_complexity_with_conditions(self, calculator):
        """Test cyclomatic complexity with conditionals."""
        code = '''
def conditional_function(x):
    if x > 0:
        return x
    elif x < 0:
        return -x
    else:
        return 0
'''
        import ast
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        complexity = calculator.calculate_cyclomatic_complexity(func_node)
        assert complexity == 3  # 1 base + 2 decision points (if, elif)
    
    def test_cyclomatic_complexity_with_loops(self, calculator):
        """Test cyclomatic complexity with loops."""
        code = '''
def loop_function(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
    while total > 100:
        total -= 10
    return total
'''
        import ast
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        complexity = calculator.calculate_cyclomatic_complexity(func_node)
        assert complexity == 4  # 1 base + 3 decision points (for, if, while)
    
    def test_cognitive_complexity(self, calculator):
        """Test cognitive complexity calculation."""
        code = '''
def complex_function(data):
    result = 0
    for item in data:
        if item > 0:
            if item % 2 == 0:
                result += item
            else:
                result -= item
        else:
            result *= 2
    return result
'''
        import ast
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        cognitive = calculator.calculate_cognitive_complexity(func_node)
        assert cognitive > 5  # Should account for nesting
    
    def test_halstead_metrics(self, calculator):
        """Test Halstead metrics calculation."""
        code = '''
def calculate(a, b):
    sum_val = a + b
    diff_val = a - b
    return sum_val * diff_val
'''
        import ast
        tree = ast.parse(code)
        
        halstead = calculator.calculate_halstead_metrics(tree)
        
        assert halstead.n1 > 0  # Distinct operators
        assert halstead.n2 > 0  # Distinct operands
        assert halstead.N1 > 0  # Total operators
        assert halstead.N2 > 0  # Total operands
        assert halstead.vocabulary > 0
        assert halstead.length > 0
        assert halstead.volume > 0
    
    def test_maintainability_index(self, analyzer):
        """Test maintainability index calculation."""
        code = '''
def well_documented_function(x, y):
    """Calculate the sum of two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
    return x + y

def poorly_written_function(a, b, c, d, e, f):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return f
    return 0
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            metrics = result.metrics
            
            assert 0 <= metrics.maintainability_index <= 100
            
            # Well-documented simple function should have higher maintainability
            # than complex nested function
            assert metrics.maintainability_index > 50
        finally:
            temp_path.unlink()
    
    def test_complex_file_metrics(self, analyzer):
        """Test metrics for a complex file."""
        code = '''
"""Complex module for testing metrics."""

import math
from typing import List, Optional

class DataProcessor:
    """Process various types of data."""
    
    def __init__(self):
        self.data = []
        self.cache = {}
    
    def process_list(self, items: List[int]) -> int:
        """Process a list of integers with complex logic."""
        total = 0
        
        for i, item in enumerate(items):
            if item > 100:
                if item % 2 == 0:
                    total += item
                else:
                    total -= item
            elif item < 0:
                if abs(item) > 50:
                    total *= 2
                else:
                    total //= 2
            else:
                total += item
        
        return total
    
    def recursive_factorial(self, n: int) -> int:
        """Calculate factorial recursively."""
        if n <= 1:
            return 1
        return n * self.recursive_factorial(n - 1)
    
    def complex_calculation(self, x: float, y: float) -> float:
        """Perform complex mathematical calculation."""
        try:
            result = math.sqrt(x ** 2 + y ** 2)
            
            if result > 10:
                result = math.log(result)
            elif result < 1:
                result = math.exp(result)
            
            return result
        except ValueError:
            return 0.0
        except Exception as e:
            print(f"Error: {e}")
            return -1.0

def standalone_complex_function(data: List[dict]) -> Optional[dict]:
    """Standalone function with high complexity."""
    if not data:
        return None
    
    filtered_data = []
    
    for item in data:
        if "id" in item and "value" in item:
            if item["value"] > 0:
                if item["id"] % 2 == 0:
                    filtered_data.append(item)
    
    if not filtered_data:
        return None
    
    # Find item with max value
    max_item = filtered_data[0]
    for item in filtered_data[1:]:
        if item["value"] > max_item["value"]:
            max_item = item
    
    return max_item
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            metrics = result.metrics
            
            # Check all metrics are calculated
            assert metrics.lines_of_code > 50
            assert metrics.lines_of_comments > 5
            assert metrics.cyclomatic_complexity > 1
            assert metrics.cognitive_complexity > 1
            assert metrics.maintainability_index > 0
            assert metrics.code_to_comment_ratio > 0
            assert metrics.average_function_length > 0
            assert metrics.max_function_length > 0
            assert metrics.number_of_functions == 4
            assert metrics.number_of_classes == 1
            
            # Check technical debt ratio
            assert 0 <= metrics.technical_debt_ratio <= 1
            
            # Check duplicate lines detection
            assert metrics.duplicate_lines >= 0
        finally:
            temp_path.unlink()
    
    def test_edge_cases(self, analyzer):
        """Test edge cases for metrics calculation."""
        # Empty file
        empty_code = ""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(empty_code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            metrics = result.metrics
            
            assert metrics.lines_of_code == 0
            assert metrics.maintainability_index == 100  # Perfect for empty file
        finally:
            temp_path.unlink()
        
        # File with only comments
        comment_only = '''
# This is a comment
# Another comment
"""
This is a docstring
spanning multiple lines
"""
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(comment_only)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            metrics = result.metrics
            
            assert metrics.lines_of_code == 0
            assert metrics.lines_of_comments > 0
        finally:
            temp_path.unlink()
        
        # Syntax error file
        syntax_error_code = '''
def broken_function(
    # Missing closing parenthesis
    pass
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(syntax_error_code)
            temp_path = Path(f.name)
        
        try:
            result = analyzer.analyze_file(temp_path)
            # Should still return metrics even with syntax error
            assert result.metrics is not None
        finally:
            temp_path.unlink()
    
    def test_cognitive_complexity_nesting(self):
        """Test cognitive complexity accounts for nesting correctly."""
        code = '''
def nested_function(data):
    # First level
    if data:
        # Second level
        for item in data:
            # Third level
            if item > 0:
                # Fourth level
                if item % 2 == 0:
                    return item
    return 0
'''
        
        import ast
        tree = ast.parse(code)
        func_node = tree.body[0]
        
        visitor = CognitiveComplexityVisitor()
        complexity = visitor.visit(func_node)
        
        # Should be higher due to nesting
        assert complexity >= 7  # Base complexity plus nesting increments
    
    def test_halstead_visitor_details(self):
        """Test Halstead visitor correctly identifies operators and operands."""
        code = '''
def math_function(x, y):
    result = x + y
    result = result * 2
    return result / 3
'''
        
        import ast
        tree = ast.parse(code)
        
        visitor = HalsteadVisitor()
        visitor.visit(tree)
        
        # Check operators
        assert '+' in str(visitor.operators) or 'Add' in visitor.operators
        assert '*' in str(visitor.operators) or 'Mult' in visitor.operators
        assert '/' in str(visitor.operators) or 'Div' in visitor.operators
        
        # Check operands
        assert 'x' in visitor.operands
        assert 'y' in visitor.operands
        assert '2' in visitor.operands
        assert '3' in visitor.operands