"""
Drift detection system for identifying specification deviations.
Compares code implementation against documented specifications.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import json

from ..code_analysis.analyzer import CodeAnalyzer
from ..code_analysis.models import ModuleAnalysis
from ..documentation.generator import DocGenerator
from ..utils import logger


class DriftType(Enum):
    """Types of specification drift."""
    MISSING_IMPLEMENTATION = "missing_implementation"
    EXTRA_IMPLEMENTATION = "extra_implementation"
    SIGNATURE_MISMATCH = "signature_mismatch"
    BEHAVIOR_DEVIATION = "behavior_deviation"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SECURITY_VIOLATION = "security_violation"
    DOCUMENTATION_OUTDATED = "documentation_outdated"
    DEPENDENCY_DRIFT = "dependency_drift"
    API_BREAKING_CHANGE = "api_breaking_change"


@dataclass
class DriftReport:
    """Report of detected specification drift."""
    file_path: Path
    drift_type: DriftType
    severity: float  # 0.0 to 1.0
    description: str
    expected: Any
    actual: Any
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    spec_reference: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'file_path': str(self.file_path),
            'drift_type': self.drift_type.value,
            'severity': self.severity,
            'description': self.description,
            'expected': self.expected,
            'actual': self.actual,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp.isoformat(),
            'spec_reference': self.spec_reference
        }


class DriftDetector:
    """Detects drift between code and specifications."""
    
    def __init__(
        self,
        code_analyzer: Optional[CodeAnalyzer] = None,
        spec_paths: Optional[List[Path]] = None
    ):
        """Initialize drift detector.
        
        Args:
            code_analyzer: Code analysis instance
            spec_paths: Paths to specification files
        """
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.spec_paths = spec_paths or []
        
        # Cache specifications
        self.specifications = {}
        self.spec_cache = {}
        self._load_specifications()
        
        # Detection thresholds
        self.thresholds = {
            'signature_similarity': 0.8,
            'documentation_coverage': 0.7,
            'performance_tolerance': 0.2,
            'complexity_increase': 0.3
        }
    
    def add_spec_path(self, path: Path):
        """Add a specification path.
        
        Args:
            path: Path to specification file or directory
        """
        if path not in self.spec_paths:
            self.spec_paths.append(path)
            self._load_specifications()
    
    def check_file_drift(self, file_path: Path) -> Optional[DriftReport]:
        """Check a single file for specification drift.
        
        Args:
            file_path: Path to check
            
        Returns:
            DriftReport if drift detected, None otherwise
        """
        try:
            # Analyze the current code
            analysis = self.code_analyzer.analyze_file(file_path)
            if not analysis:
                return None
            
            # Find corresponding specification
            spec = self._find_specification(file_path, analysis)
            if not spec:
                # No specification found - could be intentional
                return None
            
            # Check various types of drift
            drift_checks = [
                self._check_implementation_drift,
                self._check_signature_drift,
                self._check_behavior_drift,
                self._check_performance_drift,
                self._check_documentation_drift,
                self._check_dependency_drift,
                self._check_api_changes
            ]
            
            for check_func in drift_checks:
                drift_report = check_func(file_path, analysis, spec)
                if drift_report:
                    return drift_report
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking drift for {file_path}: {e}")
            return None
    
    def check_project_drift(
        self,
        project_path: Path
    ) -> List[DriftReport]:
        """Check entire project for specification drift.
        
        Args:
            project_path: Root path of project
            
        Returns:
            List of drift reports
        """
        drift_reports = []
        
        # Find all source files
        source_files = []
        for pattern in ['**/*.py', '**/*.js', '**/*.ts']:
            source_files.extend(project_path.glob(pattern))
        
        # Check each file
        for file_path in source_files:
            report = self.check_file_drift(file_path)
            if report:
                drift_reports.append(report)
        
        # Sort by severity
        drift_reports.sort(key=lambda r: r.severity, reverse=True)
        
        return drift_reports
    
    def _load_specifications(self):
        """Load specifications from configured paths."""
        self.specifications = {}
        
        for spec_path in self.spec_paths:
            if spec_path.is_file():
                self._load_spec_file(spec_path)
            elif spec_path.is_dir():
                for spec_file in spec_path.rglob('*.spec.*'):
                    self._load_spec_file(spec_file)
    
    def _load_spec_file(self, spec_file: Path):
        """Load a single specification file.
        
        Args:
            spec_file: Path to specification file
        """
        try:
            content = spec_file.read_text()
            
            # Parse based on file type
            if spec_file.suffix == '.json':
                spec_data = json.loads(content)
            elif spec_file.suffix in ['.md', '.markdown']:
                spec_data = self._parse_markdown_spec(content)
            elif spec_file.suffix in ['.yaml', '.yml']:
                import yaml
                spec_data = yaml.safe_load(content)
            else:
                # Try to parse as structured text
                spec_data = self._parse_text_spec(content)
            
            # Store specification
            module_name = spec_file.stem.replace('.spec', '')
            self.specifications[module_name] = spec_data
            
        except Exception as e:
            logger.error(f"Error loading spec file {spec_file}: {e}")
    
    def _parse_markdown_spec(self, content: str) -> Dict[str, Any]:
        """Parse a markdown specification.
        
        Args:
            content: Markdown content
            
        Returns:
            Parsed specification
        """
        spec = {
            'functions': {},
            'classes': {},
            'interfaces': {},
            'requirements': []
        }
        
        current_section = None
        current_item = None
        
        for line in content.split('\n'):
            # Section headers
            if line.startswith('## Functions'):
                current_section = 'functions'
            elif line.startswith('## Classes'):
                current_section = 'classes'
            elif line.startswith('## Requirements'):
                current_section = 'requirements'
            
            # Function/class definitions
            elif line.startswith('### ') and current_section in ['functions', 'classes']:
                item_name = line[4:].strip()
                current_item = {
                    'name': item_name,
                    'description': '',
                    'parameters': [],
                    'returns': None,
                    'requirements': []
                }
                spec[current_section][item_name] = current_item
            
            # Parameter definitions
            elif line.startswith('- Parameter:') and current_item:
                param_match = re.match(r'- Parameter: (\w+) \((\w+)\): (.+)', line)
                if param_match:
                    current_item['parameters'].append({
                        'name': param_match.group(1),
                        'type': param_match.group(2),
                        'description': param_match.group(3)
                    })
            
            # Return value
            elif line.startswith('- Returns:') and current_item:
                current_item['returns'] = line[10:].strip()
            
            # Requirements
            elif line.startswith('- ') and current_section == 'requirements':
                spec['requirements'].append(line[2:].strip())
        
        return spec
    
    def _parse_text_spec(self, content: str) -> Dict[str, Any]:
        """Parse a text specification with basic structure.
        
        Args:
            content: Text content
            
        Returns:
            Parsed specification
        """
        spec = {
            'description': '',
            'requirements': [],
            'interfaces': {}
        }
        
        # Extract requirements (lines starting with MUST, SHOULD, etc.)
        requirement_pattern = r'(MUST|SHOULD|SHALL|MAY)\s+(.+)'
        for match in re.finditer(requirement_pattern, content):
            spec['requirements'].append({
                'level': match.group(1),
                'description': match.group(2)
            })
        
        # Extract function signatures
        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(\w+))?:'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            params = match.group(2)
            return_type = match.group(3)
            
            spec['interfaces'][func_name] = {
                'parameters': params,
                'return_type': return_type
            }
        
        return spec
    
    def _find_specification(
        self,
        file_path: Path,
        analysis: ModuleAnalysis
    ) -> Optional[Dict[str, Any]]:
        """Find specification for a file.
        
        Args:
            file_path: File path
            analysis: Code analysis
            
        Returns:
            Specification if found
        """
        # Try exact match
        module_name = file_path.stem
        if module_name in self.specifications:
            return self.specifications[module_name]
        
        # Try path-based match
        relative_path = None
        for spec_path in self.spec_paths:
            try:
                relative_path = file_path.relative_to(spec_path.parent)
                path_key = str(relative_path).replace('/', '.').replace('.py', '')
                if path_key in self.specifications:
                    return self.specifications[path_key]
            except ValueError:
                continue
        
        # Try to find by content similarity
        return self._find_similar_spec(analysis)
    
    def _find_similar_spec(
        self,
        analysis: ModuleAnalysis
    ) -> Optional[Dict[str, Any]]:
        """Find specification by content similarity.
        
        Args:
            analysis: Code analysis
            
        Returns:
            Most similar specification
        """
        # Extract function names from analysis
        func_names = set(func.name for func in analysis.functions)
        class_names = set(cls.name for cls in analysis.classes)
        
        best_match = None
        best_score = 0
        
        for spec_name, spec in self.specifications.items():
            score = 0
            
            # Check function matches
            if 'functions' in spec:
                spec_funcs = set(spec['functions'].keys())
                func_overlap = len(func_names & spec_funcs)
                func_union = len(func_names | spec_funcs)
                if func_union > 0:
                    score += func_overlap / func_union
            
            # Check class matches
            if 'classes' in spec:
                spec_classes = set(spec['classes'].keys())
                class_overlap = len(class_names & spec_classes)
                class_union = len(class_names | spec_classes)
                if class_union > 0:
                    score += class_overlap / class_union
            
            if score > best_score:
                best_score = score
                best_match = spec
        
        return best_match if best_score > 0.5 else None
    
    def _check_implementation_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for missing or extra implementations.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        # Check for missing implementations
        if 'functions' in spec:
            spec_funcs = set(spec['functions'].keys())
            impl_funcs = set(func.name for func in analysis.functions)
            
            missing = spec_funcs - impl_funcs
            if missing:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.MISSING_IMPLEMENTATION,
                    severity=0.8,
                    description=f"Missing required functions: {', '.join(missing)}",
                    expected=list(missing),
                    actual=list(impl_funcs),
                    suggestions=[
                        f"Implement missing function: {func}" for func in missing
                    ],
                    spec_reference="functions"
                )
            
            # Check for extra implementations
            extra = impl_funcs - spec_funcs
            if extra and len(extra) > len(spec_funcs) * 0.5:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.EXTRA_IMPLEMENTATION,
                    severity=0.4,
                    description=f"Undocumented functions: {', '.join(extra)}",
                    expected=list(spec_funcs),
                    actual=list(impl_funcs),
                    suggestions=[
                        f"Document function '{func}' in specification" for func in extra
                    ],
                    spec_reference="functions"
                )
        
        return None
    
    def _check_signature_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for function signature mismatches.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        if 'functions' not in spec:
            return None
        
        for func in analysis.functions:
            if func.name in spec['functions']:
                spec_func = spec['functions'][func.name]
                
                # Check parameter count
                spec_params = spec_func.get('parameters', [])
                impl_params = func.parameters
                
                if len(spec_params) != len(impl_params):
                    return DriftReport(
                        file_path=file_path,
                        drift_type=DriftType.SIGNATURE_MISMATCH,
                        severity=0.7,
                        description=f"Parameter mismatch in '{func.name}'",
                        expected=spec_params,
                        actual=impl_params,
                        suggestions=[
                            f"Update function signature to match specification"
                        ],
                        spec_reference=f"functions.{func.name}"
                    )
                
                # Check return type if specified
                if 'returns' in spec_func and spec_func['returns']:
                    if func.return_type != spec_func['returns']:
                        return DriftReport(
                            file_path=file_path,
                            drift_type=DriftType.SIGNATURE_MISMATCH,
                            severity=0.6,
                            description=f"Return type mismatch in '{func.name}'",
                            expected=spec_func['returns'],
                            actual=func.return_type,
                            suggestions=[
                                f"Update return type to '{spec_func['returns']}'"
                            ],
                            spec_reference=f"functions.{func.name}.returns"
                        )
        
        return None
    
    def _check_behavior_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for behavioral deviations from spec.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        # Check requirements
        if 'requirements' in spec:
            for requirement in spec['requirements']:
                # Simple pattern matching for requirement violations
                if isinstance(requirement, dict):
                    req_text = requirement.get('description', '')
                    req_level = requirement.get('level', 'SHOULD')
                else:
                    req_text = requirement
                    req_level = 'SHOULD'
                
                # Check for specific patterns
                if 'error handling' in req_text.lower():
                    # Check if functions have try/except blocks
                    functions_with_error_handling = sum(
                        1 for func in analysis.functions
                        if 'try' in func.body or 'except' in func.body
                    )
                    
                    if functions_with_error_handling == 0 and req_level == 'MUST':
                        return DriftReport(
                            file_path=file_path,
                            drift_type=DriftType.BEHAVIOR_DEVIATION,
                            severity=0.8,
                            description="Missing required error handling",
                            expected="Error handling in all functions",
                            actual="No error handling found",
                            suggestions=[
                                "Add try/except blocks for error handling"
                            ],
                            spec_reference="requirements"
                        )
        
        return None
    
    def _check_performance_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for performance degradation.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        # Check complexity requirements
        if 'performance' in spec:
            max_complexity = spec['performance'].get('max_complexity', 10)
            
            if analysis.metrics and analysis.metrics.cyclomatic_complexity > max_complexity:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.PERFORMANCE_DEGRADATION,
                    severity=0.6,
                    description="Complexity exceeds specification",
                    expected=f"Max complexity: {max_complexity}",
                    actual=f"Current: {analysis.metrics.cyclomatic_complexity}",
                    suggestions=[
                        "Refactor complex functions",
                        "Break down large methods"
                    ],
                    spec_reference="performance.max_complexity"
                )
        
        return None
    
    def _check_documentation_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check if documentation is outdated.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        # Check if documented functions match implementation
        doc_coverage = 0
        total_functions = len(analysis.functions)
        
        if total_functions > 0:
            documented = sum(1 for func in analysis.functions if func.docstring)
            doc_coverage = documented / total_functions
            
            if doc_coverage < self.thresholds['documentation_coverage']:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.DOCUMENTATION_OUTDATED,
                    severity=0.5,
                    description="Insufficient documentation coverage",
                    expected=f"{self.thresholds['documentation_coverage']:.0%} coverage",
                    actual=f"{doc_coverage:.0%} coverage",
                    suggestions=[
                        "Add docstrings to undocumented functions",
                        "Update existing documentation"
                    ],
                    spec_reference="documentation"
                )
        
        return None
    
    def _check_dependency_drift(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for dependency version drift.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        if 'dependencies' not in spec:
            return None
        
        # Check imports against specified dependencies
        spec_deps = spec['dependencies']
        actual_imports = [imp.module for imp in analysis.imports]
        
        # Check for forbidden dependencies
        if 'forbidden' in spec_deps:
            forbidden = spec_deps['forbidden']
            used_forbidden = set(actual_imports) & set(forbidden)
            
            if used_forbidden:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.DEPENDENCY_DRIFT,
                    severity=0.8,
                    description=f"Using forbidden dependencies: {', '.join(used_forbidden)}",
                    expected="No forbidden dependencies",
                    actual=list(used_forbidden),
                    suggestions=[
                        f"Remove dependency on '{dep}'" for dep in used_forbidden
                    ],
                    spec_reference="dependencies.forbidden"
                )
        
        return None
    
    def _check_api_changes(
        self,
        file_path: Path,
        analysis: ModuleAnalysis,
        spec: Dict[str, Any]
    ) -> Optional[DriftReport]:
        """Check for breaking API changes.
        
        Args:
            file_path: File path
            analysis: Code analysis
            spec: Specification
            
        Returns:
            DriftReport if drift found
        """
        if 'api' not in spec:
            return None
        
        api_spec = spec['api']
        
        # Check if public functions have changed
        if 'public_functions' in api_spec:
            public_funcs = api_spec['public_functions']
            current_public = [
                func.name for func in analysis.functions
                if not func.name.startswith('_')
            ]
            
            removed = set(public_funcs) - set(current_public)
            if removed:
                return DriftReport(
                    file_path=file_path,
                    drift_type=DriftType.API_BREAKING_CHANGE,
                    severity=1.0,
                    description=f"Breaking change: removed public functions {', '.join(removed)}",
                    expected=public_funcs,
                    actual=current_public,
                    suggestions=[
                        f"Restore function '{func}' or deprecate properly" 
                        for func in removed
                    ],
                    spec_reference="api.public_functions"
                )
        
        return None
    
    def generate_drift_summary(
        self,
        drift_reports: List[DriftReport]
    ) -> Dict[str, Any]:
        """Generate summary of drift reports.
        
        Args:
            drift_reports: List of drift reports
            
        Returns:
            Summary statistics
        """
        if not drift_reports:
            return {
                'total_drifts': 0,
                'by_type': {},
                'by_severity': {},
                'affected_files': []
            }
        
        # Group by type
        by_type = {}
        for report in drift_reports:
            drift_type = report.drift_type.value
            if drift_type not in by_type:
                by_type[drift_type] = []
            by_type[drift_type].append(report)
        
        # Group by severity
        by_severity = {
            'high': [r for r in drift_reports if r.severity >= 0.8],
            'medium': [r for r in drift_reports if 0.5 <= r.severity < 0.8],
            'low': [r for r in drift_reports if r.severity < 0.5]
        }
        
        # Get affected files
        affected_files = list(set(str(r.file_path) for r in drift_reports))
        
        return {
            'total_drifts': len(drift_reports),
            'by_type': {k: len(v) for k, v in by_type.items()},
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'affected_files': affected_files,
            'top_issues': drift_reports[:5]  # Top 5 by severity
        }