"""Tests for workflow error handling and edge cases."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from velocitytree.workflows import (
    WorkflowStep,
    Workflow,
    WorkflowManager
)
from velocitytree.workflow_context import WorkflowContext
from velocitytree.config import Config


@pytest.fixture
def workflow_manager():
    """Create a workflow manager with mock config."""
    config = Mock(spec=Config)
    config.config = Mock()
    config.config.workflows = {}
    return WorkflowManager(config)


class TestErrorScenarios:
    """Test error scenarios in workflow execution."""
    
    def test_step_command_failure(self):
        """Test handling of failed command steps."""
        config = {
            'name': 'Failing Step',
            'type': 'command',
            'command': 'exit 1'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'error'
        assert result['exit_code'] == 1
    
    def test_step_python_exception(self):
        """Test handling of Python exceptions."""
        config = {
            'name': 'Exception Step',
            'type': 'python',
            'command': 'raise ValueError("Test error")'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'error'
        assert 'Test error' in result['error']
    
    def test_step_continue_on_error(self):
        """Test continue_on_error flag."""
        config = {
            'name': 'Error Step',
            'type': 'command',
            'command': 'exit 1',
            'continue_on_error': True
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Should not raise exception
        result = step.execute(context)
        assert result['status'] == 'error'
    
    def test_workflow_stop_on_error(self):
        """Test workflow stops on error by default."""
        config = {
            'description': 'Stop on error test',
            'steps': [
                {'name': 'Step 1', 'command': 'echo step1'},
                {'name': 'Step 2', 'command': 'exit 1'},
                {'name': 'Step 3', 'command': 'echo step3'}
            ]
        }
        workflow = Workflow('test', config)
        context = WorkflowContext()
        
        result = workflow.execute(context)
        
        assert result['status'] == 'error'
        assert len(result['results']) == 2  # Only first two steps executed
    
    def test_workflow_continue_on_error(self):
        """Test workflow continues on error when configured."""
        config = {
            'description': 'Continue on error test',
            'on_error': 'continue',
            'steps': [
                {'name': 'Step 1', 'command': 'echo step1'},
                {'name': 'Step 2', 'command': 'exit 1'},
                {'name': 'Step 3', 'command': 'echo step3'}
            ]
        }
        workflow = Workflow('test', config)
        context = WorkflowContext()
        
        result = workflow.execute(context)
        
        assert result['status'] == 'error'
        assert len(result['results']) == 3  # All steps executed
    
    def test_cleanup_on_error(self):
        """Test cleanup steps run on error."""
        config = {
            'description': 'Cleanup test',
            'on_error': 'stop',
            'steps': [
                {'name': 'Main Step', 'command': 'exit 1'}
            ],
            'cleanup': [
                {'name': 'Cleanup', 'command': 'echo cleanup'}
            ]
        }
        workflow = Workflow('test', config)
        context = WorkflowContext()
        
        with patch.object(WorkflowStep, 'execute') as mock_execute:
            # Main step fails, cleanup succeeds
            mock_execute.side_effect = [
                {'status': 'error', 'error': 'Failed'},
                {'status': 'success'}
            ]
            
            result = workflow.execute(context)
            
            assert result['status'] == 'error'
            assert mock_execute.call_count == 2  # Main + cleanup
    
    def test_invalid_step_type(self):
        """Test handling of invalid step type."""
        config = {
            'name': 'Invalid Step',
            'type': 'invalid_type',
            'command': 'echo test'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        with pytest.raises(ValueError, match="Unknown step type"):
            step.execute(context)
    
    def test_missing_workflow(self, workflow_manager):
        """Test running non-existent workflow."""
        with pytest.raises(ValueError, match="Workflow not found"):
            workflow_manager.run_workflow('non_existent')
    


class TestEdgeCases:
    """Test edge cases in workflow execution."""
    
    def test_empty_workflow(self):
        """Test workflow with no steps."""
        config = {
            'description': 'Empty workflow',
            'steps': []
        }
        workflow = Workflow('empty', config)
        context = WorkflowContext()
        
        result = workflow.execute(context)
        
        assert result['status'] == 'success'
        assert len(result['results']) == 0
    
    def test_empty_conditional_blocks(self):
        """Test conditional blocks with no steps."""
        config = {
            'name': 'Empty Conditional',
            'if': 'true',
            'then': [],
            'else': []
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert 'no steps to execute' in result['output']
    
    def test_malformed_condition(self):
        """Test handling of malformed conditions."""
        config = {
            'name': 'Bad Condition',
            'type': 'command',
            'command': 'echo test',
            'condition': '{{invalid}} === true'  # Invalid syntax
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Should handle gracefully
        result = step.execute(context)
        # Condition evaluation fails, step is skipped
        assert result['status'] in ['skipped', 'success']
    
    def test_missing_variables(self):
        """Test handling of missing variables."""
        config = {
            'name': 'Missing Var',
            'type': 'command',
            'command': 'echo {{missing_var}}'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        # Should handle missing variable gracefully
        assert result['status'] == 'success'
        assert '{{missing_var}}' in result['stdout']
    
    def test_recursive_variable_reference(self):
        """Test handling of recursive variable references."""
        config = {
            'name': 'Recursive Var',
            'type': 'python',
            'command': 'context.set_global_var("a", "{{b}}"); context.set_global_var("b", "{{a}}")'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Should not cause infinite loop
        result = step.execute(context)
        assert result['status'] == 'success'
    
    def test_large_output(self):
        """Test handling of large command output."""
        config = {
            'name': 'Large Output',
            'type': 'python',
            'command': 'print("x" * 10000)'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert len(result['stdout']) >= 10000
    
    def test_special_characters_in_command(self):
        """Test handling of special characters."""
        config = {
            'name': 'Special Chars',
            'type': 'command',
            'command': 'echo "Test with $pecial ch@rs & symbols"'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert 'Test with' in result['stdout']
    
    def test_unicode_in_workflow(self):
        """Test handling of Unicode characters."""
        config = {
            'name': 'Unicode Test',
            'type': 'python',
            'command': 'print("Unicode: αβγ 中文 🎉")'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert 'Unicode:' in result['stdout']
    
    def test_workflow_file_operations(self, workflow_manager):
        """Test file operations (export/import) with edge cases."""
        # Create workflow with special characters
        config = {
            'description': 'Test with special chars: @#$%',
            'steps': [
                {'name': 'Step with "quotes"', 'command': 'echo test'}
            ]
        }
        
        workflow_manager.create_workflow('special', config)
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            export_path = Path(tmp.name)
            
            # Export and import
            workflow_manager.export_workflow('special', export_path)
            workflow_manager.delete_workflow('special')
            workflow_manager.import_workflow(export_path, 'imported_special')
            
            # Verify
            imported = workflow_manager.get_workflow('imported_special')
            assert imported.description == config['description']
            
            # Cleanup
            export_path.unlink()
            workflow_file = workflow_manager.workflows_dir / 'imported_special.yaml'
            if workflow_file.exists():
                workflow_file.unlink()


class TestResourceManagement:
    """Test resource management and cleanup."""
    
    def test_timeout_cleanup(self):
        """Test cleanup after timeout."""
        config = {
            'name': 'Timeout Test',
            'type': 'command',
            'command': 'sleep 10',
            'timeout': 1
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Should timeout and clean up properly
        try:
            step.execute(context)
        except Exception:
            pass  # Expected timeout
    
    def test_multiple_workflow_runs(self, workflow_manager):
        """Test multiple runs of the same workflow."""
        config = {
            'description': 'Multi-run test',
            'steps': [
                {
                    'name': 'Counter',
                    'type': 'python',
                    'command': 'context.set_global_var("run_count", context.get_variable("run_count", 0) + 1)'
                }
            ]
        }
        
        workflow_manager.create_workflow('multi', config)
        
        # Run multiple times
        results = []
        for i in range(3):
            result = workflow_manager.run_workflow('multi')
            results.append(result)
        
        # Each run should be independent
        for i, result in enumerate(results):
            assert result['status'] == 'success'
            assert result['context']['global_vars']['run_count'] == 1
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'multi.yaml'
        if workflow_file.exists():
            workflow_file.unlink()
    
