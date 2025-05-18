"""
Background monitoring process for Velocitytree.
"""

import time
import threading
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ..utils import logger
from ..git_manager import GitManager
from ..code_analysis import CodeAnalyzer
from ..progress_tracking import ProgressTracker
from .drift_detector import DriftDetector
from .alert_system import AlertManager, Alert, AlertSeverity, AlertConfig


class MonitoringStatus(Enum):
    """Status of the monitoring process."""
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class MonitoringConfig:
    """Configuration for the monitoring process."""
    check_interval: int = 300  # 5 minutes
    enable_git_monitoring: bool = True
    enable_code_monitoring: bool = True
    enable_performance_monitoring: bool = True
    enable_drift_detection: bool = True
    alert_threshold: int = 3  # Number of issues before alerting
    log_file: Optional[Path] = None
    metrics_file: Optional[Path] = None
    alert_config: Optional[AlertConfig] = None


@dataclass
class MonitoringMetrics:
    """Metrics collected by the monitoring process."""
    last_check: datetime = field(default_factory=datetime.now)
    checks_completed: int = 0
    issues_detected: int = 0
    alerts_sent: int = 0
    code_changes: int = 0
    performance_degradations: int = 0
    drift_detections: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'last_check': self.last_check.isoformat(),
            'checks_completed': self.checks_completed,
            'issues_detected': self.issues_detected,
            'alerts_sent': self.alerts_sent,
            'code_changes': self.code_changes,
            'performance_degradations': self.performance_degradations,
            'drift_detections': self.drift_detections
        }


class BackgroundMonitor:
    """Background monitoring process for code quality and project health."""
    
    def __init__(self, project_path: Path, config: Optional[MonitoringConfig] = None):
        self.project_path = project_path
        self.config = config or MonitoringConfig()
        self.status = MonitoringStatus.IDLE
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Initialize components
        self.git_manager = GitManager(project_path)
        self.code_analyzer = CodeAnalyzer()
        self.progress_tracker = ProgressTracker()
        self.drift_detector = DriftDetector(project_path)
        
        # Initialize alert manager
        alert_config = self.config.alert_config or AlertConfig(
            alert_file=project_path / '.velocitytree' / 'alerts.json'
        )
        self.alert_manager = AlertManager(alert_config)
        
        # Monitoring state
        self.metrics = MonitoringMetrics()
        self.issues: List[Dict[str, Any]] = []
        self.baselines: Dict[str, Any] = {}
        
        # Initialize log file
        if self.config.log_file:
            self.config.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def start(self):
        """Start the background monitoring process."""
        if self.status == MonitoringStatus.RUNNING:
            logger.info("Monitor is already running")
            return
        
        self.status = MonitoringStatus.RUNNING
        self.stop_event.clear()
        
        # Initialize baselines
        self._initialize_baselines()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Background monitor started")
    
    def stop(self):
        """Stop the background monitoring process."""
        if self.status != MonitoringStatus.RUNNING:
            logger.info("Monitor is not running")
            return
        
        self.status = MonitoringStatus.STOPPED
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        logger.info("Background monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop running in background thread."""
        while not self.stop_event.is_set():
            try:
                # Perform monitoring check
                self._perform_check()
                
                # Save metrics
                self._save_metrics()
                
                # Wait for next check
                self.stop_event.wait(self.config.check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.status = MonitoringStatus.ERROR
                self.stop_event.wait(30)  # Wait before retry
    
    def _initialize_baselines(self):
        """Initialize baseline metrics for comparison."""
        try:
            # Code metrics baseline
            if self.config.enable_code_monitoring:
                analysis = self.code_analyzer.analyze_project(self.project_path)
                self.baselines['code_metrics'] = {
                    'complexity': analysis.metrics.average_complexity,
                    'maintainability': analysis.metrics.maintainability_index,
                    'test_coverage': analysis.metrics.test_coverage,
                    'documentation_coverage': analysis.metrics.documentation_coverage
                }
            
            # Git baseline
            if self.config.enable_git_monitoring:
                self.baselines['git_state'] = {
                    'current_branch': self.git_manager.current_branch,
                    'last_commit': self.git_manager.get_latest_commit(),
                    'file_count': len(list(self.project_path.rglob('*')))
                }
            
            # Performance baseline
            if self.config.enable_performance_monitoring:
                self.baselines['performance'] = self._measure_performance()
            
            logger.info("Baselines initialized")
            
        except Exception as e:
            logger.error(f"Error initializing baselines: {e}")
    
    def _perform_check(self):
        """Perform a monitoring check across all enabled monitors."""
        logger.debug("Starting monitoring check")
        issues_before = len(self.issues)
        
        # Git monitoring
        if self.config.enable_git_monitoring:
            self._check_git_state()
        
        # Code quality monitoring
        if self.config.enable_code_monitoring:
            self._check_code_quality()
        
        # Performance monitoring
        if self.config.enable_performance_monitoring:
            self._check_performance()
        
        # Drift detection
        if self.config.enable_drift_detection:
            self._check_for_drift()
        
        # Update metrics
        self.metrics.checks_completed += 1
        self.metrics.last_check = datetime.now()
        
        # Check if we need to send alerts
        new_issues = len(self.issues) - issues_before
        if new_issues >= self.config.alert_threshold:
            self._send_alert(new_issues)
        
        logger.debug(f"Monitoring check completed. Found {new_issues} new issues")
    
    def _check_git_state(self):
        """Check for git state changes."""
        try:
            current_state = {
                'current_branch': self.git_manager.current_branch,
                'last_commit': self.git_manager.get_latest_commit(),
                'has_uncommitted': self.git_manager.has_uncommitted_changes()
            }
            
            baseline = self.baselines.get('git_state', {})
            
            # Check for branch changes
            if current_state['current_branch'] != baseline.get('current_branch'):
                self._add_issue(
                    'git_branch_change',
                    f"Branch changed from {baseline.get('current_branch')} to {current_state['current_branch']}",
                    severity='info'
                )
            
            # Check for new commits
            if current_state['last_commit'] != baseline.get('last_commit'):
                self._add_issue(
                    'git_new_commits',
                    f"New commits detected since last check",
                    severity='info'
                )
                self.metrics.code_changes += 1
            
            # Check for uncommitted changes
            if current_state['has_uncommitted']:
                self._add_issue(
                    'git_uncommitted_changes',
                    "Uncommitted changes detected",
                    severity='warning'
                )
            
        except Exception as e:
            logger.error(f"Error checking git state: {e}")
    
    def _check_code_quality(self):
        """Check for code quality changes."""
        try:
            # Analyze current code
            analysis = self.code_analyzer.analyze_project(self.project_path)
            current_metrics = {
                'complexity': analysis.metrics.average_complexity,
                'maintainability': analysis.metrics.maintainability_index,
                'test_coverage': analysis.metrics.test_coverage,
                'documentation_coverage': analysis.metrics.documentation_coverage
            }
            
            baseline = self.baselines.get('code_metrics', {})
            
            # Check for complexity increase
            if current_metrics['complexity'] > baseline.get('complexity', 0) * 1.1:
                self._add_issue(
                    'code_complexity_increase',
                    f"Code complexity increased by {((current_metrics['complexity'] / baseline.get('complexity', 1)) - 1) * 100:.1f}%",
                    severity='warning'
                )
            
            # Check for maintainability decrease
            if current_metrics['maintainability'] < baseline.get('maintainability', 100) * 0.9:
                self._add_issue(
                    'code_maintainability_decrease',
                    f"Maintainability index decreased by {(1 - (current_metrics['maintainability'] / baseline.get('maintainability', 1))) * 100:.1f}%",
                    severity='warning'
                )
            
            # Check for test coverage decrease
            if current_metrics['test_coverage'] < baseline.get('test_coverage', 0) - 5:
                self._add_issue(
                    'test_coverage_decrease',
                    f"Test coverage decreased from {baseline.get('test_coverage', 0):.1f}% to {current_metrics['test_coverage']:.1f}%",
                    severity='error'
                )
            
            # Check for security issues
            if analysis.security_issues:
                for issue in analysis.security_issues:
                    self._add_issue(
                        'security_vulnerability',
                        f"Security issue: {issue.vulnerability_type} in {issue.file_path}:{issue.line_number}",
                        severity='critical',
                        details=issue.to_dict()
                    )
            
        except Exception as e:
            logger.error(f"Error checking code quality: {e}")
    
    def _check_performance(self):
        """Check for performance degradations."""
        try:
            current_perf = self._measure_performance()
            baseline_perf = self.baselines.get('performance', {})
            
            # Check file I/O performance
            if current_perf['file_io_time'] > baseline_perf.get('file_io_time', 0) * 1.5:
                self._add_issue(
                    'performance_file_io',
                    f"File I/O performance degraded by {((current_perf['file_io_time'] / baseline_perf.get('file_io_time', 1)) - 1) * 100:.1f}%",
                    severity='warning'
                )
                self.metrics.performance_degradations += 1
            
            # Check memory usage
            if current_perf['memory_usage'] > baseline_perf.get('memory_usage', 0) * 1.2:
                self._add_issue(
                    'performance_memory',
                    f"Memory usage increased by {((current_perf['memory_usage'] / baseline_perf.get('memory_usage', 1)) - 1) * 100:.1f}%",
                    severity='warning'
                )
                self.metrics.performance_degradations += 1
            
        except Exception as e:
            logger.error(f"Error checking performance: {e}")
    
    def _check_for_drift(self):
        """Check for project drift from specifications."""
        try:
            # Run drift detection
            drift_report = self.drift_detector.check_drift()
            
            # Process drift items
            for drift_item in drift_report.drifts:
                # Add as monitoring issue
                self._add_issue(
                    f'drift_{drift_item.drift_type.value}',
                    drift_item.description,
                    severity=drift_item.severity,
                    details={
                        'drift_type': drift_item.drift_type.value,
                        'file_path': str(drift_item.file_path) if drift_item.file_path else None,
                        'line_number': drift_item.line_number,
                        'expected': drift_item.expected,
                        'actual': drift_item.actual,
                        'spec_reference': drift_item.spec_reference
                    }
                )
                self.metrics.drift_detections += 1
            
            # Log summary
            summary = drift_report.to_dict()['summary']
            if summary['total_drifts'] > 0:
                logger.info(f"Drift detection found {summary['total_drifts']} issues")
                logger.info(f"By type: {summary['by_type']}")
                logger.info(f"By severity: {summary['by_severity']}")
            
        except Exception as e:
            logger.error(f"Error checking for drift: {e}")
    
    def _measure_performance(self) -> Dict[str, float]:
        """Measure current performance metrics."""
        import psutil
        import time
        
        # File I/O performance
        start_time = time.time()
        list(self.project_path.rglob('*.py'))
        file_io_time = time.time() - start_time
        
        # Memory usage
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'file_io_time': file_io_time,
            'memory_usage': memory_usage,
            'cpu_percent': process.cpu_percent()
        }
    
    def _add_issue(self, issue_type: str, description: str, severity: str = 'info', details: Optional[Dict] = None):
        """Add an issue to the monitoring log."""
        issue = {
            'timestamp': datetime.now().isoformat(),
            'type': issue_type,
            'description': description,
            'severity': severity,
            'details': details or {}
        }
        
        self.issues.append(issue)
        self.metrics.issues_detected += 1
        
        # Log to file if configured
        if self.config.log_file:
            with open(self.config.log_file, 'a') as f:
                f.write(json.dumps(issue) + '\n')
        
        # Log based on severity
        if severity == 'critical':
            logger.error(f"CRITICAL: {description}")
            # Send immediate alert for critical issues
            self._send_specific_alert(issue)
        elif severity == 'error':
            logger.error(description)
        elif severity == 'warning':
            logger.warning(description)
        else:
            logger.info(description)
    
    def _send_specific_alert(self, issue: Dict[str, Any]):
        """Send alert for specific issue."""
        # Map issue severity to alert severity
        severity_map = {
            'critical': AlertSeverity.CRITICAL,
            'error': AlertSeverity.ERROR,
            'warning': AlertSeverity.WARNING,
            'info': AlertSeverity.INFO
        }
        
        alert = self.alert_manager.create_alert(
            severity=severity_map.get(issue['severity'], AlertSeverity.INFO),
            title=issue['description'][:100],
            description=issue['description'],
            source="BackgroundMonitor",
            category=issue['type'],
            details=issue.get('details', {})
        )
        
        if self.alert_manager.send_alert(alert):
            logger.debug(f"Specific alert sent: {alert.title}")
    
    def _send_alert(self, issue_count: int):
        """Send an alert for multiple issues."""
        # Create alert
        alert = self.alert_manager.create_alert(
            severity=AlertSeverity.WARNING,
            title=f"{issue_count} new monitoring issues detected",
            description=f"Background monitoring has detected {issue_count} new issues that require attention.",
            source="BackgroundMonitor",
            category="monitoring",
            details={
                'issue_count': issue_count,
                'recent_issues': self.issues[-issue_count:] if len(self.issues) >= issue_count else self.issues
            }
        )
        
        # Send alert
        if self.alert_manager.send_alert(alert):
            self.metrics.alerts_sent += 1
            logger.info(f"Alert sent: {alert.title}")
        else:
            logger.warning(f"Failed to send alert: {alert.title}")
    
    def _save_metrics(self):
        """Save metrics to file."""
        if self.config.metrics_file:
            self.config.metrics_file.parent.mkdir(parents=True, exist_ok=True)
            
            metrics_data = {
                'metrics': self.metrics.to_dict(),
                'issues_summary': {
                    'total': len(self.issues),
                    'by_severity': {}
                }
            }
            
            # Count issues by severity
            for issue in self.issues:
                severity = issue['severity']
                metrics_data['issues_summary']['by_severity'][severity] = \
                    metrics_data['issues_summary']['by_severity'].get(severity, 0) + 1
            
            with open(self.config.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            'status': self.status.value,
            'metrics': self.metrics.to_dict(),
            'config': {
                'check_interval': self.config.check_interval,
                'alert_threshold': self.config.alert_threshold,
                'enabled_monitors': {
                    'git': self.config.enable_git_monitoring,
                    'code': self.config.enable_code_monitoring,
                    'performance': self.config.enable_performance_monitoring,
                    'drift': self.config.enable_drift_detection
                }
            },
            'recent_issues': self.issues[-10:] if self.issues else []
        }
    
    def get_issues(self, severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get monitoring issues, optionally filtered by severity."""
        if severity:
            return [issue for issue in self.issues if issue['severity'] == severity]
        return self.issues.copy()