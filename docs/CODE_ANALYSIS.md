# Code Analysis Documentation

VelocityTree provides AI-powered code analysis to help developers maintain high code quality, detect patterns, and receive intelligent improvement suggestions.

## Features

- **Multi-language Support**: Analyze Python, JavaScript, TypeScript, and more
- **Complexity Metrics**: Cyclomatic and cognitive complexity calculations
- **Pattern Detection**: Identify design patterns and anti-patterns
- **Issue Detection**: Find common code quality issues
- **Smart Suggestions**: Get AI-powered improvement recommendations
- **Change Analysis**: Compare code versions and track quality trends

## Command Usage

### Basic Analysis

```bash
# Analyze a single file
vtree analyze file.py

# Analyze a directory
vtree analyze src/

# Analyze with specific patterns
vtree analyze src/ --include "*.py" --include "*.js"
```

### Output Formats

```bash
# Default console output
vtree analyze src/

# JSON output for integration
vtree analyze src/ --format json > analysis.json

# HTML report
vtree analyze src/ --format html --output report.html

# Markdown report
vtree analyze src/ --format markdown > ANALYSIS.md
```

### Configuration

```bash
# Use custom rules
vtree analyze --config .velocitytree/analysis.yaml

# Disable specific checks
vtree analyze --disable long-function --disable missing-docstring

# Set severity threshold
vtree analyze --min-severity warning
```

## Code Metrics

### Cyclomatic Complexity
Measures the number of linearly independent paths through code:
- 1-10: Simple, low risk
- 11-20: Complex, moderate risk
- 21-50: Very complex, high risk
- 50+: Extremely complex, very high risk

### Cognitive Complexity
Measures how difficult code is to understand:
- Considers nesting depth
- Penalizes complex control flow
- Better reflects human comprehension

### Maintainability Index
Composite metric (0-100) based on:
- Cyclomatic complexity
- Lines of code
- Comment ratio
- Halstead volume

## Pattern Detection

### Design Patterns
- Singleton
- Factory
- Observer
- Strategy
- Decorator

### Anti-Patterns
- God Class
- Spaghetti Code
- Copy-Paste Programming
- Magic Numbers
- Long Parameter Lists

### Code Smells
- Duplicate Code
- Long Methods
- Large Classes
- Feature Envy
- Data Clumps

## Issue Categories

### Style
- Naming conventions
- Formatting issues
- Import organization

### Complexity
- High cyclomatic complexity
- Deep nesting
- Long functions

### Bug Risk
- Potential null references
- Unhandled exceptions
- Type mismatches

### Security
- Hard-coded credentials
- SQL injection risks
- Cross-site scripting

### Performance
- Inefficient algorithms
- Memory leaks
- N+1 queries

### Maintainability
- Missing documentation
- Poor modularity
- Tight coupling

## Integration

### Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/sh
vtree analyze --staged --min-severity error
```

### CI/CD Pipeline

```yaml
# GitHub Actions
- name: Code Analysis
  run: |
    vtree analyze src/
    vtree analyze --format json > analysis.json
  continue-on-error: true
```

### IDE Integration

```json
// VS Code settings.json
{
  "velocitytree.analysis.onSave": true,
  "velocitytree.analysis.severity": "warning"
}
```

## API Usage

```python
from velocitytree.code_analysis import CodeAnalyzer
from velocitytree.code_analysis.models import Severity

# Create analyzer
analyzer = CodeAnalyzer()

# Analyze single file
result = analyzer.analyze_file("src/app.py")

# Check for issues
critical_issues = [
    issue for issue in result.issues 
    if issue.severity == Severity.CRITICAL
]

# Get metrics
print(f"Complexity: {result.metrics.cyclomatic_complexity}")
print(f"Maintainability: {result.metrics.maintainability_index}")

# Analyze directory
project_result = analyzer.analyze_directory("src/")
print(f"Files analyzed: {project_result.files_analyzed}")
print(f"Total issues: {len(project_result.all_issues)}")
```

## Configuration

### Analysis Configuration File

```yaml
# .velocitytree/analysis.yaml
rules:
  max-complexity: 10
  max-function-length: 50
  max-file-length: 500
  max-parameters: 5

ignore:
  - "**/tests/**"
  - "**/migrations/**"
  - "**/__pycache__/**"

custom-rules:
  - id: company-copyright
    pattern: "^# Copyright"
    message: "Missing copyright header"
    severity: warning

thresholds:
  maintainability-index: 65
  test-coverage: 80
  documentation-coverage: 90
```

### Language-Specific Settings

```yaml
python:
  max-line-length: 88  # Black formatter
  docstring-style: google
  type-checking: strict

javascript:
  ecma-version: 2022
  module-type: esm
  jsx: true

typescript:
  strict: true
  no-implicit-any: true
```

## Best Practices

### Regular Analysis
1. Run analysis before commits
2. Include in CI/CD pipeline
3. Track metrics over time
4. Address critical issues immediately

### Team Standards
1. Define coding standards
2. Configure shared rules
3. Regular code reviews
4. Track improvement metrics

### Progressive Enhancement
1. Start with critical issues
2. Gradually increase standards
3. Focus on high-impact areas
4. Celebrate improvements

## Troubleshooting

### Performance Issues
- Use file filtering for large codebases
- Enable caching for repeated analysis
- Run in parallel with `--parallel` flag

### False Positives
- Tune rule configurations
- Add inline suppressions
- Report issues for improvement

### Language Support
- Check supported extensions
- Install language plugins
- Configure custom parsers