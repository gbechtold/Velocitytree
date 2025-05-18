"""
Test plugin lifecycle hooks.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from velocitytree.plugin_system import Plugin, PluginManager, HookManager
from velocitytree.config import Config


class MockPlugin(Plugin):
    """Mock plugin for testing."""
    
    name = "test_plugin"
    version = "1.0.0"
    description = "Test plugin for lifecycle hooks"
    
    def __init__(self, config):
        super().__init__(config)
        self.activate_called = False
        self.hooks_registered = False
    
    def activate(self):
        """Called when the plugin is activated."""
        super().activate()
        self.activate_called = True
    
    def register_hooks(self, hook_manager):
        """Register hooks for this plugin."""
        self.hooks_registered = True
        hook_manager.register_hook('test_event', self.test_hook)
    
    def test_hook(self, *args):
        """Test hook callback."""
        return "test_hook_result"


class TestHookManager:
    """Test HookManager functionality."""
    
    def test_lifecycle_hook_definitions(self):
        """Test that lifecycle hooks are properly defined."""
        hook_manager = HookManager()
        
        # Check core lifecycle hooks
        assert 'velocitytree_startup' in hook_manager.hook_metadata
        assert 'velocitytree_shutdown' in hook_manager.hook_metadata
        
        # Check plugin lifecycle hooks
        assert 'plugin_activated' in hook_manager.hook_metadata
        assert 'plugin_deactivated' in hook_manager.hook_metadata
        assert 'plugin_loaded' in hook_manager.hook_metadata
        
        # Check workflow lifecycle hooks
        assert 'workflow_start' in hook_manager.hook_metadata
        assert 'workflow_step' in hook_manager.hook_metadata
        assert 'workflow_complete' in hook_manager.hook_metadata
        assert 'workflow_error' in hook_manager.hook_metadata
        
        # Check file operation hooks
        assert 'before_flatten' in hook_manager.hook_metadata
        assert 'after_flatten' in hook_manager.hook_metadata
        
        # Check monitoring hooks
        assert 'drift_detected' in hook_manager.hook_metadata
        assert 'alert_created' in hook_manager.hook_metadata
        
        # Check AI hooks
        assert 'before_ai_request' in hook_manager.hook_metadata
        assert 'after_ai_response' in hook_manager.hook_metadata
    
    def test_hook_priority(self):
        """Test hook priority execution order."""
        hook_manager = HookManager()
        execution_order = []
        
        def hook1():
            execution_order.append('hook1')
        
        def hook2():
            execution_order.append('hook2')
        
        def hook3():
            execution_order.append('hook3')
        
        # Register hooks with different priorities
        hook_manager.register_hook('test_event', hook2, priority=50)
        hook_manager.register_hook('test_event', hook1, priority=10)  # Should run first
        hook_manager.register_hook('test_event', hook3, priority=90)  # Should run last
        
        hook_manager.trigger_hook('test_event')
        
        assert execution_order == ['hook1', 'hook2', 'hook3']
    
    def test_hook_unregister(self):
        """Test unregistering hooks."""
        hook_manager = HookManager()
        
        def test_hook():
            return "result"
        
        hook_manager.register_hook('test_event', test_hook)
        assert len(hook_manager.hooks.get('test_event', [])) == 1
        
        hook_manager.unregister_hook('test_event', test_hook)
        assert len(hook_manager.hooks.get('test_event', [])) == 0
    
    def test_hook_error_handling(self):
        """Test hook error handling."""
        hook_manager = HookManager()
        
        def failing_hook():
            raise Exception("Hook failed")
        
        def working_hook():
            return "success"
        
        hook_manager.register_hook('test_event', failing_hook)
        hook_manager.register_hook('test_event', working_hook)
        
        results = hook_manager.trigger_hook('test_event')
        
        # Should still get result from working hook
        assert "success" in results
    
    def test_list_hooks(self):
        """Test listing registered hooks."""
        hook_manager = HookManager()
        
        def test_hook():
            pass
        
        hook_manager.register_hook('test_event', test_hook, priority=25)
        
        hooks_info = hook_manager.list_hooks()
        
        assert 'test_event' in hooks_info
        assert hooks_info['test_event']['callbacks'][0]['name'] == 'test_hook'
        assert hooks_info['test_event']['callbacks'][0]['priority'] == 25


class TestPluginManagerHooks:
    """Test PluginManager hook integration."""
    
    @patch('velocitytree.plugin_system.PluginManager._auto_load_plugins')
    def test_plugin_loaded_hook(self, mock_auto_load):
        """Test plugin_loaded hook is triggered."""
        config = MagicMock(spec=Config)
        config.config_data = {}
        plugin_manager = PluginManager(config)
        
        # Mock hook trigger to track calls
        plugin_manager.trigger_hook = MagicMock()
        
        # Create and load a mock plugin
        plugin = MockPlugin(config)
        plugin_manager.plugins['test_plugin'] = plugin
        
        # Activate plugin (which should trigger hooks)
        plugin_manager.activate_plugin('test_plugin')
        
        # Check that hooks were triggered
        assert plugin_manager.trigger_hook.call_count >= 1
        
        # Find the plugin_activated call
        activated_calls = [call for call in plugin_manager.trigger_hook.call_args_list 
                          if call[0][0] == 'plugin_activated']
        assert len(activated_calls) == 1
        assert activated_calls[0][0][1] == 'test_plugin'
    
    @patch('velocitytree.plugin_system.PluginManager._auto_load_plugins')
    def test_plugin_deactivated_hook(self, mock_auto_load):
        """Test plugin_deactivated hook is triggered."""
        config = MagicMock(spec=Config)
        config.config_data = {}
        plugin_manager = PluginManager(config)
        
        # Mock hook trigger to track calls
        plugin_manager.trigger_hook = MagicMock()
        
        # Create and load a mock plugin
        plugin = MockPlugin(config)
        plugin.is_active = True
        plugin_manager.plugins['test_plugin'] = plugin
        
        # Deactivate plugin
        plugin_manager.deactivate_plugin('test_plugin')
        
        # Check that deactivated hook was triggered
        plugin_manager.trigger_hook.assert_called_with('plugin_deactivated', 'test_plugin')
    
    @patch('velocitytree.plugin_system.PluginManager._auto_load_plugins')
    def test_plugin_hooks_registration(self, mock_auto_load):
        """Test that plugin hooks are registered on activation."""
        config = MagicMock(spec=Config)
        config.config_data = {}
        plugin_manager = PluginManager(config)
        
        # Create and load a mock plugin
        plugin = MockPlugin(config)
        plugin_manager.plugins['test_plugin'] = plugin
        
        # Activate plugin
        plugin_manager.activate_plugin('test_plugin')
        
        # Check that plugin's register_hooks was called
        assert plugin.hooks_registered


class TestWorkflowHooks:
    """Test workflow lifecycle hooks."""
    
    @pytest.mark.skipif(
        not Path(__file__).parent.parent.joinpath('velocitytree', 'workflows.py').exists(),
        reason="Workflows module not available"
    )
    def test_workflow_hooks(self):
        """Test workflow lifecycle hooks are triggered."""
        from velocitytree.workflows import Workflow, WorkflowStep
        from velocitytree.workflow_context import WorkflowContext
        
        # Create a simple workflow
        workflow_config = {
            'description': 'Test workflow',
            'steps': [
                {
                    'name': 'Test Step',
                    'type': 'command',
                    'command': 'echo "test"'
                }
            ]
        }
        
        workflow = Workflow('test_workflow', workflow_config)
        context = WorkflowContext()
        
        # Mock the plugin manager to track hook calls
        with patch('velocitytree.workflows.PluginManager') as mock_plugin_manager:
            mock_instance = mock_plugin_manager.return_value
            mock_instance.trigger_hook = MagicMock()
            
            # Execute workflow
            workflow.execute(context)
            
            # Check that workflow_start hook was triggered
            mock_instance.trigger_hook.assert_any_call('workflow_start', 'test_workflow', context)


class TestHookIntegration:
    """Test hook integration with various components."""
    
    def test_hook_metadata_access(self):
        """Test accessing hook metadata."""
        hook_manager = HookManager()
        
        metadata = hook_manager.get_hook_metadata('workflow_start')
        
        assert metadata['description'] == 'Triggered when a workflow starts'
        assert metadata['args'] == ['workflow_name', 'context']
        assert metadata['return'] is None
    
    def test_hook_return_values(self):
        """Test hooks that return values."""
        hook_manager = HookManager()
        
        def modify_prompt(prompt, context, system_prompt):
            return f"Modified: {prompt}"
        
        hook_manager.register_hook('before_ai_request', modify_prompt)
        
        results = hook_manager.trigger_hook('before_ai_request', 'test prompt', {}, 'system')
        
        assert results[0] == "Modified: test prompt"
    
    def test_multiple_hook_results(self):
        """Test aggregating results from multiple hooks."""
        hook_manager = HookManager()
        
        def hook1(*args):
            return "result1"
        
        def hook2(*args):
            return "result2"
        
        hook_manager.register_hook('test_event', hook1)
        hook_manager.register_hook('test_event', hook2)
        
        results = hook_manager.trigger_hook('test_event')
        
        assert len(results) == 2
        assert "result1" in results
        assert "result2" in results


class TestModuleHooks:
    """Test hooks in different modules."""
    
    @patch('velocitytree.plugin_system.PluginManager._auto_load_plugins')
    def test_ai_hooks(self, mock_auto_load):
        """Test AI integration hooks."""
        config = MagicMock(spec=Config)
        config.config_data = {}
        plugin_manager = PluginManager(config)
        
        # Track hook calls
        ai_requests = []
        ai_responses = []
        
        def before_ai(prompt, context, system_prompt):
            ai_requests.append((prompt, context, system_prompt))
            return f"Modified: {prompt}"
        
        def after_ai(response, prompt):
            ai_responses.append((response, prompt))
            return response
        
        plugin_manager.hook_manager.register_hook('before_ai_request', before_ai)
        plugin_manager.hook_manager.register_hook('after_ai_response', after_ai)
        
        # Simulate AI request
        results = plugin_manager.trigger_hook('before_ai_request', 'test prompt', {}, 'system')
        assert results[0] == "Modified: test prompt"
        
        # Simulate AI response
        plugin_manager.trigger_hook('after_ai_response', 'AI response', 'test prompt')
        
        assert len(ai_requests) == 1
        assert len(ai_responses) == 1
    
    @patch('velocitytree.plugin_system.PluginManager._auto_load_plugins')
    def test_monitoring_hooks(self, mock_auto_load):
        """Test monitoring system hooks."""
        config = MagicMock(spec=Config)
        config.config_data = {}
        plugin_manager = PluginManager(config)
        
        # Track drift and alerts
        drifts = []
        alerts = []
        
        def on_drift(drift_info, project_path):
            drifts.append((drift_info, project_path))
        
        def on_alert(alert_data, channel):
            alerts.append((alert_data, channel))
        
        plugin_manager.hook_manager.register_hook('drift_detected', on_drift)
        plugin_manager.hook_manager.register_hook('alert_created', on_alert)
        
        # Simulate drift detection
        drift_info = {'type': 'spec_mismatch', 'severity': 'high'}
        plugin_manager.trigger_hook('drift_detected', drift_info, '/project')
        
        # Simulate alert creation
        alert_data = {'message': 'Drift detected', 'severity': 'high'}
        plugin_manager.trigger_hook('alert_created', alert_data, 'email')
        
        assert len(drifts) == 1
        assert drifts[0][0]['type'] == 'spec_mismatch'
        
        assert len(alerts) == 1
        assert alerts[0][0]['message'] == 'Drift detected'
        assert alerts[0][1] == 'email'


class TestHookDocumentation:
    """Test hook documentation and metadata."""
    
    def test_all_hooks_documented(self):
        """Test that all hooks have proper documentation."""
        hook_manager = HookManager()
        
        for hook_name, metadata in hook_manager.hook_metadata.items():
            assert 'description' in metadata, f"Hook {hook_name} missing description"
            assert 'args' in metadata, f"Hook {hook_name} missing args"
            assert 'return' in metadata, f"Hook {hook_name} missing return info"
            
            # Check description is meaningful
            assert len(metadata['description']) > 10, f"Hook {hook_name} has too short description"
            
            # Check args is a list
            assert isinstance(metadata['args'], list), f"Hook {hook_name} args should be a list"
    
    def test_hook_categories(self):
        """Test that hooks are properly categorized."""
        hook_manager = HookManager()
        
        # Define expected categories and their hooks
        expected_categories = {
            'core': ['velocitytree_startup', 'velocitytree_shutdown'],
            'plugin': ['plugin_activated', 'plugin_deactivated', 'plugin_loaded'],
            'workflow': ['workflow_start', 'workflow_step', 'workflow_complete', 'workflow_error'],
            'ai': ['before_ai_request', 'after_ai_response', 'ai_suggestion_generated'],
            'monitoring': ['drift_detected', 'alert_created', 'analysis_complete']
        }
        
        # Check that all expected hooks exist
        for category, hooks in expected_categories.items():
            for hook in hooks:
                assert hook in hook_manager.hook_metadata, f"Expected hook {hook} in {category} category"