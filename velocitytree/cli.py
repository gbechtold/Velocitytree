#!/usr/bin/env python3
"""
Command-line interface for Velocitytree.
"""

import click
import sys
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core import TreeFlattener, ContextManager
from .config import Config
from .utils import logger
from .ai import AIAssistant
from .workflows import WorkflowManager
from .version import version_info

console = Console()


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Quiet output')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """Velocitytree - Streamline your developer workflow 🌳⚡"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config(config)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    if verbose:
        logger.setLevel('DEBUG')
    elif quiet:
        logger.setLevel('ERROR')
    
    # Initialize plugin manager
    from .plugin_system import PluginManager
    ctx.obj['plugin_manager'] = PluginManager(ctx.obj['config'])
    
    # Register plugin commands
    ctx.obj['plugin_manager'].register_cli_commands(cli)


@cli.command()
@click.option('--template', '-t', help='Project template to use')
@click.option('--name', '-n', help='Project name')
@click.option('--force', '-f', is_flag=True, help='Force initialization even if config exists')
@click.pass_context
def init(ctx, template, name, force):
    """Initialize a new Velocitytree project."""
    from pathlib import Path
    import shutil
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing project...", total=None)
        
        # Check if config already exists
        config_path = Path('.velocitytree.yaml')
        if config_path.exists() and not force:
            console.print("[yellow]⚠[/yellow] Configuration file already exists. Use --force to overwrite.")
            return
        
        # Create default configuration
        config = ctx.obj['config']
        if name:
            config.set('project.name', name)
        
        # Save configuration
        config.save(config_path)
        progress.update(task, description="Created configuration file")
        
        # Create .velocitytree directory
        vtree_dir = Path('.velocitytree')
        vtree_dir.mkdir(exist_ok=True)
        
        # Create sample workflow if template requested
        if template:
            workflows_dir = vtree_dir / 'workflows'
            workflows_dir.mkdir(exist_ok=True)
            
            sample_workflow = {
                'description': f'Sample workflow for {template}',
                'steps': [
                    {
                        'name': 'flatten',
                        'type': 'velocitytree',
                        'command': 'flatten',
                        'args': {
                            'output_dir': f'{template}_output'
                        }
                    },
                    {
                        'name': 'generate context',
                        'type': 'velocitytree',
                        'command': 'context',
                        'args': {
                            'format': 'markdown',
                            'output': f'{template}_context.md'
                        }
                    }
                ]
            }
            
            import yaml
            workflow_file = workflows_dir / f'{template}.yaml'
            with open(workflow_file, 'w') as f:
                yaml.dump(sample_workflow, f, default_flow_style=False)
            
            progress.update(task, description=f"Created {template} workflow")
        
        progress.update(task, description="Project initialized successfully!")
        console.print("[green]✓[/green] Project initialized!")
        console.print(f"Configuration saved to: [blue]{config_path}[/blue]")


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--exclude', '-e', multiple=True, help='Patterns to exclude')
@click.option('--include-ext', '-i', multiple=True, help='File extensions to include')
@click.option('--preserve-structure', is_flag=True, help='Preserve directory structure')
@click.option('--follow-symlinks', is_flag=True, help='Follow symbolic links')
@click.option('--source', '-s', type=click.Path(exists=True), help='Source directory to flatten')
@click.pass_context
def flatten(ctx, output, exclude, include_ext, preserve_structure, follow_symlinks, source):
    """Flatten project directory structure (TreeTamer functionality)."""
    config = ctx.obj['config']
    
    # Merge command-line options with config
    flatten_config = config.config.flatten
    
    # Use command-line options if provided, otherwise fall back to config
    output_dir = output or flatten_config.output_dir
    exclude_patterns = list(exclude) if exclude else flatten_config.exclude
    include_extensions = list(include_ext) if include_ext else flatten_config.include_extensions
    
    # Handle boolean flags
    preserve = preserve_structure if preserve_structure else flatten_config.preserve_structure
    follow = follow_symlinks if follow_symlinks else flatten_config.follow_symlinks
    
    # Create flattener with merged configuration
    flattener = TreeFlattener(
        output_dir=output_dir,
        exclude_patterns=exclude_patterns,
        include_extensions=include_extensions,
        preserve_structure=preserve,
        follow_symlinks=follow
    )
    
    with console.status("Flattening directory structure...") as status:
        result = flattener.flatten(source_dir=source)
        
    console.print(f"[green]✓[/green] Flattened {result['files_processed']} files")
    console.print(f"Output directory: [blue]{result['output_dir']}[/blue]")
    console.print(f"Total size: {result['total_size']:,} bytes")
    
    if ctx.obj['verbose']:
        console.print(f"Files skipped: {result.get('files_skipped', 0)}")


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'markdown']), default='json')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--ai-ready', is_flag=True, help='Generate AI-ready context')
@click.pass_context
def context(ctx, format, output, ai_ready):
    """Generate project context for AI or documentation."""
    manager = ContextManager()
    
    with console.status("Generating context...") as status:
        context_data = manager.generate_context(ai_ready=ai_ready)
        
        if output:
            manager.save_context(context_data, output, format)
            console.print(f"[green]✓[/green] Context saved to {output}")
        else:
            console.print(context_data)


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed analysis')
@click.option('--metrics', is_flag=True, help='Show code metrics')
@click.option('--path', '-p', type=click.Path(exists=True), default='.', help='Path to analyze')
@click.pass_context
def analyze(ctx, detailed, metrics, path):
    """Analyze project structure and code quality."""
    from .core import ContextManager
    from pathlib import Path
    import os
    
    project_path = Path(path)
    console.print(f"[blue]Analyzing project: {project_path}[/blue]")
    
    # Use ContextManager to gather project information
    manager = ContextManager(project_root=project_path)
    context = manager.generate_context(include_code=True, include_structure=True)
    
    # Basic metrics table
    table = Table(title="Project Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    
    # Extract metrics from context
    structure = context.get('structure', {})
    code_summary = context.get('code_summary', {})
    
    # Basic metrics
    table.add_row("Project Name", context.get('project_name', 'Unknown'))
    table.add_row("Total Files", str(len(structure.get('files', []))))
    table.add_row("Total Directories", str(len(structure.get('directories', []))))
    table.add_row("Total Size", f"{structure.get('total_size', 0):,} bytes")
    table.add_row("Lines of Code", str(code_summary.get('total_lines', 0)))
    
    console.print(table)
    
    if metrics:
        # Language breakdown table
        lang_table = Table(title="Language Breakdown")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Files", style="yellow")
        lang_table.add_column("Lines", style="green")
        
        for lang, stats in code_summary.get('languages', {}).items():
            lang_table.add_row(lang, str(stats['files']), str(stats['lines']))
        
        console.print(lang_table)
    
    if detailed:
        # File type distribution
        file_types = {}
        for file_info in structure.get('files', []):
            ext = file_info.get('extension', 'no extension')
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Sort by count
        sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]
        
        type_table = Table(title="Top File Types")
        type_table.add_column("Extension", style="cyan")
        type_table.add_column("Count", style="yellow")
        
        for ext, count in sorted_types:
            type_table.add_row(ext, str(count))
        
        console.print(type_table)
        
        # Directory depth analysis
        max_depth = 0
        for dir_path in structure.get('directories', []):
            depth = len(Path(dir_path).parts)
            max_depth = max(max_depth, depth)
        
        console.print(f"\n[blue]Maximum directory depth:[/blue] {max_depth}")
        
        # Check for common project files
        project_files = [
            'README.md', 'LICENSE', 'requirements.txt', 'package.json',
            'setup.py', 'Dockerfile', '.gitignore'
        ]
        
        found_files = []
        for file_info in structure.get('files', []):
            file_name = Path(file_info['path']).name
            if file_name in project_files:
                found_files.append(file_name)
        
        if found_files:
            console.print(f"\n[green]Found project files:[/green] {', '.join(found_files)}")
        else:
            console.print(f"\n[yellow]No standard project files found[/yellow]")


@cli.group()
def ai():
    """AI assistant commands."""
    pass


@ai.command()
@click.argument('task')
@click.option('--context', is_flag=True, help='Include project context')
@click.option('--save', '-s', type=click.Path(), help='Save suggestions to file')
@click.pass_context
def suggest(ctx, task, context, save):
    """Get AI suggestions for a task."""
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        
        with console.status("Getting AI suggestions...") as status:
            suggestions = assistant.suggest(task, include_context=context)
            
        console.print("[green]AI Suggestions:[/green]")
        console.print(suggestions)
        
        if save:
            with open(save, 'w') as f:
                f.write(suggestions)
            console.print(f"\n[blue]Suggestions saved to:[/blue] {save}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("[yellow]Hint:[/yellow] Make sure your AI API key is configured.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['general', 'security', 'performance', 'refactor', 'documentation']), 
              default='general', help='Type of analysis to perform')
@click.pass_context
def analyze(ctx, file, type):
    """Analyze a code file with AI."""
    from pathlib import Path
    
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        file_path = Path(file)
        
        with console.status(f"Analyzing {file_path.name}...") as status:
            result = assistant.analyze_code(file_path, analysis_type=type)
            
        console.print(f"[green]Analysis Results for {file_path.name}:[/green]")
        console.print(result['response'])
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.option('--language', '-l', default='python', help='Programming language')
@click.option('--save', '-s', type=click.Path(), help='Save generated code to file')
@click.pass_context
def generate(ctx, language, save):
    """Generate code using AI."""
    from prompt_toolkit import prompt
    
    try:
        # Get description from user
        description = prompt("Describe what you want to generate: ")
        
        assistant = AIAssistant(config=ctx.obj['config'])
        
        with console.status("Generating code...") as status:
            code = assistant.generate_code(description, language=language)
            
        console.print(f"[green]Generated {language} code:[/green]")
        console.print(code)
        
        if save:
            with open(save, 'w') as f:
                f.write(code)
            console.print(f"\n[blue]Code saved to:[/blue] {save}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.pass_context
def test(ctx):
    """Test AI connectivity."""
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        provider_info = assistant.get_provider_info()
        
        console.print(f"[blue]Testing AI connection...[/blue]")
        console.print(f"Provider: {provider_info['provider']}")
        console.print(f"Model: {provider_info['model']}")
        console.print(f"API Key: {'✓' if provider_info['api_key_configured'] else '✗'}")
        
        with console.status("Testing connection...") as status:
            if assistant.test_connection():
                console.print("[green]✓[/green] AI connection successful!")
            else:
                console.print("[red]✗[/red] AI connection failed!")
                console.print("[yellow]Check your API key and configuration.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("[yellow]Make sure your AI provider is properly configured.[/yellow]")


@cli.group()
def workflow():
    """Workflow management commands."""
    pass


@workflow.command('list')
@click.pass_context
def list_workflows(ctx):
    """List available workflows."""
    manager = WorkflowManager(config=ctx.obj['config'])
    workflows = manager.list_workflows()
    
    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        return
    
    table = Table(title="Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="yellow")
    table.add_column("Steps", style="green")
    table.add_column("Source", style="blue")
    
    for workflow in workflows:
        table.add_row(
            workflow['name'],
            workflow['description'][:50] + "..." if len(workflow['description']) > 50 else workflow['description'],
            str(workflow['steps']),
            workflow['source']
        )
    
    console.print(table)

@workflow.command('templates')
@click.pass_context
def list_templates(ctx):
    """List available workflow templates."""
    manager = WorkflowManager(config=ctx.obj['config'])
    templates = manager.list_templates()
    
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    
    table = Table(title="Available Workflow Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Description", style="green")
    table.add_column("Steps", style="blue")
    
    for template in templates:
        table.add_row(
            template['id'],
            template['name'],
            template['description'][:50] + "..." if len(template['description']) > 50 else template['description'],
            str(template['steps'])
        )
    
    console.print(table)

@workflow.command()
@click.argument('name')
@click.option('--template', '-t', help='Use a workflow template')
@click.option('--edit', '-e', is_flag=True, help='Edit workflow after creation')
@click.pass_context
def create(ctx, name, template, edit):
    """Create a new workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Check if template is valid
    if template:
        templates = {t['id']: t for t in manager.list_templates()}
        if template not in templates:
            console.print(f"[red]Invalid template:[/red] {template}")
            console.print("Available templates:")
            for tid, tinfo in templates.items():
                console.print(f"  - {tid}: {tinfo['name']}")
            return
    
    workflow = manager.create_workflow(name, template=template)
    console.print(f"[green]✓[/green] Workflow '{name}' created")
    
    if edit:
        from pathlib import Path
        import subprocess
        import os
        
        workflow_file = Path.home() / '.velocitytree' / 'workflows' / f'{name}.yaml'
        editor = os.environ.get('EDITOR', 'nano')
        
        try:
            subprocess.run([editor, str(workflow_file)])
        except Exception as e:
            console.print(f"[yellow]Could not open editor:[/yellow] {e}")
            console.print(f"Edit manually: {workflow_file}")

@workflow.command()
@click.argument('name')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--var', '-V', multiple=True, help='Set a global variable (format: key=value)')
@click.option('--var-file', type=click.Path(exists=True), help='Load variables from JSON file')
@click.pass_context
def run(ctx, name, verbose, dry_run, var, var_file):
    """Run a workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Parse global variables
    global_vars = {}
    
    # Load from file if specified
    if var_file:
        import json
        with open(var_file, 'r') as f:
            global_vars.update(json.load(f))
    
    # Parse command-line variables
    for var_def in var:
        if '=' in var_def:
            key, value = var_def.split('=', 1)
            # Try to parse value as JSON for complex types
            try:
                import json
                value = json.loads(value)
            except:
                pass  # Keep as string
            global_vars[key] = value
    
    try:
        if dry_run:
            workflow = manager.get_workflow(name)
            if not workflow:
                console.print(f"[red]Workflow not found:[/red] {name}")
                return
            
            console.print(f"[blue]Would run workflow:[/blue] {name}")
            console.print(f"[blue]Description:[/blue] {workflow.description}")
            console.print(f"[blue]Steps:[/blue]")
            
            for i, step in enumerate(workflow.steps):
                console.print(f"  {i+1}. {step.name} ({step.type})")
            return
        
        with console.status(f"Running workflow '{name}'...") as status:
            result = manager.run_workflow(name, global_vars=global_vars)
            
        if result['status'] == 'success':
            console.print(f"[green]✓[/green] Workflow completed successfully")
        else:
            console.print(f"[red]✗[/red] Workflow failed")
            
        if verbose:
            console.print("\n[blue]Workflow Results:[/blue]")
            for step_result in result['results']:
                console.print(f"\nStep {step_result['step'] + 1}: {step_result['name']}")
                console.print(f"Status: {step_result['result']['status']}")
                
                if step_result['result'].get('output'):
                    output = str(step_result['result']['output'])
                    if len(output) > 200:
                        output = output[:200] + "..."
                    console.print(f"Output: {output}")
                
                if step_result['result'].get('error'):
                    console.print(f"[red]Error:[/red] {step_result['result']['error']}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@workflow.command()
@click.argument('name')
@click.pass_context
def delete(ctx, name):
    """Delete a workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Confirm deletion
    if click.confirm(f"Are you sure you want to delete workflow '{name}'?"):
        manager.delete_workflow(name)
        console.print(f"[green]✓[/green] Workflow '{name}' deleted")
    else:
        console.print("[yellow]Deletion cancelled[/yellow]")

@workflow.command()
@click.argument('name')
@click.pass_context
def show(ctx, name):
    """Show workflow details."""
    manager = WorkflowManager(config=ctx.obj['config'])
    manager.show_workflow_details(name)


@workflow.group()
def variables():
    """Manage workflow variables."""
    pass


@variables.command('list')
@click.option('--scope', '-s', help='Variable scope to list')
@click.pass_context
def list_variables(ctx):
    """List stored workflow variables."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    variables = store.list_variables(scope=ctx.invoked_subcommand)
    
    if not variables:
        console.print("[yellow]No variables found.[/yellow]")
        return
    
    table = Table(title="Workflow Variables")
    table.add_column("Scope", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Value", style="green")
    
    for scope, vars in variables.items():
        for name, value in vars.items():
            table.add_row(scope, name, str(value))
    
    console.print(table)


@variables.command('set')
@click.argument('name')
@click.argument('value')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def set_variable(ctx, name, value, scope):
    """Set a workflow variable."""
    from .workflow_context import VariableStore
    import json
    
    store = VariableStore()
    
    # Try to parse value as JSON
    try:
        parsed_value = json.loads(value)
    except:
        parsed_value = value
    
    store.set(name, parsed_value, scope)
    console.print(f"[green]✓[/green] Variable '{name}' set in scope '{scope}'")


@variables.command('get')
@click.argument('name')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def get_variable(ctx, name, scope):
    """Get a workflow variable."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    value = store.get(name, scope)
    
    if value is None:
        console.print(f"[yellow]Variable '{name}' not found in scope '{scope}'[/yellow]")
    else:
        console.print(f"{name} = {value}")


@variables.command('delete')
@click.argument('name')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def delete_variable(ctx, name, scope):
    """Delete a workflow variable."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    if store.delete(name, scope):
        console.print(f"[green]✓[/green] Variable '{name}' deleted from scope '{scope}'")
    else:
        console.print(f"[yellow]Variable '{name}' not found in scope '{scope}'[/yellow]")


@cli.group()
def plugin():
    """Plugin management commands."""
    pass


@plugin.command('list')
@click.pass_context
def list_plugins(ctx):
    """List available plugins."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    plugins = manager.list_plugins()
    
    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        return
    
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Version", style="green")
    table.add_column("Description", style="blue")
    
    for plugin in plugins:
        table.add_row(
            plugin['name'],
            plugin['status'],
            plugin['version'],
            plugin['description'][:50] + "..." if len(plugin['description']) > 50 else plugin['description']
        )
    
    console.print(table)


@plugin.command('activate')
@click.argument('name')
@click.pass_context
def activate_plugin(ctx, name):
    """Activate a plugin."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    
    if manager.activate_plugin(name):
        console.print(f"[green]✓[/green] Plugin '{name}' activated")
    else:
        console.print(f"[red]✗[/red] Failed to activate plugin '{name}'")


@plugin.command('deactivate')
@click.argument('name')
@click.pass_context
def deactivate_plugin(ctx, name):
    """Deactivate a plugin."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    
    if manager.deactivate_plugin(name):
        console.print(f"[green]✓[/green] Plugin '{name}' deactivated")
    else:
        console.print(f"[red]✗[/red] Failed to deactivate plugin '{name}'")


@cli.command()
def version():
    """Show version information."""
    console.print(version_info())


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', '-f', type=click.Choice(['yaml', 'json', 'toml']), default='yaml')
@click.pass_context
def config(ctx, output, format):
    """Show or create configuration."""
    config = ctx.obj['config']
    
    if output:
        # Save current configuration
        config.save(output)
        console.print(f"[green]✓[/green] Configuration saved to {output}")
    else:
        # Display current configuration
        import yaml
        import json
        import toml
        
        config_data = config.config_data
        
        if format == 'yaml':
            output_text = yaml.dump(config_data, default_flow_style=False)
        elif format == 'json':
            output_text = json.dumps(config_data, indent=2)
        elif format == 'toml':
            output_text = toml.dumps(config_data)
        
        console.print(output_text)


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()