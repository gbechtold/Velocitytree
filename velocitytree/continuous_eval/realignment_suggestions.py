"""Realignment suggestions for specification drift."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import ast
import re

from ..code_analysis.analyzer import CodeAnalyzer
from ..documentation.generator import DocGenerator
from .drift_detector import DriftDetector, DriftReport, DriftType

class SuggestionCategory(Enum):
    """Categories of realignment suggestions."""
    CODE_CHANGE = "code_change"
    SPEC_UPDATE = "spec_update"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TEST_UPDATE = "test_update"
    DEPENDENCY = "dependency"

@dataclass
class RealignmentSuggestion:
    """Individual realignment suggestion."""
    category: SuggestionCategory
    title: str
    description: str
    priority: int  # 1-5, higher is more important
    effort: int  # 1-5, higher is more effort
    file_path: Path
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    spec_snippet: Optional[str] = None
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "effort": self.effort,
            "file_path": str(self.file_path),
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "spec_snippet": self.spec_snippet,
            "confidence": self.confidence
        }

class RealignmentEngine:
    """Engine for generating realignment suggestions."""
    
    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        doc_generator: Optional[DocGenerator] = None
    ):
        """Initialize realignment engine."""
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.doc_generator = doc_generator or DocGenerator()
        self.drift_detector = DriftDetector(code_analyzer=self.code_analyzer)
    
    def generate_suggestions(
        self,
        drift_report: DriftReport
    ) -> List[RealignmentSuggestion]:
        """Generate realignment suggestions for drift report."""
        suggestions = []
        
        for drift in drift_report.drifts:
            if drift.drift_type == DriftType.MISSING_IMPLEMENTATION:
                suggestions.extend(self._suggest_implementation(drift))
            elif drift.drift_type == DriftType.SIGNATURE_MISMATCH:
                suggestions.extend(self._suggest_signature_fix(drift))
            elif drift.drift_type == DriftType.BEHAVIOR_DEVIATION:
                suggestions.extend(self._suggest_behavior_fix(drift))
            elif drift.drift_type == DriftType.PERFORMANCE_DEGRADATION:
                suggestions.extend(self._suggest_performance_fix(drift))
            elif drift.drift_type == DriftType.DOCUMENTATION_STALE:
                suggestions.extend(self._suggest_doc_update(drift))
            elif drift.drift_type == DriftType.DEPENDENCY_DRIFT:
                suggestions.extend(self._suggest_dependency_fix(drift))
            elif drift.drift_type == DriftType.API_BREAKING_CHANGE:
                suggestions.extend(self._suggest_api_fix(drift))
        
        # Sort by priority and effort
        suggestions.sort(key=lambda s: (-s.priority, s.effort))
        
        return suggestions
    
    def _suggest_implementation(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest implementation for missing functionality."""
        suggestions = []
        
        # Generate implementation template
        if drift.details.get("spec"):
            spec = drift.details["spec"]
            element = drift.details.get("element", "")
            
            # Create implementation suggestion
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.CODE_CHANGE,
                title=f"Implement missing {element}",
                description=f"Add implementation for {element} according to spec",
                priority=5,
                effort=3,
                file_path=drift.file_path,
                line_number=drift.line_number,
                code_snippet=self._generate_implementation_snippet(spec, element),
                spec_snippet=str(spec),
                confidence=0.9
            ))
            
            # Suggest test creation
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.TEST_UPDATE,
                title=f"Add tests for {element}",
                description=f"Create unit tests for new {element} implementation",
                priority=4,
                effort=2,
                file_path=self._get_test_file(drift.file_path),
                code_snippet=self._generate_test_snippet(spec, element),
                confidence=0.8
            ))
        
        return suggestions
    
    def _suggest_signature_fix(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest fixes for signature mismatches."""
        suggestions = []
        
        actual = drift.details.get("actual_signature", "")
        expected = drift.details.get("expected_signature", "")
        element = drift.details.get("element", "")
        
        # Suggest code change
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.CODE_CHANGE,
            title=f"Update {element} signature",
            description=f"Change signature from {actual} to {expected}",
            priority=4,
            effort=2,
            file_path=drift.file_path,
            line_number=drift.line_number,
            code_snippet=f"def {expected}:",
            spec_snippet=f"Expected: {expected}",
            confidence=0.95
        ))
        
        # Check if this is a breaking change
        if self._is_breaking_change(actual, expected):
            # Suggest migration guide
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.DOCUMENTATION,
                title=f"Add migration guide for {element}",
                description="Document breaking change and migration path",
                priority=5,
                effort=2,
                file_path=Path("docs/migration.md"),
                code_snippet=self._generate_migration_guide(element, actual, expected),
                confidence=0.8
            ))
            
            # Suggest compatibility layer
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.REFACTOR,
                title=f"Add compatibility layer for {element}",
                description="Create backward-compatible wrapper",
                priority=3,
                effort=3,
                file_path=drift.file_path,
                line_number=drift.line_number,
                code_snippet=self._generate_compatibility_wrapper(element, actual, expected),
                confidence=0.7
            ))
        
        return suggestions
    
    def _suggest_behavior_fix(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest fixes for behavioral deviations."""
        suggestions = []
        
        element = drift.details.get("element", "")
        behavior = drift.details.get("behavior", "")
        spec = drift.details.get("spec", "")
        
        # Suggest implementation fix
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.CODE_CHANGE,
            title=f"Fix behavior of {element}",
            description=f"Align behavior with specification: {behavior}",
            priority=4,
            effort=3,
            file_path=drift.file_path,
            line_number=drift.line_number,
            spec_snippet=spec,
            confidence=0.8
        ))
        
        # Suggest regression test
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.TEST_UPDATE,
            title=f"Add regression test for {element}",
            description="Ensure behavior matches specification",
            priority=4,
            effort=2,
            file_path=self._get_test_file(drift.file_path),
            code_snippet=self._generate_behavior_test(element, spec),
            confidence=0.85
        ))
        
        return suggestions
    
    def _suggest_performance_fix(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest fixes for performance degradation."""
        suggestions = []
        
        element = drift.details.get("element", "")
        metric = drift.details.get("metric", "")
        actual = drift.details.get("actual_value", 0)
        expected = drift.details.get("expected_value", 0)
        
        # Analyze performance issues
        if metric == "time_complexity":
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.REFACTOR,
                title=f"Optimize {element} algorithm",
                description=f"Reduce complexity from O({actual}) to O({expected})",
                priority=3,
                effort=4,
                file_path=drift.file_path,
                line_number=drift.line_number,
                confidence=0.7
            ))
        
        elif metric == "memory_usage":
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.REFACTOR,
                title=f"Reduce memory usage in {element}",
                description=f"Optimize memory from {actual}MB to {expected}MB",
                priority=3,
                effort=3,
                file_path=drift.file_path,
                line_number=drift.line_number,
                confidence=0.75
            ))
        
        # Suggest performance test
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.TEST_UPDATE,
            title=f"Add performance test for {element}",
            description="Track performance metrics over time",
            priority=2,
            effort=2,
            file_path=self._get_test_file(drift.file_path),
            code_snippet=self._generate_performance_test(element, metric, expected),
            confidence=0.8
        ))
        
        return suggestions
    
    def _suggest_doc_update(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest documentation updates."""
        suggestions = []
        
        element = drift.details.get("element", "")
        doc_type = drift.details.get("doc_type", "")
        
        # Generate documentation
        if self.doc_generator:
            doc_content = self.doc_generator.generate_documentation(
                file_path=drift.file_path,
                element=element
            )
            
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.DOCUMENTATION,
                title=f"Update {doc_type} for {element}",
                description="Synchronize documentation with implementation",
                priority=2,
                effort=1,
                file_path=drift.file_path,
                line_number=drift.line_number,
                code_snippet=doc_content,
                confidence=0.9
            ))
        
        return suggestions
    
    def _suggest_dependency_fix(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest dependency fixes."""
        suggestions = []
        
        dep_name = drift.details.get("dependency", "")
        actual_version = drift.details.get("actual_version", "")
        required_version = drift.details.get("required_version", "")
        
        # Suggest version update
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.DEPENDENCY,
            title=f"Update {dep_name} version",
            description=f"Change from {actual_version} to {required_version}",
            priority=3,
            effort=1,
            file_path=Path("requirements.txt"),
            code_snippet=f"{dep_name}=={required_version}",
            confidence=0.95
        ))
        
        # Check for breaking changes
        if self._is_major_version_change(actual_version, required_version):
            suggestions.append(RealignmentSuggestion(
                category=SuggestionCategory.TEST_UPDATE,
                title=f"Test compatibility with {dep_name} {required_version}",
                description="Run full test suite with new version",
                priority=4,
                effort=2,
                file_path=Path("tests/test_dependencies.py"),
                confidence=0.8
            ))
        
        return suggestions
    
    def _suggest_api_fix(self, drift: Any) -> List[RealignmentSuggestion]:
        """Suggest fixes for API breaking changes."""
        suggestions = []
        
        element = drift.details.get("element", "")
        change_type = drift.details.get("change_type", "")
        
        # Versioning suggestion
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.DOCUMENTATION,
            title="Update API version",
            description="Increment major version for breaking change",
            priority=5,
            effort=1,
            file_path=Path("velocitytree/version.py"),
            confidence=0.9
        ))
        
        # Deprecation warnings
        suggestions.append(RealignmentSuggestion(
            category=SuggestionCategory.CODE_CHANGE,
            title=f"Add deprecation warning for {element}",
            description="Warn users about upcoming breaking change",
            priority=4,
            effort=1,
            file_path=drift.file_path,
            line_number=drift.line_number,
            code_snippet=self._generate_deprecation_warning(element, change_type),
            confidence=0.85
        ))
        
        return suggestions
    
    def _generate_implementation_snippet(
        self,
        spec: Dict[str, Any],
        element: str
    ) -> str:
        """Generate implementation code snippet."""
        # Simplified implementation generation
        if "function" in element.lower():
            return f"""def {element}({spec.get('params', '')}) -> {spec.get('return_type', 'Any')}:
    \"\"\"
    {spec.get('description', 'Implementation needed')}
    \"\"\"
    # TODO: Implement according to spec
    raise NotImplementedError("{element} not yet implemented")"""
        
        elif "class" in element.lower():
            return f"""class {element}:
    \"\"\"
    {spec.get('description', 'Implementation needed')}
    \"\"\"
    
    def __init__(self):
        # TODO: Initialize according to spec
        pass"""
        
        return "# TODO: Implement according to spec"
    
    def _generate_test_snippet(
        self,
        spec: Dict[str, Any],
        element: str
    ) -> str:
        """Generate test code snippet."""
        return f"""def test_{element.lower()}():
    \"\"\"Test {element} implementation.\"\"\"
    # Arrange
    # TODO: Set up test data
    
    # Act
    # TODO: Call {element}
    
    # Assert
    # TODO: Verify results match spec
    assert True  # Replace with actual assertions"""
    
    def _generate_behavior_test(
        self,
        element: str,
        spec: str
    ) -> str:
        """Generate behavioral test snippet."""
        return f"""def test_{element.lower()}_behavior():
    \"\"\"Test {element} behavior matches specification.\"\"\"
    # Test case based on: {spec}
    
    # TODO: Implement behavioral test
    assert True  # Replace with actual assertions"""
    
    def _generate_performance_test(
        self,
        element: str,
        metric: str,
        expected: Any
    ) -> str:
        """Generate performance test snippet."""
        return f"""def test_{element.lower()}_performance():
    \"\"\"Test {element} meets performance requirements.\"\"\"
    import time
    import memory_profiler
    
    # Measure {metric}
    # Expected: {expected}
    
    # TODO: Implement performance test
    assert True  # Replace with actual performance check"""
    
    def _generate_migration_guide(
        self,
        element: str,
        old_signature: str,
        new_signature: str
    ) -> str:
        """Generate migration guide snippet."""
        return f"""## Migration Guide: {element}

### Breaking Change
The signature of `{element}` has changed:

**Old**: `{old_signature}`
**New**: `{new_signature}`

### Migration Steps

1. Update all calls to `{element}` with new signature
2. Review any code that depends on the return value
3. Update tests to match new behavior

### Example
```python
# Before
result = {element}(old_params)

# After
result = {element}(new_params)
```
"""
    
    def _generate_compatibility_wrapper(
        self,
        element: str,
        old_signature: str,
        new_signature: str
    ) -> str:
        """Generate backward compatibility wrapper."""
        return f"""def {element}_compat({old_signature}):
    \"\"\"Backward compatibility wrapper for {element}.\"\"\"
    import warnings
    
    warnings.warn(
        "This signature is deprecated. Use new signature: {new_signature}",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Convert old params to new params
    # TODO: Implement parameter conversion
    
    return {element}(new_params)"""
    
    def _generate_deprecation_warning(
        self,
        element: str,
        change_type: str
    ) -> str:
        """Generate deprecation warning code."""
        return f"""import warnings

warnings.warn(
    "{element} is deprecated due to {change_type}. "
    "Please see migration guide for details.",
    DeprecationWarning,
    stacklevel=2
)"""
    
    def _get_test_file(self, source_file: Path) -> Path:
        """Get test file path for source file."""
        # Convert source path to test path
        parts = source_file.parts
        if "velocitytree" in parts:
            idx = parts.index("velocitytree")
            test_parts = ("tests",) + parts[idx+1:]
            test_file = Path(*test_parts)
            return test_file.with_stem(f"test_{test_file.stem}")
        
        return Path("tests") / f"test_{source_file.stem}.py"
    
    def _is_breaking_change(
        self,
        old_signature: str,
        new_signature: str
    ) -> bool:
        """Check if signature change is breaking."""
        # Simplified check - real implementation would parse signatures
        old_params = re.findall(r'\w+:', old_signature)
        new_params = re.findall(r'\w+:', new_signature)
        
        # Breaking if parameters removed or types changed
        return set(old_params) != set(new_params)
    
    def _is_major_version_change(
        self,
        old_version: str,
        new_version: str
    ) -> bool:
        """Check if version change is major."""
        old_major = old_version.split('.')[0]
        new_major = new_version.split('.')[0]
        return old_major != new_major