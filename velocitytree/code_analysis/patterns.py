"""Pattern detection for code analysis."""

import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .models import (
    Pattern,
    PatternType,
    CodeLocation,
    LanguageSupport
)


@dataclass
class PatternDefinition:
    """Definition of a code pattern to detect."""
    name: str
    pattern_type: PatternType
    description: str
    languages: List[LanguageSupport]
    detector: 'PatternDetector'


class PatternDetector:
    """Base class for pattern detectors."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        """Detect patterns in the given module.
        
        Args:
            module_analysis: Module analysis object
            content: Source code content
            
        Returns:
            List of detected patterns
        """
        raise NotImplementedError


class SingletonPatternDetector(PatternDetector):
    """Detector for Singleton design pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            for cls in module_analysis.classes:
                # Check for common singleton indicators
                has_instance_attr = any(
                    attr in ["_instance", "__instance", "_singleton", "instance"]
                    for attr in cls.attributes
                )
                
                has_instance_method = any(
                    method.name in ["get_instance", "getInstance", "instance"]
                    for method in cls.methods
                )
                
                # Check for __new__ override
                has_new_override = any(
                    method.name == "__new__" 
                    for method in cls.methods
                )
                
                if (has_instance_attr and has_instance_method) or has_new_override:
                    patterns.append(Pattern(
                        pattern_type=PatternType.DESIGN_PATTERN,
                        name="Singleton",
                        description="Singleton design pattern ensures only one instance of the class exists",
                        location=cls.location,
                        confidence=0.9 if has_new_override else 0.8,
                        metadata={
                            "implementation_type": "new_method" if has_new_override else "instance_method"
                        }
                    ))
        
        return patterns


class FactoryPatternDetector(PatternDetector):
    """Detector for Factory design pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            for cls in module_analysis.classes:
                # Check for factory indicators
                factory_methods = [
                    method for method in cls.methods
                    if any(keyword in method.name.lower() 
                          for keyword in ["create", "make", "build", "factory"])
                ]
                
                # Check if methods return other class instances
                creates_instances = False
                for method in factory_methods:
                    # Simple heuristic: check if method contains 'return ClassName('
                    method_content = self._get_method_content(content, method.location)
                    if method_content and re.search(r'return\s+[A-Z]\w+\(', method_content):
                        creates_instances = True
                        break
                
                if factory_methods and creates_instances:
                    patterns.append(Pattern(
                        pattern_type=PatternType.DESIGN_PATTERN,
                        name="Factory",
                        description="Factory pattern provides interface for creating objects",
                        location=cls.location,
                        confidence=0.8,
                        metadata={
                            "factory_methods": [m.name for m in factory_methods]
                        }
                    ))
        
        return patterns
    
    def _get_method_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract method content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None


class ObserverPatternDetector(PatternDetector):
    """Detector for Observer design pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        if module_analysis.language == LanguageSupport.PYTHON:
            for cls in module_analysis.classes:
                # Check for observer pattern indicators
                has_observers_list = any(
                    attr in ["observers", "subscribers", "listeners", "_observers", "_listeners"]
                    for attr in cls.attributes
                )
                
                has_notify_method = any(
                    any(keyword in method.name.lower() 
                       for keyword in ["notify", "publish", "emit", "trigger"])
                    for method in cls.methods
                )
                
                has_subscribe_method = any(
                    any(keyword in method.name.lower() 
                       for keyword in ["subscribe", "attach", "register", "add_observer", "add_listener"])
                    for method in cls.methods
                )
                
                if has_observers_list and has_notify_method and has_subscribe_method:
                    patterns.append(Pattern(
                        pattern_type=PatternType.DESIGN_PATTERN,
                        name="Observer",
                        description="Observer pattern defines one-to-many dependency between objects",
                        location=cls.location,
                        confidence=0.9,
                        metadata={
                            "has_observers_list": has_observers_list,
                            "has_notify_method": has_notify_method,
                            "has_subscribe_method": has_subscribe_method
                        }
                    ))
        
        return patterns


class GodClassAntiPatternDetector(PatternDetector):
    """Detector for God Class anti-pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        for cls in module_analysis.classes:
            # Configurable thresholds
            method_threshold = 20
            attribute_threshold = 15
            lines_threshold = 500
            
            # Calculate class metrics
            num_methods = len(cls.methods)
            num_attributes = len(cls.attributes)
            class_lines = cls.location.line_end - cls.location.line_start + 1
            
            # Check if class violates thresholds
            violations = []
            confidence = 0.5
            
            if num_methods > method_threshold:
                violations.append(f"too many methods ({num_methods})")
                confidence += 0.2
            
            if num_attributes > attribute_threshold:
                violations.append(f"too many attributes ({num_attributes})")
                confidence += 0.2
            
            if class_lines > lines_threshold:
                violations.append(f"too many lines ({class_lines})")
                confidence += 0.1
            
            if violations:
                patterns.append(Pattern(
                    pattern_type=PatternType.ANTI_PATTERN,
                    name="God Class",
                    description=f"Class has too many responsibilities: {', '.join(violations)}",
                    location=cls.location,
                    confidence=min(confidence, 0.95),
                    metadata={
                        "method_count": num_methods,
                        "attribute_count": num_attributes,
                        "line_count": class_lines,
                        "violations": violations
                    }
                ))
        
        return patterns


class SpaghettiCodeAntiPatternDetector(PatternDetector):
    """Detector for Spaghetti Code anti-pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        # Check for functions with high complexity and deep nesting
        for func in module_analysis.functions:
            if func.complexity > 15:
                # Analyze nesting depth
                func_content = self._get_function_content(content, func.location)
                if func_content:
                    max_nesting = self._calculate_nesting_depth(func_content)
                    
                    if max_nesting > 4:
                        patterns.append(Pattern(
                            pattern_type=PatternType.ANTI_PATTERN,
                            name="Spaghetti Code",
                            description=f"Function has complex control flow (complexity: {func.complexity}, nesting: {max_nesting})",
                            location=func.location,
                            confidence=0.8,
                            metadata={
                                "complexity": func.complexity,
                                "max_nesting": max_nesting
                            }
                        ))
        
        # Check for classes with tangled dependencies
        for cls in module_analysis.classes:
            for method in cls.methods:
                if method.complexity > 15:
                    method_content = self._get_function_content(content, method.location)
                    if method_content:
                        max_nesting = self._calculate_nesting_depth(method_content)
                        
                        if max_nesting > 4:
                            patterns.append(Pattern(
                                pattern_type=PatternType.ANTI_PATTERN,
                                name="Spaghetti Code",
                                description=f"Method has complex control flow (complexity: {method.complexity}, nesting: {max_nesting})",
                                location=method.location,
                                confidence=0.8,
                                metadata={
                                    "complexity": method.complexity,
                                    "max_nesting": max_nesting,
                                    "class_name": cls.name
                                }
                            ))
        
        return patterns
    
    def _get_function_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract function content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None
    
    def _calculate_nesting_depth(self, code: str) -> int:
        """Calculate maximum nesting depth in code."""
        max_depth = 0
        current_depth = 0
        
        # Simple indentation-based nesting calculation
        for line in code.splitlines():
            stripped = line.lstrip()
            if stripped:
                indent_level = (len(line) - len(stripped)) // 4  # Assume 4-space indentation
                current_depth = indent_level
                max_depth = max(max_depth, current_depth)
        
        return max_depth


class LongParameterListAntiPatternDetector(PatternDetector):
    """Detector for Long Parameter List anti-pattern."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        parameter_threshold = 5
        
        # Check all functions and methods
        all_functions = module_analysis.functions + [
            method for cls in module_analysis.classes 
            for method in cls.methods
        ]
        
        for func in all_functions:
            if len(func.parameters) > parameter_threshold:
                patterns.append(Pattern(
                    pattern_type=PatternType.ANTI_PATTERN,
                    name="Long Parameter List",
                    description=f"Function has too many parameters ({len(func.parameters)})",
                    location=func.location,
                    confidence=0.9,
                    metadata={
                        "parameter_count": len(func.parameters),
                        "parameters": func.parameters,
                        "threshold": parameter_threshold
                    }
                ))
        
        return patterns


class DuplicateCodeDetector(PatternDetector):
    """Detector for Duplicate Code smell."""
    
    def detect(self, module_analysis: Any, content: str) -> List[Pattern]:
        patterns = []
        
        # Extract all function bodies
        function_bodies = []
        
        for func in module_analysis.functions:
            func_content = self._get_function_content(content, func.location)
            if func_content:
                # Normalize whitespace and strip comments
                normalized = self._normalize_code(func_content)
                function_bodies.append((func, normalized))
        
        for cls in module_analysis.classes:
            for method in cls.methods:
                method_content = self._get_function_content(content, method.location)
                if method_content:
                    normalized = self._normalize_code(method_content)
                    function_bodies.append((method, normalized))
        
        # Find similar function bodies
        for i in range(len(function_bodies)):
            for j in range(i + 1, len(function_bodies)):
                func1, body1 = function_bodies[i]
                func2, body2 = function_bodies[j]
                
                similarity = self._calculate_similarity(body1, body2)
                
                if similarity > 0.8:  # 80% similar
                    patterns.append(Pattern(
                        pattern_type=PatternType.CODE_SMELL,
                        name="Duplicate Code",
                        description=f"Functions '{func1.name}' and '{func2.name}' have similar implementation",
                        location=func1.location,
                        confidence=similarity,
                        metadata={
                            "duplicate_function": func2.name,
                            "duplicate_location": {
                                "file": func2.location.file_path,
                                "line": func2.location.line_start
                            },
                            "similarity": similarity
                        }
                    ))
        
        return patterns
    
    def _get_function_content(self, content: str, location: CodeLocation) -> Optional[str]:
        """Extract function content from source code."""
        lines = content.splitlines()
        if location.line_start <= len(lines) and location.line_end <= len(lines):
            return '\n'.join(lines[location.line_start-1:location.line_end])
        return None
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        # Remove comments
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'""".*?"""', '', code, flags=re.DOTALL)
        code = re.sub(r"'''.*?'''", '', code, flags=re.DOTALL)
        
        # Normalize whitespace
        code = re.sub(r'\s+', ' ', code)
        
        # Remove variable names (simple heuristic)
        code = re.sub(r'\b[a-z_]\w*\b', 'VAR', code)
        
        return code.strip()
    
    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code snippets."""
        # Simple token-based similarity
        tokens1 = set(code1.split())
        tokens2 = set(code2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union) if union else 0.0


class PatternDetectorRegistry:
    """Registry of all pattern detectors."""
    
    def __init__(self):
        self.detectors: List[PatternDefinition] = []
        self._register_default_detectors()
    
    def _register_default_detectors(self):
        """Register default pattern detectors."""
        # Design patterns
        self.register(PatternDefinition(
            name="Singleton",
            pattern_type=PatternType.DESIGN_PATTERN,
            description="Singleton design pattern",
            languages=[LanguageSupport.PYTHON],
            detector=SingletonPatternDetector()
        ))
        
        self.register(PatternDefinition(
            name="Factory",
            pattern_type=PatternType.DESIGN_PATTERN,
            description="Factory design pattern",
            languages=[LanguageSupport.PYTHON],
            detector=FactoryPatternDetector()
        ))
        
        self.register(PatternDefinition(
            name="Observer",
            pattern_type=PatternType.DESIGN_PATTERN,
            description="Observer design pattern",
            languages=[LanguageSupport.PYTHON],
            detector=ObserverPatternDetector()
        ))
        
        # Anti-patterns
        self.register(PatternDefinition(
            name="God Class",
            pattern_type=PatternType.ANTI_PATTERN,
            description="Class with too many responsibilities",
            languages=[LanguageSupport.PYTHON],
            detector=GodClassAntiPatternDetector()
        ))
        
        self.register(PatternDefinition(
            name="Spaghetti Code",
            pattern_type=PatternType.ANTI_PATTERN,
            description="Complex, tangled control flow",
            languages=[LanguageSupport.PYTHON],
            detector=SpaghettiCodeAntiPatternDetector()
        ))
        
        self.register(PatternDefinition(
            name="Long Parameter List",
            pattern_type=PatternType.ANTI_PATTERN,
            description="Function with too many parameters",
            languages=[LanguageSupport.PYTHON],
            detector=LongParameterListAntiPatternDetector()
        ))
        
        # Code smells
        self.register(PatternDefinition(
            name="Duplicate Code",
            pattern_type=PatternType.CODE_SMELL,
            description="Similar code in multiple locations",
            languages=[LanguageSupport.PYTHON],
            detector=DuplicateCodeDetector()
        ))
    
    def register(self, pattern_def: PatternDefinition):
        """Register a new pattern detector."""
        self.detectors.append(pattern_def)
    
    def detect_patterns(self, module_analysis: Any, content: str) -> List[Pattern]:
        """Detect all patterns in the given module."""
        patterns = []
        
        for pattern_def in self.detectors:
            if module_analysis.language in pattern_def.languages:
                detected = pattern_def.detector.detect(module_analysis, content)
                patterns.extend(detected)
        
        return patterns


# Global registry instance
pattern_registry = PatternDetectorRegistry()

# Import and register advanced patterns
from .advanced_patterns import register_advanced_patterns
register_advanced_patterns(pattern_registry)