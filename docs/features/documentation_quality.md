# Documentation Quality Checking

VelocityTree's documentation quality checking system analyzes your code documentation and provides actionable suggestions for improvement.

## Overview

The quality checking system evaluates documentation across multiple dimensions:

- **Completeness**: Are all code elements documented?
- **Consistency**: Does documentation follow a consistent style?
- **Clarity**: Is the documentation clear and understandable?
- **Structure**: Are documentation sections properly organized?
- **Examples**: Are usage examples provided where helpful?
- **Accuracy**: Does documentation match the code?

## Usage

### Check Documentation Quality

Analyze documentation quality for your code:

```bash
# Check a single file
vtree doc check src/main.py

# Check directory recursively
vtree doc check src/ --recursive

# Get detailed quality report
vtree doc check src/ --verbose
```

### Get Documentation Suggestions

Generate suggestions for improving documentation:

```bash
# Get suggestions for a file
vtree doc suggest src/utils.py

# Save suggestions to file
vtree doc suggest src/ --output suggestions.json

# Apply suggestions interactively
vtree doc suggest src/main.py --apply --interactive

# Apply all suggestions automatically
vtree doc suggest src/ --apply
```

## Quality Metrics

### Overall Score

The overall quality score (0-100) is calculated as a weighted average of:

- Completeness (30%)
- Consistency (20%)
- Clarity (20%)
- Structure (10%)
- Examples (10%)
- Accuracy (5%)
- References (5%)

### Issue Severity Levels

Issues are categorized by severity:

- **ERROR**: Critical issues that must be fixed
- **WARNING**: Important issues that should be addressed
- **INFO**: Recommendations for improvement
- **SUGGESTION**: Optional enhancements

## Documentation Styles

The quality checker supports multiple documentation styles:

### Google Style
```python
def function(arg1: int, arg2: str) -> bool:
    """Brief description of function.
    
    Longer description if needed.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When invalid input
    """
```

### NumPy Style
```python
def function(arg1: int, arg2: str) -> bool:
    """Brief description of function.
    
    Longer description if needed.
    
    Parameters
    ----------
    arg1 : int
        Description of arg1
    arg2 : str
        Description of arg2
        
    Returns
    -------
    bool
        Description of return value
    """
```

### Sphinx Style
```python
def function(arg1: int, arg2: str) -> bool:
    """Brief description of function.
    
    :param arg1: Description of arg1
    :type arg1: int
    :param arg2: Description of arg2
    :type arg2: str
    :returns: Description of return value
    :rtype: bool
    """
```

## Quality Rules

### Completeness Rules

- Module must have docstring
- Public classes must have docstrings
- Public functions/methods must have docstrings
- Parameters must be documented
- Return values must be documented
- Exceptions must be documented

### Consistency Rules

- Use consistent parameter terminology
- Follow chosen documentation style
- Maintain consistent formatting
- Use consistent section ordering

### Clarity Rules

- Avoid vague descriptions
- Explain complex logic
- Define abbreviations
- Provide context

### Structure Rules

- Use appropriate sections
- Order sections consistently
- Format lists properly
- Group related information

## Suggestion Engine

The suggestion engine provides:

### Smart Templates

Generates documentation templates based on code analysis:

```python
# For a complex function
def process_data(data, config, callback=None):
    """Process data according to configuration.
    
    This function processes input data using the provided
    configuration and optionally calls a callback function.
    
    Args:
        data: Input data to process
        config: Configuration dictionary
        callback: Optional callback function
        
    Returns:
        Processed data result
        
    Raises:
        ValueError: If data format is invalid
        KeyError: If required config key missing
        
    Examples:
        >>> result = process_data({'x': 1}, {'mode': 'fast'})
        >>> print(result)
        {'x': 2}
    """
```

### Improvement Suggestions

Enhances existing documentation:

```python
# Before
def calculate(x, y):
    """Calculate result."""
    
# After (suggested improvement)
def calculate(x: float, y: float) -> float:
    """Calculate the sum of two numbers.
    
    Args:
        x: First number
        y: Second number
        
    Returns:
        Sum of x and y
    """
```

## Configuration

Configure quality checking in your project:

```yaml
# .velocitytree/config.yaml
documentation:
  quality:
    style: google  # google, numpy, sphinx
    min_score: 80
    enforce_examples: true
    max_line_length: 79
    check_grammar: true
```

## Best Practices

1. **Start Early**: Document as you code
2. **Be Specific**: Avoid generic descriptions
3. **Include Examples**: Show how to use complex functions
4. **Update Regularly**: Keep docs in sync with code
5. **Review Periodically**: Run quality checks in CI/CD

## Integration

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: doc-quality
        name: Check documentation quality
        entry: vtree doc check
        language: system
        files: \.py$
```

### CI/CD Pipeline

```yaml
# .github/workflows/docs.yml
name: Documentation Quality
on: [push, pull_request]

jobs:
  quality-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check documentation
        run: |
          vtree doc check src/ --recursive
          vtree doc suggest src/ --output suggestions.json
      - name: Upload suggestions
        uses: actions/upload-artifact@v3
        with:
          name: doc-suggestions
          path: suggestions.json
```

## API Reference

### Python API

```python
from velocitytree.documentation import DocQualityChecker, DocSuggestionEngine

# Check quality
checker = DocQualityChecker(style=DocStyle.GOOGLE)
report = checker.check_quality(module_analysis)

print(f"Score: {report.overall_score}/100")
for issue in report.issues:
    print(f"{issue.severity}: {issue.message}")

# Get suggestions
engine = DocSuggestionEngine()
suggestion = engine.suggest_docstring(function, 'function')
print(suggestion)
```

### Custom Rules

Create custom quality rules:

```python
from velocitytree.documentation.quality import SuggestionRule

custom_rule = SuggestionRule(
    name="require_version_info",
    condition=lambda m: '@version' not in (m.docstring or ''),
    message="Add @version tag to module docstring",
    severity=DocSeverity.INFO,
)

checker.rules['custom'].append(custom_rule)
```