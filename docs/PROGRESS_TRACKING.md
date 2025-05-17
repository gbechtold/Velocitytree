# Progress Tracking Documentation

VelocityTree provides comprehensive progress tracking and velocity metrics to help teams understand project status and predict completion dates.

## Features

- **Completion Percentage Calculations**: Track progress at feature, milestone, and project levels
- **Velocity Tracking**: Monitor development speed and trends
- **Burndown Charts**: Visualize project progress over time
- **Critical Path Analysis**: Identify features that impact project timeline
- **Bottleneck Detection**: Find features blocking progress
- **Completion Date Estimation**: Predict when features and projects will complete

## Progress Commands

### Feature Progress

View progress for specific features:

```bash
# Show progress for a specific feature
vtree progress status --feature auth

# Show all features with completion percentages
vtree progress status

# Export as JSON
vtree progress status --format json
```

### Project Overview

Get overall project progress:

```bash
# Show project summary
vtree progress status

# Include velocity metrics
vtree progress velocity
```

### Milestone Tracking

Track progress by milestone:

```bash
# Show milestone progress
vtree progress milestones

# Focus on specific milestone
vtree progress status --milestone "Phase 1"
```

### Burndown Charts

Generate burndown visualizations:

```bash
# Show text-based burndown in terminal
vtree progress burndown

# Save as image
vtree progress burndown --output burndown.png

# Customize time range
vtree progress burndown --days 60
```

## Progress Calculation

### Feature Completion

Feature completion is calculated based on:

1. **Status-based completion**:
   - Completed: 100%
   - In Progress: 50%
   - Blocked: 25%
   - Pending/Planned: 0%

2. **Dependency-based completion**:
   - Weighted by completion of dependencies
   - 70% weight on dependencies, 30% on own status

### Critical Path Analysis

Features are marked as critical path if:
- They block more than 30% of other features
- They have the longest chain of dependencies
- They're on the main development timeline

### Velocity Metrics

Velocity is calculated as:
- Features completed per time period
- Weighted by feature complexity
- Adjusted for team size

## Web Interface

The web interface provides real-time progress visualization:

```javascript
// Fetch feature progress
fetch('/api/progress/feature/auth')
  .then(res => res.json())
  .then(progress => {
    console.log(`${progress.name}: ${progress.completion_percentage}%`);
  });

// Get project overview
fetch('/api/progress/project')
  .then(res => res.json())
  .then(project => {
    console.log(`Project: ${project.total_completion}%`);
  });
```

## Progress API

### Progress Objects

#### FeatureProgress
```python
@dataclass
class FeatureProgress:
    feature_id: str
    name: str
    status: str
    completion_percentage: float
    dependencies_completed: int
    total_dependencies: int
    estimated_completion_date: Optional[datetime]
    velocity: Optional[float]
    blockers: List[str]
    critical_path: bool
```

#### ProjectProgress
```python
@dataclass
class ProjectProgress:
    total_completion: float
    features_completed: int
    total_features: int
    milestones_completed: int
    total_milestones: int
    estimated_completion_date: Optional[datetime]
    current_velocity: float
    average_velocity: float
    burndown_data: List[Tuple[datetime, float]]
```

### Using the API

```python
from velocitytree.progress_tracking import ProgressCalculator
from velocitytree.core import VelocityTree

# Load project
vt = VelocityTree("/path/to/project")
calculator = ProgressCalculator(vt.feature_graph)

# Get feature progress
feature_progress = calculator.calculate_feature_progress("auth")
print(f"Auth completion: {feature_progress.completion_percentage}%")

# Get project overview
project_progress = calculator.calculate_project_progress()
print(f"Project completion: {project_progress.total_completion}%")

# Get velocity report
velocity = calculator.get_velocity_report()
print(f"Current velocity: {velocity['current_velocity']['daily']} features/day")
```

## Velocity Tracking

### Velocity Calculation

Velocity is measured in multiple ways:

1. **Current Velocity**: Features completed in recent period
2. **Average Velocity**: Historical average
3. **Predicted Velocity**: Based on trends

### Velocity Trends

The system tracks velocity trends:
- **Improving**: Current > Average by 10%
- **Stable**: Within 10% of average
- **Declining**: Current < Average by 10%

### Bottleneck Detection

Features are identified as bottlenecks if:
- They have "blocked" or "pending" status
- They block multiple other features
- They're on the critical path

## Integration with Git

Progress tracking integrates with git activity:

```bash
# Update progress from git activity
vtree git sync

# Generate progress report with git data
vtree progress status --with-git
```

Git integration provides:
- Automatic status updates from commits
- Activity-based velocity calculations
- Real completion dates from merge history

## Customization

### Custom Velocity Calculations

Override velocity calculations:

```python
class CustomProgressCalculator(ProgressCalculator):
    def _calculate_feature_velocity(self, feature_id: str) -> float:
        # Custom velocity logic
        feature = self.feature_graph.features[feature_id]
        if feature.feature_type == "epic":
            return 2.0  # Epics complete slower
        return 5.0  # Features complete faster
```

### Custom Completion Rules

Define custom completion percentage rules:

```python
def custom_completion(feature):
    if feature.tags.get("external_dependency"):
        return 75.0  # External dependencies cap at 75%
    return calculate_standard_completion(feature)
```

## Best Practices

### Accurate Status Updates

1. Update feature status regularly
2. Use git integration for automatic updates
3. Mark blockers promptly
4. Complete features when truly done

### Dependency Management

1. Define all dependencies upfront
2. Keep dependency chains short
3. Identify critical path early
4. Minimize circular dependencies

### Velocity Optimization

1. Focus on bottlenecks first
2. Limit work in progress
3. Break down large features
4. Track and improve metrics

## Reporting

### Executive Summary

Generate executive reports:

```bash
# Create summary report
vtree progress status --format json > progress-report.json

# Generate velocity trends
vtree progress velocity --export velocity-report.csv
```

### Team Dashboards

Create team dashboards:

```python
# Weekly team update
report = calculator.calculate_project_progress()
print(f"This week: {report.current_velocity * 7:.1f} features completed")
print(f"Project: {report.total_completion:.1f}% complete")
print(f"ETA: {report.estimated_completion_date}")
```

### Stakeholder Updates

Provide stakeholder updates:

```bash
# Milestone summary for stakeholders
vtree progress milestones --format markdown > milestone-update.md

# Visual burndown chart
vtree progress burndown --output visuals/burndown-week-42.png
```

## Troubleshooting

### Incorrect Completion Percentages

1. Verify dependency relationships
2. Check feature status accuracy
3. Review calculation weights
4. Validate git integration

### Velocity Anomalies

1. Check for data gaps
2. Verify feature completions
3. Review team changes
4. Validate calculation period

### Missing Progress Data

1. Ensure features have status
2. Define dependencies correctly
3. Run git sync if using integration
4. Check calculation errors