# Git Integration Documentation

VelocityTree provides deep integration with Git to automatically track feature progress based on repository activity.

## Features

- **Automatic Status Updates**: Track feature progress from commits and branches
- **Branch Management**: Create feature branches automatically
- **Progress Reports**: Generate detailed reports from git history
- **Relationship Discovery**: Suggest feature relationships based on code changes
- **Real-time Monitoring**: Watch repository for changes and update features

## Git Commands

### Sync Feature Status

Update feature status based on git activity:

```bash
# Scan repository and update features
vtree git sync

# Watch for changes continuously
vtree git sync --watch

# Scan a specific project
vtree git sync --project /path/to/project
```

### Generate Progress Report

Create detailed reports of feature progress:

```bash
# Show table format (default)
vtree git report

# Export as JSON
vtree git report --format json

# Report for specific project
vtree git report --project /path/to/project
```

### Create Feature Branches

Create git branches for features:

```bash
# Create branch for a feature
vtree git feature-branch auth

# Create and checkout
vtree git feature-branch api --checkout
```

### Suggest Relationships

Discover feature relationships from git history:

```bash
# Get relationship suggestions
vtree git suggest

# Apply suggestions interactively
vtree git suggest --interactive
```

## How It Works

### Feature Detection

VelocityTree detects features in git through:

1. **Branch Names**:
   - `feature/auth`
   - `feat/api`
   - `auth-feature`
   - `impl-dashboard`

2. **Commit Messages**:
   - `feat: auth implementation`
   - `Implement: api endpoints`
   - `[db] Add migrations`
   - `Complete: auth feature`

3. **Issue References**:
   - `#123`
   - `issue: 456`
   - `Closes #789`

### Status Determination

Features are automatically updated based on:

- **Completed**: When commit messages contain completion keywords or branch is merged
- **In Progress**: Recent commits (within 7 days)
- **Blocked**: No activity for 7-30 days
- **Stale**: No activity for over 30 days

### Relationship Discovery

VelocityTree suggests relationships by analyzing:

1. **File Overlap**: Features that modify the same files
2. **Temporal Patterns**: Features worked on in sequence
3. **Branch Dependencies**: Features branched from each other
4. **Commit Patterns**: Features mentioned together

## Configuration

### Git Patterns

Customize pattern recognition in your config:

```yaml
git:
  feature_patterns:
    - 'feat[:\s]*(\w+)'
    - 'feature[:\s]*(\w+)'
  branch_patterns:
    - 'feature/(\w+)'
    - 'feat/(\w+)'
  completion_patterns:
    - 'complete[:\s]*(\w+)'
    - '✓\s*(\w+)'
```

### Monitoring Settings

Configure automatic monitoring:

```yaml
git:
  monitor:
    enabled: true
    interval: 30  # seconds
    auto_update: true
```

## Best Practices

### Branch Naming

Use consistent branch naming for automatic detection:

```
feature/auth
feature/api-endpoints
feat/user-dashboard
```

### Commit Messages

Include feature references in commits:

```
feat: auth - implement login flow
[api] Add user endpoints
Complete: dashboard feature
Fixes #123 - auth bug
```

### Feature Completion

Mark features as complete explicitly:

```
# In commit message
Complete: auth feature

# Or merge to main branch
git checkout main
git merge feature/auth
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Update Features
on:
  push:
    branches: [main]

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Update feature status
        run: |
          pip install velocitytree
          vtree git sync
          vtree git report
```

### GitLab CI Example

```yaml
update-features:
  stage: deploy
  script:
    - pip install velocitytree
    - vtree git sync
    - vtree git report --format json > feature-report.json
  artifacts:
    paths:
      - feature-report.json
```

## Advanced Usage

### Custom Scripts

Create custom git integration scripts:

```python
from velocitytree.git_integration import GitFeatureTracker
from velocitytree.core import VelocityTree

# Load project
vt = VelocityTree("/path/to/project")
tracker = GitFeatureTracker("/path/to/project", vt.feature_graph)

# Custom analysis
feature_commits = tracker.scan_repository()
for feature_id, commits in feature_commits.items():
    print(f"{feature_id}: {len(commits)} commits")

# Update specific features
tracker.update_feature_status()

# Generate custom reports
report = tracker.generate_feature_report()
```

### Webhook Integration

Set up webhooks to trigger updates:

```python
from flask import Flask, request
from velocitytree.git_integration import GitWorkflowIntegration

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def github_webhook():
    data = request.json
    
    # Handle push events
    if data.get('ref') == 'refs/heads/main':
        integration = GitWorkflowIntegration(".", feature_graph)
        updates = integration.tracker.update_feature_status()
        
        return {"updated": len(updates)}
    
    return {"status": "ok"}
```

## Troubleshooting

### Features Not Detected

1. Check branch naming matches patterns
2. Verify commit messages include feature references
3. Ensure feature IDs match those in feature graph

### Status Not Updating

1. Run `vtree git sync` manually
2. Check git repository is accessible
3. Verify features exist in feature graph
4. Check commit dates for activity

### Performance Issues

1. Limit scan depth for large repositories
2. Use specific branches instead of all
3. Enable caching for repeat scans
4. Run sync operations asynchronously