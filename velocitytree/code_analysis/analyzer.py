"""Core code analyzer implementation."""

import ast
import os
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple
from datetime import datetime
import re
import tokenize
import io

from .models import (
    AnalysisResult,
    ModuleAnalysis,
    FunctionAnalysis,
    ClassAnalysis,
    CodeIssue,
    CodeMetrics,
    Pattern,
    Suggestion,
    CodeLocation,
    Severity,
    IssueCategory,
    PatternType,
    LanguageSupport
)
from .language_adapters import get_language_adapter, BaseLanguageAdapter
from .patterns import pattern_registry
from ..utils import logger


class CodeAnalyzer:
    """Main code analyzer class with plugin architecture."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the code analyzer.
        
        Args:
            config: Configuration dictionary for analyzer settings
        """
        self.config = config or {}
        self.language_adapters: Dict[LanguageSupport, BaseLanguageAdapter] = {}
        self._load_language_adapters()
        self.cache = {}  # Simple in-memory cache
        
    def _load_language_adapters(self):
        """Load language-specific analyzers."""
        for language in LanguageSupport:
            try:
                adapter = get_language_adapter(language)
                if adapter:
                    self.language_adapters[language] = adapter
            except Exception as e:
                logger.warning(f"Failed to load adapter for {language}: {e}")
    
    def analyze_file(self, file_path: Union[str, Path]) -> Optional[ModuleAnalysis]:
        """Analyze a single file.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            Module analysis result or None if analysis failed
        """
        file_path = Path(file_path)
        
        # Check cache
        cache_key = str(file_path)
        if cache_key in self.cache:
            file_mtime = file_path.stat().st_mtime
            cached_result, cached_mtime = self.cache[cache_key]
            if file_mtime <= cached_mtime:
                return cached_result
        
        # Detect language
        language = self._detect_language(file_path)
        if not language:
            logger.warning(f"Unsupported file type: {file_path}")
            return None
        
        # Get appropriate adapter
        adapter = self.language_adapters.get(language)
        if not adapter:
            logger.warning(f"No adapter for language: {language}")
            return None
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Perform analysis
            module_analysis = adapter.analyze_module(str(file_path), content)
            
            # Calculate metrics
            metrics = self._calculate_metrics(module_analysis, content)
            module_analysis.metrics = metrics
            
            # Detect patterns
            patterns = self._detect_patterns(module_analysis, content)
            module_analysis.patterns.extend(patterns)
            
            # Check common issues
            issues = self._check_common_issues(module_analysis, content)
            module_analysis.issues.extend(issues)
            
            # Cache result
            self.cache[cache_key] = (module_analysis, time.time())
            
            return module_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return None
    
    def analyze_directory(self, directory: Union[str, Path], 
                         recursive: bool = True,
                         file_patterns: Optional[List[str]] = None) -> AnalysisResult:
        """Analyze all files in a directory.
        
        Args:
            directory: Directory to analyze
            recursive: Whether to analyze subdirectories
            file_patterns: Glob patterns for files to include
            
        Returns:
            Complete analysis result
        """
        start_time = time.time()
        directory = Path(directory)
        
        # Find files to analyze
        files_to_analyze = self._find_files(directory, recursive, file_patterns)
        
        # Analyze each file
        modules = []
        error_files = []
        language_breakdown = {}
        
        for file_path in files_to_analyze:
            module_analysis = self.analyze_file(file_path)
            if module_analysis:
                modules.append(module_analysis)
                language = module_analysis.language
                language_breakdown[language] = language_breakdown.get(language, 0) + 1
            else:
                error_files.append(str(file_path))
        
        # Aggregate results
        all_issues = []
        all_patterns = []
        total_lines = 0
        
        for module in modules:
            all_issues.extend(module.issues)
            all_patterns.extend(module.patterns)
            total_lines += module.metrics.lines_of_code
        
        # Calculate aggregate metrics
        aggregate_metrics = self._aggregate_metrics([m.metrics for m in modules])
        
        # Generate suggestions
        suggestions = self._generate_suggestions(modules, all_issues, all_patterns)
        
        analysis_time = time.time() - start_time
        
        return AnalysisResult(
            timestamp=datetime.now(),
            files_analyzed=len(modules),
            total_lines=total_lines,
            language_breakdown=language_breakdown,
            modules=modules,
            aggregate_metrics=aggregate_metrics,
            all_issues=all_issues,
            all_patterns=all_patterns,
            suggestions=suggestions,
            analysis_time=analysis_time,
            error_files=error_files
        )
    
    def analyze_changes(self, old_content: str, new_content: str, 
                       file_path: str) -> Tuple[ModuleAnalysis, ModuleAnalysis, List[Suggestion]]:
        """Analyze changes between two versions of a file.
        
        Args:
            old_content: Previous version of the file
            new_content: New version of the file
            file_path: Path to the file (for language detection)
            
        Returns:
            Tuple of (old_analysis, new_analysis, change_suggestions)
        """
        language = self._detect_language(Path(file_path))
        if not language:
            raise ValueError(f"Unsupported file type: {file_path}")
        
        adapter = self.language_adapters.get(language)
        if not adapter:
            raise ValueError(f"No adapter for language: {language}")
        
        # Analyze both versions
        old_analysis = adapter.analyze_module(file_path, old_content)
        new_analysis = adapter.analyze_module(file_path, new_content)
        
        # Calculate metrics for both
        old_analysis.metrics = self._calculate_metrics(old_analysis, old_content)
        new_analysis.metrics = self._calculate_metrics(new_analysis, new_content)
        
        # Generate change-specific suggestions
        change_suggestions = self._analyze_changes(old_analysis, new_analysis)
        
        return old_analysis, new_analysis, change_suggestions
    
    def _detect_language(self, file_path: Path) -> Optional[LanguageSupport]:
        """Detect programming language from file extension."""
        extension_map = {
            '.py': LanguageSupport.PYTHON,
            '.js': LanguageSupport.JAVASCRIPT,
            '.jsx': LanguageSupport.JAVASCRIPT,
            '.ts': LanguageSupport.TYPESCRIPT,
            '.tsx': LanguageSupport.TYPESCRIPT,
            '.java': LanguageSupport.JAVA,
            '.cpp': LanguageSupport.CPP,
            '.cc': LanguageSupport.CPP,
            '.cxx': LanguageSupport.CPP,
            '.go': LanguageSupport.GO,
            '.rs': LanguageSupport.RUST,
            '.rb': LanguageSupport.RUBY
        }
        
        extension = file_path.suffix.lower()
        return extension_map.get(extension)
    
    def _find_files(self, directory: Path, recursive: bool, 
                   file_patterns: Optional[List[str]]) -> List[Path]:
        """Find files to analyze in a directory."""
        files = []
        
        if not file_patterns:
            # Default patterns for supported languages
            file_patterns = ['*.py', '*.js', '*.jsx', '*.ts', '*.tsx', 
                           '*.java', '*.cpp', '*.cc', '*.go', '*.rs', '*.rb']
        
        for pattern in file_patterns:
            if recursive:
                files.extend(directory.rglob(pattern))
            else:
                files.extend(directory.glob(pattern))
        
        return sorted(set(files))
    
    def _calculate_metrics(self, module: ModuleAnalysis, content: str) -> CodeMetrics:
        """Calculate code metrics for a module."""
        lines = content.splitlines()
        lines_of_code = len([line for line in lines if line.strip()])
        lines_of_comments = self._count_comment_lines(content, module.language)
        
        # Calculate complexity metrics
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(module)
        cognitive_complexity = self._calculate_cognitive_complexity(module)
        
        # Calculate maintainability index
        # MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        # Simplified version
        import math
        halstead_volume = lines_of_code * 10  # Simplified
        maintainability_index = max(0, min(100, 
            171 - 5.2 * math.log(halstead_volume + 1) 
            - 0.23 * cyclomatic_complexity 
            - 16.2 * math.log(lines_of_code + 1)
        ))
        
        # Calculate other metrics
        code_to_comment_ratio = lines_of_code / (lines_of_comments + 1)
        
        # Function metrics
        all_functions = module.functions + [m for c in module.classes for m in c.methods]
        if all_functions:
            function_lengths = [f.location.line_end - f.location.line_start + 1 
                              for f in all_functions]
            average_function_length = sum(function_lengths) / len(function_lengths)
            max_function_length = max(function_lengths)
        else:
            average_function_length = 0
            max_function_length = 0
        
        return CodeMetrics(
            lines_of_code=lines_of_code,
            lines_of_comments=lines_of_comments,
            cyclomatic_complexity=cyclomatic_complexity,
            cognitive_complexity=cognitive_complexity,
            maintainability_index=maintainability_index,
            code_to_comment_ratio=code_to_comment_ratio,
            average_function_length=average_function_length,
            max_function_length=max_function_length,
            number_of_functions=len(module.functions),
            number_of_classes=len(module.classes)
        )
    
    def _count_comment_lines(self, content: str, language: LanguageSupport) -> int:
        """Count comment lines in code."""
        if language == LanguageSupport.PYTHON:
            # Count lines starting with # and docstrings
            lines = content.splitlines()
            comment_lines = 0
            in_docstring = False
            docstring_char = None
            
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('#'):
                    comment_lines += 1
                elif stripped.startswith('"""') or stripped.startswith("'''"):
                    if not in_docstring:
                        in_docstring = True
                        docstring_char = stripped[:3]
                    elif stripped.endswith(docstring_char):
                        in_docstring = False
                    comment_lines += 1
                elif in_docstring:
                    comment_lines += 1
            
            return comment_lines
        else:
            # Simple approximation for other languages
            return len([line for line in content.splitlines() 
                       if line.strip().startswith('//') or line.strip().startswith('/*')])
    
    def _calculate_cyclomatic_complexity(self, module: ModuleAnalysis) -> float:
        """Calculate cyclomatic complexity for a module."""
        total_complexity = 0
        
        # Add complexity for each function
        for func in module.functions:
            total_complexity += func.complexity
        
        # Add complexity for methods in classes
        for cls in module.classes:
            for method in cls.methods:
                total_complexity += method.complexity
        
        # Average complexity
        total_functions = len(module.functions) + sum(len(c.methods) for c in module.classes)
        if total_functions == 0:
            return 1  # Base complexity
        
        return total_complexity / total_functions
    
    def _calculate_cognitive_complexity(self, module: ModuleAnalysis) -> float:
        """Calculate cognitive complexity (simplified version)."""
        # This is a simplified version - real cognitive complexity
        # requires deeper AST analysis
        return self._calculate_cyclomatic_complexity(module) * 1.2
    
    def _detect_patterns(self, module: ModuleAnalysis, content: str) -> List[Pattern]:
        """Detect design patterns and anti-patterns."""
        # Use the pattern registry to detect all registered patterns
        return pattern_registry.detect_patterns(module, content)
    
    def _check_common_issues(self, module: ModuleAnalysis, content: str) -> List[CodeIssue]:
        """Check for common code issues."""
        issues = []
        
        # Check for long functions
        for func in module.functions + [m for c in module.classes for m in c.methods]:
            func_length = func.location.line_end - func.location.line_start + 1
            if func_length > 50:
                issues.append(CodeIssue(
                    severity=Severity.WARNING,
                    category=IssueCategory.MAINTAINABILITY,
                    message=f"Function '{func.name}' is too long ({func_length} lines)",
                    rule_id="long-function",
                    location=func.location,
                    suggestion="Consider breaking this function into smaller, more focused functions"
                ))
        
        # Check for missing docstrings
        for func in module.functions:
            if not func.docstring:
                issues.append(CodeIssue(
                    severity=Severity.INFO,
                    category=IssueCategory.DOCUMENTATION,
                    message=f"Function '{func.name}' is missing a docstring",
                    rule_id="missing-docstring",
                    location=func.location,
                    suggestion="Add a docstring to document the function's purpose and parameters"
                ))
        
        # Check for complex functions
        for func in module.functions + [m for c in module.classes for m in c.methods]:
            if func.complexity > 10:
                issues.append(CodeIssue(
                    severity=Severity.WARNING,
                    category=IssueCategory.COMPLEXITY,
                    message=f"Function '{func.name}' has high cyclomatic complexity ({func.complexity})",
                    rule_id="high-complexity",
                    location=func.location,
                    suggestion="Consider simplifying this function by extracting complex logic"
                ))
        
        return issues
    
    def _aggregate_metrics(self, metrics_list: List[CodeMetrics]) -> CodeMetrics:
        """Aggregate metrics from multiple modules."""
        if not metrics_list:
            return CodeMetrics(
                lines_of_code=0,
                lines_of_comments=0,
                cyclomatic_complexity=0,
                cognitive_complexity=0,
                maintainability_index=0
            )
        
        total_loc = sum(m.lines_of_code for m in metrics_list)
        total_comments = sum(m.lines_of_comments for m in metrics_list)
        
        # Weighted averages
        avg_cyclomatic = sum(m.cyclomatic_complexity * m.lines_of_code for m in metrics_list) / total_loc
        avg_cognitive = sum(m.cognitive_complexity * m.lines_of_code for m in metrics_list) / total_loc
        avg_maintainability = sum(m.maintainability_index * m.lines_of_code for m in metrics_list) / total_loc
        
        return CodeMetrics(
            lines_of_code=total_loc,
            lines_of_comments=total_comments,
            cyclomatic_complexity=avg_cyclomatic,
            cognitive_complexity=avg_cognitive,
            maintainability_index=avg_maintainability,
            code_to_comment_ratio=total_loc / (total_comments + 1),
            average_function_length=sum(m.average_function_length for m in metrics_list) / len(metrics_list),
            max_function_length=max(m.max_function_length for m in metrics_list),
            number_of_functions=sum(m.number_of_functions for m in metrics_list),
            number_of_classes=sum(m.number_of_classes for m in metrics_list)
        )
    
    def _generate_suggestions(self, modules: List[ModuleAnalysis], 
                            issues: List[CodeIssue], 
                            patterns: List[Pattern]) -> List[Suggestion]:
        """Generate improvement suggestions based on analysis."""
        suggestions = []
        
        # Group issues by category
        issues_by_category = {}
        for issue in issues:
            category = issue.category
            if category not in issues_by_category:
                issues_by_category[category] = []
            issues_by_category[category].append(issue)
        
        # Generate suggestions based on issue patterns
        if IssueCategory.COMPLEXITY in issues_by_category:
            complexity_issues = issues_by_category[IssueCategory.COMPLEXITY]
            if len(complexity_issues) > 5:
                suggestions.append(Suggestion(
                    title="Reduce Overall Code Complexity",
                    description="Multiple functions have high complexity. Consider a refactoring sprint.",
                    location=CodeLocation(
                        file_path="project-wide",
                        line_start=0,
                        line_end=0
                    ),
                    category=IssueCategory.MAINTAINABILITY,
                    priority=2,
                    estimated_effort="large",
                    rationale="High complexity makes code harder to understand and maintain"
                ))
        
        # Pattern-based suggestions
        god_classes = [p for p in patterns if p.name == "God Class"]
        if god_classes:
            for pattern in god_classes:
                suggestions.append(Suggestion(
                    title=f"Refactor {pattern.location.file_path}",
                    description="This class has too many responsibilities. Consider splitting it.",
                    location=pattern.location,
                    category=IssueCategory.MAINTAINABILITY,
                    priority=3,
                    estimated_effort="large",
                    rationale="Large classes violate the Single Responsibility Principle"
                ))
        
        return suggestions
    
    def _analyze_changes(self, old_analysis: ModuleAnalysis, 
                        new_analysis: ModuleAnalysis) -> List[Suggestion]:
        """Analyze changes between two versions and suggest improvements."""
        suggestions = []
        
        # Compare complexity metrics
        old_complexity = old_analysis.metrics.cyclomatic_complexity
        new_complexity = new_analysis.metrics.cyclomatic_complexity
        
        if new_complexity > old_complexity * 1.2:  # 20% increase
            suggestions.append(Suggestion(
                title="Complexity Increase Detected",
                description=f"Code complexity increased from {old_complexity:.1f} to {new_complexity:.1f}",
                location=CodeLocation(
                    file_path=new_analysis.file_path,
                    line_start=0,
                    line_end=0
                ),
                category=IssueCategory.COMPLEXITY,
                priority=2,
                estimated_effort="medium",
                rationale="Increasing complexity makes code harder to maintain"
            ))
        
        # Check for removed documentation
        old_funcs_with_docs = sum(1 for f in old_analysis.functions if f.docstring)
        new_funcs_with_docs = sum(1 for f in new_analysis.functions if f.docstring)
        
        if new_funcs_with_docs < old_funcs_with_docs:
            suggestions.append(Suggestion(
                title="Documentation Coverage Decreased",
                description="Some functions lost their documentation",
                location=CodeLocation(
                    file_path=new_analysis.file_path,
                    line_start=0,
                    line_end=0
                ),
                category=IssueCategory.DOCUMENTATION,
                priority=3,
                estimated_effort="small",
                rationale="Documentation helps other developers understand the code"
            ))
        
        return suggestions