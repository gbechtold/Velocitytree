"""Template management for documentation generation."""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from .models import DocTemplate, DocType, DocFormat, DocStyle


class TemplateManager:
    """Manage documentation templates."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize template manager.
        
        Args:
            template_dir: Directory containing templates
        """
        self.template_dir = template_dir or self._default_template_dir()
        self.templates: Dict[str, DocTemplate] = {}
        self._load_builtin_templates()
        if self.template_dir.exists():
            self._load_custom_templates()
            
    def _default_template_dir(self) -> Path:
        """Get default template directory."""
        return Path.home() / ".velocitytree" / "templates"
        
    def _load_builtin_templates(self):
        """Load built-in templates."""
        # Module documentation template
        self.templates["module_markdown"] = DocTemplate(
            name="module_markdown",
            doc_type=DocType.MODULE,
            format=DocFormat.MARKDOWN,
            style=DocStyle.GOOGLE,
            content="""# {module_name}

{module_description}

## Overview

{overview}

## Installation

```bash
pip install {package_name}
```

## Usage

{usage_examples}

## API Reference

{api_reference}

## Examples

{examples}

## Contributing

{contributing}

## License

{license}
""",
            placeholders=[
                "module_name",
                "module_description",
                "overview",
                "package_name",
                "usage_examples",
                "api_reference",
                "examples",
                "contributing",
                "license",
            ],
            required_fields=["module_name", "module_description"],
        )
        
        # Function documentation template
        self.templates["function_markdown"] = DocTemplate(
            name="function_markdown",
            doc_type=DocType.FUNCTION,
            format=DocFormat.MARKDOWN,
            style=DocStyle.GOOGLE,
            content="""### {function_name}

```python
{function_signature}
```

{description}

**Parameters:**

{parameters}

**Returns:**

{returns}

**Raises:**

{raises}

**Examples:**

```python
{examples}
```

**See Also:**

{see_also}
""",
            placeholders=[
                "function_name",
                "function_signature",
                "description",
                "parameters",
                "returns",
                "raises",
                "examples",
                "see_also",
            ],
            required_fields=["function_name", "function_signature"],
        )
        
        # Class documentation template
        self.templates["class_markdown"] = DocTemplate(
            name="class_markdown",
            doc_type=DocType.CLASS,
            format=DocFormat.MARKDOWN,
            style=DocStyle.GOOGLE,
            content="""## {class_name}

```python
class {class_name}({base_classes})
```

{description}

### Attributes

{attributes}

### Methods

{methods}

### Examples

```python
{examples}
```

### Notes

{notes}
""",
            placeholders=[
                "class_name",
                "base_classes",
                "description",
                "attributes",
                "methods",
                "examples",
                "notes",
            ],
            required_fields=["class_name"],
        )
        
        # API reference template
        self.templates["api_reference_markdown"] = DocTemplate(
            name="api_reference_markdown",
            doc_type=DocType.API,
            format=DocFormat.MARKDOWN,
            style=DocStyle.GOOGLE,
            content="""# API Reference

## Overview

{overview}

## Modules

{modules}

## Classes

{classes}

## Functions

{functions}

## Constants

{constants}

## Exceptions

{exceptions}

## Index

{index}
""",
            placeholders=[
                "overview",
                "modules",
                "classes",
                "functions",
                "constants",
                "exceptions",
                "index",
            ],
            required_fields=["overview"],
        )
        
        # README template
        self.templates["readme_markdown"] = DocTemplate(
            name="readme_markdown",
            doc_type=DocType.README,
            format=DocFormat.MARKDOWN,
            style=DocStyle.MARKDOWN,
            content="""# {project_name}

{badges}

{description}

## Features

{features}

## Installation

{installation}

## Quick Start

{quick_start}

## Documentation

{documentation_link}

## Contributing

{contributing}

## License

{license}

## Authors

{authors}

## Acknowledgments

{acknowledgments}
""",
            placeholders=[
                "project_name",
                "badges",
                "description",
                "features",
                "installation",
                "quick_start",
                "documentation_link",
                "contributing",
                "license",
                "authors",
                "acknowledgments",
            ],
            required_fields=["project_name", "description"],
        )
        
        # Changelog template
        self.templates["changelog_markdown"] = DocTemplate(
            name="changelog_markdown",
            doc_type=DocType.CHANGELOG,
            format=DocFormat.MARKDOWN,
            style=DocStyle.MARKDOWN,
            content="""# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
{added}

### Changed
{changed}

### Deprecated
{deprecated}

### Removed
{removed}

### Fixed
{fixed}

### Security
{security}

## [{version}] - {date}

{version_changes}

[Unreleased]: {unreleased_link}
[{version}]: {version_link}
""",
            placeholders=[
                "added",
                "changed",
                "deprecated",
                "removed",
                "fixed",
                "security",
                "version",
                "date",
                "version_changes",
                "unreleased_link",
                "version_link",
            ],
            required_fields=["version", "date"],
        )
        
    def _load_custom_templates(self):
        """Load custom templates from directory."""
        for template_file in self.template_dir.glob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_data = yaml.safe_load(f)
                    
                template = DocTemplate(
                    name=template_data["name"],
                    doc_type=DocType(template_data["doc_type"]),
                    format=DocFormat(template_data["format"]),
                    style=DocStyle(template_data["style"]),
                    content=template_data["content"],
                    placeholders=template_data.get("placeholders", []),
                    required_fields=template_data.get("required_fields", []),
                    optional_fields=template_data.get("optional_fields", []),
                )
                
                self.templates[template.name] = template
                
            except Exception as e:
                print(f"Error loading template {template_file}: {e}")
                
    def get_template(
        self,
        doc_type: DocType,
        format: DocFormat,
        style: Optional[DocStyle] = None,
        name: Optional[str] = None,
    ) -> Optional[DocTemplate]:
        """Get a template by criteria.
        
        Args:
            doc_type: Type of documentation
            format: Output format
            style: Documentation style
            name: Specific template name
            
        Returns:
            Matching template or None
        """
        if name and name in self.templates:
            return self.templates[name]
            
        # Find matching templates
        matches = []
        for template in self.templates.values():
            if template.doc_type == doc_type and template.format == format:
                if style is None or template.style == style:
                    matches.append(template)
                    
        # Return best match (prefer custom templates)
        if matches:
            custom_matches = [t for t in matches if t.name.startswith("custom_")]
            return custom_matches[0] if custom_matches else matches[0]
            
        return None
        
    def list_templates(
        self,
        doc_type: Optional[DocType] = None,
        format: Optional[DocFormat] = None,
    ) -> List[DocTemplate]:
        """List available templates.
        
        Args:
            doc_type: Filter by documentation type
            format: Filter by output format
            
        Returns:
            List of matching templates
        """
        templates = list(self.templates.values())
        
        if doc_type:
            templates = [t for t in templates if t.doc_type == doc_type]
            
        if format:
            templates = [t for t in templates if t.format == format]
            
        return templates
        
    def save_template(self, template: DocTemplate, overwrite: bool = False):
        """Save a template to disk.
        
        Args:
            template: Template to save
            overwrite: Whether to overwrite existing template
        """
        if not overwrite and template.name in self.templates:
            raise ValueError(f"Template {template.name} already exists")
            
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        template_file = self.template_dir / f"{template.name}.yaml"
        
        template_data = {
            "name": template.name,
            "doc_type": template.doc_type.value,
            "format": template.format.value,
            "style": template.style.value,
            "content": template.content,
            "placeholders": template.placeholders,
            "required_fields": template.required_fields,
            "optional_fields": template.optional_fields,
        }
        
        with open(template_file, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False)
            
        self.templates[template.name] = template
        
    def delete_template(self, name: str):
        """Delete a template.
        
        Args:
            name: Template name to delete
        """
        if name not in self.templates:
            raise ValueError(f"Template {name} not found")
            
        # Don't delete built-in templates
        if not name.startswith("custom_"):
            raise ValueError("Cannot delete built-in templates")
            
        template_file = self.template_dir / f"{name}.yaml"
        if template_file.exists():
            template_file.unlink()
            
        del self.templates[name]
        
    def render_template(
        self,
        template: DocTemplate,
        context: Dict[str, Any],
        strict: bool = True,
    ) -> str:
        """Render a template with context.
        
        Args:
            template: Template to render
            context: Context data for placeholders
            strict: Whether to require all required fields
            
        Returns:
            Rendered template content
        """
        if strict:
            missing_fields = set(template.required_fields) - set(context.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
                
        rendered = template.content
        
        for placeholder in template.placeholders:
            value = context.get(placeholder, f"{{{placeholder}}}")
            rendered = rendered.replace(f"{{{placeholder}}}", str(value))
            
        return rendered
        
    def create_template_from_example(
        self,
        name: str,
        example_file: Path,
        doc_type: DocType,
        format: DocFormat,
        style: DocStyle = DocStyle.GOOGLE,
    ) -> DocTemplate:
        """Create a template from an example file.
        
        Args:
            name: Template name
            example_file: Example documentation file
            doc_type: Documentation type
            format: Output format
            style: Documentation style
            
        Returns:
            Created template
        """
        with open(example_file, 'r') as f:
            content = f.read()
            
        # Extract placeholders from content
        import re
        placeholders = re.findall(r'\{(\w+)\}', content)
        
        template = DocTemplate(
            name=f"custom_{name}",
            doc_type=doc_type,
            format=format,
            style=style,
            content=content,
            placeholders=list(set(placeholders)),
            required_fields=[],  # User should set these
            optional_fields=list(set(placeholders)),
        )
        
        self.save_template(template)
        
        return template