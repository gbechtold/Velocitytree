"""Advanced pattern detectors for code analysis."""

import ast
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .models import (
    Pattern,
    PatternType,
    CodeLocation,
    LanguageSupport
)
from .patterns import PatternDetector


class StrategyPatternDetector(PatternDetector):
    """Detector for Strategy design pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            # Look for abstract base classes or interfaces
            for cls in module_analysis.classes:
                # Check if it's an abstract class
                is_abstract = self._is_abstract_class(cls, content)
                
                if is_abstract:
                    # Find concrete implementations
                    implementations = self._find_implementations(cls, module_analysis.classes)
                    
                    if len(implementations) >= 2:
                        # Check for context class that uses the strategy
                        context_class = self._find_context_class(cls, module_analysis.classes, content)
                        
                        if context_class:
                            patterns.append(Pattern(
                                pattern_type=PatternType.DESIGN_PATTERN,
                                name="Strategy",
                                description="Strategy pattern allows selecting algorithm at runtime",
                                location=cls.location,
                                confidence=0.85,
                                metadata={
                                    "interface": cls.name,
                                    "implementations": [impl.name for impl in implementations],
                                    "context_class": context_class.name if context_class else None
                                }
                            ))
        
        return patterns
    
    def _is_abstract_class(self, cls: Any, content: str) -> bool:
        """Check if a class is abstract."""
        # Check for ABC inheritance or abstract methods
        if "ABC" in cls.parent_classes or "abc.ABC" in cls.parent_classes:
            return True
        
        # Check for abstractmethod decorator
        class_content = self._get_class_content(content, cls.location)
        if class_content and "@abstractmethod" in class_content:
            return True
        
        # Check for NotImplementedError in methods
        for method in cls.methods:
            method_content = self._get_method_content(content, method.location)
            if method_content and "NotImplementedError" in method_content:
                return True
        
        return False
    
    def _find_implementations(self, interface_cls: Any, all_classes: List[Any]) -> List[Any]:
        """Find classes that implement the interface."""
        implementations = []
        
        for cls in all_classes:
            if interface_cls.name in cls.parent_classes:
                implementations.append(cls)
        
        return implementations
    
    def _find_context_class(self, strategy_cls: Any, all_classes: List[Any], content: str) -> Optional[Any]:
        """Find the context class that uses the strategy."""
        for cls in all_classes:
            if cls == strategy_cls:
                continue
            
            # Check if class has attribute of strategy type
            for attr in cls.attributes:
                if strategy_cls.name.lower() in attr.lower():
                    return cls
            
            # Check if methods use strategy
            for method in cls.methods:
                method_content = self._get_method_content(content, method.location)
                if method_content and strategy_cls.name in method_content:
                    return cls
        
        return None
    
    def _get_class_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract class content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None
    
    def _get_method_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract method content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None


class DecoratorPatternDetector(PatternDetector):
    """Detector for Decorator design pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            # Python has built-in decorator syntax
            for func in module_analysis.functions:
                if self._has_decorators(func, content):
                    patterns.append(Pattern(
                        pattern_type=PatternType.DESIGN_PATTERN,
                        name="Decorator",
                        description="Function decorator pattern",
                        location=func.location,
                        confidence=0.95,
                        metadata={
                            "decorated_function": func.name,
                            "type": "function_decorator"
                        }
                    ))
            
            # Check for structural decorator pattern in classes
            for cls in module_analysis.classes:
                if self._is_structural_decorator(cls, module_analysis.classes):
                    patterns.append(Pattern(
                        pattern_type=PatternType.DESIGN_PATTERN,
                        name="Decorator",
                        description="Structural decorator pattern",
                        location=cls.location,
                        confidence=0.8,
                        metadata={
                            "decorator_class": cls.name,
                            "type": "structural_decorator"
                        }
                    ))
        
        return patterns
    
    def _has_decorators(self, func: Any, content: str) -> bool:
        """Check if function has decorators."""
        # Get the line before the function definition
        if func.location.line_start > 1:
            lines = content.splitlines()
            prev_line = lines[func.location.line_start - 2].strip()
            return prev_line.startswith('@')
        return False
    
    def _is_structural_decorator(self, cls: Any, all_classes: List[Any]) -> bool:
        """Check if class implements structural decorator pattern."""
        # Check if class wraps another object of same interface
        has_wrapped_attribute = any(
            attr in ["_wrapped", "_component", "_inner", "wrapped", "component"]
            for attr in cls.attributes
        )
        
        # Check if it inherits from same base as other classes
        if has_wrapped_attribute and cls.parent_classes:
            for other_cls in all_classes:
                if other_cls != cls and set(cls.parent_classes).intersection(set(other_cls.parent_classes)):
                    return True
        
        return False


class MagicNumbersCodeSmellDetector(PatternDetector):
    """Detector for Magic Numbers code smell."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        # Regular expression to find numeric literals
        # Excludes 0, 1, -1, 2 as these are often not magic numbers
        magic_number_pattern = r'(?<!\w)(?!-?[012]\b)-?\d+\.?\d*(?!\w)'
        
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            # Skip comments and strings
            if line.strip().startswith('#') or '"""' in line or "'''" in line:
                continue
            
            # Remove string literals to avoid false positives
            line_without_strings = re.sub(r'["\'].*?["\']', '', line)
            
            matches = re.finditer(magic_number_pattern, line_without_strings)
            
            for match in matches:
                number = match.group()
                
                # Additional filtering
                if float(number) in [0, 1, -1, 2, 10, 100]:  # Common non-magic numbers
                    continue
                
                # Check if it's in a good context (constant assignment)
                if re.match(r'^\s*[A-Z_]+\s*=\s*' + re.escape(number), line):
                    continue
                
                patterns.append(Pattern(
                    pattern_type=PatternType.CODE_SMELL,
                    name="Magic Numbers",
                    description=f"Magic number {number} should be a named constant",
                    location=CodeLocation(
                        file_path=module_analysis.file_path,
                        line_start=i + 1,
                        line_end=i + 1,
                        column_start=match.start()
                    ),
                    confidence=0.7,
                    metadata={
                        "value": number,
                        "line": line.strip()
                    }
                ))
        
        return patterns


class FeatureEnvyCodeSmellDetector(PatternDetector):
    """Detector for Feature Envy code smell."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            for cls in module_analysis.classes:
                for method in cls.methods:
                    # Skip special methods
                    if method.name.startswith('__') and method.name.endswith('__'):
                        continue
                    
                    method_content = self._get_method_content(content, method.location)
                    if not method_content:
                        continue
                    
                    # Count accesses to other objects
                    access_counts = self._count_object_accesses(method_content)
                    
                    # Check if method uses another object more than self
                    self_count = access_counts.get('self', 0)
                    
                    for obj, count in access_counts.items():
                        if obj != 'self' and count > self_count * 1.5:  # 50% more accesses
                            patterns.append(Pattern(
                                pattern_type=PatternType.CODE_SMELL,
                                name="Feature Envy",
                                description=f"Method '{method.name}' accesses '{obj}' more than its own class",
                                location=method.location,
                                confidence=0.8,
                                metadata={
                                    "method": method.name,
                                    "envied_object": obj,
                                    "self_accesses": self_count,
                                    "other_accesses": count
                                }
                            ))
        
        return patterns
    
    def _get_method_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract method content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None
    
    def _count_object_accesses(self, method_content: str) -> Dict[str, int]:
        """Count how many times each object is accessed in method."""
        access_counts = defaultdict(int)
        
        # Pattern to match object.attribute or object.method()
        access_pattern = r'(\w+)\.(?:\w+|\w+\(\))'
        
        for match in re.finditer(access_pattern, method_content):
            obj_name = match.group(1)
            access_counts[obj_name] += 1
        
        return dict(access_counts)


class DataClumpCodeSmellDetector(PatternDetector):
    """Detector for Data Clump code smell."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        # Find groups of parameters that appear together in multiple functions
        parameter_groups = defaultdict(list)
        
        all_functions = module_analysis.functions + [
            method for cls in module_analysis.classes 
            for method in cls.methods
        ]
        
        for func in all_functions:
            if len(func.parameters) >= 3:
                # Create parameter combinations
                for i in range(len(func.parameters) - 2):
                    for j in range(i + 3, len(func.parameters) + 1):
                        param_group = tuple(sorted(func.parameters[i:j]))
                        parameter_groups[param_group].append(func)
        
        # Find parameter groups that appear in multiple functions
        for param_group, functions in parameter_groups.items():
            if len(functions) >= 2 and len(param_group) >= 3:
                patterns.append(Pattern(
                    pattern_type=PatternType.CODE_SMELL,
                    name="Data Clump",
                    description=f"Parameters {', '.join(param_group)} appear together in multiple functions",
                    location=functions[0].location,  # Report at first occurrence
                    confidence=0.8,
                    metadata={
                        "parameters": list(param_group),
                        "occurrences": [
                            {
                                "function": func.name,
                                "location": func.location.line_start
                            }
                            for func in functions
                        ]
                    }
                ))
        
        return patterns


# Add new detectors to the registry
def register_advanced_patterns(registry):
    """Register advanced pattern detectors."""
    from .patterns import PatternDefinition
    
    registry.register(PatternDefinition(
        name="Strategy",
        pattern_type=PatternType.DESIGN_PATTERN,
        description="Strategy design pattern",
        languages=[LanguageSupport.PYTHON],
        detector=StrategyPatternDetector()
    ))
    
    registry.register(PatternDefinition(
        name="Decorator",
        pattern_type=PatternType.DESIGN_PATTERN,
        description="Decorator design pattern",
        languages=[LanguageSupport.PYTHON],
        detector=DecoratorPatternDetector()
    ))
    
    registry.register(PatternDefinition(
        name="Magic Numbers",
        pattern_type=PatternType.CODE_SMELL,
        description="Hard-coded numeric values",
        languages=[LanguageSupport.PYTHON],
        detector=MagicNumbersCodeSmellDetector()
    ))
    
    registry.register(PatternDefinition(
        name="Feature Envy",
        pattern_type=PatternType.CODE_SMELL,
        description="Method uses another object more than its own",
        languages=[LanguageSupport.PYTHON],
        detector=FeatureEnvyCodeSmellDetector()
    ))
    
    registry.register(PatternDefinition(
        name="Data Clump",
        pattern_type=PatternType.CODE_SMELL,
        description="Groups of data that appear together",
        languages=[LanguageSupport.PYTHON],
        detector=DataClumpCodeSmellDetector()
    ))