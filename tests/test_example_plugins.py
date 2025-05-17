"""Tests for example plugins."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from velocitytree.plugin_system import HookManager, PluginManager, Plugin
from velocitytree.config import Config


class TestExamplePlugins:
    """Test example plugins discovery and functionality."""
    
    def setup_method(self, method):
        """Setup for each test."""
        # Add the plugins directory to sys.path for direct imports
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        if str(plugins_dir) not in sys.path:
            sys.path.insert(0, str(plugins_dir))
    
    def test_json_formatter_plugin_discovery(self):
        """Test JSON formatter plugin can be discovered."""
        from velocitytree.config import Config
        config = Config()
        plugin_manager = PluginManager(config)
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        plugin_dir = plugins_dir / 'json_formatter'
        
        # Check plugin directory exists
        assert plugin_dir.exists()
        assert (plugin_dir / 'plugin.yaml').exists()
        assert (plugin_dir / 'plugin.py').exists()
    
    def test_json_formatter_functionality(self, tmp_path):
        """Test JSON formatter plugin functionality."""
        # Import the plugin module directly
        from json_formatter.plugin import JSONFormatterPlugin
        
        plugin = JSONFormatterPlugin()
        assert plugin.name == "json_formatter"
        assert plugin.version == "1.0.0"
        
        # Test activation
        config = {'indent': 4, 'sort_keys': False}
        plugin._config.update(config)
        plugin.activate()
        assert plugin._config['indent'] == 4
        assert plugin._config['sort_keys'] is False
        
        # Test hook functionality
        hook_manager = HookManager()
        plugin.register_hooks(hook_manager)
        
        # Create test JSON file
        json_file = tmp_path / "test.json"
        test_data = {"b": 2, "a": 1, "c": {"nested": True}}
        json_file.write_text(json.dumps(test_data))
        
        # Execute hook
        hook_manager.trigger_hook('flatten_complete', 
                                  output_path=json_file, 
                                  context=test_data)
        
        # Check formatted output
        result = json.loads(json_file.read_text())
        assert result == test_data
        
        # Check formatting (should be pretty printed)
        content = json_file.read_text()
        assert "\n" in content  # Should have newlines
        assert "    " in content  # Should have indentation
    
    def test_output_validator_plugin_discovery(self):
        """Test output validator plugin can be discovered."""
        config = Config()
        plugin_manager = PluginManager(config)
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        plugin_dir = plugins_dir / 'output_validator'
        
        # Check plugin directory exists
        assert plugin_dir.exists()
        assert (plugin_dir / 'plugin.yaml').exists()
        assert (plugin_dir / 'plugin.py').exists()
    
    def test_output_validator_functionality(self, tmp_path):
        """Test output validator plugin functionality."""
        # Import the plugin module directly
        from output_validator.plugin import OutputValidatorPlugin
        
        plugin = OutputValidatorPlugin()
        assert plugin.name == "output_validator"
        assert plugin.version == "1.0.0"
        
        # Test file validation
        valid_file = tmp_path / "test.py"
        valid_file.write_text("print('hello')")
        errors = plugin.validate_file(valid_file)
        assert len(errors) == 0
        
        # Test invalid extension
        plugin._config['allowed_extensions'] = ['.txt']
        errors = plugin.validate_file(valid_file)
        assert any("extension" in e for e in errors)
    
    def test_custom_commands_plugin_discovery(self):
        """Test custom commands plugin can be discovered."""
        config = Config()
        plugin_manager = PluginManager(config)
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        plugin_dir = plugins_dir / 'custom_commands'
        
        # Check plugin directory exists
        assert plugin_dir.exists()
        assert (plugin_dir / 'plugin.yaml').exists()
        assert (plugin_dir / 'plugin.py').exists()
    
    def test_custom_commands_functionality(self):
        """Test custom commands plugin functionality."""
        # Import the plugin module directly
        from custom_commands.plugin import CustomCommandsPlugin
        
        plugin = CustomCommandsPlugin()
        assert plugin.name == "custom_commands"
        assert plugin.version == "1.0.0"
        
        # Test activation
        config = {'commands': [{'name': 'test', 'description': 'Test command'}]}
        plugin._config.update(config)
        plugin.activate()
        assert len(plugin._config['commands']) == 1
        assert plugin._config['commands'][0]['name'] == 'test'
    
    def test_plugin_manager_discovers_example_plugins(self):
        """Test that PluginManager can discover all example plugins."""
        config = Config()
        plugin_manager = PluginManager(config)
        
        # Add our plugins directory to the manager's search path
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        plugin_manager.plugin_dirs.append(plugins_dir)
        
        # Discover plugins
        discovered = plugin_manager.discover_plugins()
        
        # Check that our example plugins are discovered (discovered is a list of strings)
        plugin_names = set(discovered)
        assert 'json_formatter' in plugin_names
        assert 'output_validator' in plugin_names
        assert 'custom_commands' in plugin_names


# Integration tests for actual plugin loading
class TestPluginIntegration:
    """Integration tests for plugin loading."""
    
    def test_load_json_formatter_plugin(self):
        """Test loading JSON formatter plugin."""
        config = Config()
        plugin_manager = PluginManager(config)
        
        # Add our plugins directory
        plugins_dir = Path(__file__).parent.parent / 'velocitytree' / 'plugins'
        plugin_manager.plugin_dirs.append(plugins_dir)
        
        # Try to load the plugin
        plugin = plugin_manager._load_plugin_from_package('json_formatter', plugins_dir / 'json_formatter')
        
        # Check that the plugin was loaded
        assert plugin is not None
        assert plugin.name == 'json_formatter'
        
        # Also verify it shows up in discovered plugins
        discovered = plugin_manager.discover_plugins()
        assert 'json_formatter' in discovered