# Smart Template Selection

VelocityTree's documentation system includes intelligent template selection that automatically chooses the best documentation template based on code characteristics.

## Overview

Smart template selection analyzes your code to determine:
- Code type (API, CLI tool, library, test file)
- Documentation style (Google, NumPy, Sphinx)
- Project context and patterns
- Language-specific features

## How It Works

### Code Pattern Detection

The system detects various code patterns:

#### API Detection
- Flask, FastAPI, Django imports
- Route decorators (`@app.route`)
- API endpoint patterns
- RESTful method names

#### CLI Tool Detection
- Click, argparse imports
- Command decorators
- Main function patterns
- Argument parsing

#### Library Detection
- `setup.py` presence
- `__init__.py` files
- Package structure
- Version variables

#### Test File Detection
- Test file naming (`test_*.py`, `*_test.py`)
- pytest/unittest imports
- Test function patterns
- Test class definitions

### Documentation Style Detection

Automatically detects existing documentation styles:

#### Google Style
```python
def function(param1, param2):
    """Brief description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
    """
```

#### NumPy Style
```python
def function(param1, param2):
    """
    Brief description.
    
    Parameters
    ----------
    param1 : type
        Description of param1
    param2 : type
        Description of param2
        
    Returns
    -------
    type
        Description of return value
    """
```

#### Sphinx Style
```python
def function(param1, param2):
    """Brief description.
    
    :param param1: Description of param1
    :param param2: Description of param2
    :return: Description of return value
    :rtype: type
    """
```

## Template Scoring

Templates are scored based on multiple factors:

### Scoring Factors

1. **Type Match** (20 points)
   - Exact match between doc type and template type

2. **API Detection** (15 points)  
   - Bonus for API templates when API patterns detected

3. **Style Match** (10 points)
   - Template style matches detected docstring style

4. **Pattern Matching** (15 points each)
   - Library patterns
   - CLI patterns  
   - Test patterns

5. **Context Matching** (10 points)
   - Project type alignment
   - Custom preferences

6. **Template Completeness** (up to 10 points)
   - Ratio of optional to required fields

7. **Custom Template Preference** (5 points)
   - Bonus for user-created templates

### Example Scoring

```python
# API module with Flask
template_scores = {
    "api_reference_markdown": 85,  # Best match
    "module_markdown": 70,         # Good match
    "function_markdown": 45,       # Poor match
}
```

## Usage

### Automatic Selection

```python
from velocitytree.documentation import DocGenerator

generator = DocGenerator()

# Automatic template selection
result = generator.generate_documentation(
    source="api_module.py",
    smart_selection=True  # Default
)
```

### Manual Override

```python
# Override with specific template
result = generator.generate_documentation(
    source="module.py",
    template=my_custom_template,
    smart_selection=False
)
```

### With Context Hints

```python
# Provide context for better selection
result = generator.generate_documentation(
    source="module.py",
    context={
        "project_type": "api",
        "template_preferences": {
            "style": "google",
            "include_examples": True
        }
    }
)
```

## Template Suggestions

The system provides improvement suggestions:

```python
selector = TemplateSelector()
template = selector.select_template(source)
suggestions = selector.suggest_improvements(template, source)

# Example suggestions:
# - "Consider using API documentation template"
# - "Docstring style appears to be NumPy, but template uses Google"
# - "Consider template 'cli_tool_markdown' (score: 82.5)"
```

## Configuration

### Enable/Disable Smart Selection

```python
config = DocConfig(
    smart_selection=True,  # Enable smart selection
    preferred_templates=["custom_api", "api_reference"]
)

generator = DocGenerator(config)
```

### Custom Pattern Detection

Add custom patterns for detection:

```python
selector = TemplateSelector()

# Add custom patterns
selector.patterns['microservice'] = [
    r'@app\.health_check',
    r'from prometheus_client import',
    r'class.*Service',
]
```

## Creating Smart Templates

Design templates that work well with smart selection:

### Template Metadata

```yaml
name: smart_api_template
doc_type: module
format: markdown
style: google
tags:
  - api
  - rest
  - flask
patterns:
  - "@app.route"
  - "from flask import"
```

### Context-Aware Placeholders

```markdown
# {module_name}

{if is_api}
## API Endpoints

{api_endpoints}
{endif}

{if is_cli}
## Command Line Usage

{cli_usage}
{endif}
```

## Best Practices

### Template Design

1. **Use descriptive names** that indicate purpose
2. **Include relevant tags** for pattern matching
3. **Support multiple styles** where appropriate
4. **Provide fallback content** for missing data

### Pattern Detection

1. **Be specific** with patterns to avoid false positives
2. **Test patterns** against various code styles
3. **Consider imports** as strong indicators
4. **Check for decorators** and class patterns

### Context Usage

1. **Provide project metadata** when available
2. **Set preferences** for consistent output
3. **Use tags** to guide selection
4. **Override** when automatic selection fails

## Troubleshooting

### Wrong Template Selected

**Problem**: Incorrect template chosen
**Solution**: 
- Add context hints
- Adjust pattern detection
- Use manual override

### Style Mismatch

**Problem**: Template style doesn't match code
**Solution**:
- Let system detect style automatically
- Create style-specific templates
- Use style conversion

### Missing Patterns

**Problem**: Code type not detected
**Solution**:
- Add custom patterns
- Extend detection logic
- Provide explicit context

## Advanced Usage

### Custom Scoring Logic

```python
class CustomTemplateSelector(TemplateSelector):
    def _score_template(self, template, source, context):
        score = super()._score_template(template, source, context)
        
        # Add custom scoring
        if "microservice" in context.get("tags", []):
            if "microservice" in template.name:
                score.score += 20
                score.reasoning["microservice_match"] = 20
                
        return score
```

### Pattern Combinations

```python
# Detect GraphQL APIs
if (self._has_pattern(source, r'from graphene import') and
    self._has_pattern(source, r'class.*Query.*Schema')):
    score += 15
    reasoning["graphql_api"] = 15
```

### Dynamic Template Loading

```python
def load_project_templates(project_path):
    """Load templates specific to project type."""
    templates = []
    
    if (project_path / "setup.py").exists():
        templates.extend(load_library_templates())
    
    if (project_path / "manage.py").exists():
        templates.extend(load_django_templates())
        
    return templates
```

## Future Enhancements

Planned improvements include:
- Machine learning-based selection
- Template recommendation engine
- Cross-project template sharing
- IDE integration with real-time suggestions
- Template evolution tracking
- Multi-language support