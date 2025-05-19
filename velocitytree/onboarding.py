"""
Interactive onboarding wizard for Velocitytree.

This module provides a guided setup experience for new users, helping them:
- Configure API keys for AI providers
- Select workflow templates for their use case
- Create initial project structure
- Learn basic commands and features
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

from .config import Config
from .workflows import WorkflowManager
from .ai import AIAssistant
from .core import TreeFlattener, ContextManager
from .utils import logger
from .improved_onboarding import BetterOnboardingWizard

console = Console()


# Use the improved implementation directly
OnboardingWizard = BetterOnboardingWizard

# Keep original class for backwards compatibility but use new implementation
class OriginalOnboardingWizard:
    """Original onboarding wizard - kept for reference."""
    
    def __init__(self, config: Config):
        self.config = config
        self.setup_complete = False
        self.api_keys = {}
        self.selected_workflows = []
        
    def run(self, reset: bool = False):
        """Run the onboarding wizard."""
        if reset:
            self._reset_configuration()
            
        # Check if already configured
        if self._is_configured() and not reset:
            console.print("[yellow]Velocitytree is already configured![/yellow]")
            # Clear any spinners
            console.print()
            if not click.confirm("Would you like to reconfigure?", default=False):
                return
            else:
                self._reset_configuration()
        
        # Start onboarding flow
        self._show_welcome()
        self._configure_api_keys()
        self._test_connections()
        self._select_workflows()
        self._create_project_structure()
        self._save_configuration()
        self._show_next_steps()
        
    def _show_welcome(self):
        """Display welcome screen with ASCII art."""
        console.clear()
        
        # Create ASCII art
        fig = Figlet(font='slant')
        ascii_art = fig.renderText('VelocityTree')
        
        # Create welcome panel
        welcome_text = f"""
[cyan]{ascii_art}[/cyan]

[yellow]Welcome to VelocityTree! 🌳⚡[/yellow]

The AI-powered workflow automation toolkit that helps you:
• 🚀 Automate repetitive tasks
• 📊 Process bulk data efficiently  
• 🤖 Leverage AI for smart workflows
• 🔧 Build custom automation pipelines

This wizard will guide you through:
1. Setting up AI providers (OpenAI, Anthropic)
2. Selecting workflow templates
3. Creating your first project
4. Getting started with commands

Let's begin!
"""
        
        panel = Panel(
            welcome_text,
            title="🎉 VelocityTree Onboarding",
            border_style="bright_blue",
            expand=False
        )
        
        console.print(panel)
        click.pause("Press any key to continue...")
        
    def _configure_api_keys(self):
        """Configure API keys for AI providers."""
        console.clear()
        console.print("\n[bold yellow]🔑 API Key Configuration[/bold yellow]\n")
        
        # OpenAI configuration
        console.print("[cyan]OpenAI API Key[/cyan]")
        console.print("Get your key from: https://platform.openai.com/api-keys")
        
        openai_key = prompt(
            "Enter your OpenAI API key (optional, press Enter to skip): ",
            is_password=True
        )
        
        if openai_key.strip():
            self.api_keys['OPENAI_API_KEY'] = openai_key.strip()
            console.print("[green]✓ OpenAI API key configured[/green]")
        else:
            console.print("[yellow]⚠ OpenAI API key skipped[/yellow]")
            
        # Anthropic configuration
        console.print("\n[cyan]Anthropic (Claude) API Key[/cyan]")
        console.print("Get your key from: https://console.anthropic.com/settings/keys")
        
        anthropic_key = prompt(
            "Enter your Anthropic API key (optional, press Enter to skip): ",
            is_password=True
        )
        
        if anthropic_key.strip():
            self.api_keys['ANTHROPIC_API_KEY'] = anthropic_key.strip()
            console.print("[green]✓ Anthropic API key configured[/green]")
        else:
            console.print("[yellow]⚠ Anthropic API key skipped[/yellow]")
            
    def _test_connections(self):
        """Test API connections."""
        if not self.api_keys:
            console.print("\n[yellow]No API keys configured. Skipping connection tests.[/yellow]")
            return
            
        console.print("\n[bold yellow]🔍 Testing Connections[/bold yellow]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Test OpenAI
            if 'OPENAI_API_KEY' in self.api_keys:
                task = progress.add_task("Testing OpenAI connection...", total=None)
                
                try:
                    # Set environment variable temporarily
                    os.environ['OPENAI_API_KEY'] = self.api_keys['OPENAI_API_KEY']
                    
                    # Test connection
                    assistant = AIAssistant(config=self.config, provider='openai')
                    if assistant.test_connection():
                        progress.print("[green]✓ OpenAI connection successful![/green]")
                    else:
                        progress.print("[red]✗ OpenAI connection failed[/red]")
                except Exception as e:
                    progress.print(f"[red]✗ OpenAI error: {str(e)}[/red]")
                finally:
                    progress.remove_task(task)
                    
            # Test Anthropic
            if 'ANTHROPIC_API_KEY' in self.api_keys:
                task = progress.add_task("Testing Anthropic connection...", total=None)
                
                try:
                    # Set environment variable temporarily
                    os.environ['ANTHROPIC_API_KEY'] = self.api_keys['ANTHROPIC_API_KEY']
                    
                    # Test connection
                    assistant = AIAssistant(config=self.config, provider='anthropic')
                    if assistant.test_connection():
                        progress.print("[green]✓ Anthropic connection successful![/green]")
                    else:
                        progress.print("[red]✗ Anthropic connection failed[/red]")
                except Exception as e:
                    progress.print(f"[red]✗ Anthropic error: {str(e)}[/red]")
                finally:
                    progress.remove_task(task)
                    
    def _select_workflows(self):
        """Select workflow templates."""
        console.clear()
        console.print("\n[bold yellow]📋 Workflow Templates[/bold yellow]\n")
        
        # Available workflow templates
        workflows = [
            {
                'id': 'google_ads',
                'name': 'Google Ads Automation',
                'description': 'Keyword research, bulk processing, CSV formatting',
                'tags': ['marketing', 'ads', 'automation']
            },
            {
                'id': 'code_docs',
                'name': 'Code Documentation',
                'description': 'Generate docs, analyze code, create READMEs',
                'tags': ['development', 'documentation', 'analysis']
            },
            {
                'id': 'content_gen',
                'name': 'Content Generation',
                'description': 'Blog posts, social media, marketing content',
                'tags': ['content', 'writing', 'marketing']
            },
            {
                'id': 'data_transform',
                'name': 'Data Transformation',
                'description': 'CSV processing, data cleaning, format conversion',
                'tags': ['data', 'etl', 'processing']
            }
        ]
        
        # Display workflow options
        table = Table(title="Available Workflow Templates")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Description", style="white")
        table.add_column("Tags", style="green")
        
        for workflow in workflows:
            table.add_row(
                workflow['id'],
                workflow['name'],
                workflow['description'],
                ', '.join(workflow['tags'])
            )
            
        console.print(table)
        
        console.print("\n[cyan]Select workflows to install (comma-separated IDs, or 'all'):[/cyan]")
        
        # Create completer
        workflow_ids = [w['id'] for w in workflows]
        completer = WordCompleter(workflow_ids + ['all', 'none'])
        
        selection = prompt(
            "Your selection: ",
            completer=completer
        )
        
        if selection.lower() == 'all':
            self.selected_workflows = workflows
        elif selection.lower() == 'none':
            self.selected_workflows = []
        else:
            selected_ids = [s.strip() for s in selection.split(',')]
            self.selected_workflows = [w for w in workflows if w['id'] in selected_ids]
            
        if self.selected_workflows:
            console.print(f"\n[green]✓ Selected {len(self.selected_workflows)} workflows[/green]")
        else:
            console.print("\n[yellow]⚠ No workflows selected[/yellow]")
            
    def _create_project_structure(self):
        """Create initial project structure."""
        console.clear()
        console.print("\n[bold yellow]🏗️ Creating Project Structure[/bold yellow]\n")
        
        project_name = prompt("Enter project name (default: my_velocitytree_project): ")
        if not project_name:
            project_name = "my_velocitytree_project"
            
        project_dir = Path.cwd() / project_name
        
        if project_dir.exists():
            if not click.confirm(f"Directory '{project_name}' already exists. Use it anyway?"):
                return
        else:
            project_dir.mkdir(parents=True, exist_ok=True)
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Create directory structure
            task = progress.add_task("Creating directories...", total=None)
            
            # Create subdirectories
            (project_dir / '.velocitytree').mkdir(exist_ok=True)
            (project_dir / '.velocitytree' / 'workflows').mkdir(exist_ok=True)
            (project_dir / '.velocitytree' / 'templates').mkdir(exist_ok=True)
            (project_dir / '.velocitytree' / 'outputs').mkdir(exist_ok=True)
            (project_dir / 'data').mkdir(exist_ok=True)
            (project_dir / 'scripts').mkdir(exist_ok=True)
            
            progress.update(task, description="Creating configuration...")
            
            # Create project configuration
            project_config = {
                'project': {
                    'name': project_name,
                    'version': '1.0.0',
                    'description': f'{project_name} - Powered by VelocityTree'
                },
                'ai': {
                    'provider': 'openai' if 'OPENAI_API_KEY' in self.api_keys else 'anthropic',
                    'model': 'gpt-4' if 'OPENAI_API_KEY' in self.api_keys else 'claude-3'
                },
                'workflows': {
                    'enabled': True,
                    'auto_save': True
                }
            }
            
            config_path = project_dir / '.velocitytree.yaml'
            with open(config_path, 'w') as f:
                yaml.dump(project_config, f, default_flow_style=False)
                
            progress.update(task, description="Installing workflow templates...")
            
            # Install selected workflow templates
            workflow_manager = WorkflowManager(config=self.config)
            
            for workflow in self.selected_workflows:
                template_file = project_dir / '.velocitytree' / 'workflows' / f"{workflow['id']}.yaml"
                
                # Create workflow from template
                workflow_config = {
                    'name': workflow['name'],
                    'description': workflow['description'],
                    'steps': self._get_workflow_steps(workflow['id'])
                }
                
                with open(template_file, 'w') as f:
                    yaml.dump(workflow_config, f, default_flow_style=False)
                    
            progress.update(task, description="Creating example files...")
            
            # Create example files
            readme_content = f"""# {project_name}

Welcome to your VelocityTree project!

## Getting Started

1. Run `velocitytree init` to initialize the project
2. Use `velocitytree workflow list` to see available workflows
3. Run `velocitytree workflow run <workflow_name>` to execute a workflow

## Available Workflows

"""
            for workflow in self.selected_workflows:
                readme_content += f"- **{workflow['name']}**: {workflow['description']}\n"
                
            with open(project_dir / 'README.md', 'w') as f:
                f.write(readme_content)
                
            progress.remove_task(task)
            
        console.print(f"\n[green]✓ Project created at: {project_dir}[/green]")
        self.project_dir = project_dir
        
    def _get_workflow_steps(self, workflow_id: str) -> List[Dict]:
        """Get workflow steps for a template."""
        # Define workflow steps for each template
        templates = {
            'google_ads': [
                {
                    'name': 'Load Keywords',
                    'type': 'file_input',
                    'config': {
                        'path': 'data/keywords.txt',
                        'format': 'text'
                    }
                },
                {
                    'name': 'Process Keywords',
                    'type': 'ai_process',
                    'config': {
                        'prompt': 'Analyze these keywords for Google Ads campaigns',
                        'model': 'gpt-4'
                    }
                },
                {
                    'name': 'Generate CSV',
                    'type': 'file_output',
                    'config': {
                        'path': 'outputs/google_ads_keywords.csv',
                        'format': 'csv'
                    }
                }
            ],
            'code_docs': [
                {
                    'name': 'Scan Codebase',
                    'type': 'velocitytree',
                    'command': 'flatten',
                    'args': {
                        'output_dir': '.velocitytree/outputs/code_scan'
                    }
                },
                {
                    'name': 'Generate Documentation',
                    'type': 'ai_process',
                    'config': {
                        'prompt': 'Generate comprehensive documentation for this codebase',
                        'include_context': True
                    }
                },
                {
                    'name': 'Save Documentation',
                    'type': 'file_output',
                    'config': {
                        'path': 'docs/API.md',
                        'format': 'markdown'
                    }
                }
            ],
            'content_gen': [
                {
                    'name': 'Load Topics',
                    'type': 'file_input',
                    'config': {
                        'path': 'data/topics.json',
                        'format': 'json'
                    }
                },
                {
                    'name': 'Generate Content',
                    'type': 'ai_process',
                    'config': {
                        'prompt': 'Create engaging blog posts for these topics',
                        'model': 'claude-3'
                    }
                },
                {
                    'name': 'Save Content',
                    'type': 'file_output',
                    'config': {
                        'path': 'outputs/blog_posts.md',
                        'format': 'markdown'
                    }
                }
            ],
            'data_transform': [
                {
                    'name': 'Load Data',
                    'type': 'file_input',
                    'config': {
                        'path': 'data/input.csv',
                        'format': 'csv'
                    }
                },
                {
                    'name': 'Transform Data',
                    'type': 'python',
                    'config': {
                        'script': 'scripts/transform.py'
                    }
                },
                {
                    'name': 'Export Results',
                    'type': 'file_output',
                    'config': {
                        'path': 'outputs/transformed.csv',
                        'format': 'csv'
                    }
                }
            ]
        }
        
        return templates.get(workflow_id, [])
        
    def _save_configuration(self):
        """Save configuration including API keys."""
        console.print("\n[bold yellow]💾 Saving Configuration[/bold yellow]\n")
        
        # Create .env file for API keys
        if self.api_keys:
            env_path = Path.home() / '.velocitytree' / '.env'
            env_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(env_path, 'w') as f:
                for key, value in self.api_keys.items():
                    f.write(f"{key}={value}\n")
                    
            console.print(f"[green]✓ API keys saved to: {env_path}[/green]")
            
        # Update global config
        if hasattr(self, 'project_dir'):
            self.config.set('defaults.project_path', str(self.project_dir))
            
        # Save config
        config_path = Path.home() / '.velocitytree' / 'config.yaml'
        self.config.save(config_path)
        
        console.print(f"[green]✓ Configuration saved to: {config_path}[/green]")
        
    def _show_next_steps(self):
        """Show next steps and useful commands."""
        console.clear()
        
        next_steps = f"""
[bold yellow]🎉 Setup Complete![/bold yellow]

Your VelocityTree environment is ready! Here's what to do next:

[cyan]1. Navigate to your project:[/cyan]
   cd {getattr(self, 'project_dir', 'my_velocitytree_project')}

[cyan]2. Initialize the project:[/cyan]
   velocitytree init

[cyan]3. List available workflows:[/cyan]
   velocitytree workflow list

[cyan]4. Run a workflow:[/cyan]
   velocitytree workflow run <workflow_name>

[cyan]5. Get AI assistance:[/cyan]
   velocitytree ai suggest "your task description"

[bold green]Useful Commands:[/bold green]
• velocitytree flatten - Flatten directory structure
• velocitytree context - Generate project context
• velocitytree ai analyze <file> - Analyze code with AI
• velocitytree workflow create <name> - Create custom workflow
• velocitytree --help - Show all commands

[bold blue]Resources:[/bold blue]
• Documentation: https://velocitytree.readthedocs.io
• GitHub: https://github.com/gbechtold/velocitytree
• Support: support@velocitytree.io

Happy automating! 🚀
"""
        
        panel = Panel(
            next_steps,
            title="🏁 Next Steps",
            border_style="bright_green",
            expand=False
        )
        
        console.print(panel)
        
    def _is_configured(self) -> bool:
        """Check if VelocityTree is already configured."""
        config_file = Path.home() / '.velocitytree' / 'config.yaml'
        env_file = Path.home() / '.velocitytree' / '.env'
        
        return config_file.exists() or env_file.exists()
        
    def _reset_configuration(self):
        """Reset all configuration."""
        console.print("[yellow]Resetting configuration...[/yellow]")
        
        # Remove config files
        config_dir = Path.home() / '.velocitytree'
        if config_dir.exists():
            import shutil
            shutil.rmtree(config_dir)
            
        console.print("[green]✓ Configuration reset[/green]")
        

def create_onboarding_command(cli):
    """Create the onboarding command for the CLI."""
    @cli.command()
    @click.option('--reset', is_flag=True, help='Reset configuration and start fresh')
    @click.option('--web', is_flag=True, help='Use web-based interface (coming soon)')
    @click.pass_context
    def onboard(ctx, reset, web):
        """Interactive setup wizard for new users."""
        if web:
            console.print("[yellow]Web interface coming soon! Using terminal interface for now.[/yellow]")
            
        wizard = OnboardingWizard(ctx.obj['config'])
        wizard.run(reset=reset)


# Additional onboarding utilities
def check_first_run():
    """Check if this is the first run and prompt for onboarding."""
    config_dir = Path.home() / '.velocitytree'
    if not config_dir.exists():
        console.print("\n[yellow]Welcome to VelocityTree! This looks like your first time.[/yellow]")
        if click.confirm("Would you like to run the setup wizard?"):
            config = Config()
            wizard = OnboardingWizard(config)
            wizard.run()
            return True
    return False


def show_onboarding_demo():
    """Show a demo of the onboarding process."""
    demo_text = """
[bold cyan]VelocityTree Onboarding Demo[/bold cyan]

The onboarding wizard will guide you through:

1. [yellow]API Key Setup[/yellow]
   - Configure OpenAI and/or Anthropic API keys
   - Test connections to ensure they work

2. [yellow]Workflow Selection[/yellow]
   - Choose from pre-built workflow templates
   - Examples: Google Ads automation, code documentation, content generation

3. [yellow]Project Creation[/yellow]
   - Set up your first VelocityTree project
   - Create directory structure and configuration files

4. [yellow]Next Steps Guide[/yellow]
   - Learn essential commands
   - Get links to documentation and support

To start the onboarding wizard, run:
[green]velocitytree onboard[/green]

To reset and reconfigure:
[green]velocitytree onboard --reset[/green]
"""
    
    console.print(Panel(demo_text, title="🎯 Onboarding Demo", border_style="blue"))