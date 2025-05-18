"""
Tests for drift detection functionality.
"""

import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from velocitytree.monitoring.drift_detector import (
    DriftDetector, DriftReport, DriftItem, DriftType, SpecificationParser
)


class TestDriftItem:
    """Test cases for DriftItem."""
    
    def test_drift_item_creation(self):
        """Test creating a drift item."""
        drift = DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Missing file",
            severity="medium",
            file_path=Path("test.py"),
            line_number=10,
            expected="File should exist",
            actual="File not found",
            spec_reference="requirements.txt"
        )
        
        assert drift.drift_type == DriftType.CODE_STRUCTURE
        assert drift.description == "Missing file"
        assert drift.severity == "medium"
        assert drift.file_path == Path("test.py")
        assert drift.line_number == 10
    
    def test_drift_item_to_dict(self):
        """Test converting drift item to dictionary."""
        drift = DriftItem(
            drift_type=DriftType.API_CONTRACT,
            description="Endpoint missing",
            severity="high"
        )
        
        data = drift.to_dict()
        assert data['drift_type'] == 'api_contract'
        assert data['description'] == "Endpoint missing"
        assert data['severity'] == "high"
        assert data['file_path'] is None


class TestDriftReport:
    """Test cases for DriftReport."""
    
    def test_drift_report_creation(self, tmp_path):
        """Test creating a drift report."""
        report = DriftReport(project_path=tmp_path)
        
        assert report.project_path == tmp_path
        assert len(report.drifts) == 0
        assert report.files_checked == 0
    
    def test_add_drift(self, tmp_path):
        """Test adding drift to report."""
        report = DriftReport(project_path=tmp_path)
        
        drift = DriftItem(
            drift_type=DriftType.DOCUMENTATION,
            description="README outdated",
            severity="low"
        )
        
        report.add_drift(drift)
        assert len(report.drifts) == 1
        assert report.drifts[0] == drift
    
    def test_drift_report_to_dict(self, tmp_path):
        """Test converting report to dictionary."""
        report = DriftReport(project_path=tmp_path)
        report.files_checked = 10
        report.checked_specs = ['velocitytree', 'openapi']
        
        # Add drifts of different types and severities
        report.add_drift(DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Test 1",
            severity="low"
        ))
        report.add_drift(DriftItem(
            drift_type=DriftType.CODE_STRUCTURE,
            description="Test 2",
            severity="medium"
        ))
        report.add_drift(DriftItem(
            drift_type=DriftType.API_CONTRACT,
            description="Test 3",
            severity="high"
        ))
        
        data = report.to_dict()
        
        assert str(data['project_path']) == str(tmp_path)
        assert data['files_checked'] == 10
        assert data['checked_specs'] == ['velocitytree', 'openapi']
        assert data['summary']['total_drifts'] == 3
        assert data['summary']['by_type']['code_structure'] == 2
        assert data['summary']['by_type']['api_contract'] == 1
        assert data['summary']['by_severity']['low'] == 1
        assert data['summary']['by_severity']['medium'] == 1
        assert data['summary']['by_severity']['high'] == 1


class TestSpecificationParser:
    """Test cases for SpecificationParser."""
    
    def test_load_velocitytree_spec(self, tmp_path):
        """Test loading velocitytree specification."""
        # Create spec file
        spec_file = tmp_path / 'velocitytree.yaml'
        spec_data = {
            'features': {
                'feature1': {'name': 'Test Feature', 'status': 'completed'}
            }
        }
        with open(spec_file, 'w') as f:
            yaml.dump(spec_data, f)
        
        parser = SpecificationParser(tmp_path)
        spec = parser._load_velocitytree_spec()
        
        assert spec == spec_data
    
    def test_load_openapi_spec(self, tmp_path):
        """Test loading OpenAPI specification."""
        # Create spec file
        spec_file = tmp_path / 'openapi.yaml'
        spec_data = {
            'openapi': '3.0.0',
            'info': {'title': 'Test API'},
            'paths': {
                '/users': {
                    'get': {'summary': 'Get users'}
                }
            }
        }
        with open(spec_file, 'w') as f:
            yaml.dump(spec_data, f)
        
        parser = SpecificationParser(tmp_path)
        spec = parser._load_openapi_spec()
        
        assert spec == spec_data
    
    def test_load_readme_spec(self, tmp_path):
        """Test loading README specification."""
        readme_file = tmp_path / 'README.md'
        readme_content = "# Test Project\n\nThis is a test project."
        readme_file.write_text(readme_content)
        
        parser = SpecificationParser(tmp_path)
        spec = parser._load_readme_spec()
        
        assert spec == readme_content
    
    def test_load_all_specifications(self, tmp_path):
        """Test loading all specifications."""
        # Create various spec files
        (tmp_path / 'velocitytree.yaml').write_text('features: {}')
        (tmp_path / 'README.md').write_text('# Test')
        
        parser = SpecificationParser(tmp_path)
        specs = parser.load_specifications()
        
        assert 'velocitytree' in specs
        assert 'readme' in specs
        assert specs['readme'] == '# Test'


class TestDriftDetector:
    """Test cases for DriftDetector."""
    
    def test_init(self, tmp_path):
        """Test drift detector initialization."""
        detector = DriftDetector(tmp_path)
        
        assert detector.project_path == tmp_path
        assert isinstance(detector.spec_parser, SpecificationParser)
    
    @patch('velocitytree.monitoring.drift_detector.FeatureGraph')
    def test_check_feature_drift(self, mock_feature_graph, tmp_path):
        """Test checking feature drift."""
        # Setup
        spec_file = tmp_path / 'velocitytree.yaml'
        spec_data = {
            'features': {
                'feature1': {'name': 'Feature 1', 'status': 'completed'},
                'feature2': {'name': 'Feature 2', 'status': 'planned'}
            }
        }
        with open(spec_file, 'w') as f:
            yaml.dump(spec_data, f)
        
        # Mock feature graph
        mock_fg = Mock()
        mock_fg.features = {
            'feature1': Mock(name='Feature 1', status='in_progress'),  # Status mismatch
            'feature3': Mock(name='Feature 3', status='completed')  # Unspecified feature
        }
        mock_feature_graph.return_value = mock_fg
        mock_fg.load_from_spec.return_value = None
        
        detector = DriftDetector(tmp_path)
        report = DriftReport(project_path=tmp_path)
        
        detector._check_feature_drift(report)
        
        # Should detect:
        # 1. feature1 status mismatch
        # 2. feature2 not implemented
        # 3. feature3 unspecified
        assert len(report.drifts) >= 3
        
        drift_types = [d.description for d in report.drifts]
        assert any("Feature 'feature1' status mismatch" in d for d in drift_types)
        assert any("Feature 'feature2' specified but not implemented" in d for d in drift_types)
        assert any("Feature 'feature3' implemented but not specified" in d for d in drift_types)
    
    def test_check_api_drift(self, tmp_path):
        """Test checking API drift."""
        # Create OpenAPI spec
        spec_file = tmp_path / 'openapi.yaml'
        spec_data = {
            'paths': {
                '/users': {
                    'get': {'summary': 'Get users'},
                    'post': {'summary': 'Create user'}
                }
            }
        }
        with open(spec_file, 'w') as f:
            yaml.dump(spec_data, f)
        
        # Create API file
        api_file = tmp_path / 'api.py'
        api_file.write_text("""
@app.route('/users', methods=['GET'])
def get_users():
    pass
# Missing POST /users endpoint
""")
        
        detector = DriftDetector(tmp_path)
        report = DriftReport(project_path=tmp_path)
        
        # Mock code analyzer
        mock_analysis = Mock()
        mock_analysis.functions = [
            Mock(name='get_users', decorators=['@app.route(\'/users\', methods=[\'GET\'])'])
        ]
        
        with patch.object(detector.code_analyzer, 'analyze_file', return_value=mock_analysis):
            detector._check_api_drift(report)
        
        # Should detect missing POST endpoint
        assert any(drift.description == "API endpoint POST /users not implemented" 
                  for drift in report.drifts)
    
    def test_check_documentation_drift(self, tmp_path):
        """Test checking documentation drift."""
        # Create README
        readme_file = tmp_path / 'README.md'
        readme_file.write_text("""
# Test Project

## Features
- Advanced search functionality
- Real-time notifications
- User authentication
""")
        
        # Create code file with only one feature
        code_file = tmp_path / 'auth.py'
        code_file.write_text("""
def authenticate_user(username, password):
    # User authentication implementation
    pass
""")
        
        detector = DriftDetector(tmp_path)
        report = DriftReport(project_path=tmp_path)
        
        detector._check_documentation_drift(report)
        
        # Should detect missing features
        drift_descriptions = [d.description for d in report.drifts]
        assert any("Advanced search functionality" in d for d in drift_descriptions)
        assert any("Real-time notifications" in d for d in drift_descriptions)
    
    def test_check_security_drift(self, tmp_path):
        """Test checking security drift."""
        detector = DriftDetector(tmp_path)
        report = DriftReport(project_path=tmp_path)
        
        # Mock security issues
        mock_issue = Mock(
            vulnerability_type="SQL Injection",
            severity="HIGH",
            file_path="test.py",
            line_number=10,
            description="Unsafe SQL query"
        )
        
        mock_analysis = Mock(security_issues=[mock_issue])
        
        with patch.object(detector.code_analyzer, 'analyze_project', return_value=mock_analysis):
            detector._check_security_drift(report)
        
        assert len(report.drifts) == 1
        drift = report.drifts[0]
        assert drift.drift_type == DriftType.SECURITY
        assert "SQL Injection" in drift.description
        assert drift.severity == "critical"
    
    def test_check_performance_drift(self, tmp_path):
        """Test checking performance drift."""
        # Create file with performance issues
        code_file = tmp_path / 'test.py'
        code_file.write_text("""
for item in items:
    result = db.query(f"SELECT * FROM table WHERE id = {item.id}")
    process(result)

async def async_function():
    with open('file.txt') as f:
        data = f.read()
""")
        
        detector = DriftDetector(tmp_path)
        report = DriftReport(project_path=tmp_path)
        
        detector._check_performance_drift(report)
        
        # Should detect N+1 query and sync I/O in async
        assert len(report.drifts) >= 2
        drift_types = [d.description for d in report.drifts]
        assert any("N+1 query pattern" in d for d in drift_types)
        assert any("Synchronous I/O" in d for d in drift_types)
    
    def test_full_drift_check(self, tmp_path):
        """Test complete drift check."""
        # Create minimal project structure
        (tmp_path / 'README.md').write_text("# Test Project")
        (tmp_path / 'test.py').write_text("print('test')")
        
        detector = DriftDetector(tmp_path)
        report = detector.check_drift()
        
        assert isinstance(report, DriftReport)
        assert report.project_path == tmp_path
        # May or may not find drifts depending on project structure
    
    def test_check_file_drift(self, tmp_path):
        """Test checking drift for specific file."""
        # Create test file
        test_file = tmp_path / 'api.py'
        test_file.write_text("""
def get_users():
    pass
""")
        
        detector = DriftDetector(tmp_path)
        
        # Mock analysis
        mock_analysis = Mock()
        mock_analysis.metrics = Mock(average_complexity=15)  # High complexity
        mock_analysis.security_issues = []
        
        with patch.object(detector.code_analyzer, 'analyze_file', return_value=mock_analysis):
            report = detector.check_file_drift(test_file)
        
        assert report.files_checked == 1
        # Should detect high complexity
        assert any(d.drift_type == DriftType.PERFORMANCE for d in report.drifts)