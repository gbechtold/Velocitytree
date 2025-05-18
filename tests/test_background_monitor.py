"""
Tests for background monitoring functionality.
"""

import time
import json
import threading
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from velocitytree.monitoring import BackgroundMonitor, MonitoringConfig, MonitoringStatus


class TestBackgroundMonitor:
    """Test cases for BackgroundMonitor."""
    
    def test_init(self, tmp_path):
        """Test monitor initialization."""
        config = MonitoringConfig(check_interval=60)
        monitor = BackgroundMonitor(tmp_path, config)
        
        assert monitor.project_path == tmp_path
        assert monitor.config.check_interval == 60
        assert monitor.status == MonitoringStatus.IDLE
    
    def test_start_stop(self, tmp_path):
        """Test starting and stopping monitor."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Start monitor
        monitor.start()
        assert monitor.status == MonitoringStatus.RUNNING
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # Stop monitor
        monitor.stop()
        # Give thread time to stop
        time.sleep(0.1)
        assert monitor.status == MonitoringStatus.STOPPED
        assert not monitor.monitor_thread.is_alive()
    
    def test_double_start(self, tmp_path):
        """Test starting monitor when already running."""
        monitor = BackgroundMonitor(tmp_path)
        
        monitor.start()
        # Starting again should not create new thread
        original_thread = monitor.monitor_thread
        monitor.start()
        assert monitor.monitor_thread == original_thread
        
        monitor.stop()
    
    def test_monitor_loop_error_handling(self, tmp_path):
        """Test error handling in monitor loop."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Mock perform_check to raise error
        with patch.object(monitor, '_perform_check', side_effect=Exception("Test error")):
            monitor.start()
            time.sleep(0.1)  # Let it run one check
            
            # Should still be running despite error
            assert monitor.status == MonitoringStatus.RUNNING
            
            monitor.stop()
    
    @patch('velocitytree.monitoring.monitor.CodeAnalyzer')
    def test_initialize_baselines(self, mock_analyzer, tmp_path):
        """Test baseline initialization."""
        # Setup mocks
        mock_analysis = Mock()
        mock_analysis.metrics.average_complexity = 5.0
        mock_analysis.metrics.maintainability_index = 80.0
        mock_analysis.metrics.test_coverage = 75.0
        mock_analysis.metrics.documentation_coverage = 60.0
        
        mock_analyzer.return_value.analyze_project.return_value = mock_analysis
        
        monitor = BackgroundMonitor(tmp_path)
        monitor._initialize_baselines()
        
        assert 'code_metrics' in monitor.baselines
        assert monitor.baselines['code_metrics']['complexity'] == 5.0
        assert monitor.baselines['code_metrics']['maintainability'] == 80.0
    
    def test_check_git_state(self, tmp_path):
        """Test git state monitoring."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Setup baseline
        monitor.baselines['git_state'] = {
            'current_branch': 'main',
            'last_commit': 'abc123',
            'file_count': 10
        }
        
        # Mock git manager
        with patch.object(monitor.git_manager, 'current_branch', 'feature'):
            with patch.object(monitor.git_manager, 'get_latest_commit', return_value='def456'):
                with patch.object(monitor.git_manager, 'has_uncommitted_changes', return_value=True):
                    monitor._check_git_state()
        
        # Should have detected branch change, new commits, and uncommitted changes
        assert len(monitor.issues) >= 3
        assert any(issue['type'] == 'git_branch_change' for issue in monitor.issues)
        assert any(issue['type'] == 'git_new_commits' for issue in monitor.issues)
        assert any(issue['type'] == 'git_uncommitted_changes' for issue in monitor.issues)
    
    @patch('velocitytree.monitoring.monitor.CodeAnalyzer')
    def test_check_code_quality(self, mock_analyzer, tmp_path):
        """Test code quality monitoring."""
        # Setup baseline
        monitor = BackgroundMonitor(tmp_path)
        monitor.baselines['code_metrics'] = {
            'complexity': 5.0,
            'maintainability': 80.0,
            'test_coverage': 75.0,
            'documentation_coverage': 60.0
        }
        
        # Setup mock for degraded metrics
        mock_analysis = Mock()
        mock_analysis.metrics.average_complexity = 6.0  # 20% increase
        mock_analysis.metrics.maintainability_index = 70.0  # 12.5% decrease
        mock_analysis.metrics.test_coverage = 65.0  # 10% decrease
        mock_analysis.metrics.documentation_coverage = 60.0
        mock_analysis.security_issues = []
        
        mock_analyzer.return_value.analyze_project.return_value = mock_analysis
        
        monitor._check_code_quality()
        
        # Should detect complexity increase, maintainability decrease, and coverage decrease
        assert len(monitor.issues) >= 3
        assert any(issue['type'] == 'code_complexity_increase' for issue in monitor.issues)
        assert any(issue['type'] == 'code_maintainability_decrease' for issue in monitor.issues)
        assert any(issue['type'] == 'test_coverage_decrease' for issue in monitor.issues)
    
    @patch('velocitytree.monitoring.monitor.psutil')
    def test_measure_performance(self, mock_psutil, tmp_path):
        """Test performance measurement."""
        # Setup mocks
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100 MB
        mock_process.cpu_percent.return_value = 25.0
        mock_psutil.Process.return_value = mock_process
        
        monitor = BackgroundMonitor(tmp_path)
        perf = monitor._measure_performance()
        
        assert perf['memory_usage'] == 100.0
        assert perf['cpu_percent'] == 25.0
        assert 'file_io_time' in perf
    
    def test_add_issue(self, tmp_path):
        """Test adding issues."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Add test issue
        monitor._add_issue(
            'test_issue',
            'Test description',
            severity='warning',
            details={'key': 'value'}
        )
        
        assert len(monitor.issues) == 1
        issue = monitor.issues[0]
        assert issue['type'] == 'test_issue'
        assert issue['description'] == 'Test description'
        assert issue['severity'] == 'warning'
        assert issue['details']['key'] == 'value'
        assert monitor.metrics.issues_detected == 1
    
    def test_send_alert(self, tmp_path):
        """Test alert sending."""
        monitor = BackgroundMonitor(tmp_path)
        
        monitor._send_alert(5)
        
        assert monitor.metrics.alerts_sent == 1
        
        # Check alert file was created
        alert_file = tmp_path / '.velocitytree' / 'alerts.log'
        assert alert_file.exists()
        
        content = alert_file.read_text()
        assert 'Monitoring alert: 5 new issues detected' in content
    
    def test_save_metrics(self, tmp_path):
        """Test metrics saving."""
        config = MonitoringConfig(
            metrics_file=tmp_path / 'metrics.json'
        )
        monitor = BackgroundMonitor(tmp_path, config)
        
        # Add some test data
        monitor.metrics.checks_completed = 10
        monitor.metrics.issues_detected = 3
        monitor._add_issue('test1', 'Test 1', severity='info')
        monitor._add_issue('test2', 'Test 2', severity='warning')
        monitor._add_issue('test3', 'Test 3', severity='error')
        
        monitor._save_metrics()
        
        # Check file was created
        assert config.metrics_file.exists()
        
        # Check content
        with open(config.metrics_file) as f:
            data = json.load(f)
        
        assert data['metrics']['checks_completed'] == 10
        assert data['metrics']['issues_detected'] == 3
        assert data['issues_summary']['total'] == 3
        assert data['issues_summary']['by_severity']['info'] == 1
        assert data['issues_summary']['by_severity']['warning'] == 1
        assert data['issues_summary']['by_severity']['error'] == 1
    
    def test_get_status(self, tmp_path):
        """Test getting monitor status."""
        config = MonitoringConfig(
            check_interval=300,
            alert_threshold=5
        )
        monitor = BackgroundMonitor(tmp_path, config)
        
        # Add test data
        monitor.metrics.checks_completed = 5
        monitor._add_issue('test', 'Test issue')
        
        status = monitor.get_status()
        
        assert status['status'] == 'idle'
        assert status['metrics']['checks_completed'] == 5
        assert status['config']['check_interval'] == 300
        assert status['config']['alert_threshold'] == 5
        assert len(status['recent_issues']) == 1
    
    def test_get_issues_filtered(self, tmp_path):
        """Test getting filtered issues."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Add issues with different severities
        monitor._add_issue('test1', 'Test 1', severity='info')
        monitor._add_issue('test2', 'Test 2', severity='warning')
        monitor._add_issue('test3', 'Test 3', severity='error')
        monitor._add_issue('test4', 'Test 4', severity='warning')
        
        # Get all issues
        all_issues = monitor.get_issues()
        assert len(all_issues) == 4
        
        # Get filtered issues
        warnings = monitor.get_issues(severity='warning')
        assert len(warnings) == 2
        assert all(issue['severity'] == 'warning' for issue in warnings)


class TestMonitoringConfig:
    """Test cases for MonitoringConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MonitoringConfig()
        
        assert config.check_interval == 300
        assert config.enable_git_monitoring is True
        assert config.enable_code_monitoring is True
        assert config.enable_performance_monitoring is True
        assert config.enable_drift_detection is True
        assert config.alert_threshold == 3
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = MonitoringConfig(
            check_interval=600,
            enable_git_monitoring=False,
            alert_threshold=5
        )
        
        assert config.check_interval == 600
        assert config.enable_git_monitoring is False
        assert config.alert_threshold == 5


class TestMonitoringIntegration:
    """Integration tests for monitoring system."""
    
    def test_full_monitoring_cycle(self, tmp_path):
        """Test complete monitoring cycle."""
        # Create test project structure
        code_file = tmp_path / "test.py"
        code_file.write_text("def test(): pass")
        
        config = MonitoringConfig(
            check_interval=0.1,  # Very short for testing
            metrics_file=tmp_path / 'metrics.json'
        )
        monitor = BackgroundMonitor(tmp_path, config)
        
        # Start monitoring
        monitor.start()
        
        # Let it run a few checks
        time.sleep(0.5)
        
        # Stop monitoring
        monitor.stop()
        
        # Verify metrics were updated
        assert monitor.metrics.checks_completed > 0
        assert config.metrics_file.exists()
        
        # Verify status
        status = monitor.get_status()
        assert status['status'] == 'stopped'
        assert status['metrics']['checks_completed'] > 0
    
    def test_performance_degradation_detection(self, tmp_path):
        """Test detection of performance degradation."""
        monitor = BackgroundMonitor(tmp_path)
        
        # Setup baseline
        monitor.baselines['performance'] = {
            'file_io_time': 0.1,
            'memory_usage': 100.0
        }
        
        # Mock degraded performance
        with patch.object(monitor, '_measure_performance') as mock_measure:
            mock_measure.return_value = {
                'file_io_time': 0.2,  # 100% increase
                'memory_usage': 150.0,  # 50% increase
                'cpu_percent': 50.0
            }
            
            monitor._check_performance()
        
        # Should detect both degradations
        assert len(monitor.issues) >= 2
        assert any(issue['type'] == 'performance_file_io' for issue in monitor.issues)
        assert any(issue['type'] == 'performance_memory' for issue in monitor.issues)
        assert monitor.metrics.performance_degradations >= 2