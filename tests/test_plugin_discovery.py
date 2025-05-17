"""Tests for plugin discovery mechanism."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from velocitytree.plugin_system import Plugin, PluginManager
from velocitytree.config import Config


class TestPluginDiscovery:
    """Test plugin discovery functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock(spec=Config)
        config.config = {
            'plugins': {
                'auto_load': False,
                'enabled': [],
                'directories': []
            }
        }
        config.config_data = {
            'plugins': []
        }
        return config
    
    @pytest.fixture
    def plugin_manager(self, mock_config):
        """Create a plugin manager."""
        return PluginManager(mock_config)
    
    def test_discover_builtin_plugins(self, plugin_manager):
        """Test discovering built-in plugins."""
        # Should discover hello_world plugin in built-in directory
        plugins = plugin_manager.discover_plugins()
        assert 'hello_world' in plugins
    
    def test_discover_from_custom_directory(self, plugin_manager):
        """Test discovering plugins from custom directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add custom directory
            plugin_manager.plugin_dirs.append(Path(tmpdir))
            
            # Create a test plugin file
            plugin_file = Path(tmpdir) / 'test_plugin.py'
            plugin_file.write_text("""
class TestPlugin:
    pass
""")
            
            plugins = plugin_manager.discover_plugins()
            assert 'test_plugin' in plugins
    
    def test_discover_plugin_packages(self, plugin_manager):
        """Test discovering plugin packages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add custom directory
            plugin_manager.plugin_dirs.append(Path(tmpdir))
            
            # Create a plugin package
            package_dir = Path(tmpdir) / 'my_plugin'
            package_dir.mkdir()
            
            # Create __init__.py
            (package_dir / '__init__.py').write_text('__plugin__ = True')
            
            plugins = plugin_manager.discover_plugins()
            assert 'my_plugin' in plugins
    
    def test_discover_with_metadata_file(self, plugin_manager):
        """Test discovering plugins with metadata files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Add custom directory
            plugin_manager.plugin_dirs.append(Path(tmpdir))
            
            # Create a plugin package with metadata
            package_dir = Path(tmpdir) / 'metadata_plugin'
            package_dir.mkdir()
            
            # Create __init__.py
            (package_dir / '__init__.py').write_text('')
            
            # Create plugin.yaml
            (package_dir / 'plugin.yaml').write_text("""
name: metadata_plugin
version: 1.0.0
description: Test plugin with metadata
""")
            
            plugins = plugin_manager.discover_plugins()
            assert 'metadata_plugin' in plugins
    
    @patch('importlib.metadata.entry_points')
    def test_discover_entry_point_plugins(self, mock_entry_points, plugin_manager):
        """Test discovering plugins from entry points."""
        # Mock entry point
        mock_ep = Mock()
        mock_ep.name = 'entry_plugin'
        
        # Python 3.10+ style
        mock_entry_points.return_value.select.return_value = [mock_ep]
        
        plugins = plugin_manager.discover_plugins()
        assert 'entry_plugin' in plugins
    
    @patch('importlib.metadata.distributions')
    @patch('importlib.metadata.entry_points')
    def test_discover_pip_plugins(self, mock_entry_points, mock_distributions, plugin_manager):
        """Test discovering pip-installed plugins."""
        # Mock distribution
        mock_dist = Mock()
        mock_dist.name = 'velocitytree-plugin-test'
        
        mock_distributions.return_value = [mock_dist]
        
        # Mock entry_points to return empty selection
        mock_entry_points.return_value.select.return_value = []
        
        plugins = plugin_manager.discover_plugins()
        assert 'test' in plugins
    
    def test_environment_variable_paths(self):
        """Test plugin directories from environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('os.environ', {'VELOCITYTREE_PLUGIN_PATH': tmpdir}):
                config = Mock(spec=Config)
                config.config = {'plugins': {}}
                config.config_data = {'plugins': []}
                
                manager = PluginManager(config)
                # Need to resolve the path since the manager normalizes paths
                resolved_path = Path(tmpdir).resolve()
                assert resolved_path in manager.plugin_dirs
    
    def test_config_custom_directories(self, mock_config):
        """Test plugin directories from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_config.config['plugins']['directories'] = [tmpdir]
            mock_config.config_data = {'plugins': {'directories': [tmpdir]}}
            
            manager = PluginManager(mock_config)
            # Need to resolve the path since the manager normalizes paths
            resolved_path = Path(tmpdir).resolve()
            assert resolved_path in manager.plugin_dirs
    
    def test_is_valid_plugin_package(self, plugin_manager):
        """Test plugin package validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            package_dir = Path(tmpdir) / 'test_plugin'
            package_dir.mkdir()
            
            # Without any marker - should be invalid
            (package_dir / '__init__.py').write_text('')
            assert not plugin_manager._is_valid_plugin_package(package_dir)
            
            # With __plugin__ marker - should be valid
            (package_dir / '__init__.py').write_text('__plugin__ = True')
            assert plugin_manager._is_valid_plugin_package(package_dir)
            
            # With Plugin class - should be valid
            (package_dir / '__init__.py').write_text('class Plugin: pass')
            assert plugin_manager._is_valid_plugin_package(package_dir)
            
            # With metadata file - should be valid
            (package_dir / '__init__.py').write_text('')
            (package_dir / 'plugin.yaml').write_text('name: test')
            assert plugin_manager._is_valid_plugin_package(package_dir)
    
    def test_no_duplicate_plugins(self, plugin_manager):
        """Test that plugin discovery returns unique names."""
        # Add duplicate directories
        plugin_manager.plugin_dirs.append(plugin_manager.plugin_dirs[0])
        
        plugins = plugin_manager.discover_plugins()
        
        # Should have unique plugin names
        assert len(plugins) == len(set(plugins))