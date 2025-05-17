# Velocitytree Plugin Development Guide

This guide covers how to develop plugins for Velocitytree.

## Plugin Discovery

Velocitytree discovers plugins from multiple sources:

1. **Built-in plugins**: Located in `velocitytree/plugins/`
2. **User plugins**: Located in `~/.velocitytree/plugins/`
3. **Custom directories**: Specified in config or environment variables
4. **Entry points**: Registered via setuptools
5. **Pip packages**: Packages named `velocitytree-plugin-*`

## Plugin Structure

### Simple Plugin (Single File)

Create a Python file in the plugins directory:

```python
# ~/.velocitytree/plugins/my_plugin.py

from velocitytree.plugin_system import Plugin

class MyPlugin(Plugin):
    @property
    def name(self) -> str:
        return "my_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def activate(self):
        self.logger.info("Plugin activated!")
    
    def register_commands(self, cli):
        import click
        
        @cli.command()
        def my_command():
            """My custom command."""
            click.echo("Hello from my plugin!")
```

### Plugin Package

Create a directory with the following structure:

```
my_plugin/
├── __init__.py
├── plugin.yaml  # Optional metadata
└── ...
```

The `__init__.py` should contain your plugin class or have a `__plugin__` marker:

```python
# my_plugin/__init__.py

from velocitytree.plugin_system import Plugin

class MyPlugin(Plugin):
    # ... plugin implementation
```

### Plugin Metadata

You can provide metadata in `plugin.yaml`:

```yaml
# plugin.yaml
name: my_plugin
version: 1.0.0
description: My awesome plugin
author: Your Name
class: MyPlugin  # Optional: specify the plugin class name
dependencies:
  - requests>=2.28.0
  - pyyaml>=5.4.0
```

## Plugin API

### Required Properties

Every plugin must implement these properties:

```python
@property
def name(self) -> str:
    """Unique plugin identifier."""
    return "my_plugin"

@property
def version(self) -> str:
    """Plugin version."""
    return "1.0.0"
```

### Optional Properties

```python
@property
def description(self) -> str:
    """Plugin description."""
    return "My plugin description"

@property
def author(self) -> str:
    """Plugin author."""
    return "Your Name"
```

### Lifecycle Methods

```python
def activate(self):
    """Called when the plugin is activated."""
    pass

def deactivate(self):
    """Called when the plugin is deactivated."""
    pass
```

### Registering Commands

```python
def register_commands(self, cli):
    """Register CLI commands."""
    import click
    
    @cli.command()
    @click.argument('name')
    def greet(name):
        """Greet someone."""
        click.echo(f"Hello, {name}!")
```

### Registering Hooks

```python
def register_hooks(self, hook_manager):
    """Register hooks."""
    def on_init_complete(project_path):
        self.logger.info(f"Project initialized at {project_path}")
    
    hook_manager.register_hook('init_complete', on_init_complete)
```

## Available Hooks

- `init_complete`: Called after project initialization
- `flatten_complete`: Called after flattening operation
- `workflow_start`: Called when a workflow starts
- `workflow_complete`: Called when a workflow completes
- `workflow_error`: Called when a workflow errors

## Configuration

### Enabling Plugins

In your `.velocitytree.yaml`:

```yaml
plugins:
  enabled:
    - my_plugin
    - another_plugin
  auto_load: true
  directories:
    - /path/to/custom/plugins
```

### Environment Variables

- `VELOCITYTREE_PLUGIN_PATH`: Colon-separated list of plugin directories

## Distribution

### Via Entry Points

In your `setup.py` or `pyproject.toml`:

```toml
[project.entry-points."velocitytree.plugins"]
my_plugin = "my_package.plugin:MyPlugin"
```

### Via Pip Package

Name your package `velocitytree-plugin-{name}` and it will be automatically discovered.

## Best Practices

1. Use the logger provided by the plugin base class
2. Handle errors gracefully in activation/deactivation
3. Document your commands and hooks
4. Use semantic versioning
5. Test your plugin with multiple Velocitytree versions
6. Provide clear error messages

## Example Plugins

See the `hello_world.py` plugin in `velocitytree/plugins/` for a complete example.