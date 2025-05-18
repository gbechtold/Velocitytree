"""Documentation quality checking and improvement suggestions."""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple, Any
from pathlib import Path

from ..code_analysis.models import (
    ModuleAnalysis,
    ClassAnalysis,
    FunctionAnalysis,
)
from .models import (
    DocIssue,
    DocSeverity,
    DocStyle,
)
from ..utils import logger


class QualityMetric(Enum):
    """Documentation quality metrics."""
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    CLARITY = "clarity"
    ACCURACY = "accuracy"
    STRUCTURE = "structure"
    EXAMPLES = "examples"
    REFERENCES = "references"
    
    
@dataclass
class QualityReport:
    """Documentation quality analysis report."""
    overall_score: float
    metric_scores: Dict[QualityMetric, float]
    issues: List[DocIssue]
    suggestions: List[str]
    statistics: Dict[str, Any]
    
    
@dataclass
class SuggestionRule:
    """Rule for generating documentation suggestions."""
    name: str
    pattern: Optional[str] = None
    condition: Optional[callable] = None
    message: str = ""
    severity: DocSeverity = DocSeverity.SUGGESTION
    

class DocQualityChecker:
    """Check documentation quality and provide improvement suggestions."""
    
    def __init__(self, style: DocStyle = DocStyle.GOOGLE):
        """Initialize the quality checker.
        
        Args:
            style: Documentation style to check against
        """
        self.style = style
        self._init_rules()
        
    def _init_rules(self):
        """Initialize checking rules and patterns."""
        self.rules = {
            'completeness': [
                SuggestionRule(
                    name="missing_module_docstring",
                    condition=lambda m: not m.docstring,
                    message="Missing module docstring",
                    severity=DocSeverity.WARNING,
                ),
                SuggestionRule(
                    name="missing_class_docstring",
                    condition=lambda c: not c.docstring,
                    message="Missing class docstring",
                    severity=DocSeverity.WARNING,
                ),
                SuggestionRule(
                    name="missing_function_docstring",
                    condition=lambda f: not f.docstring and not f.name.startswith('_'),
                    message="Missing docstring",
                    severity=DocSeverity.WARNING,
                ),
                SuggestionRule(
                    name="incomplete_parameters",
                    condition=lambda f: f.docstring and f.parameters and not self._has_parameter_docs(f),
                    message="Document all function parameters",
                    severity=DocSeverity.INFO,
                ),
                SuggestionRule(
                    name="missing_return_doc",
                    condition=lambda f: f.docstring and f.returns != 'None' and not self._has_return_doc(f),
                    message="Document the return value",
                    severity=DocSeverity.INFO,
                ),
            ],
            'consistency': [
                SuggestionRule(
                    name="inconsistent_style",
                    condition=lambda x: self._check_style_inconsistency(x),
                    message="Use consistent documentation style throughout the module",
                    severity=DocSeverity.INFO,
                ),
                SuggestionRule(
                    name="inconsistent_terminology",
                    pattern=r'\b(params?|parameters?|args?|arguments?)\b',
                    message="Use consistent terminology (prefer 'parameters' over 'params')",
                    severity=DocSeverity.SUGGESTION,
                ),
            ],
            'clarity': [
                SuggestionRule(
                    name="vague_description",
                    pattern=r'\b(does stuff|handles things|processes data)\b',
                    message="Provide specific descriptions instead of vague terms",
                    severity=DocSeverity.INFO,
                ),
                SuggestionRule(
                    name="missing_examples",
                    condition=lambda f: f.docstring and len(f.parameters) > 2 and not self._has_examples(f),
                    message="Add usage examples for complex functions",
                    severity=DocSeverity.SUGGESTION,
                ),
                SuggestionRule(
                    name="technical_jargon",
                    pattern=r'\b(impl|config|util|misc)\b',
                    message="Avoid abbreviations and technical jargon",
                    severity=DocSeverity.SUGGESTION,
                ),
            ],
            'structure': [
                SuggestionRule(
                    name="long_docstring",
                    condition=lambda x: x.docstring and len(x.docstring.split('\n')) > 50,
                    message="Consider breaking down long docstrings into sections",
                    severity=DocSeverity.SUGGESTION,
                ),
                SuggestionRule(
                    name="missing_sections",
                    condition=lambda f: f.docstring and self._should_have_sections(f) and not self._has_sections(f),
                    message="Add standard sections (Args, Returns, Raises, Examples)",
                    severity=DocSeverity.INFO,
                ),
            ],
        }
        
        # Style-specific patterns
        self.style_patterns = {
            DocStyle.GOOGLE: {
                'section_headers': [
                    r'^Args:\s*$',
                    r'^Returns:\s*$',
                    r'^Raises:\s*$',
                    r'^Example[s]?:\s*$',
                    r'^Note[s]?:\s*$',
                ],
                'parameter_format': r'^\s+(\w+)(\s+\([^)]+\))?\s*:\s*.+$',
                'return_format': r'^\s+.+$',
            },
            DocStyle.NUMPY: {
                'section_headers': [
                    r'^Parameters\s*$',
                    r'^-+\s*$',
                    r'^Returns\s*$',
                    r'^Raises\s*$',
                    r'^Example[s]?\s*$',
                ],
                'parameter_format': r'^(\w+)\s*:\s*\w+.*$',
                'return_format': r'^\w+\s*$',
            },
            DocStyle.SPHINX: {
                'section_headers': [],
                'parameter_format': r'^:param\s+(\w+):\s*.+$',
                'return_format': r'^:returns?:\s*.+$',
            },
        }
        
    def check_quality(
        self,
        analysis: ModuleAnalysis,
        recursive: bool = True,
    ) -> QualityReport:
        """Check documentation quality for a module.
        
        Args:
            analysis: Module analysis results
            recursive: Check nested classes and functions
            
        Returns:
            Quality report with scores and suggestions
        """
        issues = []
        suggestions = []
        statistics = self._gather_statistics(analysis)
        
        # Check module-level documentation
        issues.extend(self._check_element(analysis, 'module'))
        
        # Check functions
        for func in analysis.functions:
            issues.extend(self._check_element(func, 'function'))
            
        # Check classes
        for cls in analysis.classes:
            issues.extend(self._check_element(cls, 'class'))
            
            if recursive:
                # Check methods
                for method in cls.methods:
                    issues.extend(self._check_element(method, 'method'))
                    
        # Generate suggestions based on issues
        suggestions = self._generate_suggestions(issues, analysis)
        
        # Calculate scores
        metric_scores = self._calculate_metric_scores(issues, statistics)
        overall_score = self._calculate_overall_score(metric_scores)
        
        return QualityReport(
            overall_score=overall_score,
            metric_scores=metric_scores,
            issues=issues,
            suggestions=suggestions,
            statistics=statistics,
        )
        
    def _check_element(self, element: Any, element_type: str) -> List[DocIssue]:
        """Check documentation quality for a single element."""
        issues = []
        
        # Apply all rules
        for category, rules in self.rules.items():
            for rule in rules:
                if self._applies_rule(rule, element):
                    location = self._get_location(element, element_type)
                    issue = DocIssue(
                        severity=rule.severity,
                        location=location,
                        message=rule.message,
                        suggestion=self._get_suggestion_for_rule(rule),
                    )
                    # Store category separately for now
                    issue._category = category
                    issues.append(issue)
                    
        # Check style-specific patterns
        if hasattr(element, 'docstring') and element.docstring:
            issues.extend(self._check_style_compliance(element, element_type))
            
        return issues
        
    def _get_suggestion_for_rule(self, rule: SuggestionRule) -> str:
        """Get suggestion text for a rule."""
        return rule.message
        
    def _applies_rule(self, rule: SuggestionRule, element: Any) -> bool:
        """Check if a rule applies to an element."""
        if rule.condition:
            try:
                return rule.condition(element)
            except Exception:
                return False
                
        if rule.pattern and hasattr(element, 'docstring') and element.docstring:
            return bool(re.search(rule.pattern, element.docstring, re.IGNORECASE))
            
        return False
        
    def _check_style_compliance(self, element: Any, element_type: str) -> List[DocIssue]:
        """Check if documentation follows the specified style guide."""
        issues = []
        docstring = element.docstring
        
        if not docstring:
            return issues
            
        patterns = self.style_patterns[self.style]
        lines = docstring.split('\n')
        
        # Check section headers
        found_sections = set()
        for line in lines:
            for pattern in patterns['section_headers']:
                if re.match(pattern, line.strip()):
                    found_sections.add(pattern)
                    
        # Check if required sections are missing
        if element_type in ['function', 'method'] and hasattr(element, 'parameters') and element.parameters:
            required_section = 'Args:' if self.style == DocStyle.GOOGLE else 'Parameters'
            if not any(required_section in s for s in found_sections):
                issue = DocIssue(
                    severity=DocSeverity.INFO,
                    location=self._get_location(element, element_type),
                    message=f"Missing '{required_section}' section for documented parameters",
                    suggestion=f"Add '{required_section}' section to document parameters",
                )
                issue._category = 'structure'
                issues.append(issue)
                
        return issues
        
    def _has_parameter_docs(self, func: FunctionAnalysis) -> bool:
        """Check if function has parameter documentation."""
        if not func.docstring:
            return False
            
        # Simple check - look for parameter names in docstring
        for param in func.parameters:
            if param not in func.docstring:
                return False
                
        return True
        
    def _has_return_doc(self, func: FunctionAnalysis) -> bool:
        """Check if function has return value documentation."""
        if not func.docstring:
            return False
            
        return any(keyword in func.docstring.lower() 
                  for keyword in ['return', 'returns', 'yield', 'yields'])
                  
    def _has_examples(self, element: Any) -> bool:
        """Check if element has usage examples."""
        if not hasattr(element, 'docstring') or not element.docstring:
            return False
            
        return any(keyword in element.docstring.lower() 
                  for keyword in ['example', 'examples', '>>>', 'code-block'])
                  
    def _should_have_sections(self, func: FunctionAnalysis) -> bool:
        """Check if function should have structured sections."""
        # Functions with parameters or complex logic should have sections
        return (len(func.parameters) > 0 or 
                len(func.docstring.split('\n')) > 3 if func.docstring else False)
                
    def _has_sections(self, func: FunctionAnalysis) -> bool:
        """Check if function has structured sections."""
        if not func.docstring:
            return False
            
        sections = ['args:', 'arguments:', 'parameters:', 'returns:', 'raises:', 'examples:']
        return any(section in func.docstring.lower() for section in sections)
        
    def _check_style_inconsistency(self, element: Any) -> bool:
        """Check for documentation style inconsistencies."""
        # This is a simplified check - in practice would compare across module
        return False
        
    def _get_location(self, element: Any, element_type: str) -> str:
        """Get location string for an element."""
        if hasattr(element, 'name'):
            return f"{element_type.capitalize()}: {element.name}"
        else:
            return f"{element_type.capitalize()}"
            
    def _gather_statistics(self, analysis: ModuleAnalysis) -> Dict[str, Any]:
        """Gather documentation statistics."""
        stats = {
            'total_elements': 1,  # Module itself
            'documented_elements': 1 if analysis.docstring else 0,
            'functions': len(analysis.functions),
            'documented_functions': sum(1 for f in analysis.functions if f.docstring),
            'classes': len(analysis.classes),
            'documented_classes': sum(1 for c in analysis.classes if c.docstring),
            'methods': sum(len(c.methods) for c in analysis.classes),
            'documented_methods': sum(
                sum(1 for m in c.methods if m.docstring) 
                for c in analysis.classes
            ),
            'avg_docstring_length': 0,
            'total_docstring_lines': 0,
        }
        
        # Calculate totals
        stats['total_elements'] += stats['functions'] + stats['classes'] + stats['methods']
        stats['documented_elements'] += (stats['documented_functions'] + 
                                       stats['documented_classes'] + 
                                       stats['documented_methods'])
                                       
        # Calculate average docstring length
        docstring_lengths = []
        if analysis.docstring:
            docstring_lengths.append(len(analysis.docstring.split('\n')))
            
        for func in analysis.functions:
            if func.docstring:
                docstring_lengths.append(len(func.docstring.split('\n')))
                
        for cls in analysis.classes:
            if cls.docstring:
                docstring_lengths.append(len(cls.docstring.split('\n')))
            for method in cls.methods:
                if method.docstring:
                    docstring_lengths.append(len(method.docstring.split('\n')))
                    
        if docstring_lengths:
            stats['avg_docstring_length'] = sum(docstring_lengths) / len(docstring_lengths)
            stats['total_docstring_lines'] = sum(docstring_lengths)
            
        return stats
        
    def _calculate_metric_scores(
        self,
        issues: List[DocIssue],
        statistics: Dict[str, Any],
    ) -> Dict[QualityMetric, float]:
        """Calculate individual metric scores."""
        scores = {}
        
        # Completeness score
        if statistics['total_elements'] > 0:
            completeness = statistics['documented_elements'] / statistics['total_elements']
            scores[QualityMetric.COMPLETENESS] = completeness * 100
        else:
            scores[QualityMetric.COMPLETENESS] = 100.0
            
        # Consistency score (based on style issues)
        consistency_issues = sum(1 for issue in issues if hasattr(issue, '_category') and issue._category == 'consistency')
        scores[QualityMetric.CONSISTENCY] = max(0, 100 - consistency_issues * 10)
        
        # Clarity score (based on clarity issues)
        clarity_issues = sum(1 for issue in issues if hasattr(issue, '_category') and issue._category == 'clarity')
        scores[QualityMetric.CLARITY] = max(0, 100 - clarity_issues * 5)
        
        # Structure score (based on structure issues)
        structure_issues = sum(1 for issue in issues if hasattr(issue, '_category') and issue._category == 'structure')
        scores[QualityMetric.STRUCTURE] = max(0, 100 - structure_issues * 8)
        
        # Examples score
        example_count = sum(1 for issue in issues if 'example' in issue.message.lower())
        scores[QualityMetric.EXAMPLES] = max(0, 100 - example_count * 15)
        
        # Accuracy score (assume 100 unless specific issues)
        scores[QualityMetric.ACCURACY] = 100.0
        
        # References score (assume 100 unless specific issues)
        scores[QualityMetric.REFERENCES] = 100.0
        
        return scores
        
    def _calculate_overall_score(self, metric_scores: Dict[QualityMetric, float]) -> float:
        """Calculate overall quality score from individual metrics."""
        if not metric_scores:
            return 0.0
            
        # Weighted average
        weights = {
            QualityMetric.COMPLETENESS: 0.3,
            QualityMetric.CONSISTENCY: 0.2,
            QualityMetric.CLARITY: 0.2,
            QualityMetric.STRUCTURE: 0.1,
            QualityMetric.EXAMPLES: 0.1,
            QualityMetric.ACCURACY: 0.05,
            QualityMetric.REFERENCES: 0.05,
        }
        
        total_weight = sum(weights.values())
        weighted_sum = sum(
            metric_scores.get(metric, 0) * weight 
            for metric, weight in weights.items()
        )
        
        return weighted_sum / total_weight
        
    def _generate_suggestions(
        self,
        issues: List[DocIssue],
        analysis: ModuleAnalysis,
    ) -> List[str]:
        """Generate improvement suggestions based on issues."""
        suggestions = []
        
        # Priority suggestions based on severity
        high_priority = [issue for issue in issues if issue.severity in [DocSeverity.ERROR, DocSeverity.WARNING]]
        medium_priority = [issue for issue in issues if issue.severity == DocSeverity.INFO]
        low_priority = [issue for issue in issues if issue.severity == DocSeverity.SUGGESTION]
        
        # Generate actionable suggestions
        if high_priority:
            suggestions.append("Priority: Address critical documentation issues:")
            for issue in high_priority[:3]:  # Top 3 high priority
                suggestions.append(f"  - {issue.location}: {issue.message}")
                
        if medium_priority:
            suggestions.append("\nConsider improving:")
            for issue in medium_priority[:3]:  # Top 3 medium priority
                suggestions.append(f"  - {issue.location}: {issue.message}")
                
        # General suggestions based on patterns
        if analysis.functions and len(analysis.functions) > 5:
            undocumented = [f for f in analysis.functions if not f.docstring]
            if len(undocumented) > len(analysis.functions) * 0.3:
                suggestions.append("\n- Add docstrings to frequently used functions")
                
        # Style-specific suggestions
        if self.style == DocStyle.GOOGLE:
            suggestions.append("\n- Follow Google style guide: https://google.github.io/styleguide/pyguide.html")
        elif self.style == DocStyle.NUMPY:
            suggestions.append("\n- Follow NumPy style guide: https://numpydoc.readthedocs.io/")
            
        return suggestions


class DocSuggestionEngine:
    """Generate smart documentation suggestions based on code context."""
    
    def __init__(self):
        """Initialize the suggestion engine."""
        self.templates = self._init_templates()
        
    def _init_templates(self):
        """Initialize suggestion templates."""
        return {
            'function': {
                'basic': '''"""[Brief description of what the function does].
                
Args:
    {parameters}
    
Returns:
    [Description of return value]
"""''',
                'complex': '''"""[Brief description of what the function does].
                
[Longer description if needed]

Args:
    {parameters}
    
Returns:
    [Description of return value]
    
Raises:
    [ExceptionType]: [When this exception is raised]
    
Examples:
    >>> [Example usage]
    [Example output]
"""''',
            },
            'class': {
                'basic': '''"""[Brief description of the class].

Attributes:
    {attributes}
"""''',
                'complex': '''"""[Brief description of the class].

[Longer description if needed]

Attributes:
    {attributes}
    
Methods:
    {methods}
    
Examples:
    >>> [Example usage]
    [Example output]
"""''',
            },
            'module': {
                'basic': '''"""[Brief description of the module].

This module provides [main functionality].
"""''',
                'complex': '''"""[Brief description of the module].

This module provides [main functionality].

Classes:
    {classes}
    
Functions:
    {functions}
    
Constants:
    {constants}
"""''',
            },
        }
        
    def suggest_docstring(
        self,
        element: Any,
        element_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate a suggested docstring for an element.
        
        Args:
            element: Code element to document
            element_type: Type of element (function, class, module)
            context: Additional context for generation
            
        Returns:
            Suggested docstring template
        """
        templates = self.templates.get(element_type, {})
        
        # Choose template based on complexity
        if self._is_complex(element):
            template = templates.get('complex', templates.get('basic', ''))
        else:
            template = templates.get('basic', '')
            
        # Fill in template with element information
        if element_type == 'function':
            return self._fill_function_template(template, element)
        elif element_type == 'class':
            return self._fill_class_template(template, element)
        elif element_type == 'module':
            return self._fill_module_template(template, element, context)
            
        return template
        
    def _is_complex(self, element: Any) -> bool:
        """Determine if an element is complex enough for extended documentation."""
        if hasattr(element, 'parameters') and len(element.parameters) > 3:
            return True
        if hasattr(element, 'lines_of_code') and element.lines_of_code > 50:
            return True
        if hasattr(element, 'complexity') and element.complexity > 10:
            return True
        return False
        
    def _fill_function_template(self, template: str, func: FunctionAnalysis) -> str:
        """Fill function template with actual data."""
        # Format parameters
        params_list = []
        for param in func.parameters:
            param_type = func.parameter_types.get(param, 'Any') if hasattr(func, 'parameter_types') else 'Any'
            params_list.append(f"{param} ({param_type}): [Description of {param}]")
            
        parameters = '\n    '.join(params_list) if params_list else '[No parameters]'
        
        return template.format(parameters=parameters)
        
    def _fill_class_template(self, template: str, cls: ClassAnalysis) -> str:
        """Fill class template with actual data."""
        # Format attributes
        attrs_list = []
        if hasattr(cls, 'instance_attributes'):
            for attr in cls.instance_attributes:
                attrs_list.append(f"{attr}: [Description of {attr}]")
                
        attributes = '\n    '.join(attrs_list) if attrs_list else '[No public attributes]'
        
        # Format methods
        methods_list = []
        for method in cls.methods:
            if not method.name.startswith('_'):
                methods_list.append(f"{method.name}(): [Description of {method.name}]")
                
        methods = '\n    '.join(methods_list) if methods_list else '[No public methods]'
        
        return template.format(attributes=attributes, methods=methods)
        
    def _fill_module_template(self, template: str, module: ModuleAnalysis, context: Optional[Dict[str, Any]]) -> str:
        """Fill module template with actual data."""
        # Format classes
        classes_list = []
        for cls in module.classes:
            classes_list.append(f"{cls.name}: [Description of {cls.name}]")
            
        classes = '\n    '.join(classes_list) if classes_list else '[No classes]'
        
        # Format functions
        functions_list = []
        for func in module.functions:
            functions_list.append(f"{func.name}(): [Description of {func.name}]")
            
        functions = '\n    '.join(functions_list) if functions_list else '[No functions]'
        
        # Format constants
        constants_list = []
        if hasattr(module, 'constants') or hasattr(module, 'global_variables'):
            vars_to_check = getattr(module, 'constants', []) + getattr(module, 'global_variables', [])
            for const in vars_to_check:
                if const.isupper():  # Convention for constants
                    constants_list.append(f"{const}: [Description of {const}]")
                    
        constants = '\n    '.join(constants_list) if constants_list else '[No constants]'
        
        return template.format(classes=classes, functions=functions, constants=constants)
        
    def improve_docstring(
        self,
        current_docstring: str,
        element: Any,
        issues: List[DocIssue],
    ) -> str:
        """Improve an existing docstring based on quality issues.
        
        Args:
            current_docstring: Current docstring text
            element: Code element being documented
            issues: Quality issues found
            
        Returns:
            Improved docstring
        """
        improved = current_docstring
        
        # Add missing sections based on issues
        for issue in issues:
            if 'missing' in issue.message.lower() and 'section' in issue.message.lower():
                if 'args' in issue.message.lower() or 'parameters' in issue.message.lower():
                    improved = self._add_parameters_section(improved, element)
                elif 'returns' in issue.message.lower():
                    improved = self._add_returns_section(improved, element)
                elif 'examples' in issue.message.lower():
                    improved = self._add_examples_section(improved, element)
                    
        return improved
        
    def _add_parameters_section(self, docstring: str, element: Any) -> str:
        """Add parameters section to docstring."""
        if not hasattr(element, 'parameters'):
            return docstring
            
        lines = docstring.split('\n')
        insert_index = len(lines) - 1  # Before closing quotes
        
        if lines[insert_index].strip() == '"""':
            insert_index -= 1
            
        # Add parameters section
        params_section = ["\nArgs:"]
        for param in element.parameters:
            params_section.append(f"    {param}: [Description of {param}]")
            
        lines[insert_index:insert_index] = params_section
        return '\n'.join(lines)
        
    def _add_returns_section(self, docstring: str, element: Any) -> str:
        """Add returns section to docstring."""
        if not hasattr(element, 'returns') or element.returns == 'None':
            return docstring
            
        lines = docstring.split('\n')
        insert_index = len(lines) - 1
        
        if lines[insert_index].strip() == '"""':
            insert_index -= 1
            
        # Add returns section
        returns_section = ["\nReturns:", f"    [Description of return value]"]
        lines[insert_index:insert_index] = returns_section
        return '\n'.join(lines)
        
    def _add_examples_section(self, docstring: str, element: Any) -> str:
        """Add examples section to docstring."""
        lines = docstring.split('\n')
        insert_index = len(lines) - 1
        
        if lines[insert_index].strip() == '"""':
            insert_index -= 1
            
        # Add examples section
        examples_section = [
            "\nExamples:",
            "    >>> # Example usage",
            "    >>> result = function_name()",
            "    expected_output"
        ]
        lines[insert_index:insert_index] = examples_section
        return '\n'.join(lines)