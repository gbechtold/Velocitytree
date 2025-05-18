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
from .template_selector import TemplateSelector
from .quality import DocQualityChecker, DocSuggestionEngine
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
        self.template_selector = TemplateSelector(self.template_manager)
        self.quality_checker = DocQualityChecker(self.config.style)
        self.suggestion_engine = DocSuggestionEngine()
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
        template: Optional[DocTemplate] = None,
        smart_selection: bool = True,
    ) -> DocumentationResult:
        """Generate documentation for a source.
        
        Args:
            source: Source code path or analysis result
            doc_type: Type of documentation to generate
            format: Output format (uses config default if not specified)
            style: Documentation style (uses config default if not specified)
            template: Specific template to use (overrides smart selection)
            smart_selection: Whether to use smart template selection
            
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
            
        # Store current analysis for quality checker
        self._current_analysis = module_analysis
            
        # Select template if not provided
        if template is None and smart_selection:
            template = self.template_selector.select_template(
                source=module_analysis,
                doc_type=doc_type,
                config=self.config,
            )
            
            # Get suggestions for improvement
            suggestions = self.template_selector.suggest_improvements(
                template=template,
                source=module_analysis,
            )
            if suggestions:
                logger.info("Template selection suggestions:")
                for suggestion in suggestions:
                    logger.info(f"  - {suggestion}")
            
        # Generate documentation based on type or template
        if template:
            # Use template-based generation
            doc_content = self._generate_with_template(
                module_analysis, 
                template,
                style
            )
        else:
            # Use default generation methods
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
        
    def _generate_with_template(
        self,
        analysis: Union[ModuleAnalysis, ClassAnalysis, FunctionAnalysis],
        template: DocTemplate,
        style: DocStyle,
    ) -> Dict[str, Any]:
        """Generate documentation using a specific template.
        
        Args:
            analysis: Code analysis result
            template: Template to use
            style: Documentation style
            
        Returns:
            Generated documentation content
        """
        # Get context for template
        context = self.template_selector.get_template_context(analysis, template)
        
        # Add style-specific formatting
        if style == DocStyle.GOOGLE:
            context = self._apply_google_style(context, analysis)
        elif style == DocStyle.NUMPY:
            context = self._apply_numpy_style(context, analysis)
        elif style == DocStyle.SPHINX:
            context = self._apply_sphinx_style(context, analysis)
            
        # Render template
        rendered = self.template_manager.render_template(
            template=template,
            context=context,
            strict=False,  # Allow missing fields
        )
        
        # Return as structured content
        return {
            "content": rendered,
            "template": template.name,
            "context": context,
        }
        
    def _apply_google_style(self, context: Dict[str, Any], analysis: Any) -> Dict[str, Any]:
        """Apply Google documentation style to context.
        
        Args:
            context: Template context
            analysis: Code analysis
            
        Returns:
            Updated context
        """
        # Format parameters for Google style
        if 'parameters' in context and isinstance(context['parameters'], str):
            params_list = context['parameters'].split(', ')
            formatted_params = []
            for param in params_list:
                formatted_params.append(f"    {param}: Description of {param}")
            context['parameters'] = '\n'.join(formatted_params)
            
        # Format returns for Google style
        if 'returns' in context and not context['returns'].startswith('    '):
            context['returns'] = f"    {context['returns']}"
            
        return context
        
    def _apply_numpy_style(self, context: Dict[str, Any], analysis: Any) -> Dict[str, Any]:
        """Apply NumPy documentation style to context.
        
        Args:
            context: Template context
            analysis: Code analysis
            
        Returns:
            Updated context
        """
        # Format parameters for NumPy style
        if 'parameters' in context and isinstance(context['parameters'], str):
            params_list = context['parameters'].split(', ')
            formatted_params = []
            formatted_params.append("----------")
            for param in params_list:
                formatted_params.append(f"{param} : type")
                formatted_params.append(f"    Description of {param}")
                formatted_params.append("")
            context['parameters'] = '\n'.join(formatted_params)
            
        # Format returns for NumPy style
        if 'returns' in context:
            context['returns'] = f"-------\ntype\n    {context['returns']}"
            
        return context
        
    def _apply_sphinx_style(self, context: Dict[str, Any], analysis: Any) -> Dict[str, Any]:
        """Apply Sphinx documentation style to context.
        
        Args:
            context: Template context
            analysis: Code analysis
            
        Returns:
            Updated context
        """
        # Format parameters for Sphinx style
        if 'parameters' in context and isinstance(context['parameters'], str):
            params_list = context['parameters'].split(', ')
            formatted_params = []
            for param in params_list:
                formatted_params.append(f":param {param}: Description of {param}")
                formatted_params.append(f":type {param}: type")
            context['parameters'] = '\n'.join(formatted_params)
            
        # Format returns for Sphinx style
        if 'returns' in context:
            context['returns'] = f":returns: {context['returns']}\n:rtype: type"
            
        return context
        
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
        """Check documentation quality using quality checker."""
        # Use the quality checker for comprehensive analysis
        quality_report = self.quality_checker.check_quality(analysis)
        return quality_report.issues
        
    def _calculate_quality_score(self, issues: List[DocIssue]) -> float:
        """Calculate documentation quality score."""
        # Run full quality analysis to get proper scores
        quality_report = self.quality_checker.check_quality(self._current_analysis)
        return quality_report.overall_score
        
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
        
    def suggest_improvements(
        self,
        source: Union[str, Path, ModuleAnalysis],
        doc_type: DocType = DocType.MODULE,
    ) -> Dict[str, Any]:
        """Suggest documentation improvements for a source.
        
        Args:
            source: Source code path or analysis result
            doc_type: Type of documentation to analyze
            
        Returns:
            Dictionary with suggestions and quality metrics
        """
        # Get analysis if needed
        if isinstance(source, (str, Path)):
            module_analysis = self.analyzer.analyze_file(source)
            if not module_analysis:
                raise ValueError(f"Could not analyze file: {source}")
        else:
            module_analysis = source
            
        # Run quality check
        quality_report = self.quality_checker.check_quality(module_analysis)
        
        # Generate specific suggestions
        element_suggestions = {}
        
        # Suggest improvements for module
        if not module_analysis.docstring:
            element_suggestions['module'] = self.suggestion_engine.suggest_docstring(
                module_analysis, 'module'
            )
            
        # Suggest improvements for functions
        for func in module_analysis.functions:
            if not func.docstring:
                element_suggestions[f'function:{func.name}'] = self.suggestion_engine.suggest_docstring(
                    func, 'function'
                )
            elif quality_report.issues:
                # Improve existing docstring
                func_issues = [i for i in quality_report.issues if func.name in i.location]
                if func_issues:
                    improved = self.suggestion_engine.improve_docstring(
                        func.docstring, func, func_issues
                    )
                    if improved != func.docstring:
                        element_suggestions[f'function:{func.name}'] = improved
                        
        # Suggest improvements for classes
        for cls in module_analysis.classes:
            if not cls.docstring:
                element_suggestions[f'class:{cls.name}'] = self.suggestion_engine.suggest_docstring(
                    cls, 'class'
                )
                
            # Check methods
            for method in cls.methods:
                if not method.docstring and not method.name.startswith('_'):
                    element_suggestions[f'method:{cls.name}.{method.name}'] = self.suggestion_engine.suggest_docstring(
                        method, 'function'
                    )
                    
        return {
            'quality_report': {
                'overall_score': quality_report.overall_score,
                'metric_scores': {k.value: v for k, v in quality_report.metric_scores.items()},
                'issues': [{
                    'severity': issue.severity.value,
                    'location': issue.location,
                    'message': issue.message,
                    'category': getattr(issue, '_category', 'unknown'),
                } for issue in quality_report.issues],
                'suggestions': quality_report.suggestions,
                'statistics': quality_report.statistics,
            },
            'element_suggestions': element_suggestions,
            'summary': self._summarize_suggestions(quality_report, element_suggestions),
        }
        
    def _summarize_suggestions(
        self,
        quality_report: Any,
        element_suggestions: Dict[str, str],
    ) -> str:
        """Create a summary of improvement suggestions."""
        lines = []
        
        # Overall score
        lines.append(f"Documentation Quality Score: {quality_report.overall_score:.1f}/100")
        lines.append("")
        
        # Critical issues
        critical_issues = [i for i in quality_report.issues if i.severity in [DocSeverity.ERROR, DocSeverity.WARNING]]
        if critical_issues:
            lines.append(f"Critical Issues ({len(critical_issues)}):")
            for issue in critical_issues[:5]:
                lines.append(f"  • {issue.location}: {issue.message}")
            lines.append("")
            
        # Missing documentation
        missing_count = len(element_suggestions)
        if missing_count > 0:
            lines.append(f"Missing Documentation ({missing_count} elements):")
            for element, suggestion in list(element_suggestions.items())[:5]:
                element_type, name = element.split(':', 1)
                lines.append(f"  • {element_type.capitalize()} '{name}' needs documentation")
            if missing_count > 5:
                lines.append(f"  ... and {missing_count - 5} more")
            lines.append("")
            
        # General suggestions
        if quality_report.suggestions:
            lines.append("Improvement Suggestions:")
            for suggestion in quality_report.suggestions[:5]:
                lines.append(f"  • {suggestion}")
                
        return "\n".join(lines)