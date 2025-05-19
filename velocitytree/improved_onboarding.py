"""
Enhanced onboarding wizard for Velocitytree with improved UX and Claude as default.
"""

import os
import sys
import time
import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from pyfiglet import Figlet
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.validation import Validator, ValidationError

from .config import Config
from .workflows import WorkflowManager
from .ai import AIAssistant
from .core import TreeFlattener, ContextManager
from .utils import logger
from .templates.workflow_templates import WORKFLOW_TEMPLATES

console = Console()


class APIKeyValidator(Validator):
    """Validator for API keys."""
    
    def validate(self, document):
        text = document.text
        if not text:
            # Empty is OK (skip)
            return
        
        if len(text) < 10:
            raise ValidationError(message="API key seems too short. Press Enter to skip or provide a valid key.")


class BetterOnboardingWizard:
    """Enhanced onboarding wizard with better UX and Claude as default."""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_keys = {}
        self.selected_workflows = []
        self.ai_provider = 'anthropic'  # Default to Claude
        self.workflow_created = False
        
    def run(self, reset: bool = False):
        """Run the enhanced onboarding wizard."""
        if reset:
            self._reset_configuration()
            
        # Always show welcome first
        self._show_welcome()
        
        # Check if reconfiguration is needed
        if self._needs_configuration():
            self._configure_ai_provider()
            self._setup_first_workflow()
            self._save_configuration()
            self._show_success_summary()
        else:
            # If already configured, show quick start guide
            self._show_quick_start()
    
    def _show_welcome(self):
        """Display enhanced welcome screen."""
        console.clear()
        
        # Create colorful ASCII art
        fig = Figlet(font='slant')
        ascii_art = fig.renderText('VelocityTree')
        
        welcome_text = f"""
[cyan]{ascii_art}[/cyan]

[bold yellow]Welcome to VelocityTree! 🌳⚡[/bold yellow]

Your AI-powered workflow automation companion that helps you:
• 🚀 [cyan]Create custom workflows[/cyan] with AI assistance
• 📝 [green]Generate content[/green] like blog posts, documentation
• 🔄 [blue]Automate repetitive tasks[/blue] with smart templates  
• 🤖 [magenta]Use Claude AI[/magenta] for intelligent automation

[bold]Let's get you started in 3 simple steps:[/bold]
1️⃣  Configure your AI provider (Claude recommended)
2️⃣  Create your first workflow
3️⃣  Start automating!
"""
        
        panel = Panel(
            welcome_text,
            title="🎉 Welcome to VelocityTree",
            border_style="bright_blue",
            expand=False,
            width=70
        )
        
        console.print(panel)
        
        if not self._is_first_run():
            console.print("\n[dim]Already configured? Press 'S' to skip to quick start[/dim]")
        
        response = click.prompt("\nPress Enter to continue or 'S' to skip", default="", show_default=False)
        if response.lower() == 's':
            self._show_quick_start()
            return False
        return True
    
    def _configure_ai_provider(self):
        """Configure AI provider with Claude as default."""
        console.clear()
        console.print("\n[bold yellow]🤖 AI Provider Setup[/bold yellow]\n")
        
        # Provider selection
        console.print("Which AI provider would you like to use?")
        console.print("1. [magenta]Claude (Anthropic)[/magenta] - Recommended for best results")
        console.print("2. [green]ChatGPT (OpenAI)[/green] - Alternative option")
        console.print("3. [dim]Skip for now[/dim]")
        
        choice = click.prompt("\nEnter your choice", type=click.Choice(['1', '2', '3']), default='1')
        
        if choice == '1':
            self._setup_claude()
        elif choice == '2':
            self._setup_openai()
        else:
            console.print("[yellow]⚠ Skipping AI setup - some features will be limited[/yellow]")
    
    def _setup_claude(self):
        """Set up Claude API with validation."""
        console.print("\n[magenta]Claude (Anthropic) Setup[/magenta]")
        console.print("Get your API key from: [link]https://console.anthropic.com/account/keys[/link]")
        
        # Show example key format
        console.print("[dim]Example: sk-ant-api03-xxxxx...[/dim]\n")
        
        api_key = prompt(
            "Enter your Claude API key: ",
            is_password=True,
            validator=APIKeyValidator()
        )
        
        if api_key.strip():
            # Test the API key
            with console.status("Testing Claude API key..."):
                if self._test_claude_key(api_key.strip()):
                    self.api_keys['ANTHROPIC_API_KEY'] = api_key.strip()
                    self.ai_provider = 'anthropic'
                    console.print("[green]✅ Claude API key validated and saved![/green]")
                else:
                    console.print("[red]❌ Invalid API key. Please check and try again.[/red]")
                    retry = click.confirm("Would you like to try again?", default=True)
                    if retry:
                        self._setup_claude()
    
    def _setup_openai(self):
        """Set up OpenAI API with validation."""
        console.print("\n[green]OpenAI Setup[/green]")
        console.print("Get your API key from: [link]https://platform.openai.com/api-keys[/link]")
        
        # Show example key format
        console.print("[dim]Example: sk-xxxxx...[/dim]\n")
        
        api_key = prompt(
            "Enter your OpenAI API key: ",
            is_password=True,
            validator=APIKeyValidator()
        )
        
        if api_key.strip():
            # Test the API key
            with console.status("Testing OpenAI API key..."):
                if self._test_openai_key(api_key.strip()):
                    self.api_keys['OPENAI_API_KEY'] = api_key.strip()
                    self.ai_provider = 'openai'
                    console.print("[green]✅ OpenAI API key validated and saved![/green]")
                else:
                    console.print("[red]❌ Invalid API key. Please check and try again.[/red]")
                    retry = click.confirm("Would you like to try again?", default=True)
                    if retry:
                        self._setup_openai()
    
    def _setup_first_workflow(self):
        """Guide user to create their first workflow."""
        console.clear()
        console.print("\n[bold yellow]📋 Create Your First Workflow[/bold yellow]\n")
        
        # Show popular workflow options
        console.print("What would you like to automate first?")
        
        workflows = [
            ("1", "blog_post", "Blog Post Creator", "Create professional blog posts with AI"),
            ("2", "daily_report", "Daily Report Generator", "Summarize your daily work"),
            ("3", "code_review", "Code Review Assistant", "Prepare code for review"),
            ("4", "data_analysis", "Data Analysis Pipeline", "Process and analyze CSV data"),
            ("5", "custom", "Custom Workflow", "Create your own workflow")
        ]
        
        table = Table(title="Popular Workflow Templates", show_header=True)
        table.add_column("Choice", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Description", style="white")
        
        for choice, _, name, desc in workflows:
            table.add_row(choice, name, desc)
        
        console.print(table)
        
        choice = click.prompt("\nSelect a workflow template", type=click.Choice(['1', '2', '3', '4', '5']), default='1')
        
        template_map = dict([(w[0], w[1]) for w in workflows])
        selected_template = template_map[choice]
        
        if selected_template == 'custom':
            self._create_custom_workflow()
        else:
            self._create_from_template(selected_template)
    
    def _create_from_template(self, template_id: str):
        """Create workflow from enhanced template."""
        # Get workflow name
        default_name = template_id.replace('_', '-')
        workflow_name = click.prompt(
            f"\nWorkflow name",
            default=default_name,
            show_default=True
        )
        
        # Create workflow with template
        with console.status(f"Creating workflow '{workflow_name}'..."):
            manager = WorkflowManager(self.config)
            
            # Get enhanced template
            if template_id == 'blog_post':
                template_config = self._get_blog_post_template()
            else:
                template_config = WORKFLOW_TEMPLATES.get(template_id, {})
            
            # Create the workflow
            workflow = manager.create_workflow(workflow_name, config=template_config)
            
            self.workflow_created = True
            console.print(f"\n[green]✅ Workflow '{workflow_name}' created successfully![/green]")
            
            # Show next steps
            console.print("\n[bold]Next steps:[/bold]")
            console.print(f"1. Run your workflow: [cyan]vtree workflow run {workflow_name}[/cyan]")
            console.print(f"2. Edit workflow: [cyan]vtree workflow edit {workflow_name}[/cyan]")
            console.print(f"3. List all workflows: [cyan]vtree workflow list[/cyan]")
    
    def _get_blog_post_template(self) -> Dict:
        """Get enhanced blog post template."""
        return {
            'description': 'Create a professional blog post with AI assistance',
            'steps': [
                {
                    'name': 'gather_context',
                    'type': 'command',
                    'command': 'echo "📝 Starting blog post creation..."'
                },
                {
                    'name': 'get_topic',
                    'type': 'python',
                    'command': '''
topic = input("Enter your blog post topic: ")
print(f"Topic selected: {topic}")
context.set_step_var("topic", topic)
'''
                },
                {
                    'name': 'generate_outline',
                    'type': 'velocitytree',
                    'command': 'ai',
                    'args': {
                        'method': 'suggest',
                        'prompt': 'Create a detailed blog post outline for: {{topic}}',
                        'context': {'topic': '{{topic}}'}
                    }
                },
                {
                    'name': 'write_content',
                    'type': 'velocitytree',
                    'command': 'ai',
                    'args': {
                        'method': 'generate',
                        'prompt': 'Write a full blog post based on this outline: {{outline}}',
                        'context': {'outline': '{{step_2.output}}'}
                    }
                },
                {
                    'name': 'save_post',
                    'type': 'command',
                    'command': 'echo "{{step_3.output}}" > blog_post_{{topic|slugify}}.md'
                },
                {
                    'name': 'show_completion',
                    'type': 'command',
                    'command': 'echo "✅ Blog post created successfully!"'
                }
            ],
            'env': {
                'BLOG_OUTPUT_DIR': './blog_posts'
            }
        }
    
    def _create_custom_workflow(self):
        """Guide user through creating a custom workflow."""
        workflow_name = click.prompt("\nEnter a name for your workflow", default="my-workflow")
        description = click.prompt("Brief description", default="My custom workflow")
        
        console.print("\n[yellow]Creating a simple workflow to get you started...[/yellow]")
        
        config = {
            'description': description,
            'steps': [
                {
                    'name': 'start',
                    'type': 'command',
                    'command': f'echo "Starting {workflow_name} workflow..."'
                },
                {
                    'name': 'process',
                    'type': 'python',
                    'command': '''
print("Add your custom logic here")
# Example: data = process_data()
# context.set_step_var("result", data)
'''
                },
                {
                    'name': 'complete',
                    'type': 'command',
                    'command': 'echo "Workflow completed!"'
                }
            ]
        }
        
        manager = WorkflowManager(self.config)
        workflow = manager.create_workflow(workflow_name, config=config)
        
        self.workflow_created = True
        console.print(f"\n[green]✅ Custom workflow '{workflow_name}' created![/green]")
    
    def _save_configuration(self):
        """Save enhanced configuration."""
        with console.status("Saving configuration..."):
            # Update AI configuration
            if self.ai_provider == 'anthropic':
                self.config.config.ai.provider = 'anthropic'
                self.config.config.ai.model = 'claude-3-opus-20240229'
            else:
                self.config.config.ai.provider = 'openai'
                self.config.config.ai.model = 'gpt-4-turbo-preview'
            
            # Save API keys to environment
            env_file = Path.home() / '.velocitytree' / '.env'
            env_file.parent.mkdir(exist_ok=True)
            
            with open(env_file, 'w') as f:
                for key, value in self.api_keys.items():
                    f.write(f"{key}={value}\n")
            
            # Update config
            config_file = Path.home() / '.velocitytree' / 'config.yaml'
            self.config.save(config_file)
            
            time.sleep(1)  # Brief pause for effect
    
    def _show_success_summary(self):
        """Show success summary with clear next steps."""
        console.clear()
        
        success_text = f"""
[bold green]🎉 Setup Complete![/bold green]

You're ready to start automating with VelocityTree!

[bold]✅ What's configured:[/bold]
• AI Provider: [magenta]{self.ai_provider.title()}[/magenta]
• First workflow: [cyan]Created[/cyan]
• Configuration: [green]Saved[/green]

[bold]🚀 Quick Start Commands:[/bold]

1. Run your first workflow:
   [cyan]vtree workflow run {self.workflow_created if isinstance(self.workflow_created, str) else 'my-workflow'}[/cyan]

2. Create another workflow:
   [cyan]vtree workflow create blog-post[/cyan]

3. Get AI assistance:
   [cyan]vtree ai suggest "how do I create a data processing workflow?"[/cyan]

4. See all commands:
   [cyan]vtree --help[/cyan]

[bold]📚 Resources:[/bold]
• Documentation: [link]https://velocitytree.readthedocs.io[/link]
• Templates: [cyan]vtree workflow templates[/cyan]
• Support: [link]support@velocitytree.io[/link]
"""
        
        panel = Panel(
            success_text,
            title="🎉 Welcome to VelocityTree!",
            border_style="green",
            expand=False,
            width=70
        )
        
        console.print(panel)
    
    def _show_quick_start(self):
        """Show quick start guide for returning users."""
        console.clear()
        
        # Check workflow status
        manager = WorkflowManager(self.config)
        workflows = manager.list_workflows()
        
        quick_start = f"""
[bold cyan]🚀 VelocityTree Quick Start[/bold cyan]

[bold]Your Workflows:[/bold]
"""
        
        if workflows:
            for w in workflows[:5]:
                quick_start += f"• [cyan]{w['name']}[/cyan] - {w['description'][:40]}...\n"
        else:
            quick_start += "[yellow]No workflows yet. Create one with:[/yellow]\n"
            quick_start += "[cyan]vtree workflow create blog-post[/cyan]\n"
        
        quick_start += f"""
[bold]Common Commands:[/bold]
• Run workflow: [cyan]vtree workflow run <name>[/cyan]
• Create workflow: [cyan]vtree workflow create <name>[/cyan]
• AI assistance: [cyan]vtree ai suggest "your task"[/cyan]
• List workflows: [cyan]vtree workflow list[/cyan]

[bold]AI Status:[/bold]
• Provider: [magenta]{self.config.config.ai.provider.title()}[/magenta]
• Model: [green]{self.config.config.ai.model}[/green]
"""
        
        # Check API key status
        if not self._check_api_keys():
            quick_start += "\n[yellow]⚠ API keys not configured. Run:[/yellow] [cyan]vtree setup[/cyan]"
        
        panel = Panel(
            quick_start,
            title="VelocityTree Status",
            border_style="cyan",
            expand=False
        )
        
        console.print(panel)
    
    def _test_claude_key(self, api_key: str) -> bool:
        """Test Claude API key validity."""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            # Simple test request
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return True
        except Exception as e:
            logger.error(f"Claude API key test failed: {e}")
            return False
    
    def _test_openai_key(self, api_key: str) -> bool:
        """Test OpenAI API key validity."""
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            # Simple test request
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI API key test failed: {e}")
            return False
    
    def _check_api_keys(self) -> bool:
        """Check if API keys are configured."""
        env_file = Path.home() / '.velocitytree' / '.env'
        if not env_file.exists():
            return False
        
        with open(env_file) as f:
            content = f.read()
            return 'ANTHROPIC_API_KEY=' in content or 'OPENAI_API_KEY=' in content
    
    def _needs_configuration(self) -> bool:
        """Check if configuration is needed."""
        return not self._check_api_keys() or not self._has_workflows()
    
    def _has_workflows(self) -> bool:
        """Check if user has any workflows."""
        try:
            manager = WorkflowManager(self.config)
            workflows = manager.list_workflows()
            return len(workflows) > 0
        except:
            return False
    
    def _is_first_run(self) -> bool:
        """Check if this is the first run."""
        config_file = Path.home() / '.velocitytree' / 'config.yaml'
        return not config_file.exists()
    
    def _reset_configuration(self):
        """Reset all configuration."""
        console.print("[yellow]Resetting configuration...[/yellow]")
        
        # Clear config files
        config_dir = Path.home() / '.velocitytree'
        if config_dir.exists():
            import shutil
            shutil.rmtree(config_dir)
        
        # Reset config object
        self.config = Config()
        self.api_keys = {}
        self.selected_workflows = []
        
        console.print("[green]✓ Configuration reset[/green]")