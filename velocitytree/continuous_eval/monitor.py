"""
Background monitoring process for continuous code evaluation.
Watches for file changes and triggers analysis.
"""

import asyncio
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..utils import logger
from ..code_analysis.analyzer import CodeAnalyzer
from ..documentation.generator import DocGenerator
from .drift_detector import DriftDetector
from .alert_system import AlertSystem, Alert, AlertType, AlertSeverity


@dataclass
class MonitorConfig:
    """Configuration for continuous monitoring."""
    watch_paths: List[Path] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=lambda: ['*.py', '*.js', '*.ts'])
    ignore_patterns: List[str] = field(default_factory=lambda: ['__pycache__', '.git', '*.pyc'])
    check_interval: float = 5.0  # seconds
    batch_delay: float = 2.0  # seconds to wait for batch processing
    enable_drift_detection: bool = True
    enable_quality_alerts: bool = True
    enable_documentation_check: bool = True
    alert_threshold: float = 0.7  # minimum severity to trigger alerts
    cpu_limit: float = 0.05  # 5% CPU usage limit


class FileChangeHandler(FileSystemEventHandler):
    """Handles file system events for monitoring."""
    
    def __init__(self, monitor: 'ContinuousMonitor'):
        self.monitor = monitor
        self.pending_changes = {}
        
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, 'modified')
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, 'created')
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events."""
        if not event.is_directory:
            self._handle_file_change(event.src_path, 'deleted')
    
    def _handle_file_change(self, file_path: str, change_type: str):
        """Process a file change event."""
        path = Path(file_path)
        
        # Check if file matches patterns
        if not self._should_monitor_file(path):
            return
        
        # Add to pending changes
        self.pending_changes[path] = {
            'type': change_type,
            'timestamp': datetime.now()
        }
        
        # Schedule batch processing
        self.monitor._schedule_batch_processing()
    
    def _should_monitor_file(self, path: Path) -> bool:
        """Check if file should be monitored."""
        # Check ignore patterns
        for pattern in self.monitor.config.ignore_patterns:
            if path.match(pattern):
                return False
        
        # Check file patterns
        for pattern in self.monitor.config.file_patterns:
            if path.match(pattern):
                return True
        
        return False


class ContinuousMonitor:
    """Continuous monitoring system for code evaluation."""
    
    def __init__(
        self,
        config: Optional[MonitorConfig] = None,
        code_analyzer: Optional[CodeAnalyzer] = None,
        drift_detector: Optional[DriftDetector] = None,
        alert_system: Optional[AlertSystem] = None
    ):
        """Initialize continuous monitor.
        
        Args:
            config: Monitoring configuration
            code_analyzer: Code analysis instance
            drift_detector: Drift detection instance
            alert_system: Alert system instance
        """
        self.config = config or MonitorConfig()
        self.code_analyzer = code_analyzer or CodeAnalyzer()
        self.drift_detector = drift_detector or DriftDetector()
        self.alert_system = alert_system or AlertSystem()
        
        # Monitoring state
        self.observer = Observer()
        self.handler = FileChangeHandler(self)
        self.running = False
        self.batch_timer = None
        self.file_hashes = {}
        self.last_analysis = {}
        
        # Performance tracking
        self.cpu_usage = 0.0
        self.analysis_count = 0
        self.start_time = None
        
        # Callbacks
        self.on_change_callbacks = []
        self.on_alert_callbacks = []
    
    def start(self):
        """Start the monitoring process."""
        if self.running:
            logger.warning("Monitor already running")
            return
        
        logger.info("Starting continuous monitoring")
        self.running = True
        self.start_time = datetime.now()
        
        # Set up file watching
        for path in self.config.watch_paths:
            self.observer.schedule(
                self.handler,
                str(path),
                recursive=True
            )
        
        self.observer.start()
        
        # Start background analysis thread
        self.analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True
        )
        self.analysis_thread.start()
    
    def stop(self):
        """Stop the monitoring process."""
        logger.info("Stopping continuous monitoring")
        self.running = False
        
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
        
        if self.batch_timer:
            self.batch_timer.cancel()
    
    def add_watch_path(self, path: Path):
        """Add a path to monitor.
        
        Args:
            path: Path to monitor
        """
        if path not in self.config.watch_paths:
            self.config.watch_paths.append(path)
            
            if self.running:
                self.observer.schedule(
                    self.handler,
                    str(path),
                    recursive=True
                )
    
    def remove_watch_path(self, path: Path):
        """Remove a path from monitoring.
        
        Args:
            path: Path to stop monitoring
        """
        if path in self.config.watch_paths:
            self.config.watch_paths.remove(path)
            # Note: watchdog doesn't support unscheduling individual paths
    
    def register_change_callback(self, callback: Callable):
        """Register callback for file changes.
        
        Args:
            callback: Function to call on changes
        """
        self.on_change_callbacks.append(callback)
    
    def register_alert_callback(self, callback: Callable):
        """Register callback for alerts.
        
        Args:
            callback: Function to call on alerts
        """
        self.on_alert_callbacks.append(callback)
    
    def _schedule_batch_processing(self):
        """Schedule batch processing of pending changes."""
        if self.batch_timer:
            self.batch_timer.cancel()
        
        self.batch_timer = threading.Timer(
            self.config.batch_delay,
            self._process_batch
        )
        self.batch_timer.start()
    
    def _process_batch(self):
        """Process batch of pending file changes."""
        if not self.handler.pending_changes:
            return
        
        # Get pending changes
        changes = dict(self.handler.pending_changes)
        self.handler.pending_changes.clear()
        
        # Process each change
        for path, change_info in changes.items():
            try:
                self._process_file_change(path, change_info)
            except Exception as e:
                logger.error(f"Error processing {path}: {e}")
        
        # Notify callbacks
        for callback in self.on_change_callbacks:
            try:
                callback(changes)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def _process_file_change(self, path: Path, change_info: Dict[str, Any]):
        """Process a single file change.
        
        Args:
            path: File path that changed
            change_info: Change information
        """
        change_type = change_info['type']
        
        if change_type == 'deleted':
            # Remove from tracking
            if path in self.file_hashes:
                del self.file_hashes[path]
            if path in self.last_analysis:
                del self.last_analysis[path]
            return
        
        # Check if file actually changed (content-wise)
        if not self._has_content_changed(path):
            return
        
        # Analyze the file
        analysis_start = datetime.now()
        
        try:
            # Code analysis
            if self.config.enable_quality_alerts:
                analysis = self.code_analyzer.analyze_file(path)
                if analysis:
                    self._check_quality_alerts(path, analysis)
                    self.last_analysis[path] = analysis
            
            # Drift detection
            if self.config.enable_drift_detection:
                drift_report = self.drift_detector.check_file_drift(path)
                if drift_report:
                    self._check_drift_alerts(path, drift_report)
            
            # Documentation check
            if self.config.enable_documentation_check:
                self._check_documentation(path)
            
            # Update performance metrics
            duration = (datetime.now() - analysis_start).total_seconds()
            self._update_performance_metrics(duration)
            
        except Exception as e:
            logger.error(f"Analysis error for {path}: {e}")
            self._create_error_alert(path, str(e))
    
    def _has_content_changed(self, path: Path) -> bool:
        """Check if file content has changed.
        
        Args:
            path: File path to check
            
        Returns:
            True if content changed
        """
        if not path.exists():
            return False
        
        try:
            content = path.read_bytes()
            current_hash = hashlib.sha256(content).hexdigest()
            
            if path in self.file_hashes:
                previous_hash = self.file_hashes[path]
                if current_hash == previous_hash:
                    return False
            
            self.file_hashes[path] = current_hash
            return True
            
        except Exception as e:
            logger.error(f"Error checking file hash: {e}")
            return True
    
    def _check_quality_alerts(self, path: Path, analysis: Any):
        """Check for quality-related alerts.
        
        Args:
            path: File path
            analysis: Code analysis results
        """
        alerts = []
        
        # Check for high complexity
        if hasattr(analysis, 'metrics') and analysis.metrics:
            if analysis.metrics.cyclomatic_complexity > 15:
                alerts.append(Alert(
                    alert_type=AlertType.QUALITY,
                    severity=AlertSeverity.WARNING,
                    message=f"High complexity in {path.name}",
                    details={
                        'complexity': analysis.metrics.cyclomatic_complexity,
                        'threshold': 15
                    },
                    file_path=path
                ))
        
        # Check for security issues
        security_issues = [
            issue for issue in getattr(analysis, 'issues', [])
            if hasattr(issue, 'category') and issue.category == 'security'
        ]
        
        if security_issues:
            alerts.append(Alert(
                alert_type=AlertType.SECURITY,
                severity=AlertSeverity.HIGH,
                message=f"Security issues found in {path.name}",
                details={
                    'issue_count': len(security_issues),
                    'issues': [issue.message for issue in security_issues[:3]]
                },
                file_path=path
            ))
        
        # Send alerts
        for alert in alerts:
            if alert.severity.value >= self.config.alert_threshold:
                self.alert_system.send_alert(alert)
                self._notify_alert_callbacks(alert)
    
    def _check_drift_alerts(self, path: Path, drift_report: Any):
        """Check for specification drift alerts.
        
        Args:
            path: File path
            drift_report: Drift detection report
        """
        if drift_report.severity > self.config.alert_threshold:
            alert = Alert(
                alert_type=AlertType.DRIFT,
                severity=AlertSeverity.from_value(drift_report.severity),
                message=f"Specification drift detected in {path.name}",
                details={
                    'drift_type': drift_report.drift_type,
                    'description': drift_report.description,
                    'suggestions': drift_report.suggestions[:3]
                },
                file_path=path
            )
            
            self.alert_system.send_alert(alert)
            self._notify_alert_callbacks(alert)
    
    def _check_documentation(self, path: Path):
        """Check documentation status.
        
        Args:
            path: File path
        """
        # Simple documentation check
        try:
            content = path.read_text()
            
            # Check for missing docstrings
            if content.count('def ') > content.count('"""'):
                alert = Alert(
                    alert_type=AlertType.DOCUMENTATION,
                    severity=AlertSeverity.LOW,
                    message=f"Missing docstrings in {path.name}",
                    details={
                        'functions': content.count('def '),
                        'docstrings': content.count('"""') // 2
                    },
                    file_path=path
                )
                
                if alert.severity.value >= self.config.alert_threshold:
                    self.alert_system.send_alert(alert)
                    self._notify_alert_callbacks(alert)
                    
        except Exception as e:
            logger.error(f"Documentation check error: {e}")
    
    def _create_error_alert(self, path: Path, error: str):
        """Create an error alert.
        
        Args:
            path: File path
            error: Error message
        """
        alert = Alert(
            alert_type=AlertType.ERROR,
            severity=AlertSeverity.HIGH,
            message=f"Analysis error for {path.name}",
            details={'error': error},
            file_path=path
        )
        
        self.alert_system.send_alert(alert)
        self._notify_alert_callbacks(alert)
    
    def _notify_alert_callbacks(self, alert: Alert):
        """Notify alert callbacks.
        
        Args:
            alert: Alert to send
        """
        for callback in self.on_alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def _update_performance_metrics(self, duration: float):
        """Update performance tracking metrics.
        
        Args:
            duration: Analysis duration in seconds
        """
        self.analysis_count += 1
        
        # Simple CPU usage estimation
        if self.start_time:
            total_runtime = (datetime.now() - self.start_time).total_seconds()
            if total_runtime > 0:
                active_time = self.analysis_count * duration
                self.cpu_usage = active_time / total_runtime
                
                # Check CPU limit
                if self.cpu_usage > self.config.cpu_limit:
                    logger.warning(f"CPU usage {self.cpu_usage:.1%} exceeds limit")
    
    def _analysis_loop(self):
        """Background analysis loop."""
        while self.running:
            try:
                # Periodic health check
                self._health_check()
                
                # Sleep between checks
                asyncio.run(asyncio.sleep(self.config.check_interval))
                
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
    
    def _health_check(self):
        """Perform health check of monitoring system."""
        # Check observer status
        if not self.observer.is_alive():
            logger.error("Observer thread died, restarting")
            self.observer = Observer()
            self.start()
        
        # Check memory usage
        if self.analysis_count > 1000:
            # Clean up old data
            self._cleanup_old_data()
    
    def _cleanup_old_data(self):
        """Clean up old analysis data."""
        # Remove data for non-existent files
        for path in list(self.file_hashes.keys()):
            if not path.exists():
                del self.file_hashes[path]
                if path in self.last_analysis:
                    del self.last_analysis[path]
        
        self.analysis_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring system status.
        
        Returns:
            Status information
        """
        return {
            'running': self.running,
            'files_monitored': len(self.file_hashes),
            'analysis_count': self.analysis_count,
            'cpu_usage': self.cpu_usage,
            'watch_paths': [str(p) for p in self.config.watch_paths],
            'alert_count': self.alert_system.get_alert_count() if self.alert_system else 0,
            'uptime': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        }