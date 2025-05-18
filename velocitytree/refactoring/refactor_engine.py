"""
Refactoring engine for automated code improvement recommendations.
Provides safe, impact-analyzed refactoring suggestions.
"""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

from velocitytree.code_analysis.models import (
    ModuleAnalysis, FunctionAnalysis, ClassAnalysis,
    CodeLocation, CodeMetrics
)
from velocitytree.code_analysis.analyzer import CodeAnalyzer


class RefactoringType(Enum):
    """Types of refactoring operations."""
    EXTRACT_METHOD = "extract_method"
    INLINE_METHOD = "inline_method"
    EXTRACT_VARIABLE = "extract_variable"
    INLINE_VARIABLE = "inline_variable"
    EXTRACT_CLASS = "extract_class"
    MOVE_METHOD = "move_method"
    RENAME = "rename"
    DECOMPOSE_CONDITIONAL = "decompose_conditional"
    REPLACE_MAGIC_NUMBER = "replace_magic_number"
    INTRODUCE_PARAMETER_OBJECT = "introduce_parameter_object"
    REPLACE_TEMP_WITH_QUERY = "replace_temp_with_query"
    REMOVE_DEAD_CODE = "remove_dead_code"
    SIMPLIFY_BOOLEAN = "simplify_boolean"
    CONSOLIDATE_DUPLICATE = "consolidate_duplicate"
    EXTRACT_INTERFACE = "extract_interface"


class RefactoringImpact(Enum):
    """Impact level of refactoring."""
    LOW = "low"  # Single file, local scope
    MEDIUM = "medium"  # Multiple files, module scope
    HIGH = "high"  # Cross-module, API changes
    CRITICAL = "critical"  # Breaking changes


@dataclass
class RefactoringCandidate:
    """A detected opportunity for refactoring."""
    type: RefactoringType
    location: CodeLocation
    confidence: float  # 0.0 to 1.0
    rationale: str
    complexity_reduction: float
    readability_improvement: float
    maintainability_improvement: float
    impact: RefactoringImpact
    affected_files: List[Path] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RefactoringPlan:
    """A detailed plan for performing a refactoring."""
    candidate: RefactoringCandidate
    steps: List[str]
    preview: Dict[Path, str]  # File path -> preview content
    rollback_plan: List[str]
    estimated_effort: str  # "minutes", "hours", "days"
    risks: List[str]
    benefits: List[str]
    alternatives: List[RefactoringType]


@dataclass
class ImpactAnalysis:
    """Analysis of refactoring impact."""
    direct_impacts: List[str]  # Direct code changes
    indirect_impacts: List[str]  # Ripple effects
    test_impacts: List[str]  # Tests that need updating
    documentation_impacts: List[str]  # Docs that need updating
    performance_impact: str  # "positive", "neutral", "negative"
    risk_score: float  # 0.0 to 1.0
    affected_components: List[str]
    breaking_changes: List[str]


class RefactoringDetector:
    """Detects refactoring opportunities in code."""
    
    def __init__(self, analyzer: Optional[CodeAnalyzer] = None):
        self.analyzer = analyzer or CodeAnalyzer()
        self.patterns = self._initialize_patterns()
    
    def _initialize_patterns(self) -> Dict[RefactoringType, Any]:
        """Initialize refactoring detection patterns."""
        return {
            RefactoringType.EXTRACT_METHOD: {
                "min_lines": 10,
                "max_complexity": 10,
                "duplicate_threshold": 0.8
            },
            RefactoringType.EXTRACT_VARIABLE: {
                "min_occurrences": 3,
                "complex_expression": True
            },
            RefactoringType.EXTRACT_CLASS: {
                "min_methods": 20,
                "cohesion_threshold": 0.3
            },
            RefactoringType.DECOMPOSE_CONDITIONAL: {
                "min_conditions": 3,
                "nesting_depth": 2
            },
            RefactoringType.REPLACE_MAGIC_NUMBER: {
                "numeric_literals": True,
                "min_occurrences": 2
            }
        }
    
    def detect_refactoring_opportunities(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect refactoring opportunities in analyzed code."""
        candidates = []
        
        # Detect long methods that should be extracted
        candidates.extend(self._detect_extract_method(analysis))
        
        # Detect repeated expressions for variable extraction
        candidates.extend(self._detect_extract_variable(analysis))
        
        # Detect god classes that need decomposition
        candidates.extend(self._detect_extract_class(analysis))
        
        # Detect complex conditionals
        candidates.extend(self._detect_decompose_conditional(analysis))
        
        # Detect magic numbers
        candidates.extend(self._detect_magic_numbers(analysis))
        
        # Detect duplicate code
        candidates.extend(self._detect_duplicate_code(analysis))
        
        # Detect dead code
        candidates.extend(self._detect_dead_code(analysis))
        
        return candidates
    
    def _detect_extract_method(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect opportunities to extract methods."""
        candidates = []
        
        for func in analysis.functions:
            # Check for long functions
            if func.complexity > 10 or self._estimate_lines(func) > 30:
                candidates.append(RefactoringCandidate(
                    type=RefactoringType.EXTRACT_METHOD,
                    location=func.location,
                    confidence=0.9,
                    rationale=f"Function '{func.name}' is too complex (complexity: {func.complexity})",
                    complexity_reduction=0.5,
                    readability_improvement=0.7,
                    maintainability_improvement=0.8,
                    impact=RefactoringImpact.LOW,
                    affected_files=[Path(analysis.file_path)],
                    metadata={
                        "function_name": func.name,
                        "current_complexity": func.complexity,
                        "suggested_extractions": self._suggest_method_extractions(func)
                    }
                ))
        
        # Check class methods too
        for cls in analysis.classes:
            for method in cls.methods:
                if method.complexity > 10:
                    candidates.append(RefactoringCandidate(
                        type=RefactoringType.EXTRACT_METHOD,
                        location=method.location,
                        confidence=0.85,
                        rationale=f"Method '{cls.name}.{method.name}' is too complex",
                        complexity_reduction=0.5,
                        readability_improvement=0.7,
                        maintainability_improvement=0.8,
                        impact=RefactoringImpact.LOW,
                        affected_files=[Path(analysis.file_path)],
                        metadata={
                            "class_name": cls.name,
                            "method_name": method.name,
                            "current_complexity": method.complexity
                        }
                    ))
        
        return candidates
    
    def _detect_extract_variable(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect repeated expressions that could be extracted to variables."""
        candidates = []
        
        # This would require AST analysis to find repeated expressions
        # For now, we'll use a simplified approach
        
        for func in analysis.functions:
            # Look for complex expressions in function bodies
            # This is a placeholder - real implementation would parse AST
            if func.complexity > 5:
                candidates.append(RefactoringCandidate(
                    type=RefactoringType.EXTRACT_VARIABLE,
                    location=func.location,
                    confidence=0.7,
                    rationale=f"Function '{func.name}' has complex expressions that could be simplified",
                    complexity_reduction=0.3,
                    readability_improvement=0.6,
                    maintainability_improvement=0.5,
                    impact=RefactoringImpact.LOW,
                    affected_files=[Path(analysis.file_path)],
                    metadata={
                        "function_name": func.name,
                        "suggested_variables": ["result", "condition", "calculation"]
                    }
                ))
        
        return candidates
    
    def _detect_extract_class(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect god classes that should be decomposed."""
        candidates = []
        
        for cls in analysis.classes:
            method_count = len(cls.methods)
            attribute_count = len(cls.attributes)
            
            # Detect god class
            if method_count > 20 or attribute_count > 15:
                candidates.append(RefactoringCandidate(
                    type=RefactoringType.EXTRACT_CLASS,
                    location=cls.location,
                    confidence=0.8,
                    rationale=f"Class '{cls.name}' has too many responsibilities ({method_count} methods, {attribute_count} attributes)",
                    complexity_reduction=0.6,
                    readability_improvement=0.8,
                    maintainability_improvement=0.9,
                    impact=RefactoringImpact.MEDIUM,
                    affected_files=[Path(analysis.file_path)],
                    metadata={
                        "class_name": cls.name,
                        "method_count": method_count,
                        "attribute_count": attribute_count,
                        "suggested_classes": self._suggest_class_decomposition(cls)
                    }
                ))
        
        return candidates
    
    def _detect_decompose_conditional(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect complex conditionals that should be decomposed."""
        candidates = []
        
        # This would require AST analysis to find complex conditionals
        # For now, we'll use complexity as a proxy
        
        for func in analysis.functions:
            if func.complexity > 8:  # High cyclomatic complexity often means complex conditionals
                candidates.append(RefactoringCandidate(
                    type=RefactoringType.DECOMPOSE_CONDITIONAL,
                    location=func.location,
                    confidence=0.75,
                    rationale=f"Function '{func.name}' likely has complex conditionals",
                    complexity_reduction=0.4,
                    readability_improvement=0.9,
                    maintainability_improvement=0.7,
                    impact=RefactoringImpact.LOW,
                    affected_files=[Path(analysis.file_path)],
                    metadata={
                        "function_name": func.name,
                        "current_complexity": func.complexity
                    }
                ))
        
        return candidates
    
    def _detect_magic_numbers(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect magic numbers that should be constants."""
        candidates = []
        
        # This would require AST analysis to find numeric literals
        # For now, we'll use a heuristic based on file type
        
        if analysis.language.value == "python":
            # Look for common magic number patterns
            candidates.append(RefactoringCandidate(
                type=RefactoringType.REPLACE_MAGIC_NUMBER,
                location=CodeLocation(
                    file_path=analysis.file_path,
                    line_start=1,
                    line_end=1
                ),
                confidence=0.6,
                rationale="File may contain magic numbers that should be constants",
                complexity_reduction=0.2,
                readability_improvement=0.8,
                maintainability_improvement=0.9,
                impact=RefactoringImpact.LOW,
                affected_files=[Path(analysis.file_path)],
                metadata={
                    "search_pattern": r'\b\d+\b',
                    "common_numbers": [0, 1, 2, 10, 100, 1000]
                }
            ))
        
        return candidates
    
    def _detect_duplicate_code(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect duplicate code blocks."""
        candidates = []
        
        # Check for similar functions
        functions = analysis.functions
        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                similarity = self._calculate_similarity(func1, func2)
                if similarity > 0.8:
                    candidates.append(RefactoringCandidate(
                        type=RefactoringType.CONSOLIDATE_DUPLICATE,
                        location=func1.location,
                        confidence=similarity,
                        rationale=f"Functions '{func1.name}' and '{func2.name}' are very similar",
                        complexity_reduction=0.5,
                        readability_improvement=0.6,
                        maintainability_improvement=0.9,
                        impact=RefactoringImpact.MEDIUM,
                        affected_files=[Path(analysis.file_path)],
                        metadata={
                            "function1": func1.name,
                            "function2": func2.name,
                            "similarity": similarity
                        }
                    ))
        
        return candidates
    
    def _detect_dead_code(
        self, 
        analysis: ModuleAnalysis
    ) -> List[RefactoringCandidate]:
        """Detect unused code."""
        candidates = []
        
        # This would require usage analysis
        # For now, we'll look for common patterns
        
        for func in analysis.functions:
            if func.name.startswith("_unused_") or func.name.endswith("_old"):
                candidates.append(RefactoringCandidate(
                    type=RefactoringType.REMOVE_DEAD_CODE,
                    location=func.location,
                    confidence=0.7,
                    rationale=f"Function '{func.name}' appears to be unused",
                    complexity_reduction=0.3,
                    readability_improvement=0.5,
                    maintainability_improvement=0.7,
                    impact=RefactoringImpact.LOW,
                    affected_files=[Path(analysis.file_path)],
                    metadata={
                        "function_name": func.name,
                        "detection_reason": "naming_pattern"
                    }
                ))
        
        return candidates
    
    def _estimate_lines(self, func: FunctionAnalysis) -> int:
        """Estimate the number of lines in a function."""
        # Use location if available
        if func.location.line_end and func.location.line_start:
            return func.location.line_end - func.location.line_start
        # Otherwise use complexity as a rough estimate
        return func.complexity * 5
    
    def _suggest_method_extractions(self, func: FunctionAnalysis) -> List[str]:
        """Suggest how to extract methods from a complex function."""
        suggestions = []
        
        # Based on complexity, suggest extraction points
        if func.complexity > 15:
            suggestions.append("Extract validation logic into separate method")
            suggestions.append("Extract calculation logic into separate method")
            suggestions.append("Extract formatting logic into separate method")
        elif func.complexity > 10:
            suggestions.append("Extract complex conditions into separate methods")
            suggestions.append("Extract repeated code blocks")
        
        return suggestions
    
    def _suggest_class_decomposition(self, cls: ClassAnalysis) -> List[str]:
        """Suggest how to decompose a god class."""
        suggestions = []
        
        # Analyze methods and suggest groupings
        method_count = len(cls.methods)
        if method_count > 20:
            suggestions.append(f"{cls.name}Core - Core functionality")
            suggestions.append(f"{cls.name}Utils - Utility methods")
            suggestions.append(f"{cls.name}Validators - Validation methods")
            suggestions.append(f"{cls.name}Formatters - Formatting methods")
        
        return suggestions
    
    def _calculate_similarity(self, func1: FunctionAnalysis, func2: FunctionAnalysis) -> float:
        """Calculate similarity between two functions."""
        # Simple heuristic based on complexity and parameters
        complexity_similarity = 1.0 - abs(func1.complexity - func2.complexity) / max(func1.complexity, func2.complexity)
        param_similarity = 1.0 if len(func1.parameters) == len(func2.parameters) else 0.5
        
        return (complexity_similarity + param_similarity) / 2


class RefactoringPlanner:
    """Creates detailed plans for refactoring operations."""
    
    def __init__(self, analyzer: Optional[CodeAnalyzer] = None):
        self.analyzer = analyzer or CodeAnalyzer()
    
    def create_refactoring_plan(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Create a detailed plan for a refactoring candidate."""
        plan_creators = {
            RefactoringType.EXTRACT_METHOD: self._plan_extract_method,
            RefactoringType.EXTRACT_CLASS: self._plan_extract_class,
            RefactoringType.DECOMPOSE_CONDITIONAL: self._plan_decompose_conditional,
            RefactoringType.REPLACE_MAGIC_NUMBER: self._plan_replace_magic_number,
            RefactoringType.CONSOLIDATE_DUPLICATE: self._plan_consolidate_duplicate,
            RefactoringType.REMOVE_DEAD_CODE: self._plan_remove_dead_code,
        }
        
        creator = plan_creators.get(candidate.type, self._plan_generic)
        return creator(candidate, analysis)
    
    def _plan_extract_method(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan method extraction refactoring."""
        func_name = candidate.metadata.get("function_name", "unknown")
        
        steps = [
            f"Identify the code block to extract from '{func_name}'",
            "Determine input parameters and return values",
            "Create new method with descriptive name",
            "Replace original code with method call",
            "Update tests to cover new method",
            "Update documentation"
        ]
        
        preview = {
            Path(analysis.file_path): f"""
# Before:
def {func_name}(params):
    # Complex logic here...
    # More complex logic...
    
# After:
def {func_name}(params):
    result = self._extracted_method(params)
    return result
    
def _extracted_method(params):
    # Complex logic here...
    # More complex logic...
"""
        }
        
        rollback = [
            "Inline the extracted method back",
            "Remove the new method definition",
            "Restore original code"
        ]
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=rollback,
            estimated_effort="minutes",
            risks=["May affect method call sites", "Could introduce performance overhead"],
            benefits=["Improved readability", "Better testability", "Reduced complexity"],
            alternatives=[RefactoringType.INLINE_METHOD]
        )
    
    def _plan_extract_class(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan class extraction refactoring."""
        class_name = candidate.metadata.get("class_name", "UnknownClass")
        suggested_classes = candidate.metadata.get("suggested_classes", [])
        
        steps = [
            f"Analyze responsibilities of '{class_name}'",
            "Group related methods and attributes",
            f"Create new classes: {', '.join(suggested_classes)}",
            "Move methods and attributes to appropriate classes",
            "Update references throughout codebase",
            "Add necessary imports",
            "Update tests and documentation"
        ]
        
        preview = {
            Path(analysis.file_path): f"""
# Before:
class {class_name}:
    # 30+ methods and attributes
    
# After:
class {class_name}:
    # Core functionality only
    
class {class_name}Utils:
    # Utility methods
    
class {class_name}Validators:
    # Validation methods
"""
        }
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=["Merge classes back", "Update all references"],
            estimated_effort="hours",
            risks=["API changes", "Breaking dependent code"],
            benefits=["Better organization", "Improved maintainability", "Single responsibility"],
            alternatives=[RefactoringType.EXTRACT_INTERFACE]
        )
    
    def _plan_decompose_conditional(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan conditional decomposition refactoring."""
        steps = [
            "Identify complex conditional expressions",
            "Extract condition into descriptive method",
            "Extract then-clause into method",
            "Extract else-clause into method",
            "Replace with method calls"
        ]
        
        preview = {
            Path(analysis.file_path): """
# Before:
if (condition1 and condition2) or (condition3 and not condition4):
    # complex then logic
else:
    # complex else logic
    
# After:
if self._is_special_case():
    self._handle_special_case()
else:
    self._handle_normal_case()
"""
        }
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=["Inline methods back into conditional"],
            estimated_effort="minutes",
            risks=["Slight performance overhead"],
            benefits=["Improved readability", "Better testability"],
            alternatives=[RefactoringType.SIMPLIFY_BOOLEAN]
        )
    
    def _plan_replace_magic_number(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan magic number replacement refactoring."""
        steps = [
            "Identify all magic numbers in the file",
            "Determine appropriate constant names",
            "Define constants at module/class level",
            "Replace all occurrences",
            "Update documentation"
        ]
        
        preview = {
            Path(analysis.file_path): """
# Before:
if user_count > 1000:
    discount = price * 0.15
    
# After:
MAX_USERS_FOR_DISCOUNT = 1000
BULK_DISCOUNT_RATE = 0.15

if user_count > MAX_USERS_FOR_DISCOUNT:
    discount = price * BULK_DISCOUNT_RATE
"""
        }
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=["Replace constants with literal values"],
            estimated_effort="minutes",
            risks=["None"],
            benefits=["Better maintainability", "Self-documenting code"],
            alternatives=[RefactoringType.EXTRACT_VARIABLE]
        )
    
    def _plan_consolidate_duplicate(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan duplicate code consolidation."""
        func1 = candidate.metadata.get("function1", "func1")
        func2 = candidate.metadata.get("function2", "func2")
        
        steps = [
            f"Compare '{func1}' and '{func2}' implementations",
            "Extract common functionality",
            "Create shared method/function",
            "Update both functions to use shared code",
            "Remove duplication",
            "Update tests"
        ]
        
        preview = {
            Path(analysis.file_path): f"""
# Before:
def {func1}(params):
    # Similar implementation
    
def {func2}(params):
    # Similar implementation
    
# After:
def _shared_logic(params):
    # Common implementation
    
def {func1}(params):
    return self._shared_logic(params)
    
def {func2}(params):
    return self._shared_logic(params)
"""
        }
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=["Inline shared code back into original functions"],
            estimated_effort="minutes",
            risks=["May need parameter adjustments"],
            benefits=["DRY principle", "Easier maintenance", "Consistency"],
            alternatives=[RefactoringType.EXTRACT_METHOD]
        )
    
    def _plan_remove_dead_code(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Plan dead code removal."""
        func_name = candidate.metadata.get("function_name", "unknown")
        
        steps = [
            f"Verify '{func_name}' is truly unused",
            "Check for dynamic calls (getattr, eval)",
            "Search entire codebase for references",
            "Remove function/class definition",
            "Remove related imports",
            "Update tests"
        ]
        
        preview = {
            Path(analysis.file_path): f"""
# Before:
def active_function():
    pass
    
def {func_name}():  # Unused
    pass
    
# After:
def active_function():
    pass
    
# {func_name} removed
"""
        }
        
        return RefactoringPlan(
            candidate=candidate,
            steps=steps,
            preview=preview,
            rollback_plan=["Restore removed code from version control"],
            estimated_effort="minutes",
            risks=["May break dynamic calls", "External dependencies"],
            benefits=["Cleaner codebase", "Reduced complexity"],
            alternatives=[]
        )
    
    def _plan_generic(
        self,
        candidate: RefactoringCandidate,
        analysis: ModuleAnalysis
    ) -> RefactoringPlan:
        """Generic refactoring plan for unhandled types."""
        return RefactoringPlan(
            candidate=candidate,
            steps=["Analyze code", "Plan refactoring", "Implement changes", "Test"],
            preview={},
            rollback_plan=["Revert changes"],
            estimated_effort="hours",
            risks=["Unknown impact"],
            benefits=["Improved code quality"],
            alternatives=[]
        )


class ImpactAnalyzer:
    """Analyzes the impact of refactoring operations."""
    
    def __init__(self, analyzer: Optional[CodeAnalyzer] = None):
        self.analyzer = analyzer or CodeAnalyzer()
    
    def analyze_impact(
        self,
        plan: RefactoringPlan,
        codebase_path: Path
    ) -> ImpactAnalysis:
        """Analyze the impact of a refactoring plan."""
        impact_analyzers = {
            RefactoringType.EXTRACT_METHOD: self._analyze_extract_method_impact,
            RefactoringType.EXTRACT_CLASS: self._analyze_extract_class_impact,
            RefactoringType.REMOVE_DEAD_CODE: self._analyze_remove_dead_code_impact,
        }
        
        analyzer = impact_analyzers.get(
            plan.candidate.type,
            self._analyze_generic_impact
        )
        
        return analyzer(plan, codebase_path)
    
    def _analyze_extract_method_impact(
        self,
        plan: RefactoringPlan,
        codebase_path: Path
    ) -> ImpactAnalysis:
        """Analyze impact of method extraction."""
        func_name = plan.candidate.metadata.get("function_name", "")
        
        return ImpactAnalysis(
            direct_impacts=[
                f"Function '{func_name}' will be split",
                "New method will be created",
                "Original function will call new method"
            ],
            indirect_impacts=[
                "May affect performance profiling",
                "Stack traces will change"
            ],
            test_impacts=[
                f"Tests for '{func_name}' may need updates",
                "New tests needed for extracted method"
            ],
            documentation_impacts=[
                "API documentation needs update",
                "Code examples may need revision"
            ],
            performance_impact="neutral",
            risk_score=0.2,
            affected_components=[plan.candidate.location.file_path],
            breaking_changes=[]
        )
    
    def _analyze_extract_class_impact(
        self,
        plan: RefactoringPlan,
        codebase_path: Path
    ) -> ImpactAnalysis:
        """Analyze impact of class extraction."""
        class_name = plan.candidate.metadata.get("class_name", "")
        
        # Find all files importing this class
        affected_files = self._find_imports(class_name, codebase_path)
        
        return ImpactAnalysis(
            direct_impacts=[
                f"Class '{class_name}' will be split into multiple classes",
                "New import statements required",
                "Method signatures may change"
            ],
            indirect_impacts=[
                "Subclasses may be affected",
                "Serialization/deserialization may break",
                "Dependency injection configurations need updates"
            ],
            test_impacts=[
                "All tests using the class need updates",
                "Mock objects need revision",
                "Integration tests may fail"
            ],
            documentation_impacts=[
                "API reference needs major updates",
                "UML diagrams need revision",
                "Tutorials may become outdated"
            ],
            performance_impact="neutral",
            risk_score=0.8,
            affected_components=affected_files,
            breaking_changes=[
                f"Public API of '{class_name}' will change",
                "Import statements must be updated"
            ]
        )
    
    def _analyze_remove_dead_code_impact(
        self,
        plan: RefactoringPlan,
        codebase_path: Path
    ) -> ImpactAnalysis:
        """Analyze impact of dead code removal."""
        func_name = plan.candidate.metadata.get("function_name", "")
        
        # Search for any references
        references = self._find_references(func_name, codebase_path)
        
        risk_score = 0.1 if not references else 0.9
        
        return ImpactAnalysis(
            direct_impacts=[
                f"Function '{func_name}' will be removed",
                "Related imports may be cleaned up"
            ],
            indirect_impacts=[
                "Dynamic calls may break",
                "Plugin systems may be affected"
            ],
            test_impacts=[
                f"Tests for '{func_name}' can be removed",
                "Coverage metrics will change"
            ],
            documentation_impacts=[
                "Remove from API documentation",
                "Update changelog"
            ],
            performance_impact="positive",
            risk_score=risk_score,
            affected_components=[plan.candidate.location.file_path],
            breaking_changes=references
        )
    
    def _analyze_generic_impact(
        self,
        plan: RefactoringPlan,
        codebase_path: Path
    ) -> ImpactAnalysis:
        """Generic impact analysis."""
        return ImpactAnalysis(
            direct_impacts=["Code structure will change"],
            indirect_impacts=["Unknown ripple effects"],
            test_impacts=["Tests may need updates"],
            documentation_impacts=["Documentation may need updates"],
            performance_impact="neutral",
            risk_score=0.5,
            affected_components=[plan.candidate.location.file_path],
            breaking_changes=[]
        )
    
    def _find_imports(self, class_name: str, codebase_path: Path) -> List[str]:
        """Find all files importing a given class."""
        affected_files = []
        
        for py_file in codebase_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                if f"from .* import.*{class_name}" in content or f"import.*{class_name}" in content:
                    affected_files.append(str(py_file))
            except Exception:
                pass
        
        return affected_files
    
    def _find_references(self, func_name: str, codebase_path: Path) -> List[str]:
        """Find all references to a function."""
        references = []
        
        for py_file in codebase_path.rglob("*.py"):
            try:
                content = py_file.read_text()
                if func_name in content:
                    # Simple check - real implementation would use AST
                    references.append(f"{py_file}: possible reference to {func_name}")
            except Exception:
                pass
        
        return references


class RefactoringRecommendationEngine:
    """Main engine for refactoring recommendations."""
    
    def __init__(
        self,
        analyzer: Optional[CodeAnalyzer] = None,
        detector: Optional[RefactoringDetector] = None,
        planner: Optional[RefactoringPlanner] = None,
        impact_analyzer: Optional[ImpactAnalyzer] = None
    ):
        self.analyzer = analyzer or CodeAnalyzer()
        self.detector = detector or RefactoringDetector(self.analyzer)
        self.planner = planner or RefactoringPlanner(self.analyzer)
        self.impact_analyzer = impact_analyzer or ImpactAnalyzer(self.analyzer)
    
    def analyze_and_recommend(
        self,
        file_path: Path,
        codebase_path: Optional[Path] = None
    ) -> List[Tuple[RefactoringCandidate, RefactoringPlan, ImpactAnalysis]]:
        """Analyze a file and generate refactoring recommendations."""
        # Analyze the file
        analysis = self.analyzer.analyze_file(file_path)
        
        # Detect refactoring opportunities
        candidates = self.detector.detect_refactoring_opportunities(analysis)
        
        # Create plans and analyze impact
        recommendations = []
        for candidate in candidates:
            plan = self.planner.create_refactoring_plan(candidate, analysis)
            impact = self.impact_analyzer.analyze_impact(
                plan,
                codebase_path or file_path.parent
            )
            recommendations.append((candidate, plan, impact))
        
        # Sort by benefit/risk ratio
        recommendations.sort(
            key=lambda x: (x[0].maintainability_improvement / (x[2].risk_score + 0.1)),
            reverse=True
        )
        
        return recommendations
    
    def generate_suggestions(
        self,
        recommendations: List[Tuple[RefactoringCandidate, RefactoringPlan, ImpactAnalysis]]
    ) -> List[Dict[str, Any]]:
        """Convert recommendations to suggestion dictionaries."""
        # Import at runtime to avoid circular imports
        from velocitytree.realtime_suggestions import (
            CodeSuggestion, SuggestionType, Severity,
            CodePosition, CodeRange, QuickFix, QuickFixType
        )
        
        suggestions = []
        
        for candidate, plan, impact in recommendations:
            # Create quick fixes from the refactoring plan
            quick_fixes = []
            
            if plan.preview:
                quick_fixes.append(QuickFix(
                    type=QuickFixType.EXTRACT_FUNCTION,  # Map to appropriate type
                    title=f"Apply {candidate.type.value}",
                    description=candidate.rationale,
                    range=CodeRange(
                        start=CodePosition(candidate.location.line_start, 0),
                        end=CodePosition(candidate.location.line_end or candidate.location.line_start, 0)
                    ),
                    replacement="",  # Would contain actual refactored code
                    preview=str(plan.preview)
                ))
            
            suggestion = CodeSuggestion(
                type=SuggestionType.REFACTORING,
                severity=self._impact_to_severity(impact),
                message=candidate.rationale,
                range=CodeRange(
                    start=CodePosition(candidate.location.line_start, 0),
                    end=CodePosition(candidate.location.line_end or candidate.location.line_start, 999)
                ),
                file_path=Path(candidate.location.file_path),
                quick_fixes=quick_fixes,
                metadata={
                    "refactoring_type": candidate.type.value,
                    "confidence": candidate.confidence,
                    "impact": impact.risk_score,
                    "effort": plan.estimated_effort,
                    "benefits": plan.benefits,
                    "risks": plan.risks
                },
                priority=int(candidate.maintainability_improvement * 100)
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _impact_to_severity(self, impact: ImpactAnalysis) -> "Severity":
        """Convert impact analysis to suggestion severity."""
        from velocitytree.realtime_suggestions import Severity
        
        if impact.risk_score > 0.7:
            return Severity.INFO  # High risk = low severity suggestion
        elif impact.risk_score > 0.3:
            return Severity.WARNING
        else:
            return Severity.ERROR  # Low risk = high priority suggestion