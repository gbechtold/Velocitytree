"""
Hello World plugin for Velocitytree.
"""

from velocitytree.plugin_system import Plugin


class HelloWorldPlugin(Plugin):
    """A simple hello world plugin."""
    
    @property
    def name(self) -> str:
        return "hello_world"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "A simple hello world plugin for demonstration"
    
    @property
    def author(self) -> str:
        return "Velocitytree Team"
    
    def activate(self):
        """Activate the plugin."""
        self.logger.info("Hello World plugin activated!")
    
    def deactivate(self):
        """Deactivate the plugin."""
        self.logger.info("Hello World plugin deactivated!")
    
    def register_commands(self, cli):
        """Register CLI commands."""
        import click
        
        @cli.command()
        def hello():
            """Print a hello world message."""
            click.echo("🌍 Hello, World from Velocitytree plugin!")
            click.echo(f"Plugin version: {self.version}")
    
    def register_hooks(self, hook_manager):
        """Register hooks."""
        def on_init_complete(project_path):
            self.logger.info(f"Project initialized at {project_path}")
            self.logger.info("Hello from the Hello World plugin!")
        
        hook_manager.register_hook('init_complete', on_init_complete)
        
        def on_workflow_start(workflow_name):
            self.logger.info(f"Workflow '{workflow_name}' started - Hello from plugin!")
        
        hook_manager.register_hook('workflow_start', on_workflow_start)