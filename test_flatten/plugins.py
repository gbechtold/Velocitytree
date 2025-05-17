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


class HookManager:
    """Manages plugin hooks and events."""
    
    def __init__(self):
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register_hook(self, event: str, callback: Callable):
        """Register a hook for an event."""
        if event not in self.hooks:
            self.hooks[event] = []
        
        self.hooks[event].append(callback)
        logger.debug(f"Registered hook for event '{event}': {callback.__name__}")
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event."""
        results = []
        
        if event in self.hooks:
            for callback in self.hooks[event]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error in hook {callback.__name__} for event '{event}': {e}")
        
        return results
    
    def list_hooks(self) -> Dict[str, List[str]]:
        """List all registered hooks."""
        return {
            event: [callback.__name__ for callback in callbacks]
            for event, callbacks in self.hooks.items()
        }


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
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
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
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin package {plugin_name}: {e}")
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
            plugin.activate()
            logger.info(f"Activated plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error activating plugin {plugin_name}: {e}")
            return False
    
    def deactivate_plugin(self, plugin_name: str) -> bool:
        """Deactivate a plugin."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return False
        
        try:
            plugin.deactivate()
            logger.info(f"Deactivated plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error deactivating plugin {plugin_name}: {e}")
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