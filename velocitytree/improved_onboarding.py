"""Enhanced onboarding wizard for Velocitytree with improved UX."""

import time
from pathlib import Path

import click
import yaml
from prompt_toolkit import prompt
from prompt_toolkit.validation import ValidationError, Validator
from pyfiglet import Figlet
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
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
            raise ValidationError(
                message="API key seems too short. "
                "Press Enter to skip or provide a valid key."
            )


class BetterOnboardingWizard:
    """Enhanced onboarding wizard with better UX and Claude as default."""

    def __init__(self, config: Config):
        self.config = config
        self.setup_complete = False
        self.api_keys = {}
        self.selected_workflows = []
        self.project_dir = None

    def run(self, reset: bool = False):
        """Run the onboarding wizard."""
        if reset:
            self._reset_configuration()

        # Check if already configured
        if self._is_configured() and not reset:
            console.print(
                "[yellow]Velocitytree is already configured![/yellow]"
            )
            console.print()
            reconfigure = click.confirm(
                "Would you like to reconfigure?", default=False
            )
            if not reconfigure:
                return
            else:
                self._reset_configuration()

        # Start the improved onboarding flow
        self._show_welcome()
        self._select_ai_provider()
        self._configure_api_keys()
        self._test_connections()
        self._create_first_workflow()
        self._save_configuration()
        self._show_next_steps()

    def _show_welcome(self):
        """Display improved welcome screen."""
        console.clear()

        # Create ASCII art
        fig = Figlet(font="slant")
        ascii_art = fig.renderText("VelocityTree")

        # Enhanced welcome text
        welcome_text = f"""
[cyan]{ascii_art}[/cyan]

[yellow]Welcome to VelocityTree! 🌳⚡[/yellow]

Ready to supercharge your workflow automation? Let's set things up!

[bold]Quick Setup Steps:[/bold]
1. Choose AI provider (Claude recommended)
2. Configure API keys
3. Create your first workflow
4. Start automating!

This will take less than 2 minutes. Let's go!
"""

        panel = Panel(
            welcome_text,
            title="🚀 VelocityTree Setup",
            border_style="bright_blue",
            expand=False,
        )

        console.print(panel)
        click.pause("Press any key to continue...")

    def _select_ai_provider(self):
        """Let user choose AI provider with Claude as default."""
        console.clear()
        console.print(
            "\n[bold yellow]🤖 AI Provider Selection[/bold yellow]\n"
        )

        providers = {
            "1": ("anthropic", "Claude (Recommended)"),
            "2": ("openai", "OpenAI GPT"),
        }

        console.print("Choose your AI provider:")
        for key, (_, name) in providers.items():
            default = " [green](Default)[/green]" if key == "1" else ""
            console.print(f"  {key}. {name}{default}")

        choice = prompt("\nSelect (1-2, default 1): ", default="1")

        if choice not in providers:
            choice = "1"

        provider, name = providers[choice]
        self.config.ai.provider = provider

        if provider == "anthropic":
            self.config.ai.model = "claude-3-opus-20240229"
        else:
            self.config.ai.model = "gpt-4"

        console.print(f"\n[green]✓ Selected {name}[/green]")
        time.sleep(1)

    def _configure_api_keys(self):
        """Configure API keys with improved validation."""
        console.clear()
        console.print(
            "\n[bold yellow]🔑 API Key Configuration[/bold yellow]\n"
        )

        provider = self.config.ai.provider
        if provider == "anthropic":
            console.print("[cyan]Claude API Key[/cyan]")
            console.print(
                "Get your key from: "
                "https://console.anthropic.com/settings/keys"
            )

            api_key = prompt(
                "Enter your Claude API key: ",
                is_password=True,
                validator=APIKeyValidator(),
            )

            if api_key.strip():
                self.api_keys["ANTHROPIC_API_KEY"] = api_key.strip()
                console.print("[green]✓ Claude API key configured[/green]")
            else:
                console.print(
                    "[yellow]⚠ Skipped - you'll need to set this "
                    "up to use AI features[/yellow]"
                )

        else:
            console.print("[cyan]OpenAI API Key[/cyan]")
            console.print(
                "Get your key from: https://platform.openai.com/api-keys"
            )

            api_key = prompt(
                "Enter your OpenAI API key: ",
                is_password=True,
                validator=APIKeyValidator(),
            )

            if api_key.strip():
                self.api_keys["OPENAI_API_KEY"] = api_key.strip()
                console.print("[green]✓ OpenAI API key configured[/green]")
            else:
                console.print(
                    "[yellow]⚠ Skipped - you'll need to set this "
                    "up to use AI features[/yellow]"
                )

    def _test_connections(self):
        """Test API connections with proper error handling."""
        if not self.api_keys:
            console.print(
                "\n[yellow]No API keys configured. "
                "Skipping connection tests.[/yellow]"
            )
            return

        console.print("\n[bold yellow]🔍 Testing Connection[/bold yellow]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            provider = self.config.ai.provider
            key_name = "ANTHROPIC_API_KEY"
            if provider == "anthropic" and key_name in self.api_keys:
                task = progress.add_task(
                    "Testing Claude connection...", total=None
                )

                try:
                    import anthropic

                    client = anthropic.Anthropic(
                        api_key=self.api_keys["ANTHROPIC_API_KEY"]
                    )
                    # Test with a simple message
                    client.messages.create(
                        model="claude-3-opus-20240229",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=10,
                    )
                    progress.print(
                        "[green]✓ Claude connection successful![/green]"
                    )
                except Exception as e:
                    progress.print(f"[red]✗ Claude error: {str(e)}[/red]")
                    console.print(
                        "\n[yellow]Connection failed. "
                        "Check your API key.[/yellow]"
                    )
                    if click.confirm(
                        "Would you like to re-enter your API key?"
                    ):
                        self._configure_api_keys()
                finally:
                    progress.remove_task(task)

            elif provider == "openai" and "OPENAI_API_KEY" in self.api_keys:
                task = progress.add_task(
                    "Testing OpenAI connection...", total=None
                )

                try:
                    import openai

                    client = openai.Client(
                        api_key=self.api_keys["OPENAI_API_KEY"]
                    )
                    # Test with a simple completion
                    client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=10,
                    )
                    progress.print(
                        "[green]✓ OpenAI connection successful![/green]"
                    )
                except Exception as e:
                    progress.print(f"[red]✗ OpenAI error: {str(e)}[/red]")
                    console.print(
                        "\n[yellow]Connection failed. "
                        "Check your API key.[/yellow]"
                    )
                    if click.confirm(
                        "Would you like to re-enter your API key?"
                    ):
                        self._configure_api_keys()
                finally:
                    progress.remove_task(task)

    def _create_first_workflow(self):
        """Guide user to create their first workflow."""
        console.clear()
        console.print(
            "\n[bold yellow]📋 Create Your First Workflow" "[/bold yellow]\n"
        )

        console.print("Let's create a workflow to get you started!")
        console.print("\nChoose a workflow template:\n")

        # Show available templates
        templates = list(WORKFLOW_TEMPLATES.keys())
        for i, template_id in enumerate(templates, 1):
            template = WORKFLOW_TEMPLATES[template_id]
            console.print(f"  {i}. {template['name']}")
            console.print(f"     {template['description']}")
            console.print()

        # Default to blog post
        default = "1"
        choice = prompt(
            f"Select template (1-{len(templates)}, default {default}): ",
            default=default,
        )

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(templates):
                selected_template = templates[idx]
            else:
                selected_template = "blog_post"
        except ValueError:
            selected_template = "blog_post"

        # Create workflow
        template = WORKFLOW_TEMPLATES[selected_template]
        console.print(
            f"\n[green]✓ Creating '{template['name']}' workflow[/green]"
        )

        # Set up the workflow
        self.selected_workflows = [
            {
                "id": selected_template,
                "name": template["name"],
                "description": template["description"],
                "template": selected_template,
            }
        ]

        console.print("\n[cyan]This workflow will help you:[/cyan]")
        for step in template["steps"][:3]:  # Show first 3 steps
            console.print(f"  • {step['name']}")

        console.print("\n[green]Workflow created successfully![/green]")
        time.sleep(2)

    def _save_configuration(self):
        """Save configuration including API keys."""
        console.print("\n[bold yellow]💾 Saving Configuration[/bold yellow]\n")

        # Create project directory if specified
        if not self.project_dir:
            project_name = prompt(
                "Project name (default: my_velocitytree_project): "
            )
            if not project_name:
                project_name = "my_velocitytree_project"

            self.project_dir = Path.cwd() / project_name
            self.project_dir.mkdir(exist_ok=True)

        # Save workflows
        workflows_dir = self.project_dir / ".velocitytree" / "workflows"
        workflows_dir.mkdir(parents=True, exist_ok=True)

        for wf in self.selected_workflows:
            workflow_file = workflows_dir / f"{wf['id']}.yaml"
            template = WORKFLOW_TEMPLATES[wf["template"]]

            workflow_config = {
                "name": template["name"],
                "description": template["description"],
                "tags": template.get("tags", []),
                "steps": template["steps"],
            }

            with open(workflow_file, "w") as f:
                yaml.dump(workflow_config, f, default_flow_style=False)

        # Save project config
        project_config = {
            "project": {
                "name": self.project_dir.name,
                "version": "1.0.0",
                "description": "Powered by VelocityTree",
            },
            "ai": {
                "provider": self.config.ai.provider,
                "model": self.config.ai.model,
            },
            "workflows": {"enabled": True, "auto_save": True},
        }

        config_file = self.project_dir / ".velocitytree.yaml"
        with open(config_file, "w") as f:
            yaml.dump(project_config, f, default_flow_style=False)

        # Save API keys
        if self.api_keys:
            env_file = self.project_dir / ".env"
            with open(env_file, "w") as f:
                for key, value in self.api_keys.items():
                    f.write(f"{key}={value}\n")

        console.print(
            f"[green]✓ Configuration saved to: " f"{self.project_dir}[/green]"
        )

    def _show_next_steps(self):
        """Show next steps tailored to workflow usage."""
        console.clear()

        wf = self.selected_workflows[0] if self.selected_workflows else None
        workflow_name = wf["id"] if wf else "workflow"

        next_steps = f"""
[bold yellow]🎉 You're All Set![/bold yellow]

VelocityTree is configured and ready to use!

[bold cyan]Quick Start:[/bold cyan]
1. Navigate to your project:
   cd {self.project_dir}

2. Run your first workflow:
   velocitytree workflow run {workflow_name}

3. List all workflows:
   velocitytree workflow list

[bold green]Pro Tips:[/bold green]
• Create custom workflows: velocitytree workflow create
• Get AI suggestions: velocitytree ai suggest "your task"
• View help: velocitytree --help

[bold]Resources:[/bold]
• Documentation: https://velocitytree.readthedocs.io
• GitHub: https://github.com/gbechtold/velocitytree

Happy automating! 🚀
"""

        panel = Panel(
            next_steps,
            title="✨ Ready to Go!",
            border_style="bright_green",
            expand=False,
        )

        console.print(panel)

    def _is_configured(self) -> bool:
        """Check if VelocityTree is already configured."""
        config_file = Path.home() / ".velocitytree" / "config.yaml"
        env_file = Path.home() / ".velocitytree" / ".env"

        return config_file.exists() or env_file.exists()

    def _reset_configuration(self):
        """Reset all configuration."""
        console.print("[yellow]Resetting configuration...[/yellow]")

        # Remove config files
        config_dir = Path.home() / ".velocitytree"
        if config_dir.exists():
            import shutil

            shutil.rmtree(config_dir)

        console.print("[green]✓ Configuration reset[/green]")

    def _test_api_connection(self, provider: str, api_key: str) -> bool:
        """Test API connection for a provider."""
        try:
            if provider == "anthropic":
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                client.messages.create(
                    model="claude-3-opus-20240229",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10,
                )
                return True
            elif provider == "openai":
                import openai

                client = openai.Client(api_key=api_key)
                client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10,
                )
                return True
        except Exception:
            return False

        return False
