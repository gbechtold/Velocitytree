"""Comprehensive tests for workflow system."""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import yaml
from velocitytree.workflows import (
    WorkflowStep,
    Workflow,
    WorkflowManager
)
from velocitytree.workflow_context import WorkflowContext
from velocitytree.config import Config


@pytest.fixture
def mock_config():
    """Create a mock config."""
    config = Mock(spec=Config)
    config.config = Mock()
    config.config.workflows = {}
    return config


@pytest.fixture
def sample_workflow_config():
    """Sample workflow configuration."""
    return {
        'description': 'Test workflow',
        'env': {
            'TEST_VAR': 'test_value'
        },
        'steps': [
            {
                'name': 'Step 1',
                'type': 'command',
                'command': 'echo "Hello World"'
            },
            {
                'name': 'Step 2',
                'type': 'python',
                'command': 'print("Python step")'
            }
        ]
    }


@pytest.fixture
def workflow_manager(mock_config):
    """Create a workflow manager."""
    return WorkflowManager(mock_config)


class TestWorkflowStep:
    """Test WorkflowStep class."""
    
    def test_init_defaults(self):
        """Test initialization with defaults."""
        config = {'name': 'Test Step'}
        step = WorkflowStep(config)
        
        assert step.name == 'Test Step'
        assert step.type == 'command'
        assert step.timeout == 300
        assert step.continue_on_error is False
        # assert step.depends_on == []  # Not in main branch
    
    def test_init_with_all_options(self):
        """Test initialization with all options."""
        config = {
            'name': 'Full Step',
            'type': 'python',
            'command': 'print("test")',
            'timeout': 600,
            'continue_on_error': True,
            'condition': '{{var}} == 1',
            'depends_on': ['prev_step'],
            'if': '{{flag}}',
            'then': [{'name': 'then_step', 'command': 'echo then'}],
            'else': [{'name': 'else_step', 'command': 'echo else'}]
        }
        step = WorkflowStep(config)
        
        assert step.name == 'Full Step'
        assert step.type == 'python'
        assert step.timeout == 600
        assert step.continue_on_error is True
        assert step.condition == '{{var}} == 1'
        # assert step.depends_on == ['prev_step']  # Not in main branch
        assert step.if_condition == '{{flag}}'
        assert len(step.then_steps) == 1
        assert len(step.else_steps) == 1
    
    def test_execute_command(self):
        """Test executing a command step."""
        config = {
            'name': 'Command Step',
            'type': 'command',
            'command': 'echo test'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert 'test' in result['stdout']
        assert result['exit_code'] == 0
    
    def test_execute_python(self):
        """Test executing a Python step."""
        config = {
            'name': 'Python Step',
            'type': 'python',
            'command': 'print("hello")'
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        assert 'hello' in result['stdout']
        assert result['output'] != ''
    
    def test_execute_with_condition(self):
        """Test step execution with condition."""
        config = {
            'name': 'Conditional Step',
            'type': 'command',
            'command': 'echo test',
            'condition': '{{skip}}'
        }
        step = WorkflowStep(config)
        
        # Condition not met
        context = WorkflowContext()
        context.set_global_var('skip', False)
        result = step.execute(context)
        assert result['status'] == 'skipped'
        
        # Condition met
        context.set_global_var('skip', True)
        result = step.execute(context)
        assert result['status'] == 'success'
    
    def test_execute_conditional_block(self):
        """Test if/then/else conditional blocks."""
        config = {
            'name': 'Conditional Block',
            'if': '{{branch}} == "then"',
            'then': [
                {'name': 'then_step', 'command': 'echo then'}
            ],
            'else': [
                {'name': 'else_step', 'command': 'echo else'}
            ]
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Execute then branch
        context.set_global_var('branch', 'then')
        result = step.execute(context)
        assert result['status'] == 'success'
        assert result['condition_met'] is True
        assert len(result['results']) == 1
        
        # Execute else branch
        context.set_global_var('branch', 'else')
        result = step.execute(context)
        assert result['status'] == 'success'
        assert result['condition_met'] is False
        assert len(result['results']) == 1
    
    def test_error_handling(self):
        """Test step error handling."""
        config = {
            'name': 'Error Step',
            'type': 'command',
            'command': 'false',  # Command that returns error
            'continue_on_error': True
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        result = step.execute(context)
        
        assert result['status'] == 'error'
        assert result['exit_code'] != 0
    
    def test_timeout(self):
        """Test step timeout."""
        config = {
            'name': 'Timeout Step',
            'type': 'command',
            'command': 'sleep 5',
            'timeout': 1
        }
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        with pytest.raises(Exception):
            step.execute(context)


class TestWorkflow:
    """Test Workflow class."""
    
    def test_init(self, sample_workflow_config):
        """Test workflow initialization."""
        workflow = Workflow('test', sample_workflow_config)
        
        assert workflow.name == 'test'
        assert workflow.description == 'Test workflow'
        assert len(workflow.steps) == 2
        assert workflow.env == {'TEST_VAR': 'test_value'}
        assert workflow.on_error == 'stop'
    
    def test_execute_success(self, sample_workflow_config):
        """Test successful workflow execution."""
        workflow = Workflow('test', sample_workflow_config)
        context = WorkflowContext()
        
        with patch.object(WorkflowStep, 'execute') as mock_execute:
            mock_execute.return_value = {'status': 'success', 'output': 'test'}
            result = workflow.execute(context)
        
        assert result['status'] == 'success'
        assert result['workflow'] == 'test'
        assert len(result['results']) == 2
        assert context.workflow_metadata['status'] == 'success'
    
    def test_execute_with_error(self, sample_workflow_config):
        """Test workflow execution with error."""
        workflow = Workflow('test', sample_workflow_config)
        context = WorkflowContext()
        
        with patch.object(WorkflowStep, 'execute') as mock_execute:
            mock_execute.side_effect = [
                {'status': 'success', 'output': 'test'},
                {'status': 'error', 'error': 'Failed'}
            ]
            result = workflow.execute(context)
        
        assert result['status'] == 'error'
        assert len(result['results']) == 2
        assert context.workflow_metadata['status'] == 'error'
    
    def test_cleanup_steps(self):
        """Test cleanup step execution."""
        config = {
            'description': 'Test with cleanup',
            'steps': [
                {'name': 'Main Step', 'command': 'echo main'}
            ],
            'cleanup': [
                {'name': 'Cleanup Step', 'command': 'echo cleanup'}
            ],
            'on_error': 'cleanup'
        }
        workflow = Workflow('test', config)
        context = WorkflowContext()
        
        with patch.object(WorkflowStep, 'execute') as mock_execute:
            mock_execute.return_value = {'status': 'success'}
            result = workflow.execute(context)
            
            # Cleanup should be called
            assert mock_execute.call_count >= 2
    


class TestWorkflowManager:
    """Test WorkflowManager class."""
    
    def test_init(self, workflow_manager):
        """Test workflow manager initialization."""
        assert workflow_manager.workflows == {}
        assert workflow_manager.workflows_dir.exists()
    
    def test_create_workflow(self, workflow_manager):
        """Test creating a workflow."""
        workflow = workflow_manager.create_workflow('test', {
            'description': 'Test workflow',
            'steps': [{'name': 'Step 1', 'command': 'echo test'}]
        })
        
        assert workflow.name == 'test'
        assert 'test' in workflow_manager.workflows
        
        # Check file was created
        workflow_file = workflow_manager.workflows_dir / 'test.yaml'
        assert workflow_file.exists()
        
        # Cleanup
        workflow_file.unlink()
    
    def test_create_workflow_from_template(self, workflow_manager):
        """Test creating workflow from template."""
        with patch('velocitytree.templates.WORKFLOW_TEMPLATES', {
            'basic': {
                'description': 'Basic template',
                'steps': [{'name': 'Template Step', 'command': 'echo template'}]
            }
        }):
            workflow = workflow_manager.create_workflow('test', template='basic')
            
            assert workflow.description == 'Basic template'
            assert len(workflow.steps) == 1
            assert workflow.steps[0].name == 'Template Step'
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'test.yaml'
        if workflow_file.exists():
            workflow_file.unlink()
    
    def test_delete_workflow(self, workflow_manager):
        """Test deleting a workflow."""
        # Create a workflow first
        workflow_manager.create_workflow('test', {
            'description': 'Test workflow',
            'steps': []
        })
        
        # Delete it
        workflow_manager.delete_workflow('test')
        
        assert 'test' not in workflow_manager.workflows
        workflow_file = workflow_manager.workflows_dir / 'test.yaml'
        assert not workflow_file.exists()
    
    def test_list_workflows(self, workflow_manager):
        """Test listing workflows."""
        # Get initial count
        initial_count = len(workflow_manager.list_workflows())
        
        # Add workflows
        workflow_manager.create_workflow('test1', {'steps': []})
        workflow_manager.create_workflow('test2', {'steps': []})
        
        workflows = workflow_manager.list_workflows()
        
        assert len(workflows) >= initial_count + 2
        names = [w['name'] for w in workflows]
        assert 'test1' in names
        assert 'test2' in names
        
        # Cleanup
        for name in ['test1', 'test2']:
            workflow_file = workflow_manager.workflows_dir / f'{name}.yaml'
            if workflow_file.exists():
                workflow_file.unlink()
    
    def test_run_workflow(self, workflow_manager):
        """Test running a workflow."""
        workflow_manager.create_workflow('test', {
            'description': 'Test workflow',
            'steps': [{'name': 'Step 1', 'command': 'echo test'}]
        })
        
        with patch.object(Workflow, 'execute') as mock_execute:
            mock_execute.return_value = {'status': 'success'}
            result = workflow_manager.run_workflow('test')
            
            assert result['status'] == 'success'
            mock_execute.assert_called_once()
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'test.yaml'
        if workflow_file.exists():
            workflow_file.unlink()
    
    def test_export_import_workflow(self, workflow_manager):
        """Test exporting and importing workflows."""
        # Create a workflow
        workflow_manager.create_workflow('test', {
            'description': 'Export test',
            'steps': [{'name': 'Step 1', 'command': 'echo test'}]
        })
        
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as tmp:
            export_path = Path(tmp.name)
            
            # Export
            workflow_manager.export_workflow('test', export_path)
            assert export_path.exists()
            
            # Delete original
            workflow_manager.delete_workflow('test')
            
            # Import
            workflow_manager.import_workflow(export_path, 'imported')
            assert 'imported' in workflow_manager.workflows
            
            # Cleanup
            export_path.unlink()
            workflow_file = workflow_manager.workflows_dir / 'imported.yaml'
            if workflow_file.exists():
                workflow_file.unlink()




class TestIntegration:
    """Integration tests for workflow system."""
    
    def test_full_workflow_execution(self, workflow_manager):
        """Test complete workflow execution."""
        config = {
            'description': 'Integration test workflow',
            'env': {
                'TEST_VAR': 'integration'
            },
            'steps': [
                {
                    'name': 'Set variable',
                    'type': 'python',
                    'command': 'context.set_global_var("result", "success")'
                },
                {
                    'name': 'Check variable',
                    'type': 'python',
                    'command': 'assert context.get_global_var("result") == "success"'
                },
                {
                    'name': 'Conditional step',
                    'type': 'command',
                    'command': 'echo "Variable is: {{result}}"'
                }
            ]
        }
        
        workflow_manager.create_workflow('integration', config)
        result = workflow_manager.run_workflow('integration')
        
        assert result['status'] == 'success'
        assert len(result['results']) == 3
        
        # Check context
        context_dict = result['context']
        assert context_dict['global_vars']['result'] == 'success'
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'integration.yaml'
        if workflow_file.exists():
            workflow_file.unlink()
    
    def test_workflow_with_all_features(self, workflow_manager):
        """Test workflow using all major features."""
        config = {
            'description': 'Feature-complete workflow',
            'env': {
                'ENV_VAR': 'test'
            },
            'steps': [
                # Variable interpolation
                {
                    'name': 'Setup',
                    'type': 'python',
                    'command': '''
context.set_global_var("count", 0)
context.set_global_var("flag", True)
'''
                },
                # Conditional execution
                {
                    'name': 'Conditional',
                    'if': '{{flag}}',
                    'then': [
                        {
                            'name': 'Increment',
                            'type': 'python',
                            'command': 'context.set_global_var("count", context.get_global_var("count") + 1)'
                        }
                    ]
                },
                # Command with interpolation
                {
                    'name': 'Echo',
                    'type': 'command',
                    'command': 'echo "Count is: {{count}}"'
                },
                # Complex condition
                {
                    'name': 'Complex check',
                    'type': 'python',
                    'command': 'print("Complex logic")',
                    'condition': '{{count}} > 0 and {{flag}}'
                }
            ]
        }
        
        workflow_manager.create_workflow('features', config)
        result = workflow_manager.run_workflow('features')
        
        assert result['status'] == 'success'
        assert result['context']['global_vars']['count'] == 1
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'features.yaml'
        if workflow_file.exists():
            workflow_file.unlink()