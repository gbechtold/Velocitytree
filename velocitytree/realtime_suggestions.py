"""
Real-time code suggestions engine for VelocityTree.
Provides IDE-style live analysis and contextual suggestions.
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from datetime import datetime
import difflib

from velocitytree.code_analysis.analyzer import CodeAnalyzer
from velocitytree.code_analysis.models import (
    ModuleAnalysis, Pattern, Severity,
    CodeMetrics as ComplexityMetrics, CodeIssue as Issue, CodeLocation
)
from velocitytree.documentation.quality import DocQualityChecker
from velocitytree.documentation.models import DocIssue


class SuggestionType(Enum):
    """Types of code suggestions."""
    STYLE = "style"
    PERFORMANCE = "performance"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    ERROR_FIX = "error_fix"
    WARNING_FIX = "warning_fix"


class QuickFixType(Enum):
    """Types of quick fixes available."""
    AUTO_IMPORT = "auto_import"
    ADD_DOCSTRING = "add_docstring"
    FIX_NAMING = "fix_naming"
    REMOVE_UNUSED = "remove_unused"
    FIX_TYPE_HINT = "fix_type_hint"
    EXTRACT_FUNCTION = "extract_function"
    INLINE_VARIABLE = "inline_variable"
    ADD_ERROR_HANDLING = "add_error_handling"


@dataclass
class CodePosition:
    """Represents a position in code."""
    line: int
    column: int
    
    def __lt__(self, other):
        return (self.line, self.column) < (other.line, other.column)
    
    def __le__(self, other):
        return (self.line, self.column) <= (other.line, other.column)
    
    def __gt__(self, other):
        return (self.line, self.column) > (other.line, other.column)
    
    def __ge__(self, other):
        return (self.line, self.column) >= (other.line, other.column)
    
    def __eq__(self, other):
        return (self.line, self.column) == (other.line, other.column)


@dataclass
class CodeRange:
    """Represents a range in code."""
    start: CodePosition
    end: CodePosition
    
    def contains(self, position: CodePosition) -> bool:
        """Check if position is within this range."""
        return self.start <= position <= self.end


@dataclass
class QuickFix:
    """Represents a quick fix for an issue."""
    type: QuickFixType
    title: str
    description: str
    range: CodeRange
    replacement: str
    preview: Optional[str] = None
    
    def __hash__(self):
        return hash((self.type, self.title, self.range.start.line))


@dataclass
class CodeSuggestion:
    """Represents a code suggestion."""
    type: SuggestionType
    severity: Severity
    message: str
    range: CodeRange
    file_path: Path
    quick_fixes: List[QuickFix] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0  # Higher values = higher priority
    
    def __lt__(self, other):
        # Sort by priority (descending), then severity, then position
        return (-self.priority, self.severity.value, self.range.start) < \
               (-other.priority, other.severity.value, other.range.start)


class SuggestionPrioritizer:
    """Prioritizes suggestions based on various factors."""
    
    # Base priorities by type
    TYPE_PRIORITIES = {
        SuggestionType.ERROR_FIX: 100,
        SuggestionType.SECURITY: 90,
        SuggestionType.WARNING_FIX: 80,
        SuggestionType.PERFORMANCE: 70,
        SuggestionType.MAINTAINABILITY: 60,
        SuggestionType.STYLE: 50,
        SuggestionType.DOCUMENTATION: 40,
        SuggestionType.REFACTORING: 30,
    }
    
    # Severity multipliers
    SEVERITY_MULTIPLIERS = {
        Severity.CRITICAL: 2.0,
        Severity.ERROR: 1.5,
        Severity.WARNING: 1.2,
        Severity.INFO: 1.0,
    }
    
    # Context-based adjustments
    CONTEXT_ADJUSTMENTS = {
        "hot_file": 1.5,  # Frequently edited file
        "public_api": 1.3,  # Public API method
        "test_file": 0.8,  # Test file (lower priority)
        "generated_file": 0.5,  # Generated file (much lower)
    }
    
    def __init__(self, analyzer: Optional[CodeAnalyzer] = None):
        self.analyzer = analyzer or CodeAnalyzer()
        self.file_heat_map: Dict[Path, float] = {}  # Track file edit frequency
        
    def calculate_priority(
        self, 
        suggestion: CodeSuggestion, 
        context: Optional[Dict[str, Any]] = None
    ) -> int:
        """Calculate priority score for a suggestion."""
        # Base priority from type
        priority = self.TYPE_PRIORITIES.get(suggestion.type, 50)
        
        # Apply severity multiplier
        priority *= self.SEVERITY_MULTIPLIERS.get(suggestion.severity, 1.0)
        
        # Apply context adjustments
        if context:
            for key, adjustment in self.CONTEXT_ADJUSTMENTS.items():
                if context.get(key, False):
                    priority *= adjustment
        
        # Adjust for file heat (frequently edited files)
        heat = self.file_heat_map.get(suggestion.file_path, 0.0)
        priority *= (1.0 + heat * 0.1)  # Up to 10% boost for hot files
        
        # Consider suggestion position (earlier in file = higher priority)
        position_factor = 1.0 - (suggestion.range.start.line / 10000.0)
        priority *= max(position_factor, 0.9)  # Ensure position doesn't reduce priority too much
        
        return int(priority)
        
    def update_file_heat(self, file_path: Path):
        """Update file heat map for frequently edited files."""
        current_heat = self.file_heat_map.get(file_path, 0.0)
        self.file_heat_map[file_path] = min(current_heat + 0.1, 5.0)
        
        # Decay heat for other files
        for path in list(self.file_heat_map.keys()):
            if path != file_path:
                self.file_heat_map[path] *= 0.95
                if self.file_heat_map[path] < 0.01:
                    del self.file_heat_map[path]


class RealTimeSuggestionEngine:
    """Engine for generating real-time code suggestions."""
    
    def __init__(
        self,
        analyzer: Optional[CodeAnalyzer] = None,
        quality_checker: Optional[DocQualityChecker] = None,
        refactoring_engine: Optional[Any] = None
    ):
        self.analyzer = analyzer or CodeAnalyzer()
        self.quality_checker = quality_checker or DocQualityChecker()
        self._refactoring_engine = refactoring_engine
        self.prioritizer = SuggestionPrioritizer(self.analyzer)
        self.cache: Dict[Path, Tuple[str, List[CodeSuggestion]]] = {}
        self.debounce_timers: Dict[Path, asyncio.Task] = {}
        self.debounce_delay = 0.5  # seconds
    
    @property
    def refactoring_engine(self):
        """Lazy load refactoring engine to avoid circular imports."""
        if self._refactoring_engine is None:
            from velocitytree.refactoring import RefactoringRecommendationEngine
            self._refactoring_engine = RefactoringRecommendationEngine(self.analyzer)
        return self._refactoring_engine
        
    async def analyze_file_async(
        self, 
        file_path: Path,
        content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeSuggestion]:
        """Analyze a file asynchronously and generate suggestions."""
        # Cancel existing debounce timer if any
        if file_path in self.debounce_timers:
            self.debounce_timers[file_path].cancel()
            
        # Create debounce timer
        async def debounced_analyze():
            await asyncio.sleep(self.debounce_delay)
            return await self._perform_analysis(file_path, content, context)
            
        task = asyncio.create_task(debounced_analyze())
        self.debounce_timers[file_path] = task
        
        try:
            return await task
        except asyncio.CancelledError:
            return []
        finally:
            if file_path in self.debounce_timers:
                del self.debounce_timers[file_path]
    
    async def _perform_analysis(
        self,
        file_path: Path,
        content: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeSuggestion]:
        """Perform the actual analysis."""
        # Check cache
        if content is None:
            content = file_path.read_text()
            
        cache_key = file_path
        if cache_key in self.cache:
            cached_content, cached_suggestions = self.cache[cache_key]
            if cached_content == content:
                return cached_suggestions
        
        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        suggestions = await loop.run_in_executor(
            None, 
            self._analyze_sync, 
            file_path, 
            content, 
            context
        )
        
        # Cache results
        self.cache[cache_key] = (content, suggestions)
        
        # Update file heat
        self.prioritizer.update_file_heat(file_path)
        
        return suggestions
    
    def _analyze_sync(
        self,
        file_path: Path,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeSuggestion]:
        """Synchronous analysis implementation."""
        suggestions = []
        
        # Analyze code
        analysis = self.analyzer.analyze_file(file_path)
        
        # Convert issues to suggestions
        suggestions.extend(self._convert_issues_to_suggestions(
            analysis.issues, file_path
        ))
        
        # Add pattern-based suggestions
        suggestions.extend(self._generate_pattern_suggestions(
            analysis.patterns, file_path
        ))
        
        # Add complexity-based suggestions
        suggestions.extend(self._generate_complexity_suggestions(
            analysis.metrics, file_path
        ))
        
        # Add documentation quality suggestions
        doc_report = self.quality_checker.check_quality(analysis)
        suggestions.extend(self._convert_doc_issues_to_suggestions(
            doc_report.issues, file_path
        ))
        
        # Generate refactoring suggestions
        suggestions.extend(self._generate_refactoring_suggestions(
            analysis, file_path
        ))
        
        # Add advanced refactoring recommendations
        suggestions.extend(self._generate_advanced_refactoring_suggestions(
            analysis, file_path
        ))
        
        # Calculate priorities
        for suggestion in suggestions:
            suggestion.priority = self.prioritizer.calculate_priority(
                suggestion, context
            )
        
        # Sort by priority
        suggestions.sort()
        
        return suggestions
    
    def _convert_issues_to_suggestions(
        self, 
        issues: List[Issue], 
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Convert code issues to suggestions."""
        suggestions = []
        
        for issue in issues:
            suggestion_type = self._map_issue_to_suggestion_type(issue)
            
            # Create code range
            range = CodeRange(
                start=CodePosition(issue.location.line_start, 0),
                end=CodePosition(issue.location.line_end or issue.location.line_start, 999)  # Full line
            )
            
            # Generate quick fixes
            quick_fixes = self._generate_quick_fixes_for_issue(issue)
            
            suggestion = CodeSuggestion(
                type=suggestion_type,
                severity=issue.severity,
                message=issue.message,
                range=range,
                file_path=file_path,
                quick_fixes=quick_fixes,
                metadata={"issue_type": issue.category}
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _map_issue_to_suggestion_type(self, issue: Issue) -> SuggestionType:
        """Map issue type to suggestion type."""
        from velocitytree.code_analysis.models import IssueCategory
        
        # Map based on category
        category_map = {
            IssueCategory.SECURITY: SuggestionType.SECURITY,
            IssueCategory.PERFORMANCE: SuggestionType.PERFORMANCE,
            IssueCategory.STYLE: SuggestionType.STYLE,
            IssueCategory.DOCUMENTATION: SuggestionType.DOCUMENTATION,
            IssueCategory.MAINTAINABILITY: SuggestionType.MAINTAINABILITY,
        }
        
        if issue.category in category_map:
            return category_map[issue.category]
        elif issue.severity in (Severity.ERROR, Severity.CRITICAL):
            return SuggestionType.ERROR_FIX
        elif issue.severity == Severity.WARNING:
            return SuggestionType.WARNING_FIX
        else:
            return SuggestionType.MAINTAINABILITY
    
    def _generate_quick_fixes_for_issue(self, issue: Issue) -> List[QuickFix]:
        """Generate quick fixes for an issue."""
        quick_fixes = []
        
        if "import" in issue.message.lower():
            quick_fixes.append(self._create_import_fix(issue))
        elif "docstring" in issue.message.lower():
            quick_fixes.append(self._create_docstring_fix(issue))
        elif "naming" in issue.message.lower():
            quick_fixes.append(self._create_naming_fix(issue))
        elif "unused" in issue.message.lower():
            quick_fixes.append(self._create_remove_unused_fix(issue))
        elif "type" in issue.message.lower() and "hint" in issue.message.lower():
            quick_fixes.append(self._create_type_hint_fix(issue))
            
        return [fix for fix in quick_fixes if fix is not None]
    
    def _create_import_fix(self, issue: Issue) -> Optional[QuickFix]:
        """Create auto-import quick fix."""
        # Extract missing import from issue message
        import_match = None  # Parse from issue message
        if not import_match:
            return None
            
        return QuickFix(
            type=QuickFixType.AUTO_IMPORT,
            title="Add missing import",
            description="Import the missing module",
            range=CodeRange(
                start=CodePosition(0, 0),
                end=CodePosition(0, 0)
            ),
            replacement=f"import {import_match}\n",
            preview=f"+ import {import_match}"
        )
    
    def _create_docstring_fix(self, issue: Issue) -> Optional[QuickFix]:
        """Create docstring quick fix."""
        return QuickFix(
            type=QuickFixType.ADD_DOCSTRING,
            title="Add docstring",
            description="Add a docstring to document this function",
            range=CodeRange(
                start=CodePosition(issue.location.line_start, 0),
                end=CodePosition(issue.location.line_start, 0)
            ),
            replacement='    """\n    TODO: Add description\n    """\n',
            preview='+ """TODO: Add description"""'
        )
    
    def _create_naming_fix(self, issue: Issue) -> Optional[QuickFix]:
        """Create naming convention fix."""
        # Extract current name and suggested name from issue
        current_name = None  # Parse from issue message
        suggested_name = None  # Convert to proper case
        
        if not current_name or not suggested_name:
            return None
            
        return QuickFix(
            type=QuickFixType.FIX_NAMING,
            title=f"Rename to {suggested_name}",
            description="Fix naming convention",
            range=CodeRange(
                start=CodePosition(issue.location.line_start, 0),
                end=CodePosition(issue.location.line_end or issue.location.line_start, 999)
            ),
            replacement=suggested_name,
            preview=f"{current_name} → {suggested_name}"
        )
    
    def _create_remove_unused_fix(self, issue: Issue) -> Optional[QuickFix]:
        """Create remove unused code fix."""
        return QuickFix(
            type=QuickFixType.REMOVE_UNUSED,
            title="Remove unused code",
            description="Remove this unused variable/import",
            range=CodeRange(
                start=CodePosition(issue.location.line_start, 0),
                end=CodePosition(issue.location.line_end or issue.location.line_start + 1, 0)
            ),
            replacement="",
            preview="- [Remove line]"
        )
    
    def _create_type_hint_fix(self, issue: Issue) -> Optional[QuickFix]:
        """Create type hint fix."""
        return QuickFix(
            type=QuickFixType.FIX_TYPE_HINT,
            title="Add type hints",
            description="Add type hints for better type safety",
            range=CodeRange(
                start=CodePosition(issue.location.line_start, 0),
                end=CodePosition(issue.location.line_end or issue.location.line_start, 999)
            ),
            replacement="# TODO: Add type hints",
            preview="+ : TypeHint"
        )
    
    def _generate_pattern_suggestions(
        self,
        patterns: List[Pattern],
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Generate suggestions from detected patterns."""
        suggestions = []
        
        for pattern in patterns:
            # Check metadata for quality information
            quality = pattern.metadata.get("quality", "unknown")
            
            if quality == "poor":
                severity = Severity.WARNING
                message = f"Poor quality pattern detected: {pattern.name}"
            elif quality == "deprecated":
                severity = Severity.WARNING
                message = f"Deprecated pattern: {pattern.name}"
            else:
                continue  # Skip good patterns
                
            suggestion = CodeSuggestion(
                type=SuggestionType.MAINTAINABILITY,
                severity=severity,
                message=message,
                range=CodeRange(
                    start=CodePosition(pattern.location.line_start, 0),
                    end=CodePosition(pattern.location.line_end or pattern.location.line_start, 999)
                ),
                file_path=file_path,
                metadata={"pattern": pattern.pattern_type.value}
            )
            
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_complexity_suggestions(
        self,
        metrics: Optional[ComplexityMetrics],
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Generate suggestions from complexity metrics."""
        if not metrics:
            return []
            
        suggestions = []
        
        # Check cyclomatic complexity
        if metrics.cyclomatic_complexity > 10:
            suggestion = CodeSuggestion(
                type=SuggestionType.REFACTORING,
                severity=Severity.WARNING,
                message=f"High cyclomatic complexity: {metrics.cyclomatic_complexity}",
                range=CodeRange(
                    start=CodePosition(0, 0),
                    end=CodePosition(0, 0)
                ),
                file_path=file_path,
                quick_fixes=[
                    QuickFix(
                        type=QuickFixType.EXTRACT_FUNCTION,
                        title="Extract to function",
                        description="Break down complex logic into smaller functions",
                        range=CodeRange(
                            start=CodePosition(0, 0),
                            end=CodePosition(0, 0)
                        ),
                        replacement="",
                        preview="Extract complex logic"
                    )
                ]
            )
            suggestions.append(suggestion)
        
        # Check cognitive complexity as a proxy for nesting depth
        if metrics.cognitive_complexity > 15:
            suggestion = CodeSuggestion(
                type=SuggestionType.REFACTORING,
                severity=Severity.WARNING,
                message=f"High cognitive complexity: {metrics.cognitive_complexity}",
                range=CodeRange(
                    start=CodePosition(0, 0),
                    end=CodePosition(0, 0)
                ),
                file_path=file_path
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _convert_doc_issues_to_suggestions(
        self,
        doc_issues: List[DocIssue],
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Convert documentation issues to suggestions."""
        suggestions = []
        
        for issue in doc_issues:
            # Map DocSeverity to Severity
            from velocitytree.documentation.models import DocSeverity
            
            severity_map = {
                DocSeverity.ERROR: Severity.ERROR,
                DocSeverity.WARNING: Severity.WARNING,
                DocSeverity.INFO: Severity.INFO,
                DocSeverity.SUGGESTION: Severity.INFO,
            }
            
            severity = severity_map.get(issue.severity, Severity.WARNING)
            
            line_number = issue.line_number or 0
            
            suggestion = CodeSuggestion(
                type=SuggestionType.DOCUMENTATION,
                severity=severity,
                message=issue.message,
                range=CodeRange(
                    start=CodePosition(line_number, 0),
                    end=CodePosition(line_number, 999)
                ),
                file_path=file_path,
                quick_fixes=[
                    QuickFix(
                        type=QuickFixType.ADD_DOCSTRING,
                        title="Add documentation",
                        description="Add or improve documentation",
                        range=CodeRange(
                            start=CodePosition(line_number, 0),
                            end=CodePosition(line_number, 0)
                        ),
                        replacement='    """TODO: Add documentation"""\n',
                        preview='+ """TODO: Add documentation"""'
                    )
                ]
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_refactoring_suggestions(
        self,
        analysis: ModuleAnalysis,
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Generate refactoring suggestions."""
        suggestions = []
        
        # Suggest extracting long functions based on complexity
        for func in analysis.functions:
            # Use complexity metric or line count estimate
            if func.complexity > 10:  # High complexity
                suggestion = CodeSuggestion(
                    type=SuggestionType.REFACTORING,
                    severity=Severity.INFO,
                    message=f"Consider breaking down function '{func.name}' - complexity: {func.complexity}",
                    range=CodeRange(
                        start=CodePosition(func.location.line_start, 0),
                        end=CodePosition(func.location.line_end or func.location.line_start, 0)
                    ),
                    file_path=file_path,
                    quick_fixes=[
                        QuickFix(
                            type=QuickFixType.EXTRACT_FUNCTION,
                            title="Extract to multiple functions",
                            description="Break down into smaller, focused functions",
                            range=CodeRange(
                                start=CodePosition(func.location.line_start, 0),
                                end=CodePosition(func.location.line_start, 0)
                            ),
                            replacement="",
                            preview="Extract parts of this function"
                        )
                    ]
                )
                suggestions.append(suggestion)
        
        # Suggest consolidating similar functions
        # This would require more sophisticated analysis
        
        return suggestions
    
    def _generate_advanced_refactoring_suggestions(
        self,
        analysis: ModuleAnalysis,
        file_path: Path
    ) -> List[CodeSuggestion]:
        """Generate advanced refactoring suggestions using the refactoring engine."""
        suggestions = []
        
        try:
            # Get refactoring recommendations
            recommendations = self.refactoring_engine.analyze_and_recommend(
                file_path,
                file_path.parent  # Use parent as codebase path
            )
            
            # Convert to suggestions
            refactoring_suggestions = self.refactoring_engine.generate_suggestions(recommendations)
            suggestions.extend(refactoring_suggestions)
        except Exception as e:
            # Log error but don't fail the entire analysis
            import logging
            logging.debug(f"Error generating advanced refactoring suggestions: {e}")
        
        return suggestions
    
    def clear_cache(self, file_path: Optional[Path] = None):
        """Clear suggestion cache."""
        if file_path:
            if file_path in self.cache:
                del self.cache[file_path]
        else:
            self.cache.clear()