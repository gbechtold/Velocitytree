"""JSON Formatter Plugin for Velocitytree."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click

from velocitytree.plugin_system import Plugin


class JSONFormatterPlugin(Plugin):
    """Plugin that formats generated code context as pretty-printed JSON."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._config = {
            'indent': 2,
            'sort_keys': True
        }
    
    @property
    def name(self) -> str:
        return "json_formatter"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property 
    def description(self) -> str:
        return "Formats generated code context as pretty-printed JSON"
    
    def activate(self):
        """Activate the plugin with configuration."""
        super().activate()
        # Get plugin configuration from config if available
        if self.config and hasattr(self.config, 'config_data'):
            plugin_config = self.config.config_data.get('plugins', {}).get('json_formatter', {})
            self._config.update(plugin_config)
        self.logger.info(f"JSON formatter activated with config: {self._config}")
    
    def register_hooks(self, hook_manager):
        """Register hooks for JSON formatting."""
        def format_json_output(output_path: Path, context: Dict[str, Any], **kwargs):
            """Format the output as JSON."""
            if output_path.suffix.lower() == '.json':
                try:
                    self.logger.info(f"Formatting JSON output: {output_path}")
                    
                    # Pretty print the JSON
                    formatted_json = json.dumps(
                        context,
                        indent=self._config['indent'],
                        sort_keys=self._config['sort_keys']
                    )
                    
                    output_path.write_text(formatted_json)
                    self.logger.info(f"JSON formatted successfully: {output_path}")
                except Exception as e:
                    self.logger.error(f"Error formatting JSON: {e}")
        
        # Register for after flattening completes
        hook_manager.register_hook('flatten_complete', format_json_output)
    
    def register_commands(self, cli_group):
        """Register CLI commands."""
        @cli_group.command('format-json')
        @click.argument('input_file', type=click.Path(exists=True))
        @click.option('--output', '-o', help='Output file (defaults to input file)')
        @click.option('--indent', '-i', type=int, default=2, help='Indentation level')
        @click.option('--sort-keys/--no-sort-keys', default=True, help='Sort object keys')
        def format_json_command(input_file, output, indent, sort_keys):
            """Format a JSON file with pretty printing."""
            input_path = Path(input_file)
            output_path = Path(output) if output else input_path
            
            try:
                # Read input JSON
                data = json.loads(input_path.read_text())
                
                # Format with options
                formatted = json.dumps(data, indent=indent, sort_keys=sort_keys)
                
                # Write output
                output_path.write_text(formatted)
                click.echo(f"Formatted JSON written to: {output_path}")
                
            except json.JSONDecodeError as e:
                click.echo(f"Error: Invalid JSON in {input_file}: {e}", err=True)
            except Exception as e:
                click.echo(f"Error: {e}", err=True)