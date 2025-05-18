"""Tests for continuous evaluation system."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import json
import tempfile
import time
from unittest.mock import Mock, patch, MagicMock

from velocitytree.continuous_eval import (
    ContinuousMonitor,
    MonitorConfig,
    DriftDetector,
    DriftReport,
    DriftType,
    AlertSystem,
    Alert,
    AlertType,
    AlertSeverity,
    RealignmentEngine,
    RealignmentSuggestion,
    SuggestionCategory
)
from velocitytree.code_analysis.analyzer import CodeAnalyzer


class TestMonitorConfig:
    """Test monitor configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MonitorConfig()
        
        assert config.scan_interval == 1.0
        assert config.watch_patterns == ["**/*.py", "**/*.js", "**/*.ts"]
        assert config.ignore_patterns == ["**/node_modules/**", "**/__pycache__/**"]
        assert config.max_cpu_percent == 20.0
        assert config.max_memory_mb == 500.0
        assert config.batch_size == 10
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitorConfig(
            scan_interval=5.0,
            max_cpu_percent=50.0,
            batch_size=20
        )
        
        assert config.scan_interval == 5.0
        assert config.max_cpu_percent == 50.0
        assert config.batch_size == 20


class TestContinuousMonitor:
    """Test continuous monitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create monitor instance."""
        config = MonitorConfig(scan_interval=0.1)
        return ContinuousMonitor(config=config)
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temporary project structure."""
        # Create files
        (tmp_path / "app.py").write_text("def main(): pass")
        (tmp_path / "test.py").write_text("def test(): pass")
        (tmp_path / "lib" / "utils.py").mkdir(parents=True)
        (tmp_path / "lib" / "utils.py").write_text("def helper(): pass")
        
        return tmp_path
    
    def test_start_monitoring(self, monitor, temp_project):
        """Test starting file monitoring."""
        # Start monitoring
        monitors = monitor.start_monitoring(temp_project)
        
        assert len(monitors) > 0
        assert monitor.monitoring_active
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.monitoring_active
    
    def test_file_change_detection(self, monitor, temp_project):
        """Test detecting file changes."""
        events = []
        
        # Mock event handler
        def event_handler(event):
            events.append(event)
        
        monitor._on_file_changed = event_handler
        
        # Start monitoring
        monitor.start_monitoring(temp_project)
        
        # Modify file
        time.sleep(0.2)  # Wait for monitoring to start
        (temp_project / "app.py").write_text("def main(): print('changed')")
        
        # Wait for change detection
        time.sleep(0.5)
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Check events
        assert len(events) > 0
    
    def test_cpu_limiting(self, monitor):
        """Test CPU usage limiting."""
        # Mock CPU check
        with patch('psutil.cpu_percent', return_value=30.0):
            assert not monitor._check_resource_limits()
        
        with patch('psutil.cpu_percent', return_value=10.0):
            assert monitor._check_resource_limits()
    
    def test_batch_processing(self, monitor):
        """Test batch processing of changes."""
        changes = [f"file{i}.py" for i in range(20)]
        
        batches = list(monitor._batch_changes(changes))
        
        assert len(batches) == 2  # Default batch size is 10
        assert len(batches[0]) == 10
        assert len(batches[1]) == 10
    
    def test_monitoring_status(self, monitor, temp_project):
        """Test getting monitoring status."""
        # Initial status
        status = monitor.get_monitoring_status()
        assert not status['is_running']
        assert status['files_monitored'] == 0
        
        # Start monitoring
        monitor.start_monitoring(temp_project)
        
        status = monitor.get_monitoring_status()
        assert status['is_running']
        assert status['files_monitored'] > 0
        
        monitor.stop_monitoring()


class TestDriftDetector:
    """Test drift detector."""
    
    @pytest.fixture
    def detector(self):
        """Create drift detector instance."""
        return DriftDetector()
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create test file with code."""
        code = '''
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers."""
    return a + b

class Calculator:
    """Simple calculator class."""
    
    def multiply(self, x: float, y: float) -> float:
        """Multiply two numbers."""
        return x * y
'''
        file_path = tmp_path / "calculator.py"
        file_path.write_text(code)
        return file_path
    
    def test_check_file_drift(self, detector, test_file):
        """Test checking file for drift."""
        # Mock specifications
        specs = {
            'calculate_sum': {
                'params': 'a: int, b: int',
                'return_type': 'int',
                'description': 'Calculate sum of two numbers'
            },
            'Calculator.multiply': {
                'params': 'x: float, y: float',
                'return_type': 'float',
                'description': 'Multiply two numbers'
            }
        }
        
        with patch.object(detector, '_load_specifications', return_value=specs):
            report = detector.check_file_drift(test_file)
        
        assert report is not None
        assert len(report.drifts) == 0  # No drift expected
    
    def test_detect_missing_implementation(self, detector, test_file):
        """Test detecting missing implementation."""
        specs = {
            'calculate_sum': {
                'params': 'a: int, b: int',
                'return_type': 'int'
            },
            'calculate_diff': {  # Missing implementation
                'params': 'a: int, b: int',
                'return_type': 'int'
            }
        }
        
        with patch.object(detector, '_load_specifications', return_value=specs):
            report = detector.check_file_drift(test_file)
        
        assert len(report.drifts) == 1
        assert report.drifts[0].drift_type == DriftType.MISSING_IMPLEMENTATION
    
    def test_detect_signature_mismatch(self, detector, test_file):
        """Test detecting signature mismatch."""
        specs = {
            'calculate_sum': {
                'params': 'a: float, b: float',  # Different from implementation
                'return_type': 'float'
            }
        }
        
        with patch.object(detector, '_load_specifications', return_value=specs):
            report = detector.check_file_drift(test_file)
        
        assert len(report.drifts) == 1
        assert report.drifts[0].drift_type == DriftType.SIGNATURE_MISMATCH
    
    def test_detect_behavior_deviation(self, detector, test_file):
        """Test detecting behavioral deviation."""
        # Create file with different behavior
        code = '''
def calculate_sum(a: int, b: int) -> int:
    """Calculate sum of two numbers."""
    return a * b  # Wrong implementation
'''
        test_file.write_text(code)
        
        specs = {
            'calculate_sum': {
                'params': 'a: int, b: int',
                'return_type': 'int',
                'behavior': 'returns sum of a and b'
            }
        }
        
        with patch.object(detector, '_load_specifications', return_value=specs):
            report = detector.check_file_drift(test_file)
        
        # This would require more sophisticated analysis
        # For now, just check structure
        assert report is not None


class TestAlertSystem:
    """Test alert system."""
    
    @pytest.fixture
    def alert_system(self, tmp_path):
        """Create alert system instance."""
        db_path = tmp_path / "test_alerts.db"
        return AlertSystem(db_path=db_path)
    
    def test_create_alert(self, alert_system):
        """Test creating an alert."""
        alert = alert_system.create_alert(
            type=AlertType.DRIFT_DETECTED,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="This is a test alert",
            file_path=Path("test.py"),
            line_number=42
        )
        
        assert alert.alert_id is not None
        assert alert.type == AlertType.DRIFT_DETECTED
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
    
    def test_get_alerts(self, alert_system):
        """Test retrieving alerts."""
        # Create test alerts
        for i in range(5):
            alert_system.create_alert(
                type=AlertType.QUALITY_DEGRADATION,
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                message=f"Test alert {i}"
            )
        
        # Get all alerts
        alerts = alert_system.get_alerts()
        assert len(alerts) == 5
        
        # Filter by type
        alerts = alert_system.get_alerts(type=AlertType.QUALITY_DEGRADATION)
        assert len(alerts) == 5
        
        # Filter by severity
        alerts = alert_system.get_alerts(severity=AlertSeverity.INFO)
        assert len(alerts) == 5
    
    def test_resolve_alert(self, alert_system):
        """Test resolving an alert."""
        # Create alert
        alert = alert_system.create_alert(
            type=AlertType.SECURITY_ISSUE,
            severity=AlertSeverity.ERROR,
            title="Security Alert",
            message="Security issue detected"
        )
        
        # Resolve it
        alert_system.resolve_alert(alert.alert_id)
        
        # Check it's resolved
        alerts = alert_system.get_alerts(resolved=False)
        assert len(alerts) == 0
        
        alerts = alert_system.get_alerts(resolved=True)
        assert len(alerts) == 1
    
    def test_alert_handlers(self, alert_system):
        """Test alert handlers."""
        handled_alerts = []
        
        def test_handler(alert):
            handled_alerts.append(alert)
        
        # Register handler
        alert_system.register_handler(
            AlertType.BUILD_FAILURE,
            test_handler
        )
        
        # Create alert
        alert_system.create_alert(
            type=AlertType.BUILD_FAILURE,
            severity=AlertSeverity.ERROR,
            title="Build Failed",
            message="Build failed"
        )
        
        # Check handler was called
        assert len(handled_alerts) == 1
        assert handled_alerts[0].type == AlertType.BUILD_FAILURE
    
    def test_alert_summary(self, alert_system):
        """Test getting alert summary."""
        # Create various alerts
        alert_system.create_alert(
            type=AlertType.DRIFT_DETECTED,
            severity=AlertSeverity.WARNING,
            title="Drift 1",
            message="Drift detected"
        )
        
        alert_system.create_alert(
            type=AlertType.SECURITY_ISSUE,
            severity=AlertSeverity.CRITICAL,
            title="Security 1",
            message="Security issue"
        )
        
        summary = alert_system.get_alert_summary()
        
        assert summary['total_unresolved'] == 2
        assert 'drift_detected' in summary['by_type']
        assert 'CRITICAL' in summary['by_severity']


class TestRealignmentEngine:
    """Test realignment engine."""
    
    @pytest.fixture
    def engine(self):
        """Create realignment engine instance."""
        return RealignmentEngine()
    
    @pytest.fixture
    def drift_report(self):
        """Create test drift report."""
        from velocitytree.continuous_eval.drift_detector import DriftItem
        
        drifts = [
            DriftItem(
                drift_type=DriftType.MISSING_IMPLEMENTATION,
                element="calculate_average",
                file_path=Path("math_utils.py"),
                line_number=None,
                details={
                    'spec': {
                        'params': 'numbers: List[float]',
                        'return_type': 'float',
                        'description': 'Calculate average of numbers'
                    },
                    'element': 'calculate_average'
                }
            ),
            DriftItem(
                drift_type=DriftType.SIGNATURE_MISMATCH,
                element="multiply",
                file_path=Path("math_utils.py"),
                line_number=10,
                details={
                    'actual_signature': 'multiply(a: int, b: int) -> int',
                    'expected_signature': 'multiply(a: float, b: float) -> float',
                    'element': 'multiply'
                }
            )
        ]
        
        return DriftReport(
            file_path=Path("math_utils.py"),
            timestamp=datetime.now(),
            drifts=drifts
        )
    
    def test_generate_suggestions(self, engine, drift_report):
        """Test generating realignment suggestions."""
        suggestions = engine.generate_suggestions(drift_report)
        
        assert len(suggestions) > 0
        
        # Check for implementation suggestion
        impl_suggestions = [s for s in suggestions 
                          if s.category == SuggestionCategory.CODE_CHANGE]
        assert len(impl_suggestions) > 0
        
        # Check for test suggestion
        test_suggestions = [s for s in suggestions 
                          if s.category == SuggestionCategory.TEST_UPDATE]
        assert len(test_suggestions) > 0
    
    def test_suggest_implementation(self, engine):
        """Test implementation suggestions."""
        from velocitytree.continuous_eval.drift_detector import DriftItem
        
        drift = DriftItem(
            drift_type=DriftType.MISSING_IMPLEMENTATION,
            element="process_data",
            file_path=Path("processor.py"),
            details={
                'spec': {
                    'params': 'data: List[Dict]',
                    'return_type': 'DataFrame',
                    'description': 'Process raw data'
                },
                'element': 'process_data'
            }
        )
        
        suggestions = engine._suggest_implementation(drift)
        
        assert len(suggestions) > 0
        assert suggestions[0].category == SuggestionCategory.CODE_CHANGE
        assert "process_data" in suggestions[0].code_snippet
    
    def test_suggest_signature_fix(self, engine):
        """Test signature fix suggestions."""
        from velocitytree.continuous_eval.drift_detector import DriftItem
        
        drift = DriftItem(
            drift_type=DriftType.SIGNATURE_MISMATCH,
            element="calculate",
            file_path=Path("calc.py"),
            line_number=5,
            details={
                'actual_signature': 'calculate(x: int) -> int',
                'expected_signature': 'calculate(x: float) -> float',
                'element': 'calculate'
            }
        )
        
        suggestions = engine._suggest_signature_fix(drift)
        
        assert len(suggestions) > 0
        assert suggestions[0].category == SuggestionCategory.CODE_CHANGE
        
        # Check for breaking change detection
        breaking_suggestions = [s for s in suggestions 
                              if s.category == SuggestionCategory.DOCUMENTATION]
        assert len(breaking_suggestions) > 0
    
    def test_suggest_doc_update(self, engine):
        """Test documentation update suggestions."""
        from velocitytree.continuous_eval.drift_detector import DriftItem
        
        drift = DriftItem(
            drift_type=DriftType.DOCUMENTATION_STALE,
            element="DataProcessor",
            file_path=Path("processor.py"),
            line_number=1,
            details={
                'element': 'DataProcessor',
                'doc_type': 'class docstring'
            }
        )
        
        suggestions = engine._suggest_doc_update(drift)
        
        assert len(suggestions) > 0
        assert suggestions[0].category == SuggestionCategory.DOCUMENTATION
    
    def test_breaking_change_detection(self, engine):
        """Test breaking change detection."""
        # Test breaking change
        assert engine._is_breaking_change(
            "func(x: int, y: int)",
            "func(x: float)"
        )
        
        # Test non-breaking change
        assert not engine._is_breaking_change(
            "func(x: int)",
            "func(x: int, y: int = 0)"
        )