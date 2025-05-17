"""Tests for plugin lifecycle hooks."""

import pytest
from unittest.mock import Mock, patch, call

from velocitytree.plugins import Plugin, PluginManager, HookManager
from velocitytree.config import Config


class TestLifecycleHooks:
    """Test plugin lifecycle hooks."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock(spec=Config)
        config.config = {
            'plugins': {
                'auto_load': False,
                'enabled': [],
            }
        }
        return config
    
    @pytest.fixture
    def hook_manager(self):
        """Create a hook manager."""
        return HookManager()
    
    @pytest.fixture
    def plugin_manager(self, mock_config):
        """Create a plugin manager."""
        return PluginManager(mock_config)
    
    def test_hook_registration(self, hook_manager):
        """Test hook registration and priority."""
        # Register hooks with different priorities
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        hook_manager.register_hook('test_event', callback2, priority=50)
        hook_manager.register_hook('test_event', callback1, priority=10)
        hook_manager.register_hook('test_event', callback3, priority=90)
        
        # Trigger hook
        hook_manager.trigger_hook('test_event', 'arg1', key='value')
        
        # Check callbacks are called in priority order
        assert callback1.call_count == 1
        assert callback2.call_count == 1
        assert callback3.call_count == 1
        
        # Verify call order (lower priority first)
        callback1.assert_called_with('arg1', key='value')
        callback2.assert_called_with('arg1', key='value')
        callback3.assert_called_with('arg1', key='value')
    
    def test_hook_unregistration(self, hook_manager):
        """Test hook unregistration."""
        callback = Mock()
        
        # Register and unregister
        hook_manager.register_hook('test_event', callback)
        hook_manager.unregister_hook('test_event', callback)
        
        # Trigger should not call callback
        hook_manager.trigger_hook('test_event')
        assert callback.call_count == 0
    
    def test_hook_chain(self, hook_manager):
        """Test hook chain modification."""
        def modifier1(value):
            return value + " modified1"
        
        def modifier2(value):
            return value + " modified2"
        
        hook_manager.register_hook('chain_event', modifier1)
        hook_manager.register_hook('chain_event', modifier2)
        
        result = hook_manager.trigger_hook_chain('chain_event', "initial")
        assert result == "initial modified1 modified2"
    
    def test_hook_error_handling(self, hook_manager):
        """Test hook error handling."""
        def failing_hook(*args, **kwargs):
            raise Exception("Hook failed")
        
        def normal_hook(*args, **kwargs):
            return "success"
        
        hook_manager.register_hook('test_event', failing_hook)
        hook_manager.register_hook('test_event', normal_hook)
        
        # Should continue after error
        results = hook_manager.trigger_hook('test_event')
        assert len(results) == 2
        assert results[1] == "success"
    
    def test_plugin_lifecycle_methods(self, plugin_manager):
        """Test plugin lifecycle methods are called."""
        # Create a test plugin
        test_plugin = Mock(spec=Plugin)
        test_plugin.name = "test"
        test_plugin.version = "1.0.0"
        test_plugin.on_load = Mock()
        test_plugin.on_unload = Mock()
        test_plugin.activate = Mock()
        test_plugin.deactivate = Mock()
        test_plugin.register_hooks = Mock()
        
        # Manually add to plugins
        plugin_manager.plugins['test'] = test_plugin
        
        # Test activation
        plugin_manager.activate_plugin('test')
        test_plugin.register_hooks.assert_called_once()
        test_plugin.activate.assert_called_once()
        
        # Test deactivation
        plugin_manager.deactivate_plugin('test')
        test_plugin.deactivate.assert_called_once()
        
        # Test unload
        plugin_manager.unload_plugin('test')
        test_plugin.on_unload.assert_called_once()
    
    def test_plugin_lifecycle_hooks_triggered(self, plugin_manager):
        """Test plugin lifecycle hooks are triggered."""
        # Mock plugin loading
        with patch.object(plugin_manager, '_load_plugin_from_file') as mock_load:
            mock_plugin = Mock(spec=Plugin)
            mock_plugin.name = "test"
            mock_plugin.version = "1.0.0"
            mock_plugin.on_load = Mock()
            mock_load.return_value = mock_plugin
            
            # Mock hook manager
            plugin_manager.hook_manager.trigger_hook = Mock()
            
            # Load plugin through normal path
            plugin_manager.load_plugin('test')
            
            # Check hooks were triggered
            plugin_manager.hook_manager.trigger_hook.assert_any_call('plugin_loaded', 'test', mock_plugin)
    
    def test_available_hooks(self, hook_manager):
        """Test listing available hooks."""
        hooks = hook_manager.list_available_hooks()
        
        # Check some key hooks exist
        assert 'velocitytree_startup' in hooks
        assert 'velocitytree_shutdown' in hooks
        assert 'plugin_loaded' in hooks
        assert 'plugin_activated' in hooks
        assert 'workflow_start' in hooks
        assert 'workflow_complete' in hooks
        
        # Check hook metadata
        startup_hook = hooks['velocitytree_startup']
        assert startup_hook['description']
        assert startup_hook['args'] == ['config']
    
    def test_hook_propagation_stop(self, hook_manager):
        """Test hook propagation can be stopped."""
        def stopper(*args, **kwargs):
            return False  # Should stop propagation
        
        def should_not_run(*args, **kwargs):
            return "should not see this"
        
        hook_manager.register_hook('before_command', stopper, priority=10)
        hook_manager.register_hook('before_command', should_not_run, priority=20)
        
        results = hook_manager.trigger_hook('before_command', 'cmd', {})
        assert len(results) == 1
        assert results[0] is False
    
    def test_plugin_dependencies(self, plugin_manager):
        """Test plugin dependency resolution."""
        # Create plugins with dependencies
        plugin_a = Mock(spec=Plugin)
        plugin_a.name = "plugin_a"
        plugin_a.get_dependencies = Mock(return_value=[])
        
        plugin_b = Mock(spec=Plugin)
        plugin_b.name = "plugin_b"
        plugin_b.get_dependencies = Mock(return_value=["plugin_a"])
        
        plugin_c = Mock(spec=Plugin)
        plugin_c.name = "plugin_c"
        plugin_c.get_dependencies = Mock(return_value=["plugin_b"])
        
        plugin_manager.plugins = {
            'plugin_a': plugin_a,
            'plugin_b': plugin_b,
            'plugin_c': plugin_c
        }
        
        # Resolve dependencies
        order = plugin_manager.resolve_dependencies('plugin_c')
        assert order == ['plugin_a', 'plugin_b', 'plugin_c']
    
    def test_plugin_health_check(self, plugin_manager):
        """Test plugin health check."""
        # Create healthy plugin
        healthy_plugin = Mock(spec=Plugin)
        healthy_plugin.health_check = Mock(return_value=True)
        
        # Create unhealthy plugin
        unhealthy_plugin = Mock(spec=Plugin)
        unhealthy_plugin.health_check = Mock(return_value=False)
        
        plugin_manager.plugins = {
            'healthy': healthy_plugin,
            'unhealthy': unhealthy_plugin
        }
        
        assert plugin_manager.check_plugin_health('healthy') is True
        assert plugin_manager.check_plugin_health('unhealthy') is False
        assert plugin_manager.check_plugin_health('nonexistent') is False
    
    def test_plugin_reload(self, plugin_manager):
        """Test plugin reload functionality."""
        # Create a plugin
        test_plugin = Mock(spec=Plugin)
        test_plugin.name = "test"
        test_plugin.version = "1.0.0"
        test_plugin.on_unload = Mock()
        test_plugin._active = True
        
        plugin_manager.plugins['test'] = test_plugin
        
        with patch.object(plugin_manager, 'load_plugin') as mock_load:
            mock_load.return_value = test_plugin
            
            # Reload plugin
            result = plugin_manager.reload_plugin('test')
            
            assert result is True
            test_plugin.on_unload.assert_called_once()
            mock_load.assert_called_once_with('test')