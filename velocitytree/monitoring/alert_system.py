"""
Automatic alert generation system for Velocitytree.
"""

import json
import smtplib
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from ..utils import logger


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""
    LOG = "log"
    FILE = "file"
    EMAIL = "email"
    WEBHOOK = "webhook"
    CONSOLE = "console"


@dataclass
class AlertConfig:
    """Configuration for alert system."""
    enabled_channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.LOG, AlertChannel.FILE])
    alert_file: Optional[Path] = None
    email_config: Optional[Dict[str, Any]] = None
    webhook_config: Optional[Dict[str, Any]] = None
    severity_thresholds: Dict[AlertSeverity, int] = field(default_factory=lambda: {
        AlertSeverity.INFO: 10,
        AlertSeverity.WARNING: 5,
        AlertSeverity.ERROR: 2,
        AlertSeverity.CRITICAL: 1
    })
    rate_limits: Dict[str, int] = field(default_factory=lambda: {
        'per_minute': 10,
        'per_hour': 100,
        'per_day': 500
    })
    suppression_window: int = 300  # 5 minutes


@dataclass
class Alert:
    """Individual alert."""
    alert_id: str
    timestamp: datetime
    severity: AlertSeverity
    title: str
    description: str
    source: str
    category: str
    details: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'severity': self.severity.value,
            'title': self.title,
            'description': self.description,
            'source': self.source,
            'category': self.category,
            'details': self.details,
            'metadata': self.metadata
        }
    
    def format_message(self, format_type: str = 'text') -> str:
        """Format alert message."""
        if format_type == 'text':
            return f"[{self.severity.value.upper()}] {self.title}\n{self.description}\nSource: {self.source}"
        elif format_type == 'html':
            return f"""
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px;">
                <h3 style="color: {self._get_color()};">[{self.severity.value.upper()}] {self.title}</h3>
                <p>{self.description}</p>
                <p><small>Source: {self.source} | Time: {self.timestamp}</small></p>
            </div>
            """
        elif format_type == 'json':
            return json.dumps(self.to_dict(), indent=2)
        else:
            return str(self)
    
    def _get_color(self) -> str:
        """Get color for severity level."""
        return {
            AlertSeverity.INFO: '#17a2b8',
            AlertSeverity.WARNING: '#ffc107',
            AlertSeverity.ERROR: '#dc3545',
            AlertSeverity.CRITICAL: '#6c1e2c'
        }.get(self.severity, '#6c757d')


class BaseAlertChannel:
    """Base class for alert channels."""
    
    def send(self, alert: Alert):
        """Send alert through channel."""
        raise NotImplementedError


class LogChannel(BaseAlertChannel):
    """Log file alert channel."""
    
    def send(self, alert: Alert):
        """Send alert to log."""
        log_message = alert.format_message('text')
        
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(log_message)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(log_message)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)


class FileChannel(BaseAlertChannel):
    """File alert channel."""
    
    def __init__(self, alert_file: Path):
        self.alert_file = alert_file
        self.alert_file.parent.mkdir(parents=True, exist_ok=True)
    
    def send(self, alert: Alert):
        """Send alert to file."""
        with open(self.alert_file, 'a') as f:
            f.write(json.dumps(alert.to_dict()) + '\n')


class EmailChannel(BaseAlertChannel):
    """Email alert channel."""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get('smtp_host', 'localhost')
        self.smtp_port = config.get('smtp_port', 587)
        self.smtp_user = config.get('smtp_user')
        self.smtp_password = config.get('smtp_password')
        self.from_email = config.get('from_email', 'velocitytree@localhost')
        self.to_emails = config.get('to_emails', [])
        self.use_tls = config.get('use_tls', True)
    
    def send(self, alert: Alert):
        """Send alert via email."""
        if not self.to_emails:
            logger.warning("No email recipients configured")
            return
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
        msg['From'] = self.from_email
        msg['To'] = ', '.join(self.to_emails)
        
        # Create text and HTML parts
        text_part = MIMEText(alert.format_message('text'), 'plain')
        html_part = MIMEText(alert.format_message('html'), 'html')
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
                
            logger.info(f"Email alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")


class WebhookChannel(BaseAlertChannel):
    """Webhook alert channel."""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.headers = config.get('headers', {})
        self.timeout = config.get('timeout', 10)
        self.auth = config.get('auth')
    
    def send(self, alert: Alert):
        """Send alert via webhook."""
        if not self.webhook_url:
            logger.warning("No webhook URL configured")
            return
        
        try:
            response = requests.post(
                self.webhook_url,
                json=alert.to_dict(),
                headers=self.headers,
                timeout=self.timeout,
                auth=self.auth
            )
            response.raise_for_status()
            logger.info(f"Webhook alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")


class ConsoleChannel(BaseAlertChannel):
    """Console alert channel."""
    
    def send(self, alert: Alert):
        """Send alert to console."""
        from rich.console import Console
        from rich.panel import Panel
        
        console = Console()
        
        color = {
            AlertSeverity.INFO: 'blue',
            AlertSeverity.WARNING: 'yellow',
            AlertSeverity.ERROR: 'red',
            AlertSeverity.CRITICAL: 'red on white'
        }.get(alert.severity, 'white')
        
        panel = Panel(
            alert.description,
            title=f"[{color}]{alert.severity.value.upper()}: {alert.title}[/{color}]",
            subtitle=f"Source: {alert.source} | {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        console.print(panel)


class AlertManager:
    """Manager for automatic alert generation."""
    
    def __init__(self, config: Optional[AlertConfig] = None):
        self.config = config or AlertConfig()
        self.channels: Dict[AlertChannel, BaseAlertChannel] = {}
        self.alert_history: List[Alert] = []
        self.rate_limiter = RateLimiter(self.config.rate_limits)
        self.suppression_cache: Dict[str, datetime] = {}
        
        # Initialize channels
        self._initialize_channels()
        
        # Alert handlers
        self.handlers: Dict[str, List[Callable]] = {}
    
    def _initialize_channels(self):
        """Initialize alert channels based on configuration."""
        for channel_type in self.config.enabled_channels:
            if channel_type == AlertChannel.LOG:
                self.channels[channel_type] = LogChannel()
            elif channel_type == AlertChannel.FILE:
                if self.config.alert_file:
                    self.channels[channel_type] = FileChannel(self.config.alert_file)
            elif channel_type == AlertChannel.EMAIL:
                if self.config.email_config:
                    self.channels[channel_type] = EmailChannel(self.config.email_config)
            elif channel_type == AlertChannel.WEBHOOK:
                if self.config.webhook_config:
                    self.channels[channel_type] = WebhookChannel(self.config.webhook_config)
            elif channel_type == AlertChannel.CONSOLE:
                self.channels[channel_type] = ConsoleChannel()
    
    def create_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        source: str,
        category: str,
        details: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            alert_id=self._generate_alert_id(),
            timestamp=datetime.now(),
            severity=severity,
            title=title,
            description=description,
            source=source,
            category=category,
            details=details or {},
            metadata=metadata or {}
        )
        
        return alert
    
    def send_alert(self, alert: Alert) -> bool:
        """Send alert through configured channels."""
        # Check rate limits
        if not self.rate_limiter.check_limit(alert.category):
            logger.warning(f"Rate limit exceeded for category: {alert.category}")
            return False
        
        # Check suppression
        if self._is_suppressed(alert):
            logger.debug(f"Alert suppressed: {alert.title}")
            return False
        
        # Check severity threshold
        threshold = self.config.severity_thresholds.get(alert.severity, 1)
        if self._count_recent_similar_alerts(alert) < threshold:
            logger.debug(f"Alert below threshold: {alert.title}")
            return False
        
        # Send through channels
        sent = False
        for channel_type, channel in self.channels.items():
            try:
                channel.send(alert)
                sent = True
                logger.debug(f"Alert sent via {channel_type}: {alert.title}")
            except Exception as e:
                logger.error(f"Failed to send alert via {channel_type}: {e}")
        
        if sent:
            # Update history
            self.alert_history.append(alert)
            
            # Update suppression cache
            self._update_suppression_cache(alert)
            
            # Call handlers
            self._call_handlers(alert)
        
        return sent
    
    def register_handler(self, category: str, handler: Callable[[Alert], None]):
        """Register a handler for specific alert category."""
        if category not in self.handlers:
            self.handlers[category] = []
        self.handlers[category].append(handler)
    
    def _generate_alert_id(self) -> str:
        """Generate unique alert ID."""
        import uuid
        return str(uuid.uuid4())
    
    def _is_suppressed(self, alert: Alert) -> bool:
        """Check if alert should be suppressed."""
        suppression_key = f"{alert.category}:{alert.title}"
        
        if suppression_key in self.suppression_cache:
            last_sent = self.suppression_cache[suppression_key]
            if datetime.now() - last_sent < timedelta(seconds=self.config.suppression_window):
                return True
        
        return False
    
    def _update_suppression_cache(self, alert: Alert):
        """Update suppression cache."""
        suppression_key = f"{alert.category}:{alert.title}"
        self.suppression_cache[suppression_key] = datetime.now()
        
        # Clean old entries
        cutoff = datetime.now() - timedelta(seconds=self.config.suppression_window)
        self.suppression_cache = {
            k: v for k, v in self.suppression_cache.items()
            if v > cutoff
        }
    
    def _count_recent_similar_alerts(self, alert: Alert) -> int:
        """Count recent similar alerts."""
        cutoff = datetime.now() - timedelta(hours=1)
        count = 0
        
        for historical_alert in self.alert_history:
            if (historical_alert.category == alert.category and
                historical_alert.title == alert.title and
                historical_alert.timestamp > cutoff):
                count += 1
        
        return count
    
    def _call_handlers(self, alert: Alert):
        """Call registered handlers for alert."""
        # Call category-specific handlers
        if alert.category in self.handlers:
            for handler in self.handlers[alert.category]:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Handler error for {alert.category}: {e}")
        
        # Call wildcard handlers
        if '*' in self.handlers:
            for handler in self.handlers['*']:
                try:
                    handler(alert)
                except Exception as e:
                    logger.error(f"Wildcard handler error: {e}")
    
    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of recent alerts."""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_alerts = [a for a in self.alert_history if a.timestamp > cutoff]
        
        summary = {
            'total_alerts': len(recent_alerts),
            'by_severity': {},
            'by_category': {},
            'by_source': {},
            'timeline': []
        }
        
        # Count by severity
        for severity in AlertSeverity:
            summary['by_severity'][severity.value] = sum(
                1 for a in recent_alerts if a.severity == severity
            )
        
        # Count by category
        categories = {}
        for alert in recent_alerts:
            categories[alert.category] = categories.get(alert.category, 0) + 1
        summary['by_category'] = categories
        
        # Count by source
        sources = {}
        for alert in recent_alerts:
            sources[alert.source] = sources.get(alert.source, 0) + 1
        summary['by_source'] = sources
        
        # Create timeline (hourly)
        for hour in range(hours):
            hour_start = datetime.now() - timedelta(hours=hour+1)
            hour_end = datetime.now() - timedelta(hours=hour)
            
            hour_alerts = [
                a for a in recent_alerts
                if hour_start <= a.timestamp < hour_end
            ]
            
            summary['timeline'].append({
                'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                'count': len(hour_alerts)
            })
        
        return summary


class RateLimiter:
    """Rate limiter for alerts."""
    
    def __init__(self, limits: Dict[str, int]):
        self.limits = limits
        self.counters: Dict[str, List[datetime]] = {}
    
    def check_limit(self, category: str) -> bool:
        """Check if category is within rate limits."""
        now = datetime.now()
        
        # Initialize counter if needed
        if category not in self.counters:
            self.counters[category] = []
        
        # Clean old entries
        self.counters[category] = [
            ts for ts in self.counters[category]
            if now - ts < timedelta(days=1)
        ]
        
        # Check limits
        for period, limit in self.limits.items():
            if period == 'per_minute':
                cutoff = now - timedelta(minutes=1)
            elif period == 'per_hour':
                cutoff = now - timedelta(hours=1)
            elif period == 'per_day':
                cutoff = now - timedelta(days=1)
            else:
                continue
            
            recent_count = sum(1 for ts in self.counters[category] if ts > cutoff)
            if recent_count >= limit:
                return False
        
        # Update counter
        self.counters[category].append(now)
        return True