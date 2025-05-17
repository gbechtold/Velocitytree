"""
Plugin system for Velocitytree.
"""

import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod

from .utils import logger
from .config import Config


class Plugin(ABC):
    """Base class for all Velocitytree plugins."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the plugin."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """The version of the plugin."""
        pass
    
    @property
    def description(self) -> str:
        """Optional description of the plugin."""
        return ""
    
    @property
    def author(self) -> str:
        """Optional author information."""
        return ""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logger.getChild(self.name)
    
    @abstractmethod
    def activate(self):
        """Called when the plugin is activated."""
        pass
    
    def deactivate(self):
        """Called when the plugin is deactivated."""
        pass
    
    def register_commands(self, cli):
        """Register CLI commands for this plugin."""
        pass
    
    def register_hooks(self, hook_manager):
        """Register hooks for this plugin."""
        pass
    
    def on_load(self):
        """Called when the plugin is loaded (before activation)."""
        pass
    
    def on_unload(self):
        """Called when the plugin is about to be unloaded."""
        pass
    
    def on_config_change(self, config):
        """Called when configuration changes."""
        pass
    
    def get_dependencies(self) -> List[str]:
        """Return list of plugin dependencies."""
        return []
    
    def health_check(self) -> bool:
        """Check if plugin is healthy and functioning correctly."""
        return True


class HookManager:
    """Manages plugin hooks and events."""
    
    def __init__(self):
        self.hooks: Dict[str, List[Tuple[Callable, int]]] = {}
        self.hook_metadata: Dict[str, Dict[str, Any]] = {}
        self._define_lifecycle_hooks()
    
    def _define_lifecycle_hooks(self):
        """Define standard lifecycle hooks."""
        lifecycle_hooks = {
            # Core lifecycle events
            'velocitytree_startup': {
                'description': 'Triggered when Velocitytree starts',
                'args': ['config'],
                'return': None
            },
            'velocitytree_shutdown': {
                'description': 'Triggered when Velocitytree shuts down',
                'args': [],
                'return': None
            },
            
            # Plugin lifecycle events
            'plugin_loaded': {
                'description': 'Triggered when a plugin is loaded',
                'args': ['plugin_name', 'plugin_instance'],
                'return': None
            },
            'plugin_activated': {
                'description': 'Triggered when a plugin is activated',
                'args': ['plugin_name'],
                'return': None
            },
            'plugin_deactivated': {
                'description': 'Triggered when a plugin is deactivated',
                'args': ['plugin_name'],
                'return': None
            },
            'plugin_error': {
                'description': 'Triggered when a plugin encounters an error',
                'args': ['plugin_name', 'error', 'traceback'],
                'return': None
            },
            
            # Command lifecycle events
            'before_command': {
                'description': 'Triggered before a CLI command executes',
                'args': ['command_name', 'context', 'args', 'kwargs'],
                'return': 'Modified args/kwargs or None'
            },
            'after_command': {
                'description': 'Triggered after a CLI command executes',
                'args': ['command_name', 'result', 'context'],
                'return': 'Modified result or None'
            },
            'command_error': {
                'description': 'Triggered when a command encounters an error',
                'args': ['command_name', 'error', 'context'],
                'return': None
            },
            
            # Workflow lifecycle events
            'workflow_start': {
                'description': 'Triggered when a workflow starts',
                'args': ['workflow_name', 'context'],
                'return': None
            },
            'workflow_step_start': {
                'description': 'Triggered before a workflow step executes',
                'args': ['workflow_name', 'step_name', 'context'],
                'return': None
            },
            'workflow_step_complete': {
                'description': 'Triggered after a workflow step executes',
                'args': ['workflow_name', 'step_name', 'result', 'context'],
                'return': None
            },
            'workflow_complete': {
                'description': 'Triggered when a workflow completes',
                'args': ['workflow_name', 'result', 'context'],
                'return': None
            },
            'workflow_error': {
                'description': 'Triggered when a workflow encounters an error',
                'args': ['workflow_name', 'error', 'context'],
                'return': None
            },
            
            # File operation events
            'init_complete': {
                'description': 'Triggered after project initialization',
                'args': ['project_path', 'config'],
                'return': None
            },
            'flatten_start': {
                'description': 'Triggered before flattening operation',
                'args': ['source_path', 'options'],
                'return': 'Modified options or None'
            },
            'flatten_complete': {
                'description': 'Triggered after flattening operation',
                'args': ['result', 'source_path'],
                'return': None
            },
            'context_generate': {
                'description': 'Triggered when generating context',
                'args': ['project_path', 'options'],
                'return': 'Additional context data or None'
            },
            
            # AI integration events
            'ai_request': {
                'description': 'Triggered before an AI request',
                'args': ['prompt', 'context', 'model'],
                'return': 'Modified prompt or None'
            },
            'ai_response': {
                'description': 'Triggered after an AI response',
                'args': ['response', 'prompt', 'model'],
                'return': 'Modified response or None'
            }
        }
        
        for event, metadata in lifecycle_hooks.items():
            self.hook_metadata[event] = metadata
    
    def register_hook(self, event: str, callback: Callable, priority: int = 50):
        """Register a hook for an event with optional priority.
        
        Args:
            event: Event name to hook into
            callback: Function to call when event is triggered
            priority: Hook priority (0-100, lower runs first)
        """
        if event not in self.hooks:
            self.hooks[event] = []
        
        # Store callback with priority
        self.hooks[event].append((callback, priority))
        # Sort by priority
        self.hooks[event].sort(key=lambda x: x[1])
        
        logger.debug(f"Registered hook for event '{event}': {callback.__name__} (priority: {priority})")
        
        # Warn if hooking into undefined event
        if event not in self.hook_metadata:
            logger.warning(f"Registering hook for undefined event '{event}'")
    
    def unregister_hook(self, event: str, callback: Callable):
        """Unregister a hook."""
        if event in self.hooks:
            self.hooks[event] = [(cb, p) for cb, p in self.hooks[event] if cb != callback]
            logger.debug(f"Unregistered hook for event '{event}': {callback.__name__}")
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event in priority order."""
        results = []
        
        if event in self.hooks:
            logger.debug(f"Triggering {len(self.hooks[event])} hooks for event '{event}'")
            
            for callback, priority in self.hooks[event]:
                try:
                    # Check if we should pass previous results
                    if event in ['before_command', 'ai_request'] and results:
                        # For these events, pass the last modified result
                        if results[-1] is not None:
                            args = (results[-1],) + args[1:]
                    
                    result = callback(*args, **kwargs)
                    results.append(result)
                    
                    # Some hooks can stop propagation by returning False
                    if result is False and event in ['before_command']:
                        logger.debug(f"Hook {callback.__name__} stopped propagation for '{event}'")
                        break
                        
                except Exception as e:
                    logger.error(f"Error in hook {callback.__name__} for event '{event}': {e}")
                    # Trigger error event if available
                    if event != 'plugin_error':
                        self.trigger_hook('plugin_error', callback.__module__, e, None)
        
        return results
    
    def trigger_hook_chain(self, event: str, initial_value: Any, *args, **kwargs) -> Any:
        """Trigger hooks that modify and pass along a value."""
        value = initial_value
        
        if event in self.hooks:
            for callback, priority in self.hooks[event]:
                try:
                    result = callback(value, *args, **kwargs)
                    if result is not None:
                        value = result
                except Exception as e:
                    logger.error(f"Error in hook chain {callback.__name__} for event '{event}': {e}")
        
        return value
    
    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks."""
        return {
            event: [(callback.__name__, priority) for callback, priority in callbacks]
            for event, callbacks in self.hooks.items()
        }
    
    def get_hook_info(self, event: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific hook event."""
        return self.hook_metadata.get(event)
    
    def list_available_hooks(self) -> Dict[str, Dict[str, Any]]:
        """List all available hook events with metadata."""
        return self.hook_metadata.copy()


class PluginManager:
    """Manages loading, activation, and lifecycle of plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self.plugins: Dict[str, Plugin] = {}
        self.hook_manager = HookManager()
        self.plugin_dirs = [
            Path.home() / '.velocitytree' / 'plugins',
            Path(__file__).parent / 'plugins'
        ]
        
        # Ensure plugin directories exist
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(parents=True, exist_ok=True)
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins."""
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            # Look for Python files
            for py_file in plugin_dir.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                
                plugin_name = py_file.stem
                discovered.append(plugin_name)
            
            # Look for plugin packages
            for path in plugin_dir.iterdir():
                if path.is_dir() and (path / '__init__.py').exists():
                    discovered.append(path.name)
        
        return list(set(discovered))
    
    def load_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Load a plugin by name."""
        # Check if already loaded
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]
        
        # Try to find and load the plugin
        for plugin_dir in self.plugin_dirs:
            # Try as a module
            module_path = plugin_dir / f'{plugin_name}.py'
            if module_path.exists():
                return self._load_plugin_from_file(plugin_name, module_path)
            
            # Try as a package
            package_path = plugin_dir / plugin_name / '__init__.py'
            if package_path.exists():
                return self._load_plugin_from_package(plugin_name, plugin_dir / plugin_name)
        
        logger.error(f"Plugin not found: {plugin_name}")
        return None
    
    def _load_plugin_from_file(self, plugin_name: str, file_path: Path) -> Optional[Plugin]:
        """Load a plugin from a single file."""
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(plugin_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find the plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                    plugin_class = obj
                    break
            
            if not plugin_class:
                logger.error(f"No Plugin class found in {file_path}")
                return None
            
            # Instantiate the plugin
            plugin = plugin_class(self.config)
            self.plugins[plugin_name] = plugin
            
            # Trigger lifecycle methods
            try:
                plugin.on_load()
                self.hook_manager.trigger_hook('plugin_loaded', plugin_name, plugin)
            except Exception as e:
                logger.error(f"Error in plugin.on_load() for {plugin_name}: {e}")
                self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            return None
    
    def _load_plugin_from_package(self, plugin_name: str, package_path: Path) -> Optional[Plugin]:
        """Load a plugin from a package."""
        try:
            # Add package directory to Python path
            import sys
            sys.path.insert(0, str(package_path.parent))
            
            # Import the package
            module = importlib.import_module(plugin_name)
            
            # Find the plugin class
            plugin_class = getattr(module, 'Plugin', None)
            
            if not plugin_class or not issubclass(plugin_class, Plugin):
                # Look for a Plugin subclass
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                        plugin_class = obj
                        break
            
            if not plugin_class:
                logger.error(f"No Plugin class found in package {plugin_name}")
                return None
            
            # Instantiate the plugin
            plugin = plugin_class(self.config)
            self.plugins[plugin_name] = plugin
            
            # Trigger lifecycle methods
            try:
                plugin.on_load()
                self.hook_manager.trigger_hook('plugin_loaded', plugin_name, plugin)
            except Exception as e:
                logger.error(f"Error in plugin.on_load() for {plugin_name}: {e}")
                self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin package {plugin_name}: {e}")
            self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            return None
        finally:
            # Remove from path
            if str(package_path.parent) in sys.path:
                sys.path.remove(str(package_path.parent))
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """Activate a plugin."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            plugin = self.load_plugin(plugin_name)
            
        if not plugin:
            return False
        
        try:
            # Register plugin hooks first
            plugin.register_hooks(self.hook_manager)
            
            # Activate the plugin
            plugin.activate()
            
            # Trigger activation hook
            self.hook_manager.trigger_hook('plugin_activated', plugin_name)
            
            logger.info(f"Activated plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error activating plugin {plugin_name}: {e}")
            self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """Deactivate a plugin."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return False
        
        try:
            plugin.deactivate()
            
            # Trigger deactivation hook
            self.hook_manager.trigger_hook('plugin_deactivated', plugin_name)
            
            logger.info(f"Deactivated plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_name}: {e}")
            self.hook_manager.trigger_hook('plugin_error', plugin_name, e, None)
            return False
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins."""
        available = self.discover_plugins()
        plugins = []
        
        for name in available:
            plugin = self.plugins.get(name)
            
            if plugin:
                status = 'loaded'
                version = plugin.version
                description = plugin.description
                author = plugin.author
            else:
                status = 'available'
                version = 'unknown'
                description = ''
                author = ''
            
            plugins.append({
                'name': name,
                'status': status,
                'version': version,
                'description': description,
                'author': author
            })
        
        return plugins
    
    def get_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)
    
    def register_cli_commands(self, cli):
        """Register CLI commands from all active plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.register_commands(cli)
            except Exception as e:
                logger.error(f"Error registering commands for plugin {plugin.name}: {e}")
    
    def register_plugin_hooks(self):
        """Register hooks from all active plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.register_hooks(self.hook_manager)
            except Exception as e:
                logger.error(f"Error registering hooks for plugin {plugin.name}: {e}")
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger a hook event."""
        return self.hook_manager.trigger_hook(event, *args, **kwargs)
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin completely."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            return False
        
        try:
            # Deactivate first if needed
            self.deactivate_plugin(plugin_name)
            
            # Call unload lifecycle method
            plugin.on_unload()
            
            # Remove from plugins dict
            del self.plugins[plugin_name]
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin (unload and load again)."""
        # Remember if it was active
        was_active = plugin_name in self.plugins and hasattr(self.plugins[plugin_name], '_active')
        
        # Unload the plugin
        self.unload_plugin(plugin_name)
        
        # Load it again
        plugin = self.load_plugin(plugin_name)
        if not plugin:
            return False
        
        # Reactivate if it was active
        if was_active:
            self.activate_plugin(plugin_name)
        
        return True
    
    def check_plugin_health(self, plugin_name: str) -> bool:
        """Check if a plugin is healthy."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            return False
        
        try:
            return plugin.health_check()
        except Exception as e:
            logger.error(f"Error checking health of plugin {plugin_name}: {e}")
            return False
    
    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """Get plugin dependencies."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            return []
        
        try:
            return plugin.get_dependencies()
        except Exception as e:
            logger.error(f"Error getting dependencies for plugin {plugin_name}: {e}")
            return []
    
    def resolve_dependencies(self, plugin_name: str) -> List[str]:
        """Resolve plugin dependencies in load order."""
        resolved = []
        visited = set()
        
        def visit(name: str):
            if name in visited:
                return
            
            visited.add(name)
            plugin = self.plugins.get(name)
            
            if plugin:
                for dep in plugin.get_dependencies():
                    visit(dep)
            
            resolved.append(name)
        
        visit(plugin_name)
        return resolved


# Example plugin implementation
class ExamplePlugin(Plugin):
    """Example plugin implementation."""
    
    name = "example"
    version = "1.0.0"
    description = "An example Velocitytree plugin"
    author = "Velocitytree Team"
    
    def activate(self):
        """Activate the plugin."""
        self.logger.info("Example plugin activated")
    
    def deactivate(self):
        """Deactivate the plugin."""
        self.logger.info("Example plugin deactivated")
    
    def register_commands(self, cli):
        """Register CLI commands."""
        @cli.command()
        def example_command():
            """Example command from plugin."""
            click.echo("Hello from example plugin!")
    
    def register_hooks(self, hook_manager):
        """Register hooks."""
        def on_flatten_complete(result):
            self.logger.info(f"Flatten completed with {result['files_processed']} files")
        
        hook_manager.register_hook('flatten_complete', on_flatten_complete)