"""
Realignment suggestions engine for Velocitytree.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..utils import logger
from ..code_analysis import CodeAnalyzer
from ..documentation.generator import DocGenerator
from .drift_detector import DriftReport, DriftItem, DriftType


class SuggestionType(Enum):
    """Type of realignment suggestion."""
    CODE_CHANGE = "code_change"
    FILE_CREATION = "file_creation"
    FILE_DELETION = "file_deletion"
    DOCUMENTATION_UPDATE = "documentation_update"
    CONFIGURATION_CHANGE = "configuration_change"
    REFACTORING = "refactoring"
    DEPENDENCY_UPDATE = "dependency_update"
    API_UPDATE = "api_update"


class SuggestionPriority(Enum):
    """Priority level for suggestions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RealignmentSuggestion:
    """Individual realignment suggestion."""
    suggestion_id: str
    drift_item: DriftItem
    suggestion_type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    implementation_steps: List[str]
    file_changes: List[Dict[str, Any]] = field(default_factory=list)
    estimated_effort: str = "Unknown"
    automated: bool = False
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert suggestion to dictionary."""
        return {
            'suggestion_id': self.suggestion_id,
            'drift_type': self.drift_item.drift_type.value,
            'suggestion_type': self.suggestion_type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'implementation_steps': self.implementation_steps,
            'file_changes': self.file_changes,
            'estimated_effort': self.estimated_effort,
            'automated': self.automated,
            'confidence': self.confidence
        }


@dataclass
class RealignmentPlan:
    """Complete realignment plan."""
    plan_id: str
    project_path: Path
    timestamp: datetime = field(default_factory=datetime.now)
    suggestions: List[RealignmentSuggestion] = field(default_factory=list)
    total_effort: str = "Unknown"
    
    def add_suggestion(self, suggestion: RealignmentSuggestion):
        """Add a suggestion to the plan."""
        self.suggestions.append(suggestion)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary."""
        return {
            'plan_id': self.plan_id,
            'project_path': str(self.project_path),
            'timestamp': self.timestamp.isoformat(),
            'suggestions': [s.to_dict() for s in self.suggestions],
            'total_effort': self.total_effort,
            'summary': {
                'total_suggestions': len(self.suggestions),
                'by_type': self._count_by_type(),
                'by_priority': self._count_by_priority(),
                'automated_available': sum(1 for s in self.suggestions if s.automated)
            }
        }
    
    def _count_by_type(self) -> Dict[str, int]:
        """Count suggestions by type."""
        counts = {}
        for suggestion in self.suggestions:
            type_name = suggestion.suggestion_type.value
            counts[type_name] = counts.get(type_name, 0) + 1
        return counts
    
    def _count_by_priority(self) -> Dict[str, int]:
        """Count suggestions by priority."""
        counts = {}
        for suggestion in self.suggestions:
            priority = suggestion.priority.value
            counts[priority] = counts.get(priority, 0) + 1
        return counts


class RealignmentEngine:
    """Engine for generating realignment suggestions."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.code_analyzer = CodeAnalyzer()
        self.doc_generator = DocGenerator()
    
    def generate_suggestions(self, drift_report: DriftReport) -> RealignmentPlan:
        """Generate realignment suggestions from drift report."""
        plan = RealignmentPlan(
            plan_id=self._generate_plan_id(),
            project_path=self.project_path
        )
        
        # Process each drift item
        for drift_item in drift_report.drifts:
            suggestions = self._generate_suggestions_for_drift(drift_item)
            for suggestion in suggestions:
                plan.add_suggestion(suggestion)
        
        # Calculate total effort
        plan.total_effort = self._calculate_total_effort(plan.suggestions)
        
        return plan
    
    def _generate_suggestions_for_drift(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Generate suggestions for a specific drift item."""
        suggestions = []
        
        if drift_item.drift_type == DriftType.CODE_STRUCTURE:
            suggestions.extend(self._suggest_code_structure_fixes(drift_item))
        elif drift_item.drift_type == DriftType.API_CONTRACT:
            suggestions.extend(self._suggest_api_fixes(drift_item))
        elif drift_item.drift_type == DriftType.DOCUMENTATION:
            suggestions.extend(self._suggest_documentation_fixes(drift_item))
        elif drift_item.drift_type == DriftType.FEATURE_SPEC:
            suggestions.extend(self._suggest_feature_fixes(drift_item))
        elif drift_item.drift_type == DriftType.ARCHITECTURE:
            suggestions.extend(self._suggest_architecture_fixes(drift_item))
        elif drift_item.drift_type == DriftType.DEPENDENCY:
            suggestions.extend(self._suggest_dependency_fixes(drift_item))
        elif drift_item.drift_type == DriftType.SECURITY:
            suggestions.extend(self._suggest_security_fixes(drift_item))
        elif drift_item.drift_type == DriftType.PERFORMANCE:
            suggestions.extend(self._suggest_performance_fixes(drift_item))
        
        return suggestions
    
    def _suggest_code_structure_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for code structure drift."""
        suggestions = []
        
        if "Expected file" in drift_item.description and "not found" in drift_item.description:
            # Suggest creating missing file
            file_path = drift_item.file_path
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.FILE_CREATION,
                priority=SuggestionPriority.HIGH,
                title=f"Create missing file: {file_path.name}",
                description=f"Create the expected file '{file_path}' to match project structure requirements",
                implementation_steps=[
                    f"Create file: {file_path}",
                    f"Add appropriate content based on file type ({file_path.suffix})",
                    "Ensure file follows project conventions"
                ],
                file_changes=[{
                    'action': 'create',
                    'path': str(file_path),
                    'content': self._generate_file_template(file_path)
                }],
                estimated_effort="5 minutes",
                automated=True,
                confidence=0.9
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_api_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for API contract drift."""
        suggestions = []
        
        if "not implemented" in drift_item.description:
            # Extract endpoint details
            parts = drift_item.description.split()
            method = parts[2] if len(parts) > 2 else "GET"
            path = parts[3] if len(parts) > 3 else "/unknown"
            
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.CODE_CHANGE,
                priority=SuggestionPriority.HIGH,
                title=f"Implement missing API endpoint: {method} {path}",
                description=f"Add implementation for the {method} {path} endpoint as specified in the API contract",
                implementation_steps=[
                    f"Add route handler for {method} {path}",
                    "Implement request validation",
                    "Add business logic",
                    "Implement response formatting",
                    "Add error handling",
                    "Write tests for the endpoint"
                ],
                file_changes=[{
                    'action': 'modify',
                    'path': str(drift_item.file_path) if drift_item.file_path else 'api/routes.py',
                    'changes': [
                        {
                            'type': 'add_function',
                            'name': f"handle_{path.replace('/', '_').strip('_')}_{method.lower()}",
                            'content': self._generate_endpoint_template(method, path)
                        }
                    ]
                }],
                estimated_effort="30 minutes",
                automated=False,
                confidence=0.7
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_documentation_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for documentation drift."""
        suggestions = []
        
        if "claims feature" in drift_item.description and "not found" in drift_item.description:
            # Extract feature name
            feature_name = drift_item.expected.replace("Feature: ", "") if drift_item.expected else "Unknown feature"
            
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.DOCUMENTATION_UPDATE,
                priority=SuggestionPriority.MEDIUM,
                title=f"Update documentation for feature: {feature_name}",
                description="Update README to accurately reflect implemented features",
                implementation_steps=[
                    "Review current implementation of the feature",
                    "Update README to match actual functionality",
                    "Or implement the missing feature if intended",
                    "Ensure documentation is accurate"
                ],
                file_changes=[{
                    'action': 'modify',
                    'path': 'README.md',
                    'changes': [
                        {
                            'type': 'update_section',
                            'section': 'Features',
                            'update': f"Update or remove claim about: {feature_name}"
                        }
                    ]
                }],
                estimated_effort="15 minutes",
                automated=False,
                confidence=0.6
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_feature_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for feature specification drift."""
        suggestions = []
        
        if "status mismatch" in drift_item.description:
            feature_id = drift_item.description.split("'")[1]
            expected_status = drift_item.expected.split(": ")[1] if drift_item.expected else "unknown"
            actual_status = drift_item.actual.split(": ")[1] if drift_item.actual else "unknown"
            
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.CONFIGURATION_CHANGE,
                priority=SuggestionPriority.LOW,
                title=f"Update feature status for: {feature_id}",
                description=f"Update feature status from '{actual_status}' to '{expected_status}' in specification",
                implementation_steps=[
                    f"Open feature specification file",
                    f"Locate feature '{feature_id}'",
                    f"Update status to '{expected_status}'",
                    "Save changes"
                ],
                file_changes=[{
                    'action': 'modify',
                    'path': 'velocitytree.yaml',
                    'changes': [
                        {
                            'type': 'update_yaml',
                            'path': f'features.{feature_id}.status',
                            'value': expected_status
                        }
                    ]
                }],
                estimated_effort="5 minutes",
                automated=True,
                confidence=0.95
            )
            suggestions.append(suggestion)
        
        elif "specified but not implemented" in drift_item.description:
            feature_id = drift_item.description.split("'")[1]
            
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.CODE_CHANGE,
                priority=SuggestionPriority.HIGH,
                title=f"Implement missing feature: {feature_id}",
                description=f"Implement the specified feature '{feature_id}' according to specification",
                implementation_steps=[
                    "Review feature specification",
                    "Design implementation approach",
                    "Create necessary files and classes",
                    "Implement feature logic",
                    "Write tests",
                    "Update documentation"
                ],
                estimated_effort="2-4 hours",
                automated=False,
                confidence=0.5
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_architecture_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for architecture drift."""
        suggestions = []
        
        if "Expected component" in drift_item.description and "not found" in drift_item.description:
            component_name = drift_item.expected.replace("Component: ", "") if drift_item.expected else "Unknown"
            
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.FILE_CREATION,
                priority=SuggestionPriority.HIGH,
                title=f"Create missing component: {component_name}",
                description=f"Create the architectural component '{component_name}' as specified",
                implementation_steps=[
                    f"Create directory/module for {component_name}",
                    "Add __init__.py file if Python module",
                    "Implement basic structure",
                    "Add to project imports",
                    "Update documentation"
                ],
                file_changes=[{
                    'action': 'create',
                    'path': f"{component_name}/__init__.py",
                    'content': f'"""\n{component_name} module.\n"""\n\n'
                }],
                estimated_effort="1 hour",
                automated=True,
                confidence=0.8
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_dependency_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for dependency drift."""
        suggestions = []
        
        # Add dependency-specific suggestions
        suggestion = RealignmentSuggestion(
            suggestion_id=self._generate_suggestion_id(),
            drift_item=drift_item,
            suggestion_type=SuggestionType.DEPENDENCY_UPDATE,
            priority=SuggestionPriority.MEDIUM,
            title="Update project dependencies",
            description=drift_item.description,
            implementation_steps=[
                "Review dependency requirements",
                "Update requirements.txt or package.json",
                "Run dependency installation",
                "Test compatibility"
            ],
            estimated_effort="30 minutes",
            automated=False,
            confidence=0.7
        )
        suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_security_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for security vulnerabilities."""
        suggestions = []
        
        priority = SuggestionPriority.CRITICAL if drift_item.severity == 'critical' else SuggestionPriority.HIGH
        
        suggestion = RealignmentSuggestion(
            suggestion_id=self._generate_suggestion_id(),
            drift_item=drift_item,
            suggestion_type=SuggestionType.CODE_CHANGE,
            priority=priority,
            title=f"Fix security vulnerability: {drift_item.description}",
            description=f"Address security issue: {drift_item.actual}",
            implementation_steps=[
                "Review the security vulnerability",
                "Implement secure coding practices",
                "Validate input/output",
                "Add security tests",
                "Document security measures"
            ],
            file_changes=[{
                'action': 'modify',
                'path': str(drift_item.file_path) if drift_item.file_path else 'unknown',
                'line': drift_item.line_number,
                'security_fix': True
            }],
            estimated_effort="1-2 hours",
            automated=False,
            confidence=0.6
        )
        suggestions.append(suggestion)
        
        return suggestions
    
    def _suggest_performance_fixes(self, drift_item: DriftItem) -> List[RealignmentSuggestion]:
        """Suggest fixes for performance issues."""
        suggestions = []
        
        if "N+1 query" in drift_item.description:
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.REFACTORING,
                priority=SuggestionPriority.MEDIUM,
                title="Fix N+1 query pattern",
                description="Optimize database queries to avoid N+1 pattern",
                implementation_steps=[
                    "Identify the query loop",
                    "Refactor to use batch query or joins",
                    "Test performance improvement",
                    "Add query optimization comments"
                ],
                file_changes=[{
                    'action': 'refactor',
                    'path': str(drift_item.file_path) if drift_item.file_path else 'unknown',
                    'pattern': 'n+1_query',
                    'line': drift_item.line_number
                }],
                estimated_effort="45 minutes",
                automated=False,
                confidence=0.7
            )
            suggestions.append(suggestion)
        
        elif "Synchronous I/O" in drift_item.description:
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.CODE_CHANGE,
                priority=SuggestionPriority.MEDIUM,
                title="Convert to asynchronous I/O",
                description="Replace synchronous I/O with async operations",
                implementation_steps=[
                    "Identify synchronous I/O calls",
                    "Replace with async equivalents",
                    "Update function signatures if needed",
                    "Test async behavior"
                ],
                file_changes=[{
                    'action': 'modify',
                    'path': str(drift_item.file_path) if drift_item.file_path else 'unknown',
                    'pattern': 'sync_to_async',
                    'line': drift_item.line_number
                }],
                estimated_effort="30 minutes",
                automated=False,
                confidence=0.8
            )
            suggestions.append(suggestion)
        
        elif "High code complexity" in drift_item.description:
            suggestion = RealignmentSuggestion(
                suggestion_id=self._generate_suggestion_id(),
                drift_item=drift_item,
                suggestion_type=SuggestionType.REFACTORING,
                priority=SuggestionPriority.LOW,
                title="Reduce code complexity",
                description="Refactor complex code to improve maintainability",
                implementation_steps=[
                    "Identify complex functions",
                    "Extract methods or functions",
                    "Simplify conditional logic",
                    "Add appropriate abstractions",
                    "Update tests"
                ],
                estimated_effort="1-2 hours",
                automated=False,
                confidence=0.5
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_file_template(self, file_path: Path) -> str:
        """Generate template content for a new file."""
        if file_path.suffix == '.py':
            return f'"""\n{file_path.stem} module.\n"""\n\n'
        elif file_path.suffix == '.js':
            return f'/**\n * {file_path.stem} module\n */\n\n'
        elif file_path.suffix == '.md':
            return f'# {file_path.stem}\n\n'
        elif file_path.name == 'requirements.txt':
            return '# Python dependencies\n\n'
        elif file_path.name == 'package.json':
            return json.dumps({
                "name": self.project_path.name,
                "version": "1.0.0",
                "description": "",
                "main": "index.js",
                "scripts": {},
                "dependencies": {}
            }, indent=2)
        else:
            return ''
    
    def _generate_endpoint_template(self, method: str, path: str) -> str:
        """Generate template for API endpoint."""
        function_name = f"handle_{path.replace('/', '_').strip('_')}_{method.lower()}"
        
        return f'''def {function_name}(request):
    """
    Handle {method} {path} endpoint.
    
    Args:
        request: The HTTP request object
        
    Returns:
        Response object
    """
    # TODO: Implement {method} {path} logic
    # 1. Validate request parameters
    # 2. Process business logic
    # 3. Return response
    
    return {{"status": "not_implemented"}}
'''
    
    def _calculate_total_effort(self, suggestions: List[RealignmentSuggestion]) -> str:
        """Calculate total estimated effort."""
        total_minutes = 0
        
        for suggestion in suggestions:
            effort = suggestion.estimated_effort
            
            # Parse effort string
            if "minutes" in effort:
                try:
                    minutes = int(effort.split()[0])
                    total_minutes += minutes
                except:
                    pass
            elif "hour" in effort:
                try:
                    if "-" in effort:
                        # Range like "1-2 hours"
                        hours = float(effort.split("-")[0])
                    else:
                        hours = float(effort.split()[0])
                    total_minutes += int(hours * 60)
                except:
                    pass
        
        if total_minutes < 60:
            return f"{total_minutes} minutes"
        else:
            hours = total_minutes / 60
            return f"{hours:.1f} hours"
    
    def _generate_plan_id(self) -> str:
        """Generate unique plan ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _generate_suggestion_id(self) -> str:
        """Generate unique suggestion ID."""
        import uuid
        return str(uuid.uuid4())
    
    def apply_suggestion(self, suggestion: RealignmentSuggestion) -> bool:
        """Apply an automated suggestion."""
        if not suggestion.automated:
            logger.warning(f"Suggestion {suggestion.suggestion_id} is not automated")
            return False
        
        try:
            for change in suggestion.file_changes:
                if change['action'] == 'create':
                    file_path = Path(change['path'])
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(change['content'])
                    logger.info(f"Created file: {file_path}")
                
                elif change['action'] == 'modify':
                    file_path = Path(change['path'])
                    if file_path.exists():
                        # Simple append for now
                        # In reality, would need more sophisticated modification
                        logger.info(f"Would modify file: {file_path}")
                    else:
                        logger.warning(f"File not found: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying suggestion: {e}")
            return False