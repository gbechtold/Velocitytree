"""Specialized prompts for Claude."""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

from ..utils import logger


@dataclass
class PromptTemplate:
    """Template for Claude prompts."""
    name: str
    template: str
    variables: List[str]
    system_prompt: Optional[str] = None
    examples: List[Dict[str, str]] = None
    tags: List[str] = None
    
    def format(self, **kwargs) -> str:
        """Format the template with variables."""
        # Check all required variables are provided
        missing = set(self.variables) - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")
        
        # Format template
        try:
            formatted = self.template.format(**kwargs)
            return formatted
        except KeyError as e:
            raise ValueError(f"Template formatting error: {e}")


class PromptManager:
    """Manages prompt templates for different tasks."""
    
    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize prompt manager.
        
        Args:
            template_dir: Directory containing prompt templates
        """
        self.template_dir = template_dir or Path(__file__).parent / "templates"
        self.templates = {}
        self._load_builtin_templates()
        self._load_custom_templates()
    
    def _load_builtin_templates(self):
        """Load built-in prompt templates."""
        # Code analysis prompts
        self.templates["code_analysis"] = PromptTemplate(
            name="code_analysis",
            template="""Analyze the following code and provide insights:

File: {file_path}
Content:
```{language}
{code}
```

Please analyze:
1. Code quality and best practices
2. Potential bugs or issues
3. Performance considerations
4. Security concerns
5. Suggestions for improvement

{additional_context}""",
            variables=["file_path", "language", "code", "additional_context"],
            system_prompt="You are an expert code reviewer with deep knowledge of software engineering best practices.",
            tags=["analysis", "code", "review"]
        )
        
        # Documentation generation
        self.templates["generate_docs"] = PromptTemplate(
            name="generate_docs",
            template="""Generate comprehensive documentation for the following code:

File: {file_path}
Language: {language}
Documentation Style: {doc_style}

Code:
```{language}
{code}
```

Requirements:
- Follow {doc_style} documentation style
- Include parameter descriptions
- Document return values
- Add usage examples where appropriate
- Explain complex logic

{specific_requirements}""",
            variables=["file_path", "language", "doc_style", "code", "specific_requirements"],
            system_prompt="You are a technical documentation expert who creates clear, comprehensive documentation.",
            tags=["documentation", "generation"]
        )
        
        # Feature planning
        self.templates["feature_planning"] = PromptTemplate(
            name="feature_planning",
            template="""Help plan the implementation of a new feature:

Feature Name: {feature_name}
Description: {description}
Requirements:
{requirements}

Current Codebase Context:
{context}

Please provide:
1. Implementation approach
2. Required components/modules
3. Dependencies and prerequisites
4. Potential challenges
5. Testing strategy
6. Estimated timeline

Consider: {considerations}""",
            variables=["feature_name", "description", "requirements", "context", "considerations"],
            system_prompt="You are a senior software architect planning feature implementations.",
            tags=["planning", "feature", "architecture"]
        )
        
        # Bug fixing
        self.templates["bug_fix"] = PromptTemplate(
            name="bug_fix",
            template="""Help diagnose and fix a bug:

Bug Description: {bug_description}
Error Message: {error_message}
Stack Trace:
```
{stack_trace}
```

Relevant Code:
```{language}
{code_context}
```

Steps to Reproduce:
{steps_to_reproduce}

Please:
1. Analyze the likely cause
2. Suggest a fix
3. Explain why the bug occurs
4. Recommend preventive measures
5. Suggest test cases""",
            variables=["bug_description", "error_message", "stack_trace", "language", "code_context", "steps_to_reproduce"],
            system_prompt="You are a debugging expert who systematically analyzes and fixes software bugs.",
            tags=["debugging", "bug-fix", "troubleshooting"]
        )
        
        # Refactoring suggestions
        self.templates["refactoring"] = PromptTemplate(
            name="refactoring",
            template="""Suggest refactoring improvements for this code:

File: {file_path}
Current Code:
```{language}
{code}
```

Goals:
{refactoring_goals}

Constraints:
{constraints}

Please provide:
1. Specific refactoring recommendations
2. Benefits of each change
3. Potential risks
4. Step-by-step refactoring plan
5. Alternative approaches""",
            variables=["file_path", "language", "code", "refactoring_goals", "constraints"],
            system_prompt="You are a refactoring expert focused on code quality and maintainability.",
            tags=["refactoring", "code-quality"]
        )
        
        # Test generation
        self.templates["test_generation"] = PromptTemplate(
            name="test_generation",
            template="""Generate comprehensive tests for this code:

File: {file_path}
Code to Test:
```{language}
{code}
```

Testing Framework: {test_framework}
Coverage Requirements: {coverage_requirements}

Generate:
1. Unit tests for all public methods
2. Edge case tests
3. Error handling tests
4. Integration tests if applicable
5. Test data fixtures

Additional Requirements: {additional_requirements}""",
            variables=["file_path", "language", "code", "test_framework", "coverage_requirements", "additional_requirements"],
            system_prompt="You are a test-driven development expert who writes comprehensive test suites.",
            tags=["testing", "test-generation", "tdd"]
        )
        
        # Progress analysis
        self.templates["progress_analysis"] = PromptTemplate(
            name="progress_analysis",
            template="""Analyze project progress and provide insights:

Project Overview:
{project_overview}

Current Progress:
{current_progress}

Completed Features:
{completed_features}

Pending Features:
{pending_features}

Timeline:
{timeline}

Please analyze:
1. Overall progress assessment
2. Risk factors and blockers
3. Velocity trends
4. Recommendations for acceleration
5. Resource allocation suggestions
6. Realistic completion estimates""",
            variables=["project_overview", "current_progress", "completed_features", "pending_features", "timeline"],
            system_prompt="You are a project management expert analyzing software development progress.",
            tags=["progress", "analysis", "project-management"]
        )
        
        # Code review
        self.templates["code_review"] = PromptTemplate(
            name="code_review",
            template="""Perform a detailed code review:

Pull Request: {pr_title}
Description: {pr_description}

Changes:
{code_diff}

Review Checklist:
- Code quality and style
- Logic correctness
- Performance implications
- Security considerations
- Test coverage
- Documentation updates
- Breaking changes

Previous Reviews: {previous_reviews}

Provide feedback in categories:
1. Must Fix (blocking issues)
2. Should Fix (important improvements)
3. Consider (nice to have)
4. Nitpicks (minor style issues)""",
            variables=["pr_title", "pr_description", "code_diff", "previous_reviews"],
            system_prompt="You are a thorough code reviewer focused on quality and team collaboration.",
            tags=["review", "pull-request", "collaboration"]
        )
    
    def _load_custom_templates(self):
        """Load custom templates from directory."""
        if not self.template_dir.exists():
            return
        
        for template_file in self.template_dir.glob("*.json"):
            try:
                with open(template_file, 'r') as f:
                    data = json.load(f)
                
                template = PromptTemplate(
                    name=data["name"],
                    template=data["template"],
                    variables=data["variables"],
                    system_prompt=data.get("system_prompt"),
                    examples=data.get("examples"),
                    tags=data.get("tags", [])
                )
                
                self.templates[template.name] = template
                logger.info(f"Loaded custom template: {template.name}")
                
            except Exception as e:
                logger.warning(f"Failed to load template {template_file}: {e}")
    
    def get_template(self, name: str) -> PromptTemplate:
        """Get a prompt template by name."""
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
        return self.templates[name]
    
    def list_templates(self, tags: Optional[List[str]] = None) -> List[str]:
        """List available templates, optionally filtered by tags."""
        if not tags:
            return list(self.templates.keys())
        
        matching = []
        for name, template in self.templates.items():
            if template.tags and any(tag in template.tags for tag in tags):
                matching.append(name)
        
        return matching
    
    def create_prompt(
        self,
        template_name: str,
        **variables
    ) -> str:
        """Create a prompt from a template."""
        template = self.get_template(template_name)
        return template.format(**variables)
    
    def create_contextual_prompt(
        self,
        template_name: str,
        context: Dict[str, Any],
        **variables
    ) -> str:
        """Create a prompt with additional context."""
        template = self.get_template(template_name)
        
        # Add context to variables
        enhanced_variables = variables.copy()
        
        # Format context based on template needs
        if "additional_context" in template.variables:
            context_str = self._format_context(context)
            enhanced_variables["additional_context"] = context_str
        
        return template.format(**enhanced_variables)
    
    def save_template(self, template: PromptTemplate, overwrite: bool = False):
        """Save a template to the custom templates directory."""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
        
        template_file = self.template_dir / f"{template.name}.json"
        
        if template_file.exists() and not overwrite:
            raise ValueError(f"Template '{template.name}' already exists")
        
        data = {
            "name": template.name,
            "template": template.template,
            "variables": template.variables,
            "system_prompt": template.system_prompt,
            "examples": template.examples,
            "tags": template.tags
        }
        
        with open(template_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.templates[template.name] = template
        logger.info(f"Saved template: {template.name}")
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context dictionary into readable string."""
        formatted_parts = []
        
        for key, value in context.items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value, indent=2)
            else:
                value_str = str(value)
            
            formatted_parts.append(f"{key}:\n{value_str}")
        
        return "\n\n".join(formatted_parts)
    
    def optimize_prompt_for_context(
        self,
        template_name: str,
        available_tokens: int,
        **variables
    ) -> str:
        """Optimize prompt to fit within token limits."""
        template = self.get_template(template_name)
        
        # Start with full prompt
        full_prompt = template.format(**variables)
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        estimated_tokens = len(full_prompt) // 4
        
        if estimated_tokens <= available_tokens:
            return full_prompt
        
        # Truncate variables to fit
        truncated_vars = variables.copy()
        
        # Priority order for truncation
        truncation_order = ["additional_context", "code_context", "context", "code"]
        
        for var_name in truncation_order:
            if var_name in truncated_vars:
                original = truncated_vars[var_name]
                if isinstance(original, str) and len(original) > 1000:
                    # Truncate progressively
                    reduction_factor = available_tokens / estimated_tokens
                    new_length = int(len(original) * reduction_factor * 0.8)
                    truncated_vars[var_name] = original[:new_length] + "\n... (truncated)"
                    
                    # Re-estimate
                    new_prompt = template.format(**truncated_vars)
                    estimated_tokens = len(new_prompt) // 4
                    
                    if estimated_tokens <= available_tokens:
                        return new_prompt
        
        return template.format(**truncated_vars)