# Continuous Evaluation System

## Overview

The Continuous Evaluation system provides real-time monitoring of code changes, detects specification drift, generates alerts, and offers realignment suggestions. This system helps maintain code quality and consistency by continuously evaluating your codebase against defined specifications.

## Architecture

The system consists of four main components:

1. **ContinuousMonitor**: Watches for file changes and orchestrates evaluation
2. **DriftDetector**: Compares code against specifications to detect deviations
3. **AlertSystem**: Manages alerts with persistence and notification handlers
4. **RealignmentEngine**: Generates suggestions to fix detected issues

## Usage

### Starting Continuous Monitoring

```bash
# Start monitoring with default settings
velocitytree monitor start

# Custom configuration
velocitytree monitor start --interval 2.0 --cpu-limit 30 --batch-size 20

# Monitor specific project
velocitytree monitor start --project /path/to/project
```

### Viewing Alerts

```bash
# View all alerts
velocitytree monitor alerts

# Filter by type
velocitytree monitor alerts --type drift_detected

# Filter by severity
velocitytree monitor alerts --severity error

# Show only unresolved alerts
velocitytree monitor alerts --unresolved
```

### Managing Alerts

```bash
# Resolve an alert
velocitytree monitor resolve 123

# Get summary of current alerts
velocitytree monitor summary

# Generate suggestions for an alert
velocitytree monitor suggest 123
```

## Configuration

### Monitor Configuration

```python
from velocitytree.continuous_eval import MonitorConfig

config = MonitorConfig(
    scan_interval=1.0,  # seconds between scans
    watch_patterns=["**/*.py", "**/*.js"],
    ignore_patterns=["**/node_modules/**"],
    max_cpu_percent=20.0,
    max_memory_mb=500.0,
    batch_size=10,
    enabled_checks=['drift', 'quality', 'security', 'performance']
)
```

### Alert Types

- `DRIFT_DETECTED`: Code deviates from specifications
- `QUALITY_DEGRADATION`: Code quality metrics have declined
- `SECURITY_ISSUE`: Security vulnerabilities detected
- `PERFORMANCE_REGRESSION`: Performance degradation detected
- `DEPENDENCY_UPDATE`: Dependencies need updating
- `COMPLEXITY_INCREASE`: Code complexity has increased
- `COVERAGE_DROP`: Test coverage has decreased
- `DOCUMENTATION_STALE`: Documentation is out of date

### Drift Types

- `MISSING_IMPLEMENTATION`: Expected functionality is not implemented
- `SIGNATURE_MISMATCH`: Function/method signatures don't match spec
- `BEHAVIOR_DEVIATION`: Implementation behavior differs from spec
- `PERFORMANCE_DEGRADATION`: Performance doesn't meet requirements
- `DOCUMENTATION_STALE`: Documentation doesn't match implementation
- `DEPENDENCY_DRIFT`: Dependencies don't match requirements
- `API_BREAKING_CHANGE`: API changes that break compatibility

## Realignment Suggestions

The system provides categorized suggestions for addressing detected issues:

### Suggestion Categories

- `CODE_CHANGE`: Direct code modifications
- `SPEC_UPDATE`: Update specifications to match reality
- `REFACTOR`: Code refactoring suggestions
- `DOCUMENTATION`: Documentation updates
- `TEST_UPDATE`: Test modifications or additions
- `DEPENDENCY`: Dependency version changes

### Example Suggestions

```python
suggestion = RealignmentSuggestion(
    category=SuggestionCategory.CODE_CHANGE,
    title="Update function signature",
    description="Change parameter types to match specification",
    priority=4,  # 1-5, higher is more important
    effort=2,    # 1-5, higher is more effort
    file_path=Path("utils.py"),
    line_number=42,
    code_snippet="def calculate(x: float, y: float) -> float:",
    confidence=0.95
)
```

## Programmatic Usage

### Python API

```python
from velocitytree.continuous_eval import (
    ContinuousMonitor,
    AlertSystem,
    DriftDetector,
    RealignmentEngine
)

# Start monitoring
monitor = ContinuousMonitor()
monitor.start_monitoring("/path/to/project")

# Check for drift
detector = DriftDetector()
report = detector.check_file_drift("app.py")

# Generate suggestions
engine = RealignmentEngine()
suggestions = engine.generate_suggestions(report)

# Create custom alert
alert_system = AlertSystem()
alert = alert_system.create_alert(
    type=AlertType.CUSTOM,
    severity=AlertSeverity.WARNING,
    title="Custom Alert",
    message="This is a custom alert"
)
```

### Custom Alert Handlers

```python
def email_handler(alert: Alert):
    """Send email notification for critical alerts."""
    if alert.severity == AlertSeverity.CRITICAL:
        send_email(
            subject=f"Critical Alert: {alert.title}",
            body=alert.message
        )

# Register handler
alert_system.register_handler(
    AlertType.SECURITY_ISSUE,
    email_handler,
    severity_filter=AlertSeverity.ERROR
)
```

## Best Practices

1. **Resource Management**
   - Set appropriate CPU and memory limits
   - Use batch processing for large projects
   - Configure ignore patterns to skip unnecessary files

2. **Alert Management**
   - Regularly review and resolve alerts
   - Set up handlers for critical alerts
   - Use alert summaries to track trends

3. **Specifications**
   - Keep specifications up to date
   - Use clear, testable requirements
   - Document expected behavior thoroughly

4. **Performance**
   - Monitor system resource usage
   - Adjust scan intervals based on project size
   - Use caching where appropriate

## CLI Commands Reference

```bash
# Monitoring commands
velocitytree monitor start    # Start monitoring
velocitytree monitor stop     # Stop monitoring
velocitytree monitor status   # Show status

# Alert commands
velocitytree monitor alerts   # List alerts
velocitytree monitor resolve  # Resolve alert
velocitytree monitor summary  # Alert summary

# Suggestion commands
velocitytree monitor suggest  # Generate suggestions
```

## Integration with Other Features

The Continuous Evaluation system integrates with:

- **Documentation Generator**: Updates docs when code changes
- **Code Analysis**: Uses analysis results for drift detection
- **Progress Tracking**: Monitors feature completion
- **Workflow Management**: Triggers workflows on alerts

## Future Enhancements

- Machine learning for better drift detection
- Automated fix application
- Integration with CI/CD pipelines
- Custom check plugins
- Real-time collaboration features