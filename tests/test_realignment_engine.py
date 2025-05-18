"""
Tests for realignment engine functionality.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from velocitytree.monitoring.realignment_engine import (
    RealignmentEngine, RealignmentPlan, RealignmentSuggestion,
    SuggestionType, SuggestionPriority
)
from velocitytree.monitoring.drift_detector import DriftReport, DriftItem, DriftType


class TestRealignmentSuggestion:
    """Test cases for RealignmentSuggestion."""
    
    def test_suggestion_creation(self):
        """Test creating a realignment suggestion."""
        drift_item = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Test drift",
            severity="medium"
        )
        
        suggestion = RealignmentSuggestion(
            suggestion_id="test-123",
            drift_item=drift_item,
            suggestion_type=SuggestionType.CODE_CHANGE,
            priority=SuggestionPriority.MEDIUM,
            title="Fix test drift",
            description="This suggestion fixes test drift",
            implementation_steps=["Step 1", "Step 2"],
            estimated_effort="30 minutes",
            automated=True,
            confidence=0.8
        )
        
        assert suggestion.suggestion_id == "test-123"
        assert suggestion.suggestion_type == SuggestionType.CODE_CHANGE
        assert suggestion.priority == SuggestionPriority.MEDIUM
        assert suggestion.automated is True
        assert suggestion.confidence == 0.8
    
    def test_suggestion_to_dict(self):
        """Test converting suggestion to dictionary."""
        drift_item = DriftItem(
            drift_type=DriftType.API_CONTRACT,
            description="API drift",
            severity="high"
        )
        
        suggestion = RealignmentSuggestion(
            suggestion_id="test-456",
            drift_item=drift_item,
            suggestion_type=SuggestionType.API_UPDATE,
            priority=SuggestionPriority.HIGH,
            title="Update API",
            description="Update API endpoint",
            implementation_steps=["Update handler"],
            file_changes=[{
                'action': 'modify',
                'path': 'api.py'
            }]
        )
        
        data = suggestion.to_dict()
        assert data['suggestion_id'] == "test-456"
        assert data['drift_type'] == 'api_contract'
        assert data['suggestion_type'] == 'api_update'
        assert data['priority'] == 'high'
        assert len(data['file_changes']) == 1


class TestRealignmentPlan:
    """Test cases for RealignmentPlan."""
    
    def test_plan_creation(self, tmp_path):
        """Test creating a realignment plan."""
        plan = RealignmentPlan(
            plan_id="plan-123",
            project_path=tmp_path
        )
        
        assert plan.plan_id == "plan-123"
        assert plan.project_path == tmp_path
        assert len(plan.suggestions) == 0
    
    def test_add_suggestion(self, tmp_path):
        """Test adding suggestions to plan."""
        plan = RealignmentPlan(
            plan_id="plan-123",
            project_path=tmp_path
        )
        
        drift_item = DriftItem(
            drift_type=DriftType.DOCUMENTATION,
            description="Doc drift",
            severity="low"
        )
        
        suggestion = RealignmentSuggestion(
            suggestion_id="sug-1",
            drift_item=drift_item,
            suggestion_type=SuggestionType.DOCUMENTATION_UPDATE,
            priority=SuggestionPriority.LOW,
            title="Update docs",
            description="Update documentation",
            implementation_steps=["Update README"]
        )
        
        plan.add_suggestion(suggestion)
        assert len(plan.suggestions) == 1
        assert plan.suggestions[0] == suggestion
    
    def test_plan_to_dict(self, tmp_path):
        """Test converting plan to dictionary."""
        plan = RealignmentPlan(
            plan_id="plan-123",
            project_path=tmp_path,
            total_effort="2 hours"
        )
        
        # Add suggestions of different types and priorities
        for i in range(3):
            drift_item = DriftItem(
                drift_type=DriftType.CODE_STRUCTURE,
                description=f"Drift {i}",
                severity="medium"
            )
            
            suggestion = RealignmentSuggestion(
                suggestion_id=f"sug-{i}",
                drift_item=drift_item,
                suggestion_type=SuggestionType.CODE_CHANGE if i < 2 else SuggestionType.FILE_CREATION,
                priority=SuggestionPriority.MEDIUM if i < 2 else SuggestionPriority.HIGH,
                title=f"Fix {i}",
                description=f"Fix drift {i}",
                implementation_steps=[f"Step {i}"],
                automated=i == 0
            )
            plan.add_suggestion(suggestion)
        
        data = plan.to_dict()
        assert data['plan_id'] == "plan-123"
        assert data['total_effort'] == "2 hours"
        assert data['summary']['total_suggestions'] == 3
        assert data['summary']['by_type']['code_change'] == 2
        assert data['summary']['by_type']['file_creation'] == 1
        assert data['summary']['by_priority']['medium'] == 2
        assert data['summary']['by_priority']['high'] == 1
        assert data['summary']['automated_available'] == 1


class TestRealignmentEngine:
    """Test cases for RealignmentEngine."""
    
    def test_init(self, tmp_path):
        """Test engine initialization."""
        engine = RealignmentEngine(tmp_path)
        assert engine.project_path == tmp_path
    
    def test_generate_suggestions_empty(self, tmp_path):
        """Test generating suggestions for empty drift report."""
        engine = RealignmentEngine(tmp_path)
        drift_report = DriftReport(project_path=tmp_path)
        
        plan = engine.generate_suggestions(drift_report)
        
        assert isinstance(plan, RealignmentPlan)
        assert len(plan.suggestions) == 0
    
    def test_suggest_code_structure_fixes(self, tmp_path):
        """Test suggesting fixes for code structure drift."""
        engine = RealignmentEngine(tmp_path)
        
        # Missing file drift
        drift_item = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Expected file 'setup.py' not found",
            severity="medium",
            file_path=tmp_path / "setup.py",
            expected="Python package setup file",
            actual="File not found"
        )
        
        suggestions = engine._suggest_code_structure_fixes(drift_item)
        
        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.suggestion_type == SuggestionType.FILE_CREATION
        assert "Create missing file" in suggestion.title
        assert suggestion.automated is True
        assert len(suggestion.file_changes) > 0
    
    def test_suggest_api_fixes(self, tmp_path):
        """Test suggesting fixes for API drift."""
        engine = RealignmentEngine(tmp_path)
        
        # Missing endpoint drift
        drift_item = DriftItem(
            drift_type=DriftType.API_CONTRACT,
            description="API endpoint POST /users not implemented",
            severity="high",
            file_path=tmp_path / "api.py"
        )
        
        suggestions = engine._suggest_api_fixes(drift_item)
        
        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.suggestion_type == SuggestionType.CODE_CHANGE
        assert "POST /users" in suggestion.title
        assert suggestion.priority == SuggestionPriority.HIGH
        assert len(suggestion.implementation_steps) > 0
    
    def test_suggest_documentation_fixes(self, tmp_path):
        """Test suggesting fixes for documentation drift."""
        engine = RealignmentEngine(tmp_path)
        
        drift_item = DriftItem(
            drift_type=DriftType.DOCUMENTATION,
            description="README claims feature 'Advanced search' but implementation not found",
            severity="medium",
            expected="Feature: Advanced search"
        )
        
        suggestions = engine._suggest_documentation_fixes(drift_item)
        
        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.suggestion_type == SuggestionType.DOCUMENTATION_UPDATE
        assert "Advanced search" in suggestion.title
    
    def test_suggest_security_fixes(self, tmp_path):
        """Test suggesting fixes for security vulnerabilities."""
        engine = RealignmentEngine(tmp_path)
        
        drift_item = DriftItem(
            drift_type=DriftType.SECURITY,
            description="Security vulnerability: SQL Injection",
            severity="critical",
            file_path=tmp_path / "db.py",
            line_number=42,
            actual="Unsafe SQL query construction"
        )
        
        suggestions = engine._suggest_security_fixes(drift_item)
        
        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.priority == SuggestionPriority.CRITICAL
        assert "SQL Injection" in suggestion.title
        assert suggestion.suggestion_type == SuggestionType.CODE_CHANGE
    
    def test_suggest_performance_fixes(self, tmp_path):
        """Test suggesting fixes for performance issues."""
        engine = RealignmentEngine(tmp_path)
        
        # N+1 query pattern
        drift_item = DriftItem(
            drift_type=DriftType.PERFORMANCE,
            description="Potential N+1 query pattern detected",
            severity="medium",
            file_path=tmp_path / "models.py",
            line_number=100
        )
        
        suggestions = engine._suggest_performance_fixes(drift_item)
        
        assert len(suggestions) > 0
        suggestion = suggestions[0]
        assert suggestion.suggestion_type == SuggestionType.REFACTORING
        assert "N+1 query" in suggestion.title
        
        # Synchronous I/O
        drift_item2 = DriftItem(
            drift_type=DriftType.PERFORMANCE,
            description="Synchronous I/O 'open(' in async context",
            severity="medium",
            file_path=tmp_path / "async_handler.py",
            line_number=50
        )
        
        suggestions2 = engine._suggest_performance_fixes(drift_item2)
        
        assert len(suggestions2) > 0
        suggestion2 = suggestions2[0]
        assert "asynchronous I/O" in suggestion2.title
    
    def test_generate_file_template(self, tmp_path):
        """Test generating file templates."""
        engine = RealignmentEngine(tmp_path)
        
        # Python file
        py_file = tmp_path / "test.py"
        template = engine._generate_file_template(py_file)
        assert '"""' in template
        assert "test module" in template
        
        # JavaScript file
        js_file = tmp_path / "test.js"
        template = engine._generate_file_template(js_file)
        assert "/**" in template
        assert "test module" in template
        
        # Package.json
        package_file = tmp_path / "package.json"
        template = engine._generate_file_template(package_file)
        data = json.loads(template)
        assert data['name'] == tmp_path.name
        assert 'version' in data
    
    def test_calculate_total_effort(self, tmp_path):
        """Test calculating total effort."""
        engine = RealignmentEngine(tmp_path)
        
        suggestions = []
        
        # Add suggestions with different effort estimates
        drift_item = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Test",
            severity="medium"
        )
        
        suggestions.append(RealignmentSuggestion(
            suggestion_id="1",
            drift_item=drift_item,
            suggestion_type=SuggestionType.CODE_CHANGE,
            priority=SuggestionPriority.MEDIUM,
            title="Test 1",
            description="Test",
            implementation_steps=[],
            estimated_effort="30 minutes"
        ))
        
        suggestions.append(RealignmentSuggestion(
            suggestion_id="2",
            drift_item=drift_item,
            suggestion_type=SuggestionType.CODE_CHANGE,
            priority=SuggestionPriority.MEDIUM,
            title="Test 2",
            description="Test",
            implementation_steps=[],
            estimated_effort="45 minutes"
        ))
        
        suggestions.append(RealignmentSuggestion(
            suggestion_id="3",
            drift_item=drift_item,
            suggestion_type=SuggestionType.CODE_CHANGE,
            priority=SuggestionPriority.MEDIUM,
            title="Test 3",
            description="Test",
            implementation_steps=[],
            estimated_effort="2 hours"
        ))
        
        effort = engine._calculate_total_effort(suggestions)
        assert "3.2 hours" in effort or "195 minutes" in effort
    
    def test_apply_suggestion(self, tmp_path):
        """Test applying automated suggestions."""
        engine = RealignmentEngine(tmp_path)
        
        # Create file suggestion
        drift_item = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Missing file",
            severity="medium"
        )
        
        suggestion = RealignmentSuggestion(
            suggestion_id="test",
            drift_item=drift_item,
            suggestion_type=SuggestionType.FILE_CREATION,
            priority=SuggestionPriority.MEDIUM,
            title="Create test file",
            description="Create missing file",
            implementation_steps=["Create file"],
            file_changes=[{
                'action': 'create',
                'path': str(tmp_path / 'test_file.txt'),
                'content': 'Test content'
            }],
            automated=True
        )
        
        result = engine.apply_suggestion(suggestion)
        assert result is True
        assert (tmp_path / 'test_file.txt').exists()
        assert (tmp_path / 'test_file.txt').read_text() == 'Test content'
    
    def test_apply_non_automated_suggestion(self, tmp_path):
        """Test applying non-automated suggestion fails."""
        engine = RealignmentEngine(tmp_path)
        
        drift_item = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Complex change",
            severity="medium"
        )
        
        suggestion = RealignmentSuggestion(
            suggestion_id="test",
            drift_item=drift_item,
            suggestion_type=SuggestionType.REFACTORING,
            priority=SuggestionPriority.MEDIUM,
            title="Refactor code",
            description="Complex refactoring",
            implementation_steps=["Refactor"],
            automated=False
        )
        
        result = engine.apply_suggestion(suggestion)
        assert result is False