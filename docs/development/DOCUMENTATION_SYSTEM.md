# Documentation Generation System

VelocityTree includes an AI-powered documentation generation system that automatically creates and maintains documentation for your codebase.

## Overview

The documentation system provides:
- Automatic generation from code analysis
- Multiple output formats (Markdown, HTML, RST, JSON, YAML)
- Template-based customization
- Quality checking and completeness scoring
- Support for various documentation styles (Google, NumPy, Sphinx)

## Features

### Multi-Format Support

Generate documentation in various formats:
- **Markdown**: GitHub-compatible documentation
- **HTML**: Web-ready documentation
- **reStructuredText**: Sphinx-compatible docs
- **JSON**: Machine-readable format
- **YAML**: Configuration-friendly format

### Documentation Types

- **Module Documentation**: Complete module overview
- **API Reference**: Detailed API documentation
- **Class Documentation**: Class-specific docs
- **Function Documentation**: Function/method docs
- **README Generation**: Project readme files
- **Changelog Creation**: Version history

### Quality Analysis

- Missing docstring detection
- Incomplete documentation warnings
- Parameter documentation validation
- Return value documentation checks
- Example code verification

## Usage

### Command Line

```bash
# Generate module documentation
vtree doc generate module.py

# Generate API reference
vtree doc generate --type api src/

# Generate in different formats
vtree doc generate --format html module.py
vtree doc generate --format rst module.py

# Generate with custom template
vtree doc generate --template custom_module module.py
```

### Programmatic Usage

```python
from velocitytree.documentation import DocGenerator, DocFormat, DocType

# Create generator
generator = DocGenerator()

# Generate module documentation
result = generator.generate_documentation(
    source="module.py",
    doc_type=DocType.MODULE,
    format=DocFormat.MARKDOWN
)

# Access generated content
print(result.content)
print(f"Quality Score: {result.quality_score}")
print(f"Completeness: {result.completeness_score}%")

# Check for issues
for issue in result.issues:
    print(f"{issue.severity}: {issue.message}")
```

### Custom Configuration

```python
from velocitytree.documentation import DocConfig, DocStyle

config = DocConfig(
    format=DocFormat.MARKDOWN,
    style=DocStyle.GOOGLE,
    include_examples=True,
    include_private=False,
    table_of_contents=True
)

generator = DocGenerator(config)
```

## Templates

### Built-in Templates

The system includes templates for:
- Module documentation
- Function documentation
- Class documentation
- API references
- README files
- Changelogs

### Custom Templates

Create custom templates:

```python
from velocitytree.documentation import TemplateManager, DocTemplate

manager = TemplateManager()

# Create from existing file
template = manager.create_template_from_example(
    name="my_module",
    example_file="docs/example.md",
    doc_type=DocType.MODULE,
    format=DocFormat.MARKDOWN
)

# Save custom template
manager.save_template(template)
```

### Template Syntax

Templates use placeholder syntax:

```markdown
# {module_name}

{module_description}

## Installation

```bash
pip install {package_name}
```

## Usage

{usage_examples}
```

## Documentation Styles

### Google Style

```python
def function(param1: int, param2: str) -> bool:
    """Brief description.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is negative
    """
```

### NumPy Style

```python
def function(param1, param2):
    """
    Brief description.
    
    Parameters
    ----------
    param1 : int
        Description of param1
    param2 : str
        Description of param2
        
    Returns
    -------
    bool
        Description of return value
    """
```

## Quality Metrics

### Completeness Score

Measures documentation coverage:
- Module docstring: 10%
- Class docstrings: 20%
- Public method docstrings: 40%
- Parameter documentation: 20%
- Return value documentation: 10%

### Quality Score

Based on:
- Missing docstrings (high severity)
- Incomplete parameters (medium severity)
- Missing examples (low severity)
- Style consistency (info)

## Integration

### With Code Analysis

```python
from velocitytree.code_analysis import CodeAnalyzer
from velocitytree.documentation import DocGenerator

# Analyze code
analyzer = CodeAnalyzer()
analysis = analyzer.analyze_file("module.py")

# Generate documentation from analysis
generator = DocGenerator()
result = generator.generate_documentation(
    source=analysis,  # Use analysis result directly
    doc_type=DocType.MODULE
)
```

### With Git Hooks

```bash
#!/bin/sh
# .git/hooks/pre-commit

# Update documentation before commit
vtree doc generate --update src/
git add docs/
```

### With CI/CD

```yaml
# GitHub Actions example
- name: Generate Documentation
  run: |
    vtree doc generate src/ --output docs/
    
- name: Deploy Documentation
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./docs
```

## Advanced Features

### Incremental Updates

Update only changed files:

```python
generator.update_documentation(
    directory="src/",
    incremental=True,
    since="last-commit"
)
```

### Batch Processing

Generate documentation for multiple files:

```python
from pathlib import Path

for py_file in Path("src").rglob("*.py"):
    result = generator.generate_documentation(py_file)
    output_file = Path("docs") / f"{py_file.stem}.md"
    output_file.write_text(result.content)
```

### Cross-References

Automatically link related documentation:

```python
config = DocConfig(
    auto_links=True,
    cross_reference=True
)

generator = DocGenerator(config)
```

## Best Practices

### Docstring Guidelines

1. **Always include docstrings** for public modules, classes, and functions
2. **Use consistent style** throughout the project
3. **Document parameters** with types and descriptions
4. **Include examples** for complex functions
5. **Document exceptions** that can be raised

### Template Design

1. **Keep templates modular** for reusability
2. **Use meaningful placeholders**
3. **Include all necessary sections**
4. **Provide default values** for optional fields
5. **Test with various inputs**

### Automation

1. **Set up pre-commit hooks** for documentation updates
2. **Include in CI/CD pipeline** for automatic generation
3. **Version control templates** for consistency
4. **Monitor documentation quality** metrics
5. **Schedule periodic reviews**

## Troubleshooting

### Common Issues

**Missing Docstrings**
- Solution: Add docstrings to all public APIs
- Use `--include-private` for internal docs

**Incorrect Parsing**
- Solution: Ensure docstring format matches style
- Check for syntax errors in docstrings

**Template Errors**
- Solution: Verify all required fields are provided
- Check placeholder names match

**Performance Issues**
- Solution: Use incremental updates
- Cache analysis results
- Limit file patterns

## Future Enhancements

Planned features include:
- AI-powered docstring generation
- Multi-language support
- Documentation diffing
- Interactive documentation editor
- Real-time preview
- Documentation linting
- API versioning support