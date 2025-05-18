"""Alert system for continuous evaluation."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import json
import sqlite3
from collections import defaultdict

class AlertType(Enum):
    """Types of alerts."""
    DRIFT_DETECTED = "drift_detected"
    QUALITY_DEGRADATION = "quality_degradation"
    SECURITY_ISSUE = "security_issue"
    PERFORMANCE_REGRESSION = "performance_regression"
    DEPENDENCY_UPDATE = "dependency_update"
    COMPLEXITY_INCREASE = "complexity_increase"
    COVERAGE_DROP = "coverage_drop"
    DOCUMENTATION_STALE = "documentation_stale"
    BUILD_FAILURE = "build_failure"
    TEST_FAILURE = "test_failure"

class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

@dataclass
class Alert:
    """Individual alert instance."""
    type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    alert_id: Optional[int] = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.context is None:
            self.context = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "type": self.type.value,
            "severity": self.severity.name,
            "title": self.title,
            "message": self.message,
            "file_path": str(self.file_path) if self.file_path else None,
            "line_number": self.line_number,
            "context": self.context,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "alert_id": self.alert_id
        }

class AlertSystem:
    """Manages alerts and notifications."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize alert system."""
        if db_path is None:
            db_path = Path.home() / ".velocitytree" / "alerts.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Alert handlers by type
        self.handlers: Dict[AlertType, List[Callable[[Alert], None]]] = defaultdict(list)
        
        # Initialize database
        self._init_database()
        
        # Set up default handlers
        self._setup_default_handlers()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    file_path TEXT,
                    line_number INTEGER,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN NOT NULL DEFAULT 0,
                    resolved_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_type 
                ON alerts(type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_severity 
                ON alerts(severity)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_resolved 
                ON alerts(resolved)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    def _setup_default_handlers(self):
        """Set up default alert handlers."""
        # Console handler for critical alerts
        self.register_handler(
            AlertType.SECURITY_ISSUE,
            self._console_handler,
            severity_filter=AlertSeverity.ERROR
        )
        
        self.register_handler(
            AlertType.BUILD_FAILURE,
            self._console_handler,
            severity_filter=AlertSeverity.ERROR
        )
        
        self.register_handler(
            AlertType.TEST_FAILURE,
            self._console_handler,
            severity_filter=AlertSeverity.ERROR
        )
    
    def _console_handler(self, alert: Alert):
        """Default console handler for alerts."""
        severity_color = {
            AlertSeverity.INFO: '\033[0m',  # Normal
            AlertSeverity.WARNING: '\033[93m',  # Yellow
            AlertSeverity.ERROR: '\033[91m',  # Red
            AlertSeverity.CRITICAL: '\033[41m\033[97m'  # Red background, white text
        }
        
        reset_color = '\033[0m'
        color = severity_color.get(alert.severity, '\033[0m')
        
        print(f"{color}[{alert.severity.name}] {alert.title}{reset_color}")
        print(f"  {alert.message}")
        if alert.file_path:
            location = f"{alert.file_path}"
            if alert.line_number:
                location += f":{alert.line_number}"
            print(f"  Location: {location}")
    
    def register_handler(
        self,
        alert_type: AlertType,
        handler: Callable[[Alert], None],
        severity_filter: Optional[AlertSeverity] = None
    ):
        """Register an alert handler."""
        if severity_filter:
            # Wrap handler with severity filter
            original_handler = handler
            def filtered_handler(alert: Alert):
                if alert.severity.value >= severity_filter.value:
                    original_handler(alert)
            handler = filtered_handler
        
        self.handlers[alert_type].append(handler)
    
    def create_alert(
        self,
        type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        **kwargs
    ) -> Alert:
        """Create and store an alert."""
        alert = Alert(
            type=type,
            severity=severity,
            title=title,
            message=message,
            **kwargs
        )
        
        # Store in database
        self._store_alert(alert)
        
        # Trigger handlers
        self._trigger_handlers(alert)
        
        return alert
    
    def _store_alert(self, alert: Alert):
        """Store alert in database."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("""
                INSERT INTO alerts (
                    type, severity, title, message,
                    file_path, line_number, context,
                    timestamp, resolved, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.type.value,
                alert.severity.name,
                alert.title,
                alert.message,
                str(alert.file_path) if alert.file_path else None,
                alert.line_number,
                json.dumps(alert.context) if alert.context else None,
                alert.timestamp.isoformat() if alert.timestamp else None,
                alert.resolved,
                alert.resolved_at.isoformat() if alert.resolved_at else None
            ))
            
            alert.alert_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()
    
    def _trigger_handlers(self, alert: Alert):
        """Trigger registered handlers for alert."""
        handlers = self.handlers.get(alert.type, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                # Log handler errors but don't fail alert creation
                print(f"Error in alert handler: {e}")
    
    def get_alerts(
        self,
        type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        resolved: Optional[bool] = None,
        file_path: Optional[Path] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Alert]:
        """Get alerts from database."""
        query = "SELECT * FROM alerts WHERE 1=1"
        params = []
        
        if type is not None:
            query += " AND type = ?"
            params.append(type.value)
        
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity.name)
        
        if resolved is not None:
            query += " AND resolved = ?"
            params.append(1 if resolved else 0)
        
        if file_path is not None:
            query += " AND file_path = ?"
            params.append(str(file_path))
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(query, params)
            alerts = []
            
            for row in cursor.fetchall():
                alert = Alert(
                    type=AlertType(row[1]),
                    severity=AlertSeverity[row[2]],
                    title=row[3],
                    message=row[4],
                    file_path=Path(row[5]) if row[5] else None,
                    line_number=row[6],
                    context=json.loads(row[7]) if row[7] else {},
                    timestamp=datetime.fromisoformat(row[8]) if row[8] else None,
                    resolved=bool(row[9]),
                    resolved_at=datetime.fromisoformat(row[10]) if row[10] else None,
                    alert_id=row[0]
                )
                alerts.append(alert)
            
            return alerts
        finally:
            conn.close()
    
    def resolve_alert(self, alert_id: int):
        """Mark an alert as resolved."""
        resolved_at = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                UPDATE alerts 
                SET resolved = 1, resolved_at = ?
                WHERE id = ?
            """, (resolved_at.isoformat(), alert_id))
            conn.commit()
        finally:
            conn.close()
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Count by type
            cursor = conn.execute("""
                SELECT type, COUNT(*) 
                FROM alerts 
                WHERE resolved = 0 
                GROUP BY type
            """)
            by_type = dict(cursor.fetchall())
            
            # Count by severity
            cursor = conn.execute("""
                SELECT severity, COUNT(*) 
                FROM alerts 
                WHERE resolved = 0 
                GROUP BY severity
            """)
            by_severity = dict(cursor.fetchall())
            
            # Recent alerts
            cursor = conn.execute("""
                SELECT COUNT(*) 
                FROM alerts 
                WHERE resolved = 0 
                AND timestamp > datetime('now', '-1 hour')
            """)
            recent_count = cursor.fetchone()[0]
            
            # Files with most alerts
            cursor = conn.execute("""
                SELECT file_path, COUNT(*) as alert_count
                FROM alerts 
                WHERE resolved = 0 
                AND file_path IS NOT NULL
                GROUP BY file_path
                ORDER BY alert_count DESC
                LIMIT 5
            """)
            top_files = [
                {"file": row[0], "count": row[1]}
                for row in cursor.fetchall()
            ]
            
            return {
                "by_type": by_type,
                "by_severity": by_severity,
                "recent_count": recent_count,
                "top_files": top_files,
                "total_unresolved": sum(by_type.values())
            }
        finally:
            conn.close()
    
    def cleanup_old_alerts(self, days: int = 30):
        """Clean up old resolved alerts."""
        cutoff_date = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                DELETE FROM alerts 
                WHERE resolved = 1 
                AND resolved_at < datetime('now', '-{} days')
            """.format(days))
            conn.commit()
        finally:
            conn.close()