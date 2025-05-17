"""Advanced complexity metrics calculation for code analysis."""

import ast
import math
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

from .models import (
    CodeMetrics,
    FunctionAnalysis,
    ClassAnalysis,
    ModuleAnalysis,
    LanguageSupport,
    CodeLocation
)


@dataclass
class HalsteadMetrics:
    """Halstead complexity metrics."""
    n1: int  # Number of distinct operators
    n2: int  # Number of distinct operands
    N1: int  # Total number of operators
    N2: int  # Total number of operands
    
    @property
    def vocabulary(self) -> int:
        """Program vocabulary (n)."""
        return self.n1 + self.n2
    
    @property
    def length(self) -> int:
        """Program length (N)."""
        return self.N1 + self.N2
    
    @property
    def calculated_length(self) -> float:
        """Calculated program length."""
        if self.n1 == 0 or self.n2 == 0:
            return 0
        return self.n1 * math.log2(self.n1) + self.n2 * math.log2(self.n2)
    
    @property
    def volume(self) -> float:
        """Program volume (V)."""
        if self.vocabulary == 0:
            return 0
        return self.length * math.log2(self.vocabulary)
    
    @property
    def difficulty(self) -> float:
        """Program difficulty (D)."""
        if self.n2 == 0 or self.N2 == 0:
            return 0
        return (self.n1 / 2) * (self.N2 / self.n2)
    
    @property
    def effort(self) -> float:
        """Program effort (E)."""
        return self.difficulty * self.volume
    
    @property
    def time(self) -> float:
        """Time required to program (T) in seconds."""
        return self.effort / 18  # 18 = Stroud number
    
    @property
    def bugs(self) -> float:
        """Estimated number of bugs (B)."""
        return self.volume / 3000  # Empirical constant


class ComplexityCalculator:
    """Calculate various complexity metrics for code."""
    
    def __init__(self):
        self.operators = {
            # Python operators
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.LShift, ast.RShift, ast.BitOr, ast.BitXor, ast.BitAnd,
            ast.FloorDiv, ast.And, ast.Or, ast.Not, ast.Invert,
            ast.UAdd, ast.USub, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
            ast.Gt, ast.GtE, ast.Is, ast.IsNot, ast.In, ast.NotIn
        }
    
    def calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe's cyclomatic complexity.
        
        Formula: M = E - N + 2P
        Where:
        - E = number of edges
        - N = number of nodes
        - P = number of connected components (usually 1)
        
        Simplified: Count decision points + 1
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Count each 'and' or 'or' 
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
            elif isinstance(child, ast.Lambda):
                complexity += 1
        
        return complexity
    
    def calculate_cognitive_complexity(self, node: ast.AST) -> int:
        """Calculate cognitive complexity (how hard code is to understand).
        
        Based on:
        1. Nesting level
        2. Control flow breaks
        3. Logical operations
        """
        return CognitiveComplexityVisitor().visit(node)
    
    def calculate_halstead_metrics(self, node: ast.AST) -> HalsteadMetrics:
        """Calculate Halstead complexity metrics."""
        visitor = HalsteadVisitor()
        visitor.visit(node)
        
        return HalsteadMetrics(
            n1=len(visitor.operators),
            n2=len(visitor.operands),
            N1=visitor.total_operators,
            N2=visitor.total_operands
        )
    
    def calculate_maintainability_index(self, module: ModuleAnalysis) -> float:
        """Calculate Maintainability Index.
        
        Formula: MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        Where:
        - HV = Halstead Volume
        - CC = Cyclomatic Complexity
        - LOC = Lines of Code
        
        Optionally adjusted by comments:
        MI = MI + 50 * sin(sqrt(2.4 * CM))
        Where CM = Comment percentage
        """
        # Get average complexity for the module
        total_complexity = 0
        function_count = 0
        
        for func in module.functions:
            total_complexity += func.complexity
            function_count += 1
        
        for cls in module.classes:
            for method in cls.methods:
                total_complexity += method.complexity
                function_count += 1
        
        avg_complexity = total_complexity / function_count if function_count > 0 else 1
        
        # Get Halstead volume (simplified)
        halstead_volume = module.metrics.lines_of_code * 10  # Simplified approximation
        
        # Calculate base MI
        loc = module.metrics.lines_of_code
        if loc == 0:
            return 100  # Perfect maintainability for empty file
        
        mi = 171 - 5.2 * math.log(halstead_volume) - 0.23 * avg_complexity - 16.2 * math.log(loc)
        
        # Adjust for comments
        comment_ratio = module.metrics.lines_of_comments / (loc + module.metrics.lines_of_comments)
        if comment_ratio > 0:
            mi = mi + 50 * math.sin(math.sqrt(2.4 * comment_ratio))
        
        # Ensure MI is in valid range [0, 100]
        return max(0, min(100, mi))
    
    def calculate_complexity_metrics(self, module: ModuleAnalysis, content: str) -> CodeMetrics:
        """Calculate all complexity metrics for a module."""
        # Parse AST for detailed analysis
        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Return default metrics for files with syntax errors
            return self._default_metrics(module, content)
        
        # Calculate module-level metrics
        module_cyclomatic = self.calculate_cyclomatic_complexity(tree)
        module_cognitive = self.calculate_cognitive_complexity(tree)
        halstead = self.calculate_halstead_metrics(tree)
        
        # Calculate metrics for all functions
        all_functions = module.functions + [
            method for cls in module.classes 
            for method in cls.methods
        ]
        
        function_complexities = []
        function_lengths = []
        
        for func in all_functions:
            # Get function node from AST
            func_node = self._find_function_node(tree, func.name)
            if func_node:
                func_complexity = self.calculate_cyclomatic_complexity(func_node)
                func.complexity = func_complexity
                function_complexities.append(func_complexity)
                
                func_length = func.location.line_end - func.location.line_start + 1
                function_lengths.append(func_length)
        
        # Calculate aggregate metrics
        lines = content.splitlines()
        lines_of_code = len([line for line in lines if line.strip()])
        lines_of_comments = self._count_comment_lines(content, module.language)
        
        avg_complexity = sum(function_complexities) / len(function_complexities) if function_complexities else module_cyclomatic
        avg_function_length = sum(function_lengths) / len(function_lengths) if function_lengths else 0
        max_function_length = max(function_lengths) if function_lengths else 0
        
        # Calculate additional metrics
        duplicate_lines = self._estimate_duplicate_lines(content)
        technical_debt_ratio = self._calculate_technical_debt(avg_complexity, lines_of_code)
        
        metrics = CodeMetrics(
            lines_of_code=lines_of_code,
            lines_of_comments=lines_of_comments,
            cyclomatic_complexity=avg_complexity,
            cognitive_complexity=module_cognitive,
            maintainability_index=0,  # Will be calculated separately
            test_coverage=None,  # Would require test execution
            duplicate_lines=duplicate_lines,
            technical_debt_ratio=technical_debt_ratio,
            code_to_comment_ratio=lines_of_code / (lines_of_comments + 1),
            average_function_length=avg_function_length,
            max_function_length=max_function_length,
            number_of_functions=len(module.functions),
            number_of_classes=len(module.classes)
        )
        
        # Calculate maintainability index with full metrics
        module.metrics = metrics
        metrics.maintainability_index = self.calculate_maintainability_index(module)
        
        return metrics
    
    def _find_function_node(self, tree: ast.AST, func_name: str) -> Optional[ast.FunctionDef]:
        """Find a function node in the AST by name."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    return node
        return None
    
    def _count_comment_lines(self, content: str, language: LanguageSupport) -> int:
        """Count comment lines in code."""
        if language == LanguageSupport.PYTHON:
            lines = content.splitlines()
            comment_lines = 0
            in_docstring = False
            docstring_delimiter = None
            
            for line in lines:
                stripped = line.strip()
                
                # Single-line comments
                if stripped.startswith('#'):
                    comment_lines += 1
                # Docstrings
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    delimiter = stripped[:3]
                    if not in_docstring:
                        in_docstring = True
                        docstring_delimiter = delimiter
                        comment_lines += 1
                        # Check if it's a single-line docstring
                        if stripped.endswith(delimiter) and len(stripped) > 6:
                            in_docstring = False
                    elif stripped.endswith(docstring_delimiter):
                        in_docstring = False
                        comment_lines += 1
                elif in_docstring:
                    comment_lines += 1
            
            return comment_lines
        
        # Simple fallback for other languages
        return len([line for line in content.splitlines() 
                   if line.strip().startswith('//') or line.strip().startswith('/*')])
    
    def _estimate_duplicate_lines(self, content: str) -> int:
        """Estimate number of duplicate lines."""
        lines = content.splitlines()
        stripped_lines = [line.strip() for line in lines if line.strip()]
        
        # Count duplicates (simple approach)
        line_counts = defaultdict(int)
        for line in stripped_lines:
            if len(line) > 10:  # Ignore very short lines
                line_counts[line] += 1
        
        duplicate_count = sum(count - 1 for count in line_counts.values() if count > 1)
        return duplicate_count
    
    def _calculate_technical_debt(self, complexity: float, loc: int) -> float:
        """Calculate technical debt ratio based on complexity and size."""
        if loc == 0:
            return 0.0
        
        # Simple formula: higher complexity and size increase debt
        debt_score = (complexity / 10) * (loc / 1000)
        
        # Normalize to 0-1 range
        return min(1.0, debt_score)
    
    def _default_metrics(self, module: ModuleAnalysis, content: str) -> CodeMetrics:
        """Return default metrics for files that can't be parsed."""
        lines = content.splitlines()
        lines_of_code = len([line for line in lines if line.strip()])
        
        return CodeMetrics(
            lines_of_code=lines_of_code,
            lines_of_comments=0,
            cyclomatic_complexity=1,
            cognitive_complexity=1,
            maintainability_index=50,
            duplicate_lines=0,
            technical_debt_ratio=0.5,
            code_to_comment_ratio=float('inf'),
            average_function_length=0,
            max_function_length=0,
            number_of_functions=len(module.functions),
            number_of_classes=len(module.classes)
        )


class CognitiveComplexityVisitor(ast.NodeVisitor):
    """Calculate cognitive complexity by visiting AST nodes."""
    
    def __init__(self):
        self.complexity = 0
        self.nesting_level = 0
    
    def visit(self, node):
        """Visit a node and return total complexity."""
        super().visit(node)
        return self.complexity
    
    def visit_If(self, node):
        """If statements increase complexity."""
        self.complexity += (1 + self.nesting_level)
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_While(self, node):
        """While loops increase complexity."""
        self.complexity += (1 + self.nesting_level)
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_For(self, node):
        """For loops increase complexity."""
        self.complexity += (1 + self.nesting_level)
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_ExceptHandler(self, node):
        """Exception handlers increase complexity."""
        self.complexity += (1 + self.nesting_level)
        self.nesting_level += 1
        self.generic_visit(node)
        self.nesting_level -= 1
    
    def visit_BoolOp(self, node):
        """Boolean operations increase complexity."""
        # Each additional boolean operator adds complexity
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
    
    def visit_Lambda(self, node):
        """Lambda functions increase complexity."""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ListComp(self, node):
        """List comprehensions increase complexity."""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_DictComp(self, node):
        """Dict comprehensions increase complexity."""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_SetComp(self, node):
        """Set comprehensions increase complexity."""
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_GeneratorExp(self, node):
        """Generator expressions increase complexity."""
        self.complexity += 1
        self.generic_visit(node)


class HalsteadVisitor(ast.NodeVisitor):
    """Calculate Halstead metrics by visiting AST nodes."""
    
    def __init__(self):
        self.operators: Set[str] = set()
        self.operands: Set[str] = set()
        self.total_operators = 0
        self.total_operands = 0
    
    def visit_BinOp(self, node):
        """Count binary operators."""
        op_name = type(node.op).__name__
        self.operators.add(op_name)
        self.total_operators += 1
        self.generic_visit(node)
    
    def visit_UnaryOp(self, node):
        """Count unary operators."""
        op_name = type(node.op).__name__
        self.operators.add(op_name)
        self.total_operators += 1
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        """Count boolean operators."""
        op_name = type(node.op).__name__
        self.operators.add(op_name)
        self.total_operators += 1
        self.generic_visit(node)
    
    def visit_Compare(self, node):
        """Count comparison operators."""
        for op in node.ops:
            op_name = type(op).__name__
            self.operators.add(op_name)
            self.total_operators += 1
        self.generic_visit(node)
    
    def visit_Name(self, node):
        """Count variable names as operands."""
        self.operands.add(node.id)
        self.total_operands += 1
        self.generic_visit(node)
    
    def visit_Constant(self, node):
        """Count constants as operands."""
        self.operands.add(str(node.value))
        self.total_operands += 1
        self.generic_visit(node)
    
    def visit_Str(self, node):
        """Count strings as operands (for older Python versions)."""
        self.operands.add(node.s)
        self.total_operands += 1
        self.generic_visit(node)
    
    def visit_Num(self, node):
        """Count numbers as operands (for older Python versions)."""
        self.operands.add(str(node.n))
        self.total_operands += 1
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """Count function calls as operators."""
        if isinstance(node.func, ast.Name):
            self.operators.add(node.func.id)
            self.total_operators += 1
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        """Count attribute access as operators."""
        self.operators.add(f".{node.attr}")
        self.total_operators += 1
        self.generic_visit(node)


# Create global instance
complexity_calculator = ComplexityCalculator()