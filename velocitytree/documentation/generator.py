"""Documentation generator for VelocityTree."""

import ast
import inspect
import os
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Union, Any, Tuple

from ..code_analysis.analyzer import CodeAnalyzer
from ..code_analysis.models import (
    ModuleAnalysis,
    ClassAnalysis,
    FunctionAnalysis,
    LanguageSupport,
)
from .models import (
    DocFormat,
    DocType,
    DocStyle,
    DocSeverity,
    DocTemplate,
    DocSection,
    DocIssue,
    DocMetadata,
    DocumentationResult,
    DocConfig,
    FunctionDoc,
    ClassDoc,
    ModuleDoc,
)
from .templates import TemplateManager
from ..utils import logger


class DocGenerator:
    """Generate documentation from code analysis results."""
    
    def __init__(self, config: Optional[DocConfig] = None):
        """Initialize the documentation generator.
        
        Args:
            config: Documentation configuration
        """
        self.config = config or DocConfig()
        self.analyzer = CodeAnalyzer()
        self.template_manager = TemplateManager()
        self._init_formatters()
        
    def _init_formatters(self):
        """Initialize format-specific formatters."""
        self.formatters = {
            DocFormat.MARKDOWN: self._format_markdown,
            DocFormat.HTML: self._format_html,
            DocFormat.RST: self._format_rst,
            DocFormat.JSON: self._format_json,
            DocFormat.YAML: self._format_yaml,
        }
        
    def generate_documentation(
        self,
        source: Union[str, Path, ModuleAnalysis],
        doc_type: DocType = DocType.MODULE,
        format: Optional[DocFormat] = None,
        style: Optional[DocStyle] = None,
    ) -> DocumentationResult:
        """Generate documentation for a source.
        
        Args:
            source: Source code path or analysis result
            doc_type: Type of documentation to generate
            format: Output format (uses config default if not specified)
            style: Documentation style (uses config default if not specified)
            
        Returns:
            Generated documentation result
        """
        start_time = time.time()
        
        # Use defaults from config if not specified
        format = format or self.config.format
        style = style or self.config.style
        
        # Get analysis if needed
        if isinstance(source, (str, Path)):
            module_analysis = self.analyzer.analyze_file(source)
            if not module_analysis:
                raise ValueError(f"Could not analyze file: {source}")
        else:
            module_analysis = source
            
        # Generate documentation based on type
        if doc_type == DocType.MODULE:
            doc_content = self._generate_module_doc(module_analysis, style)
        elif doc_type == DocType.CLASS:
            doc_content = self._generate_class_docs(module_analysis, style)
        elif doc_type == DocType.FUNCTION:
            doc_content = self._generate_function_docs(module_analysis, style)
        elif doc_type == DocType.API:
            doc_content = self._generate_api_doc(module_analysis, style)
        else:
            raise ValueError(f"Unsupported documentation type: {doc_type}")
            
        # Format the documentation
        formatter = self.formatters.get(format)
        if not formatter:
            raise ValueError(f"Unsupported format: {format}")
            
        formatted_content = formatter(doc_content)
        
        # Create metadata
        metadata = DocMetadata(
            title=self._get_title(module_analysis, doc_type),
            description=self._get_description(module_analysis, doc_type),
            version=self._get_version(module_analysis),
        )
        
        # Check documentation quality
        issues = self._check_quality(doc_content, module_analysis)
        quality_score = self._calculate_quality_score(issues)
        completeness_score = self._calculate_completeness_score(doc_content, module_analysis)
        
        generation_time = time.time() - start_time
        
        return DocumentationResult(
            content=formatted_content,
            format=format,
            metadata=metadata,
            sections=doc_content.sections if hasattr(doc_content, 'sections') else [],
            issues=issues,
            quality_score=quality_score,
            completeness_score=completeness_score,
            generation_time=generation_time,
        )
        
    def _generate_module_doc(self, module: ModuleAnalysis, style: DocStyle) -> ModuleDoc:
        """Generate documentation for a module."""
        # Extract module docstring
        module_docstring = module.docstring or "No module description available."
        
        # Generate function documentation
        function_docs = []
        for func in module.functions:
            function_docs.append(self._generate_function_doc(func, style))
            
        # Generate class documentation
        class_docs = []
        for cls in module.classes:
            class_docs.append(self._generate_class_doc(cls, style))
            
        return ModuleDoc(
            name=module.file_path,
            description=module_docstring,
            imports=module.imports,
            functions=function_docs,
            classes=class_docs,
            examples=self._extract_examples(module_docstring),
        )
        
    def _generate_class_doc(self, cls: ClassAnalysis, style: DocStyle) -> ClassDoc:
        """Generate documentation for a class."""
        # Generate method documentation
        method_docs = []
        for method in cls.methods:
            method_docs.append(self._generate_function_doc(method, style))
            
        # Extract class attributes from docstring
        attributes = self._extract_attributes(cls.docstring)
        
        return ClassDoc(
            name=cls.name,
            description=cls.docstring or f"{cls.name} class.",
            base_classes=cls.parent_classes,
            attributes=attributes,
            methods=method_docs,
            examples=self._extract_examples(cls.docstring),
        )
        
    def _generate_function_doc(self, func: FunctionAnalysis, style: DocStyle) -> FunctionDoc:
        """Generate documentation for a function."""
        # Parse docstring based on style
        if style == DocStyle.GOOGLE:
            parsed = self._parse_google_docstring(func.docstring)
        elif style == DocStyle.NUMPY:
            parsed = self._parse_numpy_docstring(func.docstring)
        else:
            parsed = self._parse_generic_docstring(func.docstring)
            
        # Create function signature
        signature = self._create_signature(func)
        
        return FunctionDoc(
            name=func.name,
            signature=signature,
            description=parsed.get('description', ''),
            parameters=parsed.get('parameters', {}),
            returns=parsed.get('returns'),
            raises=parsed.get('raises', []),
            examples=parsed.get('examples', []),
            notes=parsed.get('notes'),
        )
        
    def _generate_api_doc(self, module: ModuleAnalysis, style: DocStyle) -> Dict[str, Any]:
        """Generate API reference documentation."""
        sections = []
        
        # Overview section
        overview = DocSection(
            title="API Overview",
            content=module.docstring or "API reference documentation.",
            level=1,
        )
        sections.append(overview)
        
        # Functions section
        if module.functions:
            functions_section = DocSection(
                title="Functions",
                content="",
                level=2,
            )
            
            for func in module.functions:
                func_doc = self._generate_function_doc(func, style)
                func_section = DocSection(
                    title=func.name,
                    content=self._format_function_doc(func_doc),
                    level=3,
                )
                functions_section.subsections.append(func_section)
                
            sections.append(functions_section)
            
        # Classes section
        if module.classes:
            classes_section = DocSection(
                title="Classes",
                content="",
                level=2,
            )
            
            for cls in module.classes:
                cls_doc = self._generate_class_doc(cls, style)
                cls_section = DocSection(
                    title=cls.name,
                    content=self._format_class_doc(cls_doc),
                    level=3,
                )
                classes_section.subsections.append(cls_section)
                
            sections.append(classes_section)
            
        return {"sections": sections}
        
    def _format_markdown(self, content: Union[ModuleDoc, ClassDoc, FunctionDoc, Dict]) -> str:
        """Format documentation as Markdown."""
        if isinstance(content, ModuleDoc):
            return self._format_module_markdown(content)
        elif isinstance(content, ClassDoc):
            return self._format_class_markdown(content)
        elif isinstance(content, FunctionDoc):
            return self._format_function_markdown(content)
        elif isinstance(content, dict) and "sections" in content:
            return self._format_sections_markdown(content["sections"])
        else:
            return str(content)
            
    def _format_module_markdown(self, module: ModuleDoc) -> str:
        """Format module documentation as Markdown."""
        lines = []
        
        # Title
        lines.append(f"# {module.name}")
        lines.append("")
        
        # Description
        lines.append(module.description)
        lines.append("")
        
        # Table of contents
        if self.config.table_of_contents:
            lines.append("## Table of Contents")
            lines.append("")
            if module.functions:
                lines.append("- [Functions](#functions)")
            if module.classes:
                lines.append("- [Classes](#classes)")
            lines.append("")
            
        # Functions
        if module.functions:
            lines.append("## Functions")
            lines.append("")
            for func in module.functions:
                lines.append(self._format_function_markdown(func))
                lines.append("")
                
        # Classes
        if module.classes:
            lines.append("## Classes")
            lines.append("")
            for cls in module.classes:
                lines.append(self._format_class_markdown(cls))
                lines.append("")
                
        return "\n".join(lines)
        
    def _format_class_markdown(self, cls: ClassDoc) -> str:
        """Format class documentation as Markdown."""
        lines = []
        
        # Class name
        lines.append(f"### {cls.name}")
        lines.append("")
        
        # Description
        lines.append(cls.description)
        lines.append("")
        
        # Base classes
        if cls.base_classes:
            lines.append(f"**Inherits from:** {', '.join(cls.base_classes)}")
            lines.append("")
            
        # Attributes
        if cls.attributes:
            lines.append("#### Attributes")
            lines.append("")
            for name, desc in cls.attributes.items():
                lines.append(f"- `{name}`: {desc}")
            lines.append("")
            
        # Methods
        if cls.methods:
            lines.append("#### Methods")
            lines.append("")
            for method in cls.methods:
                lines.append(self._format_function_markdown(method, level=4))
                lines.append("")
                
        # Examples
        if cls.examples:
            lines.append("#### Examples")
            lines.append("")
            for example in cls.examples:
                lines.append("```python")
                lines.append(example)
                lines.append("```")
                lines.append("")
                
        return "\n".join(lines)
        
    def _format_function_markdown(self, func: FunctionDoc, level: int = 3) -> str:
        """Format function documentation as Markdown."""
        lines = []
        heading = "#" * level
        
        # Function signature
        lines.append(f"{heading} `{func.signature}`")
        lines.append("")
        
        # Description
        if func.description:
            lines.append(func.description)
            lines.append("")
            
        # Parameters
        if func.parameters:
            lines.append("**Parameters:**")
            lines.append("")
            for name, desc in func.parameters.items():
                lines.append(f"- `{name}`: {desc}")
            lines.append("")
            
        # Returns
        if func.returns:
            lines.append("**Returns:**")
            lines.append("")
            lines.append(f"{func.returns}")
            lines.append("")
            
        # Raises
        if func.raises:
            lines.append("**Raises:**")
            lines.append("")
            for exc in func.raises:
                lines.append(f"- {exc}")
            lines.append("")
            
        # Examples
        if func.examples:
            lines.append("**Examples:**")
            lines.append("")
            for example in func.examples:
                lines.append("```python")
                lines.append(example)
                lines.append("```")
                lines.append("")
                
        # Notes
        if func.notes:
            lines.append("**Notes:**")
            lines.append("")
            lines.append(func.notes)
            lines.append("")
            
        return "\n".join(lines)
        
    def _format_html(self, content: Any) -> str:
        """Format documentation as HTML."""
        # Basic HTML formatting
        html_content = "<html><body>"
        html_content += self._content_to_html(content)
        html_content += "</body></html>"
        return html_content
        
    def _format_rst(self, content: Any) -> str:
        """Format documentation as reStructuredText."""
        # Basic RST formatting
        return self._content_to_rst(content)
        
    def _format_json(self, content: Any) -> str:
        """Format documentation as JSON."""
        import json
        return json.dumps(content, indent=2, default=str)
        
    def _format_yaml(self, content: Any) -> str:
        """Format documentation as YAML."""
        import yaml
        return yaml.dump(content, default_flow_style=False)
        
    def _parse_google_docstring(self, docstring: Optional[str]) -> Dict[str, Any]:
        """Parse Google-style docstring."""
        if not docstring:
            return {}
            
        parsed = {
            'description': '',
            'parameters': {},
            'returns': None,
            'raises': [],
            'examples': [],
            'notes': None,
        }
        
        lines = docstring.split('\n')
        current_section = 'description'
        current_param = None
        
        for line in lines:
            stripped = line.strip()
            
            # Check for section headers
            if stripped in ['Args:', 'Arguments:', 'Parameters:']:
                current_section = 'parameters'
                continue
            elif stripped in ['Returns:', 'Return:']:
                current_section = 'returns'
                continue
            elif stripped in ['Raises:', 'Raise:']:
                current_section = 'raises'
                continue
            elif stripped in ['Example:', 'Examples:']:
                current_section = 'examples'
                continue
            elif stripped in ['Note:', 'Notes:']:
                current_section = 'notes'
                continue
                
            # Process content based on current section
            if current_section == 'description' and stripped:
                parsed['description'] += stripped + ' '
            elif current_section == 'parameters' and stripped:
                if ':' in stripped and not line.startswith('    '):
                    param_name, param_desc = stripped.split(':', 1)
                    current_param = param_name.strip()
                    parsed['parameters'][current_param] = param_desc.strip()
                elif current_param and line.startswith('    '):
                    parsed['parameters'][current_param] += ' ' + stripped
            elif current_section == 'returns' and stripped:
                if parsed['returns'] is None:
                    parsed['returns'] = stripped
                else:
                    parsed['returns'] += ' ' + stripped
            elif current_section == 'raises' and stripped:
                parsed['raises'].append(stripped)
            elif current_section == 'examples' and line.strip():
                parsed['examples'].append(line)
            elif current_section == 'notes' and stripped:
                if parsed['notes'] is None:
                    parsed['notes'] = stripped
                else:
                    parsed['notes'] += ' ' + stripped
                    
        # Clean up
        parsed['description'] = parsed['description'].strip()
        if parsed['returns']:
            parsed['returns'] = parsed['returns'].strip()
        if parsed['notes']:
            parsed['notes'] = parsed['notes'].strip()
            
        return parsed
        
    def _parse_numpy_docstring(self, docstring: Optional[str]) -> Dict[str, Any]:
        """Parse NumPy-style docstring."""
        # Similar to Google style but with different section markers
        # Implementation would be similar with adjusted patterns
        return self._parse_google_docstring(docstring)
        
    def _parse_generic_docstring(self, docstring: Optional[str]) -> Dict[str, Any]:
        """Parse generic docstring format."""
        if not docstring:
            return {}
            
        return {
            'description': docstring.strip(),
            'parameters': {},
            'returns': None,
            'raises': [],
            'examples': [],
            'notes': None,
        }
        
    def _create_signature(self, func: FunctionAnalysis) -> str:
        """Create function signature."""
        params = []
        for param in func.parameters:
            if hasattr(func, 'parameter_types') and param in func.parameter_types:
                params.append(f"{param}: {func.parameter_types[param]}")
            else:
                params.append(param)
                
        signature = f"{func.name}({', '.join(params)})"
        
        if func.returns:
            signature += f" -> {func.returns}"
            
        return signature
        
    def _extract_examples(self, docstring: Optional[str]) -> List[str]:
        """Extract code examples from docstring."""
        if not docstring:
            return []
            
        examples = []
        in_example = False
        current_example = []
        
        for line in docstring.split('\n'):
            if '>>>' in line or 'Example:' in line or 'Examples:' in line:
                in_example = True
                if current_example:
                    examples.append('\n'.join(current_example))
                    current_example = []
            elif in_example:
                if line.strip() == '':
                    in_example = False
                    if current_example:
                        examples.append('\n'.join(current_example))
                        current_example = []
                else:
                    current_example.append(line)
                    
        if current_example:
            examples.append('\n'.join(current_example))
            
        return examples
        
    def _extract_attributes(self, docstring: Optional[str]) -> Dict[str, str]:
        """Extract attributes from class docstring."""
        if not docstring:
            return {}
            
        attributes = {}
        in_attributes = False
        
        for line in docstring.split('\n'):
            stripped = line.strip()
            
            if stripped in ['Attributes:', 'Attribute:']:
                in_attributes = True
                continue
            elif in_attributes and stripped and ':' in stripped:
                name, desc = stripped.split(':', 1)
                attributes[name.strip()] = desc.strip()
            elif in_attributes and not stripped:
                in_attributes = False
                
        return attributes
        
    def _check_quality(self, content: Any, analysis: ModuleAnalysis) -> List[DocIssue]:
        """Check documentation quality."""
        issues = []
        
        # Check for missing docstrings
        for func in analysis.functions:
            if not func.docstring:
                issues.append(DocIssue(
                    severity=DocSeverity.WARNING,
                    location=f"Function: {func.name}",
                    message="Missing docstring",
                    suggestion="Add a docstring describing the function's purpose",
                ))
                
        for cls in analysis.classes:
            if not cls.docstring:
                issues.append(DocIssue(
                    severity=DocSeverity.WARNING,
                    location=f"Class: {cls.name}",
                    message="Missing docstring",
                    suggestion="Add a docstring describing the class",
                ))
                
            for method in cls.methods:
                if not method.docstring and not method.name.startswith('_'):
                    issues.append(DocIssue(
                        severity=DocSeverity.WARNING,
                        location=f"Method: {cls.name}.{method.name}",
                        message="Missing docstring",
                        suggestion="Add a docstring describing the method",
                    ))
                    
        # Check for incomplete docstrings
        if isinstance(content, FunctionDoc):
            if content.parameters and not all(content.parameters.values()):
                issues.append(DocIssue(
                    severity=DocSeverity.INFO,
                    location=f"Function: {content.name}",
                    message="Incomplete parameter documentation",
                    suggestion="Document all parameters",
                ))
                
        return issues
        
    def _calculate_quality_score(self, issues: List[DocIssue]) -> float:
        """Calculate documentation quality score."""
        if not issues:
            return 100.0
            
        # Weight by severity
        weights = {
            DocSeverity.ERROR: 10,
            DocSeverity.WARNING: 5,
            DocSeverity.INFO: 2,
            DocSeverity.SUGGESTION: 1,
        }
        
        total_penalty = sum(weights.get(issue.severity, 0) for issue in issues)
        
        # Cap at 0
        score = max(0, 100 - total_penalty)
        
        return score
        
    def _calculate_completeness_score(self, content: Any, analysis: ModuleAnalysis) -> float:
        """Calculate documentation completeness score."""
        total_items = 0
        documented_items = 0
        
        # Count module docstring
        total_items += 1
        if analysis.docstring:
            documented_items += 1
            
        # Count functions
        for func in analysis.functions:
            total_items += 1
            if func.docstring:
                documented_items += 1
                
        # Count classes and methods
        for cls in analysis.classes:
            total_items += 1
            if cls.docstring:
                documented_items += 1
                
            for method in cls.methods:
                if not method.name.startswith('_'):
                    total_items += 1
                    if method.docstring:
                        documented_items += 1
                        
        if total_items == 0:
            return 100.0
            
        return (documented_items / total_items) * 100
        
    def _get_title(self, analysis: ModuleAnalysis, doc_type: DocType) -> str:
        """Get title for documentation."""
        if doc_type == DocType.MODULE:
            return Path(analysis.file_path).stem
        elif doc_type == DocType.API:
            return f"{Path(analysis.file_path).stem} API Reference"
        else:
            return "Documentation"
            
    def _get_description(self, analysis: ModuleAnalysis, doc_type: DocType) -> str:
        """Get description for documentation."""
        if analysis.docstring:
            return analysis.docstring.split('\n')[0]
        else:
            return f"Documentation for {Path(analysis.file_path).name}"
            
    def _get_version(self, analysis: ModuleAnalysis) -> Optional[str]:
        """Extract version from module."""
        # Look for __version__ variable
        for var in analysis.global_variables:
            if var == '__version__':
                # Would need to parse the actual value
                return "1.0.0"
        return None
        
    def _content_to_html(self, content: Any) -> str:
        """Convert content to HTML."""
        # Basic implementation - would be more sophisticated in practice
        return f"<pre>{content}</pre>"
        
    def _content_to_rst(self, content: Any) -> str:
        """Convert content to reStructuredText."""
        # Basic implementation - would be more sophisticated in practice
        return str(content)