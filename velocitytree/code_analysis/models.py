"""Data models for code analysis."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime


class Severity(Enum):
    """Issue severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categories of code issues."""
    STYLE = "style"
    COMPLEXITY = "complexity"
    BUG_RISK = "bug_risk"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"


class PatternType(Enum):
    """Types of code patterns."""
    DESIGN_PATTERN = "design_pattern"
    ANTI_PATTERN = "anti_pattern"
    CODE_SMELL = "code_smell"
    IDIOM = "idiom"


class LanguageSupport(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    GO = "go"
    RUST = "rust"
    RUBY = "ruby"


class SeverityLevel(Enum):
    """Severity levels for vulnerabilities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    

class SecurityCategory(Enum):
    """Categories of security vulnerabilities."""
    INJECTION = "injection"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_EXPOSURE = "data_exposure"
    CONFIGURATION = "configuration"
    CRYPTOGRAPHY = "cryptography"
    INPUT_VALIDATION = "input_validation"
    PATH_TRAVERSAL = "path_traversal"


@dataclass
class CodeLocation:
    """Location in source code."""
    file_path: str
    line_start: int
    line_end: int
    column_start: Optional[int] = None
    column_end: Optional[int] = None


@dataclass
class CodeIssue:
    """Represents a code quality issue."""
    severity: Severity
    category: IssueCategory
    message: str
    rule_id: str
    location: CodeLocation
    suggestion: Optional[str] = None
    fix_hint: Optional[str] = None
    impact: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class Pattern:
    """Represents a detected code pattern."""
    pattern_type: PatternType
    name: str
    description: str
    location: CodeLocation
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeMetrics:
    """Code complexity and quality metrics."""
    lines_of_code: int
    lines_of_comments: int
    cyclomatic_complexity: float
    cognitive_complexity: float
    maintainability_index: float
    test_coverage: Optional[float] = None
    duplicate_lines: int = 0
    technical_debt_ratio: float = 0.0
    code_to_comment_ratio: float = 0.0
    average_function_length: float = 0.0
    max_function_length: int = 0
    number_of_functions: int = 0
    number_of_classes: int = 0


@dataclass
class Suggestion:
    """Code improvement suggestion."""
    title: str
    description: str
    location: CodeLocation
    category: IssueCategory
    priority: int  # 1 (highest) to 5 (lowest)
    estimated_effort: str  # "trivial", "small", "medium", "large"
    before_code: Optional[str] = None
    after_code: Optional[str] = None
    rationale: Optional[str] = None
    references: List[str] = field(default_factory=list)


@dataclass
class FunctionAnalysis:
    """Analysis results for a single function."""
    name: str
    location: CodeLocation
    complexity: int
    parameters: List[str]
    returns: Optional[str]
    docstring: Optional[str]
    issues: List[CodeIssue] = field(default_factory=list)
    metrics: Optional[CodeMetrics] = None


@dataclass
class ClassAnalysis:
    """Analysis results for a single class."""
    name: str
    location: CodeLocation
    methods: List[FunctionAnalysis]
    attributes: List[str]
    parent_classes: List[str]
    docstring: Optional[str]
    issues: List[CodeIssue] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)


@dataclass
class ModuleAnalysis:
    """Analysis results for a single module/file."""
    file_path: str
    language: LanguageSupport
    imports: List[str]
    functions: List[FunctionAnalysis]
    classes: List[ClassAnalysis]
    global_variables: List[str]
    docstring: Optional[str]
    metrics: CodeMetrics
    issues: List[CodeIssue] = field(default_factory=list)
    patterns: List[Pattern] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Complete analysis result for a codebase."""
    timestamp: datetime
    files_analyzed: int
    total_lines: int
    language_breakdown: Dict[LanguageSupport, int]
    modules: List[ModuleAnalysis]
    aggregate_metrics: CodeMetrics
    all_issues: List[CodeIssue]
    all_patterns: List[Pattern]
    suggestions: List[Suggestion]
    analysis_time: float  # seconds
    error_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class VulnerabilityInfo:
    """Information about a security vulnerability."""
    type: str
    severity: SeverityLevel
    category: SecurityCategory
    description: str
    location: CodeLocation
    code_snippet: str
    fix_suggestion: str
    references: List[str] = field(default_factory=list)
    confidence: float = 0.8
    

@dataclass
class CodebaseProfile:
    """Profile of a codebase for tracking over time."""
    project_name: str
    analysis_history: List[AnalysisResult]
    quality_trend: List[float]  # maintainability index over time
    complexity_trend: List[float]  # average complexity over time
    issue_trend: Dict[IssueCategory, List[int]]  # issues by category over time
    common_patterns: List[Pattern]
    team_conventions: Dict[str, Any]
    last_analysis: datetime