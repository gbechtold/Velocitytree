"""
Tests for the alert system functionality.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import pytest

from velocitytree.monitoring.alert_system import (
    AlertManager, Alert, AlertConfig, AlertSeverity, AlertChannel,
    BaseAlertChannel, LogChannel, FileChannel, EmailChannel,
    WebhookChannel, ConsoleChannel, RateLimiter
)


class TestAlert:
    """Test cases for Alert class."""
    
    def test_alert_creation(self):
        """Test creating an alert."""
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="This is a test alert",
            source="test",
            category="testing"
        )
        
        assert alert.alert_id == "test-123"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.source == "test"
    
    def test_alert_to_dict(self):
        """Test converting alert to dictionary."""
        timestamp = datetime.now()
        alert = Alert(
            alert_id="test-123",
            timestamp=timestamp,
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing",
            details={'key': 'value'}
        )
        
        data = alert.to_dict()
        assert data['alert_id'] == "test-123"
        assert data['timestamp'] == timestamp.isoformat()
        assert data['severity'] == 'error'
        assert data['details']['key'] == 'value'
    
    def test_alert_format_text(self):
        """Test formatting alert as text."""
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        text = alert.format_message('text')
        assert "[ERROR] Test Alert" in text
        assert "Test description" in text
        assert "Source: test" in text
    
    def test_alert_format_html(self):
        """Test formatting alert as HTML."""
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        html = alert.format_message('html')
        assert "<h3" in html
        assert "[WARNING]" in html
        assert "Test Alert" in html
        assert "#ffc107" in html  # Warning color
    
    def test_alert_format_json(self):
        """Test formatting alert as JSON."""
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.INFO,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        json_str = alert.format_message('json')
        data = json.loads(json_str)
        assert data['alert_id'] == "test-123"
        assert data['severity'] == 'info'


class TestAlertChannels:
    """Test cases for alert channels."""
    
    def test_log_channel(self):
        """Test log channel functionality."""
        channel = LogChannel()
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        with patch('velocitytree.monitoring.alert_system.logger') as mock_logger:
            channel.send(alert)
            mock_logger.error.assert_called_once()
    
    def test_file_channel(self, tmp_path):
        """Test file channel functionality."""
        alert_file = tmp_path / "alerts.json"
        channel = FileChannel(alert_file)
        
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        channel.send(alert)
        
        # Check file was created and contains alert
        assert alert_file.exists()
        with open(alert_file) as f:
            data = json.loads(f.read())
        assert data['alert_id'] == "test-123"
    
    @patch('smtplib.SMTP')
    def test_email_channel(self, mock_smtp):
        """Test email channel functionality."""
        config = {
            'smtp_host': 'localhost',
            'smtp_port': 587,
            'from_email': 'test@example.com',
            'to_emails': ['recipient@example.com']
        }
        
        channel = EmailChannel(config)
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        channel.send(alert)
        mock_smtp.assert_called_once_with('localhost', 587)
    
    @patch('requests.post')
    def test_webhook_channel(self, mock_post):
        """Test webhook channel functionality."""
        config = {
            'webhook_url': 'https://example.com/webhook',
            'headers': {'Authorization': 'Bearer token'}
        }
        
        channel = WebhookChannel(config)
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        mock_post.return_value.status_code = 200
        channel.send(alert)
        
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == 'https://example.com/webhook'
        assert kwargs['json']['alert_id'] == "test-123"
    
    @patch('velocitytree.monitoring.alert_system.Console')
    def test_console_channel(self, mock_console_class):
        """Test console channel functionality."""
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        channel = ConsoleChannel()
        alert = Alert(
            alert_id="test-123",
            timestamp=datetime.now(),
            severity=AlertSeverity.INFO,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        channel.send(alert)
        mock_console.print.assert_called_once()


class TestAlertManager:
    """Test cases for AlertManager."""
    
    def test_init(self):
        """Test alert manager initialization."""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG]
        )
        manager = AlertManager(config)
        
        assert manager.config == config
        assert len(manager.channels) > 0
        assert AlertChannel.LOG in manager.channels
    
    def test_create_alert(self):
        """Test creating an alert through manager."""
        manager = AlertManager()
        
        alert = manager.create_alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        assert alert.severity == AlertSeverity.WARNING
        assert alert.title == "Test Alert"
        assert alert.alert_id is not None
    
    def test_send_alert(self, tmp_path):
        """Test sending alert through manager."""
        config = AlertConfig(
            enabled_channels=[AlertChannel.FILE],
            alert_file=tmp_path / "alerts.json"
        )
        manager = AlertManager(config)
        
        alert = manager.create_alert(
            severity=AlertSeverity.ERROR,
            title="Test Alert",
            description="Test description",
            source="test",
            category="testing"
        )
        
        result = manager.send_alert(alert)
        assert result is True
        assert len(manager.alert_history) == 1
        assert (tmp_path / "alerts.json").exists()
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG],
            rate_limits={'per_minute': 2}
        )
        manager = AlertManager(config)
        
        # Send alerts up to limit
        for i in range(2):
            alert = manager.create_alert(
                severity=AlertSeverity.INFO,
                title=f"Alert {i}",
                description="Test",
                source="test",
                category="testing"
            )
            result = manager.send_alert(alert)
            assert result is True
        
        # Third alert should be rate limited
        alert = manager.create_alert(
            severity=AlertSeverity.INFO,
            title="Alert 3",
            description="Test",
            source="test",
            category="testing"
        )
        result = manager.send_alert(alert)
        assert result is False
    
    def test_suppression(self):
        """Test alert suppression."""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG],
            suppression_window=60  # 1 minute
        )
        manager = AlertManager(config)
        
        # First alert should go through
        alert1 = manager.create_alert(
            severity=AlertSeverity.WARNING,
            title="Duplicate Alert",
            description="Test",
            source="test",
            category="testing"
        )
        result1 = manager.send_alert(alert1)
        assert result1 is True
        
        # Duplicate alert should be suppressed
        alert2 = manager.create_alert(
            severity=AlertSeverity.WARNING,
            title="Duplicate Alert",
            description="Test",
            source="test",
            category="testing"
        )
        result2 = manager.send_alert(alert2)
        assert result2 is False
    
    def test_severity_threshold(self):
        """Test severity threshold."""
        config = AlertConfig(
            enabled_channels=[AlertChannel.LOG],
            severity_thresholds={AlertSeverity.ERROR: 2}
        )
        manager = AlertManager(config)
        
        # First error alert should not be sent (below threshold)
        alert1 = manager.create_alert(
            severity=AlertSeverity.ERROR,
            title="Test Error",
            description="Test",
            source="test",
            category="error"
        )
        result1 = manager.send_alert(alert1)
        assert result1 is False
        
        # After adding to history, second should trigger
        manager.alert_history.append(alert1)
        
        alert2 = manager.create_alert(
            severity=AlertSeverity.ERROR,
            title="Test Error",
            description="Test",
            source="test",
            category="error"
        )
        result2 = manager.send_alert(alert2)
        assert result2 is True
    
    def test_alert_handlers(self):
        """Test alert handlers."""
        manager = AlertManager()
        
        # Track handler calls
        handler_calls = []
        
        def test_handler(alert):
            handler_calls.append(alert)
        
        manager.register_handler('testing', test_handler)
        
        alert = manager.create_alert(
            severity=AlertSeverity.INFO,
            title="Test Alert",
            description="Test",
            source="test",
            category="testing"
        )
        
        manager.send_alert(alert)
        
        assert len(handler_calls) == 1
        assert handler_calls[0] == alert
    
    def test_get_alert_summary(self):
        """Test getting alert summary."""
        manager = AlertManager()
        
        # Add some test alerts
        for i in range(5):
            alert = manager.create_alert(
                severity=AlertSeverity.WARNING if i < 3 else AlertSeverity.ERROR,
                title=f"Alert {i}",
                description="Test",
                source="test",
                category="category1" if i < 2 else "category2"
            )
            manager.alert_history.append(alert)
        
        summary = manager.get_alert_summary(hours=24)
        
        assert summary['total_alerts'] == 5
        assert summary['by_severity']['warning'] == 3
        assert summary['by_severity']['error'] == 2
        assert summary['by_category']['category1'] == 2
        assert summary['by_category']['category2'] == 3
        assert len(summary['timeline']) == 24


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    def test_rate_limiter(self):
        """Test rate limiter functionality."""
        limits = {
            'per_minute': 3,
            'per_hour': 10
        }
        limiter = RateLimiter(limits)
        
        # First 3 should pass
        for i in range(3):
            assert limiter.check_limit('test') is True
        
        # Fourth should fail (per minute limit)
        assert limiter.check_limit('test') is False
        
        # Different category should pass
        assert limiter.check_limit('other') is True