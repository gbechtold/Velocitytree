"""Comprehensive tests for the Velocitytree plugin system."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import yaml

from velocitytree.plugin_system import Plugin, PluginManager, HookManager
from velocitytree.config import Config


class MockPlugin(Plugin):
    """Mock plugin for testing."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.activated = False
        self.deactivated = False
        self.commands_registered = False
        self.hooks_registered = False
    
    @property
    def name(self) -> str:
        return "mock_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "A mock plugin for testing"
    
    def activate(self):
        """Activate the plugin."""
        super().activate()
        self.activated = True
    
    def deactivate(self):
        """Deactivate the plugin."""
        super().deactivate()
        self.deactivated = True
    
    def register_commands(self, cli):
        """Register commands."""
        self.commands_registered = True
        
        @cli.command()
        def mock_command():
            """Mock command."""
            pass
    
    def register_hooks(self, hook_manager):
        """Register hooks."""
        self.hooks_registered = True
        hook_manager.register_hook('test_event', self.on_test_event)
    
    def on_test_event(self, data, **kwargs):
        """Handle test event."""
        return f"Handled: {data}"


class BrokenPlugin(Plugin):
    """Plugin that fails to activate."""
    
    @property
    def name(self) -> str:
        return "broken_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def activate(self):
        """Fail during activation."""
        raise Exception("Activation failed!")


class TestHookManager:
    """Test the HookManager class."""
    
    def test_hook_registration(self):
        """Test registering hooks."""
        manager = HookManager()
        callback = Mock()
        
        manager.register_hook('test_event', callback)
        
        assert 'test_event' in manager.hooks
        assert callback in manager.hooks['test_event']
    
    def test_hook_execution(self):
        """Test executing hooks."""
        manager = HookManager()
        callback = Mock(return_value="result")
        
        manager.register_hook('test_event', callback)
        results = manager.trigger_hook('test_event', data="test_data")
        
        callback.assert_called_once_with(data="test_data")
        assert results == ["result"]
    
    def test_multiple_hooks(self):
        """Test multiple hooks for same event."""
        manager = HookManager()
        callback1 = Mock(return_value="result1")
        callback2 = Mock(return_value="result2")
        
        manager.register_hook('test_event', callback1)
        manager.register_hook('test_event', callback2)
        
        results = manager.trigger_hook('test_event', data="test")
        
        assert len(results) == 2
        assert "result1" in results
        assert "result2" in results
    
    def test_hook_error_handling(self):
        """Test error handling in hooks."""
        manager = HookManager()
        
        def failing_callback(**kwargs):
            raise Exception("Hook failed!")
        
        manager.register_hook('test_event', failing_callback)
        results = manager.trigger_hook('test_event')
        
        # Should handle error gracefully
        assert results == [None]
    
    def test_list_hooks(self):
        """Test listing registered hooks."""
        manager = HookManager()
        
        def callback1():
            pass
        
        def callback2():
            pass
        
        manager.register_hook('event1', callback1)
        manager.register_hook('event2', callback2)
        
        hooks = manager.list_hooks()
        
        assert 'event1' in hooks
        assert 'event2' in hooks
        assert 'callback1' in hooks['event1']
        assert 'callback2' in hooks['event2']


class TestPlugin:
    """Test the Plugin base class."""
    
    def test_plugin_initialization(self):
        """Test plugin initialization."""
        config = Config()
        plugin = MockPlugin(config)
        
        assert plugin.config == config
        assert plugin.logger is not None
    
    def test_plugin_activation(self):
        """Test plugin activation."""
        plugin = MockPlugin()
        plugin.activate()
        
        assert plugin.activated is True
        assert plugin.is_active is True
    
    def test_plugin_deactivation(self):
        """Test plugin deactivation."""
        plugin = MockPlugin()
        plugin.activate()
        plugin.deactivate()
        
        assert plugin.deactivated is True
        assert plugin.is_active is False
    
    def test_health_status(self):
        """Test plugin health status."""
        plugin = MockPlugin()
        plugin.activate()
        
        status = plugin.get_health_status()
        
        assert status['name'] == 'mock_plugin'
        assert status['version'] == '1.0.0'
        assert status['active'] is True
        assert status['status'] == 'healthy'


class TestPluginManager:
    """Test the PluginManager class."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = Config()
        self.manager = PluginManager(self.config)
    
    def test_plugin_discovery_directory(self, tmp_path):
        """Test discovering plugins from directory."""
        # Create test plugin file
        plugin_file = tmp_path / "test_plugin.py"
        plugin_file.write_text("""
from velocitytree.plugin_system import Plugin

class TestPlugin(Plugin):
    @property
    def name(self):
        return "test_plugin"
    
    @property
    def version(self):
        return "1.0.0"
""")
        
        self.manager.plugin_dirs.append(tmp_path)
        discovered = self.manager.discover_plugins()
        
        assert "test_plugin" in discovered
    
    def test_plugin_discovery_package(self, tmp_path):
        """Test discovering plugin packages."""
        # Create plugin package
        package_dir = tmp_path / "test_package"
        package_dir.mkdir()
        
        init_file = package_dir / "__init__.py"
        init_file.write_text("""
from velocitytree.plugin_system import Plugin

class TestPackagePlugin(Plugin):
    @property
    def name(self):
        return "test_package"
    
    @property
    def version(self):
        return "1.0.0"

__plugin__ = TestPackagePlugin
""")
        
        self.manager.plugin_dirs.append(tmp_path)
        discovered = self.manager.discover_plugins()
        
        assert "test_package" in discovered
    
    def test_plugin_loading(self):
        """Test loading a plugin."""
        # Mock plugin loading
        plugin = MockPlugin(self.config)
        
        with patch.object(self.manager, '_load_plugin_from_file', return_value=plugin):
            loaded = self.manager.load_plugin('mock_plugin')
            
            assert loaded is not None
            assert loaded.name == 'mock_plugin'
            assert 'mock_plugin' in self.manager.plugins
    
    def test_plugin_activation(self):
        """Test activating a plugin."""
        plugin = MockPlugin(self.config)
        self.manager.plugins['mock_plugin'] = plugin
        
        self.manager.activate_plugin('mock_plugin')
        
        assert plugin.activated is True
        assert plugin.hooks_registered is True
    
    def test_plugin_deactivation(self):
        """Test deactivating a plugin."""
        plugin = MockPlugin(self.config)
        plugin.activate()
        self.manager.plugins['mock_plugin'] = plugin
        
        self.manager.deactivate_plugin('mock_plugin')
        
        assert plugin.deactivated is True
    
    def test_plugin_error_handling(self):
        """Test handling plugin errors."""
        plugin = BrokenPlugin(self.config)
        self.manager.plugins['broken_plugin'] = plugin
        
        # Should handle activation failure gracefully
        with patch('velocitytree.plugin_system.logger') as mock_logger:
            self.manager.activate_plugin('broken_plugin')
            mock_logger.error.assert_called()
    
    def test_command_registration(self):
        """Test registering plugin commands."""
        plugin = MockPlugin(self.config)
        mock_cli = Mock()
        
        self.manager.plugins['mock_plugin'] = plugin
        self.manager.register_plugin_commands(plugin, mock_cli)
        
        assert plugin.commands_registered is True
    
    def test_list_plugins(self):
        """Test listing plugins."""
        plugin1 = MockPlugin(self.config)
        plugin2 = MockPlugin(self.config)
        plugin2._name = "mock_plugin_2"
        
        self.manager.plugins['mock_plugin'] = plugin1
        self.manager.plugins['mock_plugin_2'] = plugin2
        
        plugins = self.manager.list_plugins()
        
        assert len(plugins) == 2
        assert any(p['name'] == 'mock_plugin' for p in plugins)
        assert any(p['name'] == 'mock_plugin_2' for p in plugins)
    
    def test_metadata_loading(self, tmp_path):
        """Test loading plugin metadata."""
        # Create plugin with metadata
        plugin_dir = tmp_path / "metadata_plugin"
        plugin_dir.mkdir()
        
        # YAML metadata
        yaml_file = plugin_dir / "plugin.yaml"
        yaml_file.write_text("""
name: metadata_plugin
version: 2.0.0
description: Plugin with metadata
author: Test Author
requirements:
  - requests>=2.0.0
""")
        
        metadata = self.manager._load_plugin_metadata(plugin_dir)
        
        assert metadata['name'] == 'metadata_plugin'
        assert metadata['version'] == '2.0.0'
        assert metadata['author'] == 'Test Author'
    
    def test_environment_variable_path(self, monkeypatch):
        """Test loading plugin paths from environment."""
        custom_path = "/custom/plugin/path"
        monkeypatch.setenv("VELOCITYTREE_PLUGIN_PATH", custom_path)
        
        manager = PluginManager(self.config)
        
        assert any(str(path) == custom_path for path in manager.plugin_dirs)
    
    def test_auto_load_configuration(self):
        """Test auto-load configuration."""
        # Test with auto_load disabled
        config_data = {'plugins': {'auto_load': False}}
        
        with patch.object(self.config, 'config_data', config_data):
            manager = PluginManager(self.config)
            # Should not attempt to load plugins automatically
            assert len(manager.plugins) == 0
    
    def test_enabled_plugins_configuration(self):
        """Test loading specific enabled plugins."""
        config_data = {
            'plugins': {
                'enabled': ['plugin1', 'plugin2']
            }
        }
        
        with patch.object(self.config, 'config_data', config_data):
            with patch.object(PluginManager, 'load_plugin') as mock_load:
                manager = PluginManager(self.config)
                
                # Should attempt to load enabled plugins
                calls = [call[0][0] for call in mock_load.call_args_list]
                assert 'plugin1' in calls
                assert 'plugin2' in calls


class TestPluginIntegration:
    """Integration tests for the plugin system."""
    
    def test_full_plugin_lifecycle(self, tmp_path):
        """Test complete plugin lifecycle."""
        # Create a test plugin
        plugin_file = tmp_path / "lifecycle_plugin.py"
        plugin_file.write_text("""
from velocitytree.plugin_system import Plugin

class LifecyclePlugin(Plugin):
    def __init__(self, config=None):
        super().__init__(config)
        self.events = []
    
    @property
    def name(self):
        return "lifecycle_plugin"
    
    @property
    def version(self):
        return "1.0.0"
    
    def activate(self):
        super().activate()
        self.events.append('activated')
    
    def deactivate(self):
        super().deactivate()
        self.events.append('deactivated')
    
    def register_hooks(self, hook_manager):
        hook_manager.register_hook('test_event', self.on_test)
    
    def on_test(self, **kwargs):
        self.events.append('hook_triggered')
""")
        
        # Add plugin directory to sys.path
        sys.path.insert(0, str(tmp_path))
        
        try:
            # Create manager and discover plugin
            config = Config()
            manager = PluginManager(config)
            manager.plugin_dirs.append(tmp_path)
            
            # Discover and load plugin
            discovered = manager.discover_plugins()
            assert "lifecycle_plugin" in discovered
            
            # Load and activate plugin
            plugin = manager.load_plugin("lifecycle_plugin")
            assert plugin is not None
            
            manager.activate_plugin("lifecycle_plugin")
            assert plugin.is_active
            
            # Trigger hook
            manager.hook_manager.trigger_hook('test_event')
            
            # Deactivate plugin
            manager.deactivate_plugin("lifecycle_plugin")
            
            # Check events
            assert 'activated' in plugin.events
            assert 'hook_triggered' in plugin.events
            assert 'deactivated' in plugin.events
            
        finally:
            # Clean up sys.path
            sys.path.remove(str(tmp_path))
    
    def test_plugin_configuration(self, tmp_path):
        """Test plugin configuration handling."""
        # Create plugin that uses configuration
        plugin_file = tmp_path / "config_plugin.py"
        plugin_file.write_text("""
from velocitytree.plugin_system import Plugin

class ConfigPlugin(Plugin):
    def __init__(self, config=None):
        super().__init__(config)
        self.settings = {}
    
    @property
    def name(self):
        return "config_plugin"
    
    @property
    def version(self):
        return "1.0.0"
    
    def activate(self):
        super().activate()
        if self.config and hasattr(self.config, 'config_data'):
            plugin_config = self.config.config_data.get('plugins', {})
            if isinstance(plugin_config, dict):
                self.settings = plugin_config.get(self.name, {})
""")
        
        # Create configuration
        config_data = {
            'plugins': {
                'config_plugin': {
                    'option1': 'value1',
                    'option2': 42
                }
            }
        }
        
        # Mock config with test data
        config = Config()
        with patch.object(config, 'config_data', config_data):
            sys.path.insert(0, str(tmp_path))
            
            try:
                manager = PluginManager(config)
                manager.plugin_dirs.append(tmp_path)
                
                # Load and activate plugin
                plugin = manager.load_plugin("config_plugin")
                manager.activate_plugin("config_plugin")
                
                # Check configuration was loaded
                assert plugin.settings['option1'] == 'value1'
                assert plugin.settings['option2'] == 42
                
            finally:
                sys.path.remove(str(tmp_path))


class TestPluginErrors:
    """Test error handling in the plugin system."""
    
    def test_invalid_plugin_file(self, tmp_path):
        """Test handling invalid plugin files."""
        # Create invalid Python file
        invalid_file = tmp_path / "invalid_plugin.py"
        invalid_file.write_text("This is not valid Python code!")
        
        config = Config()
        manager = PluginManager(config)
        manager.plugin_dirs.append(tmp_path)
        
        # Should handle error gracefully
        with patch('velocitytree.plugin_system.logger') as mock_logger:
            discovered = manager.discover_plugins()
            # May or may not discover the file, but shouldn't crash
            assert isinstance(discovered, list)
    
    def test_missing_required_properties(self, tmp_path):
        """Test plugin missing required properties."""
        plugin_file = tmp_path / "incomplete_plugin.py"
        plugin_file.write_text("""
from velocitytree.plugin_system import Plugin

class IncompletePlugin(Plugin):
    # Missing required properties
    pass
""")
        
        config = Config()
        manager = PluginManager(config)
        manager.plugin_dirs.append(tmp_path)
        
        sys.path.insert(0, str(tmp_path))
        
        try:
            # Should fail to instantiate
            plugin = manager.load_plugin("incomplete_plugin")
            assert plugin is None
            
        finally:
            sys.path.remove(str(tmp_path))
    
    def test_circular_dependency(self):
        """Test handling circular plugin dependencies."""
        # Create two plugins that depend on each other
        # This is a conceptual test - actual implementation would need dependency handling
        config = Config()
        manager = PluginManager(config)
        
        # Create mock plugins with circular dependency
        plugin1 = MockPlugin(config)
        plugin1._name = "plugin1"
        plugin1.dependencies = ["plugin2"]
        
        plugin2 = MockPlugin(config)
        plugin2._name = "plugin2"
        plugin2.dependencies = ["plugin1"]
        
        manager.plugins["plugin1"] = plugin1
        manager.plugins["plugin2"] = plugin2
        
        # Should handle circular dependency gracefully
        # (actual implementation would need to detect and handle this)
        manager.activate_plugin("plugin1")
        manager.activate_plugin("plugin2")


def test_plugin_discovery_with_metadata(tmp_path):
    """Test plugin discovery with various metadata formats."""
    # Create plugin with JSON metadata
    json_plugin = tmp_path / "json_plugin"
    json_plugin.mkdir()
    
    (json_plugin / "__init__.py").write_text("""
from velocitytree.plugin_system import Plugin

class JSONPlugin(Plugin):
    @property
    def name(self):
        return "json_plugin"
    
    @property
    def version(self):
        return "1.0.0"
""")
    
    (json_plugin / "plugin.json").write_text(json.dumps({
        "name": "json_plugin",
        "version": "1.0.0",
        "description": "Plugin with JSON metadata"
    }))
    
    # Create plugin with TOML metadata
    toml_plugin = tmp_path / "toml_plugin"
    toml_plugin.mkdir()
    
    (toml_plugin / "__init__.py").write_text("""
from velocitytree.plugin_system import Plugin

class TOMLPlugin(Plugin):
    @property
    def name(self):
        return "toml_plugin"
    
    @property
    def version(self):
        return "1.0.0"
""")
    
    (toml_plugin / "plugin.toml").write_text("""
name = "toml_plugin"
version = "1.0.0"
description = "Plugin with TOML metadata"
""")
    
    config = Config()
    manager = PluginManager(config)
    manager.plugin_dirs.append(tmp_path)
    
    discovered = manager.discover_plugins()
    
    assert "json_plugin" in discovered
    assert "toml_plugin" in discovered


def test_plugin_cli_integration():
    """Test plugin CLI command integration."""
    config = Config()
    manager = PluginManager(config)
    
    # Create mock CLI
    mock_cli = Mock()
    mock_plugin_group = Mock()
    mock_cli.group.return_value = mock_plugin_group
    
    # Add a test plugin
    plugin = MockPlugin(config)
    manager.plugins['mock_plugin'] = plugin
    
    # Register CLI commands
    manager.register_cli_commands(mock_cli)
    
    # Should create plugin group and register commands
    mock_cli.group.assert_called_with('plugin')
    assert mock_plugin_group.command.call_count > 0