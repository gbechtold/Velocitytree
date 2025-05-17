"""Tests for plugin hook integration."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from velocitytree.plugin_system import Plugin, PluginManager, HookManager
from velocitytree.config import Config


class HookTestPlugin(Plugin):
    """Plugin for testing hooks."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.events_received = []
    
    @property
    def name(self) -> str:
        return "hook_test_plugin"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def activate(self):
        """Activate the plugin."""
        super().activate()
    
    def register_hooks(self, hook_manager):
        """Register hooks for all events."""
        # Core system hooks
        hook_manager.register_hook('startup', self.on_startup)
        hook_manager.register_hook('shutdown', self.on_shutdown)
        hook_manager.register_hook('error', self.on_error)
        
        # Plugin lifecycle hooks
        hook_manager.register_hook('plugin_loaded', self.on_plugin_loaded)
        hook_manager.register_hook('plugin_activated', self.on_plugin_activated)
        hook_manager.register_hook('plugin_deactivated', self.on_plugin_deactivated)
        
        # Command lifecycle hooks
        hook_manager.register_hook('before_command', self.on_before_command)
        hook_manager.register_hook('after_command', self.on_after_command)
        
        # Project operation hooks
        hook_manager.register_hook('init_complete', self.on_init_complete)
        hook_manager.register_hook('flatten_complete', self.on_flatten_complete)
        
        # Workflow hooks
        hook_manager.register_hook('workflow_start', self.on_workflow_start)
        hook_manager.register_hook('workflow_complete', self.on_workflow_complete)
    
    def on_startup(self, **kwargs):
        self.events_received.append(('startup', kwargs))
    
    def on_shutdown(self, **kwargs):
        self.events_received.append(('shutdown', kwargs))
    
    def on_error(self, error, **kwargs):
        self.events_received.append(('error', {'error': error, **kwargs}))
    
    def on_plugin_loaded(self, plugin_name, **kwargs):
        self.events_received.append(('plugin_loaded', {'plugin_name': plugin_name, **kwargs}))
    
    def on_plugin_activated(self, plugin_name, **kwargs):
        self.events_received.append(('plugin_activated', {'plugin_name': plugin_name, **kwargs}))
    
    def on_plugin_deactivated(self, plugin_name, **kwargs):
        self.events_received.append(('plugin_deactivated', {'plugin_name': plugin_name, **kwargs}))
    
    def on_before_command(self, command_name, **kwargs):
        self.events_received.append(('before_command', {'command_name': command_name, **kwargs}))
    
    def on_after_command(self, command_name, result, **kwargs):
        self.events_received.append(('after_command', {'command_name': command_name, 'result': result, **kwargs}))
    
    def on_init_complete(self, project_path, **kwargs):
        self.events_received.append(('init_complete', {'project_path': project_path, **kwargs}))
    
    def on_flatten_complete(self, output_path, context, **kwargs):
        self.events_received.append(('flatten_complete', {'output_path': output_path, 'context': context, **kwargs}))
    
    def on_workflow_start(self, workflow_name, **kwargs):
        self.events_received.append(('workflow_start', {'workflow_name': workflow_name, **kwargs}))
    
    def on_workflow_complete(self, workflow_name, result, **kwargs):
        self.events_received.append(('workflow_complete', {'workflow_name': workflow_name, 'result': result, **kwargs}))


class TestPluginHooks:
    """Test plugin hook system."""
    
    def setup_method(self):
        """Setup for each test."""
        self.config = Config()
        self.plugin_manager = PluginManager(self.config)
        self.plugin = HookTestPlugin(self.config)
        self.plugin_manager.plugins['hook_test_plugin'] = self.plugin
        self.plugin_manager.activate_plugin('hook_test_plugin')
        # Register hooks
        self.plugin.register_hooks(self.plugin_manager.hook_manager)
    
    def test_startup_shutdown_hooks(self):
        """Test startup and shutdown hooks."""
        # Trigger startup
        self.plugin_manager.hook_manager.trigger_hook('startup')
        
        # Trigger shutdown
        self.plugin_manager.hook_manager.trigger_hook('shutdown')
        
        # Check events
        events = [event[0] for event in self.plugin.events_received]
        assert 'startup' in events
        assert 'shutdown' in events
    
    def test_error_hook(self):
        """Test error handling hook."""
        error = Exception("Test error")
        self.plugin_manager.hook_manager.trigger_hook('error', error=error, context="test_context")
        
        # Check error was received
        error_events = [e for e in self.plugin.events_received if e[0] == 'error']
        assert len(error_events) == 1
        assert error_events[0][1]['error'] == error
        assert error_events[0][1]['context'] == "test_context"
    
    def test_plugin_lifecycle_hooks(self):
        """Test plugin lifecycle hooks."""
        # Trigger plugin loaded
        self.plugin_manager.hook_manager.trigger_hook('plugin_loaded', plugin_name='test_plugin')
        
        # Trigger plugin activated
        self.plugin_manager.hook_manager.trigger_hook('plugin_activated', plugin_name='test_plugin')
        
        # Trigger plugin deactivated
        self.plugin_manager.hook_manager.trigger_hook('plugin_deactivated', plugin_name='test_plugin')
        
        # Check events
        events = {event[0]: event[1] for event in self.plugin.events_received}
        
        assert 'plugin_loaded' in events
        assert events['plugin_loaded']['plugin_name'] == 'test_plugin'
        
        assert 'plugin_activated' in events
        assert events['plugin_activated']['plugin_name'] == 'test_plugin'
        
        assert 'plugin_deactivated' in events
        assert events['plugin_deactivated']['plugin_name'] == 'test_plugin'
    
    def test_command_hooks(self):
        """Test command lifecycle hooks."""
        # Trigger before command
        self.plugin_manager.hook_manager.trigger_hook('before_command', command_name='flatten')
        
        # Trigger after command
        self.plugin_manager.hook_manager.trigger_hook('after_command', command_name='flatten', result={'status': 'success'})
        
        # Check events
        events = {event[0]: event[1] for event in self.plugin.events_received}
        
        assert 'before_command' in events
        assert events['before_command']['command_name'] == 'flatten'
        
        assert 'after_command' in events
        assert events['after_command']['command_name'] == 'flatten'
        assert events['after_command']['result']['status'] == 'success'
    
    def test_project_operation_hooks(self):
        """Test project operation hooks."""
        # Trigger init complete
        self.plugin_manager.hook_manager.trigger_hook('init_complete', project_path='/test/project')
        
        # Trigger flatten complete
        self.plugin_manager.hook_manager.trigger_hook('flatten_complete', 
                                                     output_path='/test/output',
                                                     context={'files': 10})
        
        # Check events
        events = {event[0]: event[1] for event in self.plugin.events_received}
        
        assert 'init_complete' in events
        assert events['init_complete']['project_path'] == '/test/project'
        
        assert 'flatten_complete' in events
        assert events['flatten_complete']['output_path'] == '/test/output'
        assert events['flatten_complete']['context']['files'] == 10
    
    def test_workflow_hooks(self):
        """Test workflow hooks."""
        # Trigger workflow start
        self.plugin_manager.hook_manager.trigger_hook('workflow_start', workflow_name='test_workflow')
        
        # Trigger workflow complete
        self.plugin_manager.hook_manager.trigger_hook('workflow_complete', 
                                                     workflow_name='test_workflow',
                                                     result={'status': 'completed'})
        
        # Check events
        events = {event[0]: event[1] for event in self.plugin.events_received}
        
        assert 'workflow_start' in events
        assert events['workflow_start']['workflow_name'] == 'test_workflow'
        
        assert 'workflow_complete' in events
        assert events['workflow_complete']['workflow_name'] == 'test_workflow'
        assert events['workflow_complete']['result']['status'] == 'completed'
    
    def test_hook_execution_order(self):
        """Test hook execution order with multiple plugins."""
        # Create second plugin
        plugin2 = HookTestPlugin(self.config)
        plugin2._name = "hook_test_plugin_2"
        
        self.plugin_manager.plugins['hook_test_plugin_2'] = plugin2
        self.plugin_manager.activate_plugin('hook_test_plugin_2')
        plugin2.register_hooks(self.plugin_manager.hook_manager)
        
        # Clear previous events
        self.plugin.events_received.clear()
        plugin2.events_received.clear()
        
        # Trigger a hook
        self.plugin_manager.hook_manager.trigger_hook('startup')
        
        # Both plugins should receive the event
        assert len(self.plugin.events_received) == 1
        assert len(plugin2.events_received) == 1
        assert self.plugin.events_received[0][0] == 'startup'
        assert plugin2.events_received[0][0] == 'startup'
    
    def test_hook_return_values(self):
        """Test collecting return values from hooks."""
        # Create plugin that returns values
        class ReturningPlugin(Plugin):
            @property
            def name(self):
                return "returning_plugin"
            
            @property
            def version(self):
                return "1.0.0"
            
            def activate(self):
                super().activate()
            
            def register_hooks(self, hook_manager):
                hook_manager.register_hook('process_data', self.process)
            
            def process(self, data, **kwargs):
                return f"Processed: {data}"
        
        plugin = ReturningPlugin(self.config)
        self.plugin_manager.plugins['returning_plugin'] = plugin
        self.plugin_manager.activate_plugin('returning_plugin')
        plugin.register_hooks(self.plugin_manager.hook_manager)
        
        # Trigger hook and collect results
        results = self.plugin_manager.hook_manager.trigger_hook('process_data', data="test_data")
        
        assert "Processed: test_data" in results
    
    def test_hook_error_isolation(self):
        """Test that errors in one hook don't affect others."""
        # Create plugin that fails
        class FailingPlugin(Plugin):
            @property
            def name(self):
                return "failing_plugin"
            
            @property
            def version(self):
                return "1.0.0"
            
            def activate(self):
                super().activate()
            
            def register_hooks(self, hook_manager):
                hook_manager.register_hook('test_event', self.fail)
            
            def fail(self, **kwargs):
                raise Exception("Hook failed!")
        
        failing_plugin = FailingPlugin(self.config)
        self.plugin_manager.plugins['failing_plugin'] = failing_plugin
        self.plugin_manager.activate_plugin('failing_plugin')
        failing_plugin.register_hooks(self.plugin_manager.hook_manager)
        
        # Clear events
        self.plugin.events_received.clear()
        
        # Register test event handler in our test plugin
        def handle_test_event(**kwargs):
            self.plugin.events_received.append(('test_event', kwargs))
        
        self.plugin_manager.hook_manager.register_hook('test_event', handle_test_event)
        
        # Trigger event - should handle error in failing plugin
        self.plugin_manager.hook_manager.trigger_hook('test_event')
        
        # Our plugin should still receive the event
        assert len(self.plugin.events_received) == 1
        assert self.plugin.events_received[0][0] == 'test_event'


class TestHookIntegration:
    """Integration tests for hook system with actual commands."""
    
    def test_cli_hook_integration(self, tmp_path):
        """Test hooks triggered by CLI commands."""
        # This test demonstrates how hooks would be integrated with CLI
        # Since the actual CLI imports are done locally within functions,
        # we'll test the behavior directly instead of mocking imports
        
        config = Config()
        plugin_manager = PluginManager(config)
        
        # Add test plugin
        plugin = HookTestPlugin(config)
        plugin_manager.plugins['hook_test_plugin'] = plugin
        plugin_manager.activate_plugin('hook_test_plugin')
        plugin.register_hooks(plugin_manager.hook_manager)
        
        # Simulate CLI lifecycle
        plugin_manager.hook_manager.trigger_hook('before_command', command_name='init')
        plugin_manager.hook_manager.trigger_hook('init_complete', project_path=str(tmp_path))
        plugin_manager.hook_manager.trigger_hook('after_command', command_name='init', result={'status': 'success'})
        
        # Check hooks were triggered
        events = {event[0]: event[1] for event in plugin.events_received}
        assert 'before_command' in events
        assert events['before_command']['command_name'] == 'init'
        assert 'init_complete' in events
        assert 'after_command' in events
            
    def test_workflow_hook_integration(self):
        """Test hooks triggered by workflow execution."""
        # This test demonstrates how hooks would be integrated with workflows
        # Since WorkflowExecutor would be the one triggering hooks,
        # we'll simulate the behavior here
        
        config = Config()
        plugin_manager = PluginManager(config)
        
        # Add test plugin
        plugin = HookTestPlugin(config)
        plugin_manager.plugins['hook_test_plugin'] = plugin
        plugin_manager.activate_plugin('hook_test_plugin')
        plugin.register_hooks(plugin_manager.hook_manager)
        
        # Simulate workflow execution with hooks
        plugin_manager.hook_manager.trigger_hook('workflow_start', workflow_name='test_workflow')
        # Simulate workflow execution...
        result = {'status': 'success', 'steps_completed': 5}
        plugin_manager.hook_manager.trigger_hook('workflow_complete', 
                                                workflow_name='test_workflow',
                                                result=result)
        
        # Check hooks were triggered
        events = {event[0]: event[1] for event in plugin.events_received}
        assert 'workflow_start' in events
        assert events['workflow_start']['workflow_name'] == 'test_workflow'
        assert 'workflow_complete' in events
        assert events['workflow_complete']['workflow_name'] == 'test_workflow'
        assert events['workflow_complete']['result']['status'] == 'success'