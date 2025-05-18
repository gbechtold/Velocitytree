"""Smart template selection for documentation generation."""

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

from ..code_analysis.models import (
    ModuleAnalysis,
    ClassAnalysis,
    FunctionAnalysis,
    LanguageSupport,
)
from .models import (
    DocTemplate,
    DocType,
    DocFormat,
    DocStyle,
    DocConfig,
)
from .templates import TemplateManager
from ..utils import logger


@dataclass
class TemplateScore:
    """Score for a template match."""
    template: DocTemplate
    score: float
    reasoning: Dict[str, float]
    suggestions: List[str]


class TemplateSelector:
    """Smart template selector based on code characteristics."""
    
    def __init__(self, template_manager: Optional[TemplateManager] = None):
        """Initialize the template selector.
        
        Args:
            template_manager: Template manager instance
        """
        self.template_manager = template_manager or TemplateManager()
        self._init_pattern_matchers()
        
    def _init_pattern_matchers(self):
        """Initialize pattern matchers for template selection."""
        self.patterns = {
            # Library/Package patterns
            'library': [
                r'setup\.py',
                r'__init__\.py',
                r'requirements\.txt',
                r'pyproject\.toml',
            ],
            # API patterns
            'api': [
                r'api/',
                r'endpoints/',
                r'routes/',
                r'@app\.(get|post|put|delete)',
                r'class.*API',
                r'def.*endpoint',
            ],
            # CLI tool patterns
            'cli': [
                r'click\.',
                r'argparse',
                r'__main__',
                r'@click\.',
                r'parser\.add_argument',
            ],
            # Test patterns
            'test': [
                r'test_',
                r'_test\.py',
                r'pytest',
                r'unittest',
                r'def test_',
                r'class Test',
            ],
            # Configuration patterns
            'config': [
                r'config\.py',
                r'settings\.py',
                r'\.env',
                r'\.yaml',
                r'\.json',
            ],
            # Data model patterns
            'model': [
                r'@dataclass',
                r'class.*Model',
                r'from dataclasses import',
                r'from pydantic import',
                r'__tablename__',
            ],
        }
        
    def select_template(
        self,
        source: Any,
        doc_type: DocType,
        config: Optional[DocConfig] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DocTemplate:
        """Select the best template for the given source.
        
        Args:
            source: Source code or analysis result
            doc_type: Type of documentation
            config: Documentation configuration
            context: Additional context for selection
            
        Returns:
            Selected template
        """
        config = config or DocConfig()
        context = context or {}
        
        # Get candidate templates
        candidates = self.template_manager.list_templates(
            doc_type=doc_type,
            format=config.format,
        )
        
        if not candidates:
            raise ValueError(f"No templates found for {doc_type}")
            
        # Score each template
        scores = []
        for template in candidates:
            score = self._score_template(template, source, context)
            scores.append(score)
            
        # Sort by score
        scores.sort(key=lambda x: x.score, reverse=True)
        
        # Log selection reasoning
        best_score = scores[0]
        logger.debug(
            f"Selected template: {best_score.template.name} "
            f"(score: {best_score.score:.2f})"
        )
        for reason, value in best_score.reasoning.items():
            logger.debug(f"  {reason}: {value:.2f}")
            
        return best_score.template
        
    def _score_template(
        self,
        template: DocTemplate,
        source: Any,
        context: Dict[str, Any],
    ) -> TemplateScore:
        """Score a template based on source characteristics.
        
        Args:
            template: Template to score
            source: Source code or analysis
            context: Additional context
            
        Returns:
            Template score with reasoning
        """
        reasoning = {}
        suggestions = []
        
        # Base score
        score = 50.0
        
        # Match documentation type
        if isinstance(source, ModuleAnalysis):
            if template.doc_type == DocType.MODULE:
                score += 20
                reasoning['type_match'] = 20
            elif template.doc_type == DocType.API and self._is_api_module(source):
                score += 15
                reasoning['api_detection'] = 15
                
        elif isinstance(source, ClassAnalysis):
            if template.doc_type == DocType.CLASS:
                score += 20
                reasoning['type_match'] = 20
                
        elif isinstance(source, FunctionAnalysis):
            if template.doc_type == DocType.FUNCTION:
                score += 20
                reasoning['type_match'] = 20
                
        # Match style preferences
        if hasattr(source, 'docstring') and source.docstring:
            detected_style = self._detect_docstring_style(source.docstring)
            if template.style == detected_style:
                score += 10
                reasoning['style_match'] = 10
                
        # Check for specific patterns
        if isinstance(source, ModuleAnalysis):
            # Library detection
            if self._is_library(source):
                if 'library' in template.name.lower() or template.doc_type == DocType.MODULE:
                    score += 15
                    reasoning['library_pattern'] = 15
                    suggestions.append("Consider using library-specific template")
                    
            # CLI tool detection
            if self._is_cli_tool(source):
                if 'cli' in template.name.lower():
                    score += 15
                    reasoning['cli_pattern'] = 15
                    suggestions.append("Detected CLI application patterns")
                    
            # Test file detection
            if self._is_test_file(source):
                if 'test' in template.name.lower():
                    score += 15
                    reasoning['test_pattern'] = 15
                    suggestions.append("Consider test documentation template")
                    
        # Context-based scoring
        if context:
            # Project type
            project_type = context.get('project_type')
            if project_type and project_type.lower() in template.name.lower():
                score += 10
                reasoning['project_type_match'] = 10
                
            # Custom preferences
            preferences = context.get('template_preferences', {})
            for pref_key, pref_value in preferences.items():
                if hasattr(template, pref_key) and getattr(template, pref_key) == pref_value:
                    score += 5
                    reasoning[f'preference_{pref_key}'] = 5
                    
        # Template completeness
        if template.required_fields:
            completeness = len(template.optional_fields) / (
                len(template.required_fields) + len(template.optional_fields)
            )
            completeness_score = completeness * 10
            score += completeness_score
            reasoning['template_completeness'] = completeness_score
            
        # Custom template preference
        if template.name.startswith('custom_'):
            score += 5
            reasoning['custom_template'] = 5
            suggestions.append("Using custom template")
            
        return TemplateScore(
            template=template,
            score=score,
            reasoning=reasoning,
            suggestions=suggestions,
        )
        
    def _detect_docstring_style(self, docstring: str) -> DocStyle:
        """Detect the documentation style from a docstring.
        
        Args:
            docstring: Docstring content
            
        Returns:
            Detected documentation style
        """
        if not docstring:
            return DocStyle.GOOGLE  # Default
            
        lines = docstring.split('\n')
        
        # Google style detection
        google_markers = ['Args:', 'Returns:', 'Yields:', 'Raises:', 'Note:', 'Example:']
        if any(marker in docstring for marker in google_markers):
            return DocStyle.GOOGLE
            
        # NumPy style detection
        numpy_markers = ['Parameters\n----------', 'Returns\n-------', 'Examples\n--------']
        for marker in numpy_markers:
            if marker in docstring:
                return DocStyle.NUMPY
                
        # Check for NumPy-style section headers
        if re.search(r'^\s*Parameters\s*\n\s*-+\s*$', docstring, re.MULTILINE):
            return DocStyle.NUMPY
        if re.search(r'^\s*Returns\s*\n\s*-+\s*$', docstring, re.MULTILINE):
            return DocStyle.NUMPY
                
        # Sphinx style detection
        sphinx_markers = [':param', ':return:', ':rtype:', ':raises:']
        if any(marker in docstring for marker in sphinx_markers):
            return DocStyle.SPHINX
            
        # Default to Google style
        return DocStyle.GOOGLE
        
    def _is_api_module(self, module: ModuleAnalysis) -> bool:
        """Check if module is an API module.
        
        Args:
            module: Module analysis
            
        Returns:
            True if module appears to be an API
        """
        if not module:
            return False
            
        # Check imports
        api_imports = ['flask', 'fastapi', 'django', 'tornado', 'aiohttp']
        for import_name in module.imports:
            if any(api_lib in import_name.lower() for api_lib in api_imports):
                return True
                
        # Check patterns in code
        if hasattr(module, 'file_path'):
            with open(module.file_path, 'r') as f:
                content = f.read()
                for pattern in self.patterns['api']:
                    if re.search(pattern, content, re.IGNORECASE):
                        return True
                        
        return False
        
    def _is_library(self, module: ModuleAnalysis) -> bool:
        """Check if module is part of a library.
        
        Args:
            module: Module analysis
            
        Returns:
            True if module appears to be a library
        """
        if not module:
            return False
            
        if hasattr(module, 'file_path'):
            module_path = Path(module.file_path)
            project_root = module_path.parent
            
            # Check for library indicators
            for pattern in self.patterns['library']:
                if project_root.glob(pattern):
                    return True
                    
        return False
        
    def _is_cli_tool(self, module: ModuleAnalysis) -> bool:
        """Check if module is a CLI tool.
        
        Args:
            module: Module analysis
            
        Returns:
            True if module appears to be a CLI tool
        """
        if not module:
            return False
            
        # Check imports
        cli_imports = ['click', 'argparse', 'fire', 'typer']
        for import_name in module.imports:
            if any(cli_lib in import_name.lower() for cli_lib in cli_imports):
                return True
                
        # Check patterns
        if hasattr(module, 'file_path'):
            with open(module.file_path, 'r') as f:
                content = f.read()
                for pattern in self.patterns['cli']:
                    if re.search(pattern, content):
                        return True
                        
        return False
        
    def _is_test_file(self, module: ModuleAnalysis) -> bool:
        """Check if module is a test file.
        
        Args:
            module: Module analysis
            
        Returns:
            True if module appears to be a test file
        """
        if not module:
            return False
            
        if hasattr(module, 'file_path'):
            file_name = Path(module.file_path).name
            
            # Check file name patterns
            if file_name.startswith('test_') or file_name.endswith('_test.py'):
                return True
                
            # Check content patterns
            with open(module.file_path, 'r') as f:
                content = f.read()
                for pattern in self.patterns['test']:
                    if re.search(pattern, content):
                        return True
                        
        return False
        
    def suggest_improvements(
        self,
        template: DocTemplate,
        source: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Suggest improvements for template selection.
        
        Args:
            template: Selected template
            source: Source code or analysis
            context: Additional context
            
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        if not source:
            return suggestions
        
        # Check if better templates might exist
        all_scores = []
        candidates = self.template_manager.list_templates(doc_type=template.doc_type)
        
        for candidate in candidates:
            score = self._score_template(candidate, source, context or {})
            all_scores.append(score)
            
        all_scores.sort(key=lambda x: x.score, reverse=True)
        
        # Suggest alternatives if close scores
        if len(all_scores) > 1:
            best_score = all_scores[0].score
            for alt_score in all_scores[1:4]:  # Top 3 alternatives
                if alt_score.score > best_score * 0.9:  # Within 10% of best
                    suggestions.append(
                        f"Consider template '{alt_score.template.name}' "
                        f"(score: {alt_score.score:.1f})"
                    )
                    
        # Context-specific suggestions
        if isinstance(source, ModuleAnalysis):
            if self._is_api_module(source) and template.doc_type != DocType.API:
                suggestions.append("Consider using API documentation template")
                
            if self._is_cli_tool(source) and 'cli' not in template.name.lower():
                suggestions.append("Consider using CLI-specific template")
                
        # Style suggestions
        detected_styles = set()
        
        # Check module docstring style
        if hasattr(source, 'docstring') and source.docstring:
            detected_styles.add(self._detect_docstring_style(source.docstring))
            
        # Check function docstrings for style
        if hasattr(source, 'functions'):
            for func in source.functions:
                if func.docstring:
                    detected_styles.add(self._detect_docstring_style(func.docstring))
                    
        # Check class docstrings
        if hasattr(source, 'classes'):
            for cls in source.classes:
                if cls.docstring:
                    detected_styles.add(self._detect_docstring_style(cls.docstring))
                    
        # If we found styles
        if detected_styles:
            if len(detected_styles) > 1:
                # Mixed styles - always suggest consistency
                styles_str = ', '.join(s.value for s in detected_styles)
                suggestions.append(
                    f"Mixed docstring styles detected ({styles_str}), "
                    f"but template uses {template.style.value}"
                )
            elif len(detected_styles) == 1 and template.style not in detected_styles:
                # Single style different from template
                detected_style = list(detected_styles)[0]
                suggestions.append(
                    f"Docstring style appears to be {detected_style.value}, "
                    f"but template uses {template.style.value}"
                )
                
        return suggestions
        
    def get_template_context(
        self,
        source: Any,
        template: DocTemplate,
    ) -> Dict[str, Any]:
        """Get context data for rendering a template.
        
        Args:
            source: Source code or analysis
            template: Template to render
            
        Returns:
            Context dictionary for template rendering
        """
        context = {}
        
        if not source:
            return context
        
        # Extract basic information
        if isinstance(source, ModuleAnalysis):
            context['module_name'] = Path(source.file_path).stem
            context['module_description'] = source.docstring or "Module description"
            context['imports'] = ', '.join(source.imports[:5])  # First 5 imports
            
            # Extract version if available
            for var in source.global_variables:
                if var == '__version__':
                    context['version'] = "0.1.0"  # Would need actual value
                    
        elif isinstance(source, ClassAnalysis):
            context['class_name'] = source.name
            context['description'] = source.docstring or f"{source.name} class"
            context['base_classes'] = ', '.join(source.parent_classes) or 'object'
            
        elif isinstance(source, FunctionAnalysis):
            context['function_name'] = source.name
            context['description'] = source.docstring or f"{source.name} function"
            context['parameters'] = ', '.join(source.parameters)
            
        # Add default values for all placeholders
        for placeholder in template.placeholders:
            if placeholder not in context:
                context[placeholder] = f"{{{placeholder}}}"
                
        return context