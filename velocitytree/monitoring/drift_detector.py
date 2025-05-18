"""
Drift detection from specifications for Velocitytree.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..utils import logger
from ..feature_graph import FeatureGraph
from ..git_manager import GitManager
from ..code_analysis import CodeAnalyzer
from ..documentation.generator import DocGenerator


class DriftType(Enum):
    """Types of drift that can be detected."""
    CODE_STRUCTURE = "code_structure"
    API_CONTRACT = "api_contract"
    DOCUMENTATION = "documentation"
    FEATURE_SPEC = "feature_spec"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    SECURITY = "security"
    PERFORMANCE = "performance"


@dataclass
class DriftItem:
    """Individual drift detected."""
    drift_type: DriftType
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    spec_reference: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'drift_type': self.drift_type.value,
            'description': self.description,
            'severity': self.severity,
            'file_path': str(self.file_path) if self.file_path else None,
            'line_number': self.line_number,
            'expected': self.expected,
            'actual': self.actual,
            'spec_reference': self.spec_reference
        }


@dataclass
class DriftReport:
    """Report of all drift detected."""
    project_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    drifts: List[DriftItem] = field(default_factory=list)
    checked_specs: List[str] = field(default_factory=list)
    files_checked: int = 0
    
    def add_drift(self, drift: DriftItem):
        """Add a drift item to the report."""
        self.drifts.append(drift)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'project_path': str(self.project_path),
            'timestamp': self.timestamp.isoformat(),
            'drifts': [drift.to_dict() for drift in self.drifts],
            'checked_specs': self.checked_specs,
            'files_checked': self.files_checked,
            'summary': {
                'total_drifts': len(self.drifts),
                'by_type': self._count_by_type(),
                'by_severity': self._count_by_severity()
            }
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count drifts by type."""
        counts = {}
        for drift in self.drifts:
            counts[drift.drift_type.value] = counts.get(drift.drift_type.value, 0) + 1
        return counts
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Count drifts by severity."""
        counts = {}
        for drift in self.drifts:
            counts[drift.severity] = counts.get(drift.severity, 0) + 1
        return counts


class SpecificationParser:
    """Parser for project specifications."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.specs = {}
    
    def load_specifications(self) -> Dict[str, Any]:
        """Load all project specifications."""
        specs = {}
        
        # Load from various sources
        specs['velocitytree'] = self._load_velocitytree_spec()
        specs['openapi'] = self._load_openapi_spec()
        specs['readme'] = self._load_readme_spec()
        specs['architecture'] = self._load_architecture_spec()
        specs['feature_graph'] = self._load_feature_graph_spec()
        
        return specs
    
    def _load_velocitytree_spec(self) -> Optional[Dict[str, Any]]:
        """Load velocitytree.yaml specification."""
        spec_file = self.project_path / 'velocitytree.yaml'
        if not spec_file.exists():
            spec_file = self.project_path / '.velocitytree.yaml'
        
        if spec_file.exists():
            with open(spec_file) as f:
                return yaml.safe_load(f)
        return None
    
    def _load_openapi_spec(self) -> Optional[Dict[str, Any]]:
        """Load OpenAPI/Swagger specification."""
        for filename in ['openapi.yaml', 'openapi.yml', 'swagger.yaml', 'swagger.yml']:
            spec_file = self.project_path / filename
            if spec_file.exists():
                with open(spec_file) as f:
                    return yaml.safe_load(f)
        
        # Check docs directory
        docs_dir = self.project_path / 'docs'
        if docs_dir.exists():
            for filename in ['openapi.yaml', 'openapi.yml', 'swagger.yaml', 'swagger.yml']:
                spec_file = docs_dir / filename
                if spec_file.exists():
                    with open(spec_file) as f:
                        return yaml.safe_load(f)
        
        return None
    
    def _load_readme_spec(self) -> Optional[str]:
        """Load README specification."""
        for filename in ['README.md', 'README.rst', 'README.txt']:
            readme_file = self.project_path / filename
            if readme_file.exists():
                return readme_file.read_text()
        return None
    
    def _load_architecture_spec(self) -> Optional[Dict[str, Any]]:
        """Load architecture specification."""
        arch_file = self.project_path / 'ARCHITECTURE.md'
        if arch_file.exists():
            return {'content': arch_file.read_text()}
        
        # Check docs directory
        docs_arch = self.project_path / 'docs' / 'ARCHITECTURE.md'
        if docs_arch.exists():
            return {'content': docs_arch.read_text()}
        
        return None
    
    def _load_feature_graph_spec(self) -> Optional[Dict[str, Any]]:
        """Load feature graph specification."""
        fg_file = self.project_path / '.velocitytree' / 'feature_graph.json'
        if fg_file.exists():
            with open(fg_file) as f:
                return json.load(f)
        return None


class DriftDetector:
    """Detector for project drift from specifications."""
    
    def __init__(self, project_path: Path, monitor_config: Optional[Dict[str, Any]] = None):
        self.project_path = project_path
        self.config = monitor_config or {}
        
        # Initialize components
        self.spec_parser = SpecificationParser(project_path)
        self.code_analyzer = CodeAnalyzer()
        self.git_manager = GitManager(project_path)
        
        # Load specifications
        self.specifications = self.spec_parser.load_specifications()
    
    def check_drift(self) -> DriftReport:
        """Check for drift across entire project."""
        report = DriftReport(project_path=self.project_path)
        
        # Check different types of drift
        if self.specifications.get('velocitytree'):
            self._check_feature_drift(report)
            report.checked_specs.append('velocitytree')
        
        if self.specifications.get('openapi'):
            self._check_api_drift(report)
            report.checked_specs.append('openapi')
        
        if self.specifications.get('architecture'):
            self._check_architecture_drift(report)
            report.checked_specs.append('architecture')
        
        if self.specifications.get('readme'):
            self._check_documentation_drift(report)
            report.checked_specs.append('readme')
        
        # Always check code structure drift
        self._check_code_structure_drift(report)
        
        # Check security and performance drift
        self._check_security_drift(report)
        self._check_performance_drift(report)
        
        return report
    
    def _check_feature_drift(self, report: DriftReport):
        """Check for drift from feature specifications."""
        spec = self.specifications.get('velocitytree', {})
        features_spec = spec.get('features', {})
        
        # Load current feature graph
        try:
            feature_graph = FeatureGraph()
            feature_graph.load_from_spec(self.project_path)
            
            # Check for missing features
            for feature_id, feature_spec in features_spec.items():
                if feature_id not in feature_graph.features:
                    report.add_drift(DriftItem(
                        drift_type=DriftType.FEATURE_SPEC,
                        description=f"Feature '{feature_id}' specified but not implemented",
                        severity='high',
                        expected=f"Feature: {feature_spec.get('name', feature_id)}",
                        actual="Feature not found in implementation",
                        spec_reference='velocitytree.yaml'
                    ))
                else:
                    # Check feature status
                    feature = feature_graph.features[feature_id]
                    if feature.status != feature_spec.get('status', 'planned'):
                        report.add_drift(DriftItem(
                            drift_type=DriftType.FEATURE_SPEC,
                            description=f"Feature '{feature_id}' status mismatch",
                            severity='medium',
                            expected=f"Status: {feature_spec.get('status', 'planned')}",
                            actual=f"Status: {feature.status}",
                            spec_reference='velocitytree.yaml'
                        ))
            
            # Check for unspecified features
            for feature_id in feature_graph.features:
                if feature_id not in features_spec:
                    report.add_drift(DriftItem(
                        drift_type=DriftType.FEATURE_SPEC,
                        description=f"Feature '{feature_id}' implemented but not specified",
                        severity='medium',
                        actual=f"Feature: {feature_graph.features[feature_id].name}",
                        expected="Feature specification not found",
                        spec_reference='velocitytree.yaml'
                    ))
        
        except Exception as e:
            logger.error(f"Error checking feature drift: {e}")
    
    def _check_api_drift(self, report: DriftReport):
        """Check for API drift from OpenAPI spec."""
        spec = self.specifications.get('openapi', {})
        if not spec:
            return
        
        paths = spec.get('paths', {})
        
        # Analyze actual API implementations
        api_files = list(self.project_path.rglob('*api*.py'))
        api_files.extend(list(self.project_path.rglob('*routes*.py')))
        api_files.extend(list(self.project_path.rglob('*endpoints*.py')))
        
        for api_file in api_files:
            try:
                analysis = self.code_analyzer.analyze_file(api_file)
                
                # Check for missing endpoints
                for path, methods in paths.items():
                    for method, endpoint_spec in methods.items():
                        # Simple check - look for route decorators or method names
                        if not self._find_endpoint_implementation(analysis, path, method):
                            report.add_drift(DriftItem(
                                drift_type=DriftType.API_CONTRACT,
                                description=f"API endpoint {method.upper()} {path} not implemented",
                                severity='high',
                                file_path=api_file,
                                expected=f"{method.upper()} {path}",
                                actual="Endpoint not found",
                                spec_reference='OpenAPI specification'
                            ))
                
            except Exception as e:
                logger.error(f"Error analyzing API file {api_file}: {e}")
    
    def _find_endpoint_implementation(self, analysis, path: str, method: str) -> bool:
        """Find if an endpoint is implemented in the code analysis."""
        # This is a simplified check - in reality would need more sophisticated parsing
        method_lower = method.lower()
        
        # Check for Flask/FastAPI style decorators
        for function in analysis.functions:
            # Check function decorators
            if hasattr(function, 'decorators'):
                for decorator in function.decorators:
                    if method_lower in str(decorator).lower() and path in str(decorator):
                        return True
            
            # Check function name
            if method_lower in function.name.lower() and path.replace('/', '_') in function.name:
                return True
        
        return False
    
    def _check_architecture_drift(self, report: DriftReport):
        """Check for architecture drift."""
        arch_spec = self.specifications.get('architecture', {})
        if not arch_spec:
            return
        
        content = arch_spec.get('content', '')
        
        # Extract expected components from architecture doc
        expected_components = self._extract_components_from_arch(content)
        
        # Analyze actual project structure
        actual_components = self._analyze_project_structure()
        
        # Compare expected vs actual
        for component in expected_components:
            if component not in actual_components:
                report.add_drift(DriftItem(
                    drift_type=DriftType.ARCHITECTURE,
                    description=f"Expected component '{component}' not found",
                    severity='medium',
                    expected=f"Component: {component}",
                    actual="Component not found in project structure",
                    spec_reference='ARCHITECTURE.md'
                ))
    
    def _extract_components_from_arch(self, content: str) -> Set[str]:
        """Extract expected components from architecture doc."""
        components = set()
        
        # Look for common patterns in architecture docs
        lines = content.split('\n')
        for line in lines:
            # Look for module/component definitions
            if any(keyword in line.lower() for keyword in ['module:', 'component:', 'service:', 'layer:']):
                # Extract component name
                parts = line.split(':')
                if len(parts) > 1:
                    component = parts[1].strip().split()[0]
                    if component:
                        components.add(component.lower())
        
        return components
    
    def _analyze_project_structure(self) -> Set[str]:
        """Analyze actual project structure."""
        components = set()
        
        # Look for top-level Python packages
        for path in self.project_path.iterdir():
            if path.is_dir() and (path / '__init__.py').exists():
                components.add(path.name.lower())
        
        # Look for src directory
        src_dir = self.project_path / 'src'
        if src_dir.exists():
            for path in src_dir.iterdir():
                if path.is_dir() and (path / '__init__.py').exists():
                    components.add(path.name.lower())
        
        return components
    
    def _check_documentation_drift(self, report: DriftReport):
        """Check for documentation drift."""
        readme_content = self.specifications.get('readme', '')
        if not readme_content:
            return
        
        # Extract claimed features from README
        claimed_features = self._extract_features_from_readme(readme_content)
        
        # Check if claimed features exist
        for feature in claimed_features:
            if not self._verify_feature_exists(feature):
                report.add_drift(DriftItem(
                    drift_type=DriftType.DOCUMENTATION,
                    description=f"README claims feature '{feature}' but implementation not found",
                    severity='medium',
                    expected=f"Feature: {feature}",
                    actual="Feature not found in codebase",
                    spec_reference='README.md'
                ))
    
    def _extract_features_from_readme(self, content: str) -> List[str]:
        """Extract feature claims from README."""
        features = []
        
        lines = content.split('\n')
        in_features_section = False
        
        for line in lines:
            # Look for Features section
            if any(header in line for header in ['## Features', '### Features', '# Features']):
                in_features_section = True
                continue
            
            # Stop at next section
            if in_features_section and line.startswith('#'):
                break
            
            # Extract feature items
            if in_features_section and line.strip().startswith(('- ', '* ', '+ ')):
                feature = line.strip()[2:].strip()
                if feature:
                    features.append(feature)
        
        return features
    
    def _verify_feature_exists(self, feature: str) -> bool:
        """Verify if a claimed feature exists in the codebase."""
        # Simple keyword search in codebase
        feature_keywords = feature.lower().split()[:3]  # Use first 3 words
        
        for py_file in self.project_path.rglob('*.py'):
            try:
                content = py_file.read_text().lower()
                if all(keyword in content for keyword in feature_keywords):
                    return True
            except Exception:
                continue
        
        return False
    
    def _check_code_structure_drift(self, report: DriftReport):
        """Check for code structure drift."""
        # Check for files that should exist based on project type
        expected_files = {
            'setup.py': 'Python package setup file',
            'requirements.txt': 'Python dependencies',
            'package.json': 'Node.js package file',
            'Dockerfile': 'Docker configuration',
            '.gitignore': 'Git ignore patterns'
        }
        
        for filename, description in expected_files.items():
            file_path = self.project_path / filename
            if not file_path.exists() and self._should_file_exist(filename):
                report.add_drift(DriftItem(
                    drift_type=DriftType.CODE_STRUCTURE,
                    description=f"Expected file '{filename}' not found",
                    severity='low',
                    expected=description,
                    actual="File not found",
                    file_path=file_path
                ))
    
    def _should_file_exist(self, filename: str) -> bool:
        """Determine if a file should exist based on project type."""
        # Python project indicators
        if filename in ['setup.py', 'requirements.txt']:
            return any(self.project_path.rglob('*.py'))
        
        # Node.js project indicators
        if filename == 'package.json':
            return any(self.project_path.rglob('*.js'))
        
        # Docker
        if filename == 'Dockerfile':
            # Only expect if there's evidence of containerization
            return (self.project_path / 'docker-compose.yml').exists()
        
        # Git
        if filename == '.gitignore':
            return (self.project_path / '.git').exists()
        
        return False
    
    def _check_security_drift(self, report: DriftReport):
        """Check for security drift."""
        try:
            # Analyze project for security issues
            analysis = self.code_analyzer.analyze_project(self.project_path)
            
            if analysis.security_issues:
                for issue in analysis.security_issues:
                    report.add_drift(DriftItem(
                        drift_type=DriftType.SECURITY,
                        description=f"Security vulnerability: {issue.vulnerability_type}",
                        severity='critical' if issue.severity == 'HIGH' else 'high',
                        file_path=Path(issue.file_path),
                        line_number=issue.line_number,
                        actual=issue.description,
                        expected="Secure code without vulnerabilities"
                    ))
        
        except Exception as e:
            logger.error(f"Error checking security drift: {e}")
    
    def _check_performance_drift(self, report: DriftReport):
        """Check for performance drift."""
        try:
            # Check for common performance anti-patterns
            for py_file in self.project_path.rglob('*.py'):
                content = py_file.read_text()
                
                # Check for N+1 query patterns
                if 'for ' in content and 'query(' in content:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'for ' in line and i + 1 < len(lines) and 'query(' in lines[i + 1]:
                            report.add_drift(DriftItem(
                                drift_type=DriftType.PERFORMANCE,
                                description="Potential N+1 query pattern detected",
                                severity='medium',
                                file_path=py_file,
                                line_number=i + 1,
                                actual="Query inside loop",
                                expected="Batch query or join"
                            ))
                
                # Check for synchronous I/O in async context
                if 'async def' in content:
                    sync_io_patterns = ['open(', 'file.read(', 'file.write(']
                    for pattern in sync_io_patterns:
                        if pattern in content:
                            report.add_drift(DriftItem(
                                drift_type=DriftType.PERFORMANCE,
                                description=f"Synchronous I/O '{pattern}' in async context",
                                severity='medium',
                                file_path=py_file,
                                actual=f"Synchronous {pattern}",
                                expected="Asynchronous I/O operation"
                            ))
        
        except Exception as e:
            logger.error(f"Error checking performance drift: {e}")
    
    def check_file_drift(self, file_path: Path) -> DriftReport:
        """Check for drift in a specific file."""
        report = DriftReport(project_path=self.project_path)
        report.files_checked = 1
        
        if file_path.suffix == '.py':
            # Analyze Python file
            try:
                analysis = self.code_analyzer.analyze_file(file_path)
                
                # Check against specifications
                if self.specifications.get('openapi') and 'api' in str(file_path).lower():
                    self._check_api_file_drift(file_path, analysis, report)
                
                # Always check for general issues
                self._check_file_security_drift(file_path, analysis, report)
                self._check_file_performance_drift(file_path, analysis, report)
                
            except Exception as e:
                logger.error(f"Error analyzing file {file_path}: {e}")
        
        return report
    
    def _check_api_file_drift(self, file_path: Path, analysis: Any, report: DriftReport):
        """Check API file for drift from OpenAPI spec."""
        spec = self.specifications.get('openapi', {})
        paths = spec.get('paths', {})
        
        # Check each endpoint in spec
        for path, methods in paths.items():
            for method, endpoint_spec in methods.items():
                if not self._find_endpoint_implementation(analysis, path, method):
                    report.add_drift(DriftItem(
                        drift_type=DriftType.API_CONTRACT,
                        description=f"API endpoint {method.upper()} {path} not implemented in this file",
                        severity='medium',
                        file_path=file_path,
                        expected=f"{method.upper()} {path}",
                        actual="Endpoint not found in file",
                        spec_reference='OpenAPI specification'
                    ))
    
    def _check_file_security_drift(self, file_path: Path, analysis: Any, report: DriftReport):
        """Check file for security drift."""
        if hasattr(analysis, 'security_issues'):
            for issue in analysis.security_issues:
                report.add_drift(DriftItem(
                    drift_type=DriftType.SECURITY,
                    description=f"Security vulnerability: {issue.vulnerability_type}",
                    severity='critical' if issue.severity == 'HIGH' else 'high',
                    file_path=file_path,
                    line_number=issue.line_number,
                    actual=issue.description,
                    expected="Secure code without vulnerabilities"
                ))
    
    def _check_file_performance_drift(self, file_path: Path, analysis: Any, report: DriftReport):
        """Check file for performance drift."""
        if hasattr(analysis, 'metrics'):
            # Check complexity
            if analysis.metrics.average_complexity > 10:
                report.add_drift(DriftItem(
                    drift_type=DriftType.PERFORMANCE,
                    description=f"High code complexity: {analysis.metrics.average_complexity:.1f}",
                    severity='medium',
                    file_path=file_path,
                    actual=f"Complexity: {analysis.metrics.average_complexity:.1f}",
                    expected="Complexity < 10"
                ))
    
    def get_drift_summary(self) -> Dict[str, Any]:
        """Get a summary of current drift state."""
        report = self.check_drift()
        return report.to_dict()['summary']