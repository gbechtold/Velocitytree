"""Performance tests for workflow system."""

import pytest
import time
import asyncio
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


class TestPerformance:
    """Test performance characteristics of workflow system."""
    
    def test_large_workflow_execution(self, workflow_manager):
        """Test execution of workflow with many steps."""
        # Create workflow with 100 steps
        steps = []
        for i in range(100):
            steps.append({
                'name': f'Step {i}',
                'type': 'python',
                'command': f'context.set_global_var("step_{i}", {i})'
            })
        
        config = {
            'description': 'Large workflow',
            'steps': steps
        }
        
        workflow_manager.create_workflow('large', config)
        
        start_time = time.time()
        result = workflow_manager.run_workflow('large')
        end_time = time.time()
        
        assert result['status'] == 'success'
        assert len(result['results']) == 100
        
        # Should complete in reasonable time (< 10 seconds)
        assert end_time - start_time < 10
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'large.yaml'
        if workflow_file.exists():
            workflow_file.unlink()
    
    def test_context_variable_performance(self):
        """Test performance with many context variables."""
        context = WorkflowContext()
        
        # Add many variables
        start_time = time.time()
        for i in range(1000):
            context.set_global_var(f'var_{i}', i)
        
        # Access variables
        for i in range(1000):
            value = context.get_global_var(f'var_{i}')
            assert value == i
        
        end_time = time.time()
        
        # Should be fast (< 1 second)
        assert end_time - start_time < 1
    
    def test_variable_interpolation_performance(self):
        """Test performance of variable interpolation."""
        context = WorkflowContext()
        
        # Add variables
        for i in range(100):
            context.set_global_var(f'var_{i}', f'value_{i}')
        
        # Create template with many variables
        template = ' '.join([f'{{{{var_{i}}}}}' for i in range(100)])
        
        start_time = time.time()
        # Interpolate many times
        for _ in range(100):
            result = context.interpolate_string(template)
        end_time = time.time()
        
        # Should be reasonably fast
        assert end_time - start_time < 2
    
    def test_condition_evaluation_performance(self):
        """Test performance of condition evaluation."""
        from velocitytree.workflow_conditions import evaluate_condition
        
        context = WorkflowContext()
        context.set_global_var('a', 1)
        context.set_global_var('b', 2)
        context.set_global_var('c', 3)
        
        # Complex condition
        condition = '{{a}} < {{b}} and {{b}} < {{c}} and ({{a}} + {{b}}) == {{c}}'
        
        start_time = time.time()
        # Evaluate many times
        for _ in range(1000):
            result = evaluate_condition(condition, context)
            assert result is True
        end_time = time.time()
        
        # Should be fast
        assert end_time - start_time < 1
    
    def test_workflow_loading_performance(self, workflow_manager):
        """Test performance of loading many workflows."""
        # Create many workflows
        for i in range(50):
            config = {
                'description': f'Workflow {i}',
                'steps': [
                    {'name': 'Step 1', 'command': 'echo test'}
                ]
            }
            workflow_manager.create_workflow(f'workflow_{i}', config)
        
        # Measure loading time
        start_time = time.time()
        workflows = workflow_manager.list_workflows()
        end_time = time.time()
        
        assert len(workflows) >= 50
        # Should be fast even with many workflows
        assert end_time - start_time < 1
        
        # Cleanup
        for i in range(50):
            workflow_file = workflow_manager.workflows_dir / f'workflow_{i}.yaml'
            if workflow_file.exists():
                workflow_file.unlink()


class TestMemoryUsage:
    """Test memory usage patterns."""
    
    def test_context_memory_cleanup(self):
        """Test that context doesn't leak memory."""
        import gc
        import sys
        
        initial_objects = len(gc.get_objects())
        
        # Create and destroy many contexts
        for _ in range(100):
            context = WorkflowContext()
            for i in range(100):
                context.set_global_var(f'var_{i}', f'value_{i}')
            # Context should be garbage collected
            del context
        
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Object count shouldn't grow significantly
        growth = final_objects - initial_objects
        assert growth < 1000  # Allow some growth but not excessive
    
    def test_workflow_execution_memory(self, workflow_manager):
        """Test memory usage during workflow execution."""
        config = {
            'description': 'Memory test',
            'steps': [
                {
                    'name': 'Memory Step',
                    'type': 'python',
                    'command': '''
# Create large data structure
data = [i for i in range(10000)]
context.set_global_var("data", data)
'''
                }
            ]
        }
        
        workflow_manager.create_workflow('memory', config)
        
        # Run workflow multiple times
        for _ in range(10):
            result = workflow_manager.run_workflow('memory')
            assert result['status'] == 'success'
        
        # Memory should be cleaned up between runs
        # (This is a simple test - real memory profiling would be more complex)
        
        # Cleanup
        workflow_file = workflow_manager.workflows_dir / 'memory.yaml'
        if workflow_file.exists():
            workflow_file.unlink()


class TestScalability:
    """Test scalability of workflow system."""
    
    def test_sequential_workflow_performance(self):
        """Test performance of sequential workflow execution."""
        from velocitytree.workflows import Workflow
        
        # Create workflow with many sequential steps
        steps = []
        for i in range(50):
            steps.append({
                'name': f'step_{i}',
                'type': 'command',
                'command': 'echo test'
            })
        
        config = {
            'description': 'Sequential workflow',
            'steps': steps
        }
        
        workflow = Workflow('sequential', config)
        context = WorkflowContext()
        
        start_time = time.time()
        result = workflow.execute(context)
        end_time = time.time()
        
        assert result['status'] == 'success'
        # Should complete in reasonable time
        assert end_time - start_time < 15
    
    def test_deep_condition_nesting(self):
        """Test deeply nested conditions."""
        config = {
            'name': 'Deep Nesting',
            'if': '{{level1}}',
            'then': [
                {
                    'name': 'Level 2',
                    'if': '{{level2}}',
                    'then': [
                        {
                            'name': 'Level 3',
                            'if': '{{level3}}',
                            'then': [
                                {'name': 'Deep Step', 'command': 'echo nested'}
                            ]
                        }
                    ]
                }
            ]
        }
        
        step = WorkflowStep(config)
        context = WorkflowContext()
        
        # Set all conditions to true
        context.set_global_var('level1', True)
        context.set_global_var('level2', True)
        context.set_global_var('level3', True)
        
        result = step.execute(context)
        
        assert result['status'] == 'success'
        # Should handle deep nesting without stack overflow