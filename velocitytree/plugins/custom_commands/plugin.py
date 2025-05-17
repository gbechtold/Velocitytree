"""Custom Commands Plugin for Velocitytree."""

import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import click

from velocitytree.plugin_system import Plugin


class CustomCommandsPlugin(Plugin):
    """Plugin that adds custom commands for common development tasks."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._config = {
            'commands': [
                {'name': 'stats', 'description': 'Show project statistics'},
                {'name': 'clean', 'description': 'Clean generated files'},
                {'name': 'backup', 'description': 'Create backup of project'}
            ]
        }
    
    @property
    def name(self) -> str:
        return "custom_commands"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Adds custom commands for common development tasks"
    
    def activate(self):
        """Activate the plugin with configuration."""
        super().activate()
        # Get plugin configuration from config if available
        if self.config and hasattr(self.config, 'config_data'):
            plugin_config = self.config.config_data.get('plugins', {}).get('custom_commands', {})
            if 'commands' in plugin_config:
                self._config.update(plugin_config)
        self.logger.info(f"Custom commands activated with {len(self._config['commands'])} commands")
    
    def register_commands(self, cli_group):
        """Register custom CLI commands."""
        
        @cli_group.command('stats')
        @click.pass_context
        def show_stats(ctx):
            """Show project statistics."""
            project_path = Path(ctx.obj.get('project_root', '.'))
            
            # Count files by extension
            stats = {}
            total_files = 0
            total_lines = 0
            
            for file_path in project_path.rglob('*'):
                if file_path.is_file() and not any(part.startswith('.') for part in file_path.parts):
                    total_files += 1
                    ext = file_path.suffix
                    
                    if ext not in stats:
                        stats[ext] = {'count': 0, 'lines': 0}
                    
                    stats[ext]['count'] += 1
                    
                    # Count lines for text files
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = len(f.readlines())
                            stats[ext]['lines'] += lines
                            total_lines += lines
                    except:
                        pass  # Skip binary files
            
            # Display stats
            click.echo(f"Project Statistics for {project_path}")
            click.echo(f"Total files: {total_files}")
            click.echo(f"Total lines: {total_lines}")
            click.echo("\nBreakdown by file type:")
            
            for ext, data in sorted(stats.items()):
                if ext:
                    click.echo(f"  {ext}: {data['count']} files, {data['lines']} lines")
                else:
                    click.echo(f"  (no extension): {data['count']} files, {data['lines']} lines")
        
        @cli_group.command('clean')
        @click.option('--dry-run', is_flag=True, help='Show what would be deleted without deleting')
        @click.option('--force', '-f', is_flag=True, help='Force deletion without confirmation')
        @click.pass_context
        def clean_generated(ctx, dry_run, force):
            """Clean generated files and directories."""
            project_path = Path(ctx.obj.get('project_root', '.'))
            
            # Patterns to clean
            patterns = [
                '*.pyc',
                '__pycache__',
                '.pytest_cache',
                '.mypy_cache',
                '*.egg-info',
                'dist',
                'build',
                '.coverage',
                'htmlcov',
                '.velocitytree_cache'
            ]
            
            files_to_delete = []
            
            # Find files matching patterns
            for pattern in patterns:
                for item in project_path.rglob(pattern):
                    files_to_delete.append(item)
            
            if not files_to_delete:
                click.echo("No files to clean")
                return
            
            # Show files to delete
            click.echo(f"Files/directories to delete ({len(files_to_delete)} items):")
            for item in files_to_delete:
                click.echo(f"  {item}")
            
            if dry_run:
                click.echo("\nDry run - no files deleted")
                return
            
            # Confirm deletion
            if not force:
                if not click.confirm("\nDelete these files?"):
                    click.echo("Cancelled")
                    return
            
            # Delete files
            deleted = 0
            for item in files_to_delete:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    deleted += 1
                except Exception as e:
                    click.echo(f"Error deleting {item}: {e}", err=True)
            
            click.echo(f"\nDeleted {deleted} items")
        
        @cli_group.command('backup')
        @click.option('--output', '-o', help='Output file (defaults to timestamped tarball)')
        @click.option('--exclude', '-e', multiple=True, help='Patterns to exclude')
        @click.pass_context
        def create_backup(ctx, output, exclude):
            """Create backup of the project."""
            project_path = Path(ctx.obj.get('project_root', '.'))
            
            # Generate output filename if not provided
            if not output:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output = f"{project_path.name}_backup_{timestamp}.tar.gz"
            
            output_path = Path(output)
            
            # Default excludes
            default_excludes = {
                '__pycache__', '.pytest_cache', '.mypy_cache',
                '.git', '.venv', 'venv', 'env',
                '*.pyc', '*.egg-info', 'dist', 'build'
            }
            
            exclude_patterns = set(default_excludes)
            if exclude:
                exclude_patterns.update(exclude)
            
            click.echo(f"Creating backup of {project_path}")
            click.echo(f"Output: {output_path}")
            click.echo(f"Excluding: {', '.join(exclude_patterns)}")
            
            # Create tarball
            with tarfile.open(output_path, 'w:gz') as tar:
                def filter_func(tarinfo):
                    # Check if file should be excluded
                    path_parts = Path(tarinfo.name).parts
                    
                    for pattern in exclude_patterns:
                        if any(pattern.replace('*', '') in str(part) for part in path_parts):
                            return None
                    
                    return tarinfo
                
                tar.add(project_path, arcname=project_path.name, filter=filter_func)
            
            click.echo(f"Backup created: {output_path}")
            click.echo(f"Size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")
    
    def register_hooks(self, hook_manager):
        """Register hooks for custom commands."""
        def on_backup_complete(output_path: str, **kwargs):
            """Log when a backup is created."""
            self.logger.info(f"Backup created: {output_path}")
        
        # Could add hooks for backup events if needed
        pass