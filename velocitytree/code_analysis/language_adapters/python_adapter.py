"""Python language adapter for code analysis."""

import ast
import re
from typing import List, Optional, Set

from . import BaseLanguageAdapter
from ..models import (
    ModuleAnalysis,
    FunctionAnalysis,
    ClassAnalysis,
    CodeLocation,
    LanguageSupport,
    CodeIssue,
    Severity,
    IssueCategory
)


class PythonAnalysisVisitor(ast.NodeVisitor):
    """AST visitor for analyzing Python code."""
    
    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.lines = source_code.splitlines()
        self.imports: List[str] = []
        self.functions: List[FunctionAnalysis] = []
        self.classes: List[ClassAnalysis] = []
        self.global_variables: List[str] = []
        self.current_class: Optional[ClassAnalysis] = None
        
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statements."""
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from-import statements."""
        module = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                self.imports.append(f"{module}.*")
            else:
                self.imports.append(f"{module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        # Get function location
        location = CodeLocation(
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=self._get_node_end_line(node),
            column_start=node.col_offset
        )
        
        # Extract parameters
        parameters = [arg.arg for arg in node.args.args]
        
        # Get return type if annotated
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns) if hasattr(ast, 'unparse') else str(node.returns)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Calculate complexity
        complexity = self._calculate_function_complexity(node)
        
        # Create function analysis
        func_analysis = FunctionAnalysis(
            name=node.name,
            location=location,
            complexity=complexity,
            parameters=parameters,
            returns=returns,
            docstring=docstring
        )
        
        # Check for issues
        self._check_function_issues(func_analysis, node)
        
        # Add to appropriate container
        if self.current_class:
            self.current_class.methods.append(func_analysis)
        else:
            self.functions.append(func_analysis)
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        # Treat async functions similar to regular functions
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions."""
        # Get class location
        location = CodeLocation(
            file_path=self.file_path,
            line_start=node.lineno,
            line_end=self._get_node_end_line(node),
            column_start=node.col_offset
        )
        
        # Get parent classes
        parent_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                parent_classes.append(base.id)
            else:
                parent_classes.append(ast.unparse(base) if hasattr(ast, 'unparse') else str(base))
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        # Create class analysis
        class_analysis = ClassAnalysis(
            name=node.name,
            location=location,
            methods=[],
            attributes=[],
            parent_classes=parent_classes,
            docstring=docstring
        )
        
        # Process class body
        old_class = self.current_class
        self.current_class = class_analysis
        
        # Find attributes and methods
        for item in node.body:
            if isinstance(item, ast.Assign):
                # Class attribute
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_analysis.attributes.append(target.id)
            elif isinstance(item, ast.AnnAssign):
                # Annotated class attribute
                if isinstance(item.target, ast.Name):
                    class_analysis.attributes.append(item.target.id)
        
        self.generic_visit(node)
        
        self.current_class = old_class
        self.classes.append(class_analysis)
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements."""
        # Track global variables (module-level assignments)
        if not self.current_class and isinstance(node.targets[0], ast.Name):
            # Check if it's at module level (no function parent)
            if not any(isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)) 
                      for parent in ast.walk(node)):
                self.global_variables.append(node.targets[0].id)
        
        self.generic_visit(node)
    
    def _get_node_end_line(self, node: ast.AST) -> int:
        """Get the end line of a node."""
        # Python 3.8+ has end_lineno
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        
        # Fallback: estimate based on node content
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            if node.body:
                return self._get_node_end_line(node.body[-1])
        
        return node.lineno
    
    def _calculate_function_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Decision points
            if isinstance(child, (ast.If, ast.While, ast.For)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # Each 'and' or 'or' adds complexity
                complexity += len(child.values) - 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        
        return complexity
    
    def _check_function_issues(self, func_analysis: FunctionAnalysis, node: ast.FunctionDef) -> None:
        """Check for function-specific issues."""
        # Check for missing return type annotation
        if not node.returns and func_analysis.name != "__init__":
            func_analysis.issues.append(CodeIssue(
                severity=Severity.INFO,
                category=IssueCategory.BEST_PRACTICE,
                message=f"Function '{func_analysis.name}' is missing return type annotation",
                rule_id="missing-return-type",
                location=func_analysis.location,
                suggestion="Add return type annotation for better type safety"
            ))
        
        # Check for too many parameters
        if len(func_analysis.parameters) > 5:
            func_analysis.issues.append(CodeIssue(
                severity=Severity.WARNING,
                category=IssueCategory.MAINTAINABILITY,
                message=f"Function '{func_analysis.name}' has too many parameters ({len(func_analysis.parameters)})",
                rule_id="too-many-parameters",
                location=func_analysis.location,
                suggestion="Consider using a configuration object or splitting the function"
            ))


class PythonAdapter(BaseLanguageAdapter):
    """Python-specific code analyzer."""
    
    def analyze_module(self, file_path: str, content: str) -> ModuleAnalysis:
        """Analyze a Python module."""
        try:
            # Parse the AST
            tree = ast.parse(content, filename=file_path)
            
            # Visit the AST
            visitor = PythonAnalysisVisitor(content, file_path)
            visitor.visit(tree)
            
            # Get module docstring
            module_docstring = ast.get_docstring(tree)
            
            # Create module analysis
            return ModuleAnalysis(
                file_path=file_path,
                language=LanguageSupport.PYTHON,
                imports=visitor.imports,
                functions=visitor.functions,
                classes=visitor.classes,
                global_variables=visitor.global_variables,
                docstring=module_docstring,
                metrics=None,  # Metrics will be calculated by the main analyzer
                issues=[],
                patterns=[]
            )
            
        except SyntaxError as e:
            # Return partial analysis with syntax error
            return ModuleAnalysis(
                file_path=file_path,
                language=LanguageSupport.PYTHON,
                imports=[],
                functions=[],
                classes=[],
                global_variables=[],
                docstring=None,
                metrics=None,
                issues=[
                    CodeIssue(
                        severity=Severity.ERROR,
                        category=IssueCategory.STYLE,
                        message=f"Syntax error: {e.msg}",
                        rule_id="syntax-error",
                        location=CodeLocation(
                            file_path=file_path,
                            line_start=e.lineno or 1,
                            line_end=e.lineno or 1,
                            column_start=e.offset
                        )
                    )
                ],
                patterns=[]
            )
    
    def can_analyze(self, file_path: str) -> bool:
        """Check if this adapter can analyze the given file."""
        return file_path.endswith('.py')