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
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.is_active = False
        if config:
            self.logger = logger.getChild(self.name)
        else:
            self.logger = logger
    
    @abstractmethod
    def activate(self):
        """Called when the plugin is activated."""
        self.is_active = True
    
    def deactivate(self):
        """Called when the plugin is deactivated."""
        self.is_active = False
    
    def register_commands(self, cli):
        """Register CLI commands for this plugin."""
        pass
    
    def register_hooks(self, hook_manager):
        """Register hooks for this plugin."""
        pass
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get the health status of the plugin."""
        return {
            'name': self.name,
            'version': self.version,
            'active': self.is_active,
            'status': 'healthy' if self.is_active else 'inactive'
        }


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
            'plugin_loaded': {
                'description': 'Triggered when a plugin is loaded',
                'args': ['plugin_name', 'plugin_instance'],
                'return': None
            },
            
            # Command lifecycle events
            'before_command': {
                'description': 'Triggered before a CLI command is executed',
                'args': ['command_name', 'args', 'kwargs'],
                'return': 'modified_args'
            },
            'after_command': {
                'description': 'Triggered after a CLI command is executed',
                'args': ['command_name', 'result'],
                'return': 'modified_result'
            },
            
            # Workflow lifecycle events
            'workflow_start': {
                'description': 'Triggered when a workflow starts',
                'args': ['workflow_name', 'context'],
                'return': None
            },
            'workflow_step': {
                'description': 'Triggered before each workflow step',
                'args': ['workflow_name', 'step_name', 'context'],
                'return': 'skip_step'
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
            'before_flatten': {
                'description': 'Triggered before flattening operation',
                'args': ['directory', 'options'],
                'return': 'modified_options'
            },
            'after_flatten': {
                'description': 'Triggered after flattening operation',
                'args': ['result'],
                'return': None
            },
            'before_context_generation': {
                'description': 'Triggered before context generation',
                'args': ['files', 'options'],
                'return': 'modified_options'
            },
            'after_context_generation': {
                'description': 'Triggered after context generation',
                'args': ['context'],
                'return': 'modified_context'
            },
            
            # Monitoring and analysis events
            'drift_detected': {
                'description': 'Triggered when code drift is detected',
                'args': ['drift_info', 'project_path'],
                'return': None
            },
            'alert_created': {
                'description': 'Triggered when an alert is created',
                'args': ['alert_data', 'channel'],
                'return': None
            },
            'analysis_complete': {
                'description': 'Triggered when code analysis completes',
                'args': ['analysis_results', 'project_path'],
                'return': None
            },
            
            # AI integration events
            'before_ai_request': {
                'description': 'Triggered before AI request',
                'args': ['prompt', 'context', 'system_prompt'],
                'return': 'modified_prompt'
            },
            'after_ai_response': {
                'description': 'Triggered after AI response',
                'args': ['response', 'prompt'],
                'return': 'modified_response'
            },
            'ai_suggestion_generated': {
                'description': 'Triggered when AI generates a suggestion',
                'args': ['suggestion', 'context'],
                'return': None
            }
        }
        
        # Store metadata for each hook
        for event, metadata in lifecycle_hooks.items():
            self.hook_metadata[event] = metadata
    
    def register_hook(self, event: str, callback: Callable, priority: int = 50):
        """Register a hook for an event with priority (0-100, lower runs first)."""
        if event not in self.hooks:
            self.hooks[event] = []
        
        # Add callback with priority
        self.hooks[event].append((callback, priority))
        
        # Sort by priority
        self.hooks[event].sort(key=lambda x: x[1])
        
        logger.debug(f"Registered hook for event '{event}': {callback.__name__} (priority: {priority})")
    
    def unregister_hook(self, event: str, callback: Callable):
        """Unregister a hook for an event."""
        if event in self.hooks:
            self.hooks[event] = [(cb, p) for cb, p in self.hooks[event] if cb != callback]
            logger.debug(f"Unregistered hook for event '{event}': {callback.__name__}")
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event in priority order."""
        results = []
        
        if event in self.hooks:
            for callback, priority in self.hooks[event]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                    logger.debug(f"Executed hook {callback.__name__} for event '{event}'")
                except Exception as e:
                    logger.error(f"Error in hook {callback.__name__} for event '{event}': {e}")
        
        return results
    
    def list_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """List all registered hooks with metadata."""
        hooks_info = {}
        
        for event, callbacks in self.hooks.items():
            hooks_info[event] = {
                'metadata': self.hook_metadata.get(event, {}),
                'callbacks': [
                    {
                        'name': callback.__name__,
                        'priority': priority,
                        'module': callback.__module__
                    }
                    for callback, priority in callbacks
                ]
            }
        
        return hooks_info
    
    def get_hook_metadata(self, event: str) -> Dict[str, Any]:
        """Get metadata for a specific hook event."""
        return self.hook_metadata.get(event, {})


class PluginManager:
    """Manages loading, activation, and lifecycle of plugins."""
    
    def __init__(self, config: Config):
        self.config = config
        self.plugins: Dict[str, Plugin] = {}
        self.hook_manager = HookManager()
        self.plugin_dirs = self._get_plugin_directories()
        
        # Ensure plugin directories exist
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(parents=True, exist_ok=True)
        
        # Auto-discover and load enabled plugins
        plugin_config = config.config_data.get('plugins', [])
        if isinstance(plugin_config, dict) and plugin_config.get('auto_load', True):
            self._auto_load_plugins()
        else:
            # If plugins is a list or not configured, still auto-load
            self._auto_load_plugins()
    
    def _get_plugin_directories(self) -> List[Path]:
        """Get all plugin directories."""
        dirs = [
            Path.home() / '.velocitytree' / 'plugins',  # User plugins
            Path(__file__).parent / 'plugins',           # Built-in plugins
        ]
        
        # Add custom plugin directories from config
        plugin_config = self.config.config_data.get('plugins', [])
        if isinstance(plugin_config, dict):
            custom_dirs = plugin_config.get('directories', [])
        else:
            custom_dirs = []
        for dir_path in custom_dirs:
            path = Path(dir_path).expanduser().resolve()
            if path not in dirs:
                dirs.append(path)
        
        # Add environment variable paths
        env_paths = os.environ.get('VELOCITYTREE_PLUGIN_PATH', '').split(':')
        for env_path in env_paths:
            if env_path:
                path = Path(env_path).expanduser().resolve()
                if path not in dirs:
                    dirs.append(path)
        
        return dirs
    
    def _auto_load_plugins(self):
        """Auto-load enabled plugins from config."""
        plugin_config = self.config.config_data.get('plugins', [])
        if isinstance(plugin_config, dict):
            enabled_plugins = plugin_config.get('enabled', [])
        else:
            enabled_plugins = []
        
        for plugin_name in enabled_plugins:
            try:
                self.activate_plugin(plugin_name)
            except Exception as e:
                logger.error(f"Failed to auto-load plugin {plugin_name}: {e}")
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins."""
        discovered = []
        
        # 1. Discover plugins from directories
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
                    if self._is_valid_plugin_package(path):
                        discovered.append(path.name)
        
        # 2. Discover plugins from entry points
        discovered.extend(self._discover_entry_point_plugins())
        
        # 3. Discover plugins from pip packages
        discovered.extend(self._discover_pip_plugins())
        
        return list(set(discovered))
    
    def _is_valid_plugin_package(self, path: Path) -> bool:
        """Check if a directory is a valid plugin package."""
        # Check for plugin.yaml or plugin.toml metadata
        metadata_files = ['plugin.yaml', 'plugin.yml', 'plugin.toml', 'plugin.json']
        for metadata_file in metadata_files:
            if (path / metadata_file).exists():
                return True
        
        # Check for __plugin__ marker
        init_file = path / '__init__.py'
        if init_file.exists():
            try:
                with open(init_file, 'r') as f:
                    content = f.read()
                    if '__plugin__' in content or 'Plugin' in content:
                        return True
            except Exception:
                pass
        
        return False
    
    def _discover_entry_point_plugins(self) -> List[str]:
        """Discover plugins registered as entry points."""
        discovered = []
        
        try:
            from importlib.metadata import entry_points
            
            # Look for velocitytree.plugins entry points
            if hasattr(entry_points(), 'select'):
                # Python 3.10+
                eps = entry_points().select(group='velocitytree.plugins')
            else:
                # Python 3.9 and earlier
                eps = entry_points().get('velocitytree.plugins', [])
            
            for ep in eps:
                discovered.append(ep.name)
        except ImportError:
            # Fall back for older Python versions
            try:
                import pkg_resources
                for ep in pkg_resources.iter_entry_points('velocitytree.plugins'):
                    discovered.append(ep.name)
            except ImportError:
                pass
        
        return discovered
    
    def _discover_pip_plugins(self) -> List[str]:
        """Discover plugins installed via pip (velocitytree-plugin-*)."""
        discovered = []
        
        try:
            from importlib.metadata import distributions
            
            for dist in distributions():
                if dist.name.startswith('velocitytree-plugin-'):
                    plugin_name = dist.name.replace('velocitytree-plugin-', '')
                    discovered.append(plugin_name)
        except ImportError:
            # Fall back for older Python versions
            try:
                import pkg_resources
                for dist in pkg_resources.working_set:
                    if dist.project_name.startswith('velocitytree-plugin-'):
                        plugin_name = dist.project_name.replace('velocitytree-plugin-', '')
                        discovered.append(plugin_name)
            except ImportError:
                pass
        
        return discovered
    
    def load_plugin(self, plugin_name: str) -> Optional[Plugin]:
        """Load a plugin by name."""
        # Check if already loaded
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]
        
        # 1. Try to find and load from directories
        for plugin_dir in self.plugin_dirs:
            # Try as a module
            module_path = plugin_dir / f'{plugin_name}.py'
            if module_path.exists():
                return self._load_plugin_from_file(plugin_name, module_path)
            
            # Try as a package
            package_path = plugin_dir / plugin_name / '__init__.py'
            if package_path.exists():
                return self._load_plugin_from_package(plugin_name, plugin_dir / plugin_name)
        
        # 2. Try to load from entry points
        plugin = self._load_from_entry_point(plugin_name)
        if plugin:
            return plugin
        
        # 3. Try to load from pip packages
        plugin = self._load_from_pip_package(plugin_name)
        if plugin:
            return plugin
        
        logger.error(f"Plugin not found: {plugin_name}")
        return None
    
    def _load_from_entry_point(self, plugin_name: str) -> Optional[Plugin]:
        """Load a plugin from an entry point."""
        try:
            from importlib.metadata import entry_points
            
            # Look for the specific entry point
            if hasattr(entry_points(), 'select'):
                # Python 3.10+
                eps = entry_points().select(group='velocitytree.plugins', name=plugin_name)
            else:
                # Python 3.9 and earlier
                eps = [ep for ep in entry_points().get('velocitytree.plugins', []) 
                       if ep.name == plugin_name]
            
            for ep in eps:
                try:
                    plugin_class = ep.load()
                    plugin = plugin_class(self.config)
                    self.plugins[plugin_name] = plugin
                    logger.info(f"Loaded plugin from entry point: {plugin_name} v{plugin.version}")
                    return plugin
                except Exception as e:
                    logger.error(f"Error loading entry point plugin {plugin_name}: {e}")
        except ImportError:
            # Fall back for older Python versions
            try:
                import pkg_resources
                for ep in pkg_resources.iter_entry_points('velocitytree.plugins'):
                    if ep.name == plugin_name:
                        try:
                            plugin_class = ep.load()
                            plugin = plugin_class(self.config)
                            self.plugins[plugin_name] = plugin
                            logger.info(f"Loaded plugin from entry point: {plugin_name} v{plugin.version}")
                            return plugin
                        except Exception as e:
                            logger.error(f"Error loading entry point plugin {plugin_name}: {e}")
            except ImportError:
                pass
        
        return None
    
    def _load_from_pip_package(self, plugin_name: str) -> Optional[Plugin]:
        """Load a plugin from a pip package."""
        package_name = f'velocitytree-plugin-{plugin_name}'
        
        try:
            # Try to import the package
            module = importlib.import_module(package_name)
            
            # Find the plugin class
            plugin_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Plugin) and obj is not Plugin:
                    plugin_class = obj
                    break
            
            if plugin_class:
                plugin = plugin_class(self.config)
                self.plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin from pip package: {plugin_name} v{plugin.version}")
                return plugin
            else:
                logger.error(f"No Plugin class found in package {package_name}")
        except ImportError:
            logger.debug(f"Package {package_name} not found")
        except Exception as e:
            logger.error(f"Error loading pip package plugin {plugin_name}: {e}")
        
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
            # Load plugin metadata if available
            metadata = self._load_plugin_metadata(package_path)
            
            # Add package directory to Python path
            import sys
            sys.path.insert(0, str(package_path.parent))
            
            # Import the package
            module = importlib.import_module(plugin_name)
            
            # Find the plugin class
            plugin_class = None
            
            # Check metadata for class name
            if metadata and 'class' in metadata:
                plugin_class = getattr(module, metadata['class'], None)
            
            if not plugin_class:
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
            
            # Apply metadata overrides if available
            if metadata:
                for attr in ['name', 'version', 'description', 'author']:
                    if attr in metadata and hasattr(plugin, f'_{attr}'):
                        setattr(plugin, f'_{attr}', metadata[attr])
            
            logger.info(f"Loaded plugin: {plugin_name} v{plugin.version}")
            return plugin
            
        except Exception as e:
            logger.error(f"Error loading plugin package {plugin_name}: {e}")
            return None
        finally:
            # Remove from path
            if str(package_path.parent) in sys.path:
                sys.path.remove(str(package_path.parent))
    
    def _load_plugin_metadata(self, package_path: Path) -> Optional[Dict[str, Any]]:
        """Load plugin metadata from plugin.yaml/json/toml files."""
        metadata_files = {
            'plugin.yaml': lambda f: __import__('yaml').safe_load(f),
            'plugin.yml': lambda f: __import__('yaml').safe_load(f),
            'plugin.json': lambda f: __import__('json').load(f),
            'plugin.toml': lambda f: __import__('toml').load(f),
        }
        
        for filename, loader in metadata_files.items():
            metadata_path = package_path / filename
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r') as f:
                        return loader(f)
                except Exception as e:
                    logger.warning(f"Error loading plugin metadata from {metadata_path}: {e}")
        
        return None
    
    def activate_plugin(self, plugin_name: str) -> bool:
        """Activate a plugin."""
        plugin = self.plugins.get(plugin_name)
        
        if not plugin:
            plugin = self.load_plugin(plugin_name)
            if plugin:
                # Trigger plugin_loaded hook
                self.trigger_hook('plugin_loaded', plugin_name, plugin)
            
        if not plugin:
            return False
        
        try:
            plugin.activate()
            plugin.register_hooks(self.hook_manager)  # Register plugin hooks
            logger.info(f"Activated plugin: {plugin_name}")
            
            # Trigger plugin_activated hook
            self.trigger_hook('plugin_activated', plugin_name)
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
            
            # Trigger plugin_deactivated hook
            self.trigger_hook('plugin_deactivated', plugin_name)
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
        import click
        
        @cli.command()
        def example_command():
            """Example command from plugin."""
            click.echo("Hello from example plugin!")
    
    def register_hooks(self, hook_manager):
        """Register hooks."""
        def on_flatten_complete(result):
            self.logger.info(f"Flatten completed with {result['files_processed']} files")
        
        hook_manager.register_hook('flatten_complete', on_flatten_complete)