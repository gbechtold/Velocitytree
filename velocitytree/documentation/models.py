"""Data models for documentation generation."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime


class DocFormat(Enum):
    """Supported documentation formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    RST = "restructuredtext"
    PDF = "pdf"
    JSON = "json"
    YAML = "yaml"


class DocType(Enum):
    """Types of documentation."""
    API = "api"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    README = "readme"
    CHANGELOG = "changelog"
    TUTORIAL = "tutorial"
    REFERENCE = "reference"


class DocStyle(Enum):
    """Documentation styles."""
    GOOGLE = "google"
    NUMPY = "numpy"
    SPHINX = "sphinx"
    MARKDOWN = "markdown"
    CUSTOM = "custom"


class DocSeverity(Enum):
    """Documentation issue severity."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


@dataclass
class DocTemplate:
    """Documentation template definition."""
    name: str
    doc_type: DocType
    format: DocFormat
    style: DocStyle
    content: str
    placeholders: List[str] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)


@dataclass
class DocSection:
    """A section within documentation."""
    title: str
    content: str
    level: int = 1
    subsections: List['DocSection'] = field(default_factory=list)
    code_examples: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


@dataclass
class DocIssue:
    """A documentation quality issue."""
    severity: DocSeverity
    location: str
    message: str
    suggestion: Optional[str] = None
    line_number: Optional[int] = None


@dataclass
class DocMetadata:
    """Metadata for generated documentation."""
    title: str
    description: str
    author: Optional[str] = None
    version: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    language: str = "en"


@dataclass
class DocumentationResult:
    """Result of documentation generation."""
    content: str
    format: DocFormat
    metadata: DocMetadata
    sections: List[DocSection] = field(default_factory=list)
    issues: List[DocIssue] = field(default_factory=list)
    quality_score: float = 0.0
    completeness_score: float = 0.0
    generation_time: float = 0.0


@dataclass
class DocConfig:
    """Configuration for documentation generation."""
    format: DocFormat = DocFormat.MARKDOWN
    style: DocStyle = DocStyle.GOOGLE
    include_examples: bool = True
    include_tests: bool = False
    include_private: bool = False
    max_line_length: int = 80
    heading_style: str = "#"  # For markdown
    code_fence_style: str = "```"
    auto_links: bool = True
    table_of_contents: bool = True


@dataclass
class FunctionDoc:
    """Documentation for a function."""
    name: str
    signature: str
    description: str
    parameters: Dict[str, str] = field(default_factory=dict)
    returns: Optional[str] = None
    raises: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    see_also: List[str] = field(default_factory=list)
    deprecated: bool = False
    since: Optional[str] = None


@dataclass
class ClassDoc:
    """Documentation for a class."""
    name: str
    description: str
    base_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    methods: List[FunctionDoc] = field(default_factory=list)
    class_methods: List[FunctionDoc] = field(default_factory=list)
    static_methods: List[FunctionDoc] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    see_also: List[str] = field(default_factory=list)


@dataclass
class ModuleDoc:
    """Documentation for a module."""
    name: str
    description: str
    imports: List[str] = field(default_factory=list)
    global_variables: Dict[str, str] = field(default_factory=dict)
    functions: List[FunctionDoc] = field(default_factory=list)
    classes: List[ClassDoc] = field(default_factory=list)
    submodules: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    see_also: List[str] = field(default_factory=list)


@dataclass
class DocumentationPlan:
    """Plan for generating documentation."""
    modules: List[str] = field(default_factory=list)
    doc_types: List[DocType] = field(default_factory=list)
    formats: List[DocFormat] = field(default_factory=list)
    output_directory: str = "docs"
    recursive: bool = True
    overwrite: bool = False
    config: DocConfig = field(default_factory=DocConfig)