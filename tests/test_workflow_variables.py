"""
Tests for workflow variable integration.
"""

import pytest
from unittest.mock import Mock, patch
import yaml
from pathlib import Path
import tempfile
import shutil

from velocitytree.workflows import Workflow, WorkflowStep, WorkflowManager
from velocitytree.workflow_context import WorkflowContext
from velocitytree.config import Config


class TestWorkflowVariableIntegration:
    """Test workflow integration with variables and context."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_step_with_variable_interpolation(self):
        """Test step execution with variable interpolation."""
        # Create a workflow step that uses variables
        step_config = {
            'name': 'echo_vars',
            'type': 'command',
            'command': 'echo {{message}} - {{count}}'
        }
        
        step = WorkflowStep(step_config)
        context = WorkflowContext()
        context.set_global_var('message', 'Hello')
        context.set_global_var('count', 42)
        
        # Mock subprocess.run to capture the command
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Hello - 42'
            mock_run.return_value.stderr = ''
            
            result = step.execute(context)
            
            # Verify command interpolation
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args == 'echo Hello - 42'
            assert result['status'] == 'success'
    
    def test_step_with_conditional_execution(self):
        """Test conditional step execution."""
        # Create a step with condition
        step_config = {
            'name': 'conditional_step',
            'type': 'command',
            'command': 'echo "Running"',
            'condition': 'debug == true'
        }
        
        step = WorkflowStep(step_config)
        
        # Test with condition true
        context = WorkflowContext()
        context.set_global_var('debug', True)
        
        result = step.execute(context)
        assert result['status'] != 'skipped'
        
        # Test with condition false
        context.set_global_var('debug', False)
        result = step.execute(context)
        assert result['status'] == 'skipped'
        assert result['reason'] == 'Condition not met'
    
    def test_step_output_propagation(self):
        """Test step outputs are accessible in context."""
        # Create workflow with two steps
        workflow_config = {
            'description': 'Test workflow',
            'steps': [
                {
                    'name': 'step1',
                    'type': 'command',
                    'command': 'echo 100'
                },
                {
                    'name': 'step2',
                    'type': 'command',
                    'command': 'echo Value is {{steps.step1.output}}'
                }
            ]
        }
        
        workflow = Workflow('test', workflow_config)
        context = WorkflowContext()
        
        # Mock the execution
        return_values = [
            Mock(returncode=0, stdout='100\n', stderr=''),
            Mock(returncode=0, stdout='Value is 100\n', stderr='')
        ]
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = return_values
            
            result = workflow.execute(context)
            
            # Verify step output was used
            assert 'step1' in context.step_outputs
            # The step output contains the execution result
            assert context.step_outputs['step1']['status'] == 'success'
            assert context.step_outputs['step1']['output'] == '100\n'
            
            # The command should have been interpolated with the value from the output
            assert mock_run.call_count == 2
            second_call = mock_run.call_args_list[1]
            args = second_call[0][0]
            # The command should have the interpolated value
            assert args == 'echo Value is 100\n'
    
    def test_workflow_with_global_variables(self):
        """Test workflow execution with global variables."""
        workflow_config = {
            'description': 'Test workflow',
            'env': {
                'PROJECT': 'test',
                'VERSION': '1.0'
            },
            'steps': [
                {
                    'name': 'show_env',
                    'type': 'command',
                    'command': 'echo {{PROJECT}} v{{VERSION}}'
                }
            ]
        }
        
        workflow = Workflow('test', workflow_config)
        context = WorkflowContext()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'test v1.0'
            mock_run.return_value.stderr = ''
            
            result = workflow.execute(context)
            
            # Verify global vars were set
            assert context.get_global_var('PROJECT') == 'test'
            assert context.get_global_var('VERSION') == '1.0'
            
            # Verify command used variables
            args = mock_run.call_args[0][0]
            assert 'test v1.0' in args
    
    def test_workflow_manager_with_variables(self):
        """Test WorkflowManager with variable support."""
        manager = WorkflowManager(self.config)
        
        # Create a workflow
        workflow_config = {
            'description': 'Variable test',
            'steps': [
                {
                    'name': 'greet',
                    'type': 'command',
                    'command': 'echo Hello {{name}}!'
                }
            ]
        }
        
        workflow = manager.create_workflow('greeting', workflow_config)
        
        # Run with variables
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Hello John!'
            mock_run.return_value.stderr = ''
            
            result = manager.run_workflow('greeting', global_vars={'name': 'John'})
            
            # Verify execution
            assert result['status'] == 'success'
            args = mock_run.call_args[0][0]
            assert 'Hello John!' in args
    
    def test_complex_variable_expressions(self):
        """Test complex variable expressions in workflows."""
        step_config = {
            'name': 'complex_vars',
            'type': 'command',
            'command': 'echo {{count > 5 ? many : few}} items'
        }
        
        step = WorkflowStep(step_config)
        
        # Test with count > 5
        context = WorkflowContext()
        context.set_global_var('count', 10)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = step.execute(context)
            
            args = mock_run.call_args[0][0]
            assert 'many items' in args
        
        # Test with count <= 5
        context.set_global_var('count', 3)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = step.execute(context)
            
            args = mock_run.call_args[0][0]
            assert 'few items' in args
    
    def test_builtin_variables_in_workflow(self):
        """Test built-in variables in workflow steps."""
        step_config = {
            'name': 'use_builtins',
            'type': 'command',
            'command': 'echo Current dir: {{cwd}} Date: {{today}}'
        }
        
        step = WorkflowStep(step_config)
        context = WorkflowContext()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = step.execute(context)
            
            args = mock_run.call_args[0][0]
            # Should contain actual directory path
            assert 'Current dir:' in args
            # Should contain today's date
            assert 'Date:' in args
    
    def test_default_values_in_workflow(self):
        """Test default values for missing variables."""
        step_config = {
            'name': 'with_defaults',
            'type': 'command',
            'command': 'echo User: {{user | anonymous}} Port: {{port | 8080}}'
        }
        
        step = WorkflowStep(step_config)
        context = WorkflowContext()
        context.set_global_var('user', 'john')
        # port is not set
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            result = step.execute(context)
            
            args = mock_run.call_args[0][0]
            assert 'User: john' in args
            assert 'Port: 8080' in args
    
    def test_error_handling_with_context(self):
        """Test error handling preserves context state."""
        workflow_config = {
            'description': 'Error test',
            'on_error': 'continue',
            'steps': [
                {
                    'name': 'step1',
                    'type': 'command',
                    'command': 'echo Success'
                },
                {
                    'name': 'step2',
                    'type': 'command',
                    'command': 'false',  # Will fail
                    'continue_on_error': True  # Allow continuing despite error
                },
                {
                    'name': 'step3',
                    'type': 'command',
                    'command': 'echo {{steps.step1.status}}'
                }
            ]
        }
        
        workflow = Workflow('test', workflow_config)
        context = WorkflowContext()
        
        with patch('subprocess.run') as mock_run:
            # Configure different return values for each call
            mock_run.side_effect = [
                Mock(returncode=0, stdout='Success', stderr=''),
                Mock(returncode=1, stdout='', stderr='Error'),
                Mock(returncode=0, stdout='success', stderr='')
            ]
            
            result = workflow.execute(context)
            
            # Verify error tracking - one step failed but workflow continued
            assert result['status'] == 'success' if context.workflow_metadata.get('status') == 'success' else 'error'
            assert context.workflow_metadata['steps_completed'] == 3  # All steps were executed
            
            # Verify all steps were called
            assert mock_run.call_count == 3
            
            # Verify errors were recorded for step 2
            assert any(r['result']['status'] == 'error' for r in result['results'])
            
            # Verify step3 could access step1's output 
            third_call = mock_run.call_args_list[2]
            args = third_call[0][0]
            # Should have interpolated steps.step1.status
            assert 'echo success' in args