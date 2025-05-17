"""Tests for parallel workflow execution."""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from velocitytree.workflow_parallel import (
    ParallelExecutionMode,
    ParallelGroup,
    ParallelWorkflowExecutor,
    create_parallel_group
)
from velocitytree.workflows import WorkflowStep, WorkflowContext, WorkflowExecutor


@pytest.fixture
def mock_context():
    """Create a mock workflow context."""
    context = WorkflowContext()
    context.set_step_output('test_var', 'test_value')
    return context


@pytest.fixture
def mock_steps():
    """Create mock workflow steps."""
    steps = []
    for i in range(3):
        step = Mock(spec=WorkflowStep)
        step.name = f'step_{i}'
        step.execute.return_value = {
            'status': 'success',
            'output': f'output_{i}'
        }
        steps.append(step)
    return steps


@pytest.fixture
def mock_executor(mock_steps):
    """Create a mock workflow executor."""
    executor = Mock(spec=WorkflowExecutor)
    executor.workflow_name = 'test_workflow'
    executor.steps = mock_steps
    executor.execute_step.side_effect = lambda step, context: step.execute(context)
    return executor


@pytest.fixture
def parallel_executor(mock_executor):
    """Create a parallel workflow executor."""
    return ParallelWorkflowExecutor(mock_executor)


class TestParallelGroup:
    """Test ParallelGroup class."""
    
    def test_init(self, mock_steps):
        """Test parallel group initialization."""
        group = ParallelGroup(
            name='test_group',
            steps=mock_steps,
            execution_mode=ParallelExecutionMode.CONCURRENT
        )
        
        assert group.name == 'test_group'
        assert group.steps == mock_steps
        assert group.execution_mode == ParallelExecutionMode.CONCURRENT
        assert group.max_workers is None
    
    def test_init_empty_steps(self):
        """Test parallel group with empty steps."""
        with pytest.raises(ValueError, match="must have at least one step"):
            ParallelGroup(
                name='test_group',
                steps=[],
                execution_mode=ParallelExecutionMode.CONCURRENT
            )
    
    def test_fork_join_without_condition(self, mock_steps):
        """Test fork-join mode without join condition."""
        with pytest.raises(ValueError, match="requires a join_condition"):
            ParallelGroup(
                name='test_group',
                steps=mock_steps,
                execution_mode=ParallelExecutionMode.FORK_JOIN
            )


class TestParallelWorkflowExecutor:
    """Test ParallelWorkflowExecutor class."""
    
    @pytest.mark.asyncio
    async def test_execute_concurrent(self, parallel_executor, mock_steps, mock_context):
        """Test concurrent execution mode."""
        group = ParallelGroup(
            name='test_group',
            steps=mock_steps,
            execution_mode=ParallelExecutionMode.CONCURRENT
        )
        
        results = await parallel_executor.execute_parallel_group(group, mock_context)
        
        # All steps should be executed
        for step in mock_steps:
            step.execute.assert_called_once()
        
        # Check results
        assert len(results) == 3
        for i, step in enumerate(mock_steps):
            assert results[step.name] == {
                'status': 'success',
                'output': f'output_{i}'
            }
    
    @pytest.mark.asyncio
    async def test_execute_batch(self, parallel_executor, mock_steps, mock_context):
        """Test batch execution mode."""
        group = ParallelGroup(
            name='test_group',
            steps=mock_steps,
            max_workers=2,
            execution_mode=ParallelExecutionMode.BATCH
        )
        
        results = await parallel_executor.execute_parallel_group(group, mock_context)
        
        # All steps should be executed
        for step in mock_steps:
            step.execute.assert_called_once()
        
        # Check results
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_execute_fork_join(self, parallel_executor, mock_steps, mock_context):
        """Test fork-join execution mode."""
        group = ParallelGroup(
            name='test_group',
            steps=mock_steps,
            execution_mode=ParallelExecutionMode.FORK_JOIN,
            join_condition='true'
        )
        
        with patch('velocitytree.workflow_parallel.evaluate_condition', return_value=True):
            results = await parallel_executor.execute_parallel_group(group, mock_context)
        
        # All steps should be executed
        for step in mock_steps:
            step.execute.assert_called_once()
        
        # Check results
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_execute_fork_join_failed_condition(self, parallel_executor, mock_steps, mock_context):
        """Test fork-join with failed condition."""
        group = ParallelGroup(
            name='test_group',
            steps=mock_steps,
            execution_mode=ParallelExecutionMode.FORK_JOIN,
            join_condition='false'
        )
        
        with patch('velocitytree.workflow_parallel.evaluate_condition', return_value=False):
            with pytest.raises(RuntimeError, match="Fork-join condition failed"):
                await parallel_executor.execute_parallel_group(group, mock_context)
    
    @pytest.mark.asyncio
    async def test_execute_pipeline(self, parallel_executor, mock_context):
        """Test pipeline execution mode."""
        # Create steps with dependencies
        step1 = Mock(spec=WorkflowStep)
        step1.name = 'step_1'
        step1.depends_on = []
        step1.execute.return_value = {'status': 'success', 'output': 'output_1'}
        
        step2 = Mock(spec=WorkflowStep)
        step2.name = 'step_2'
        step2.depends_on = ['step_1']
        step2.execute.return_value = {'status': 'success', 'output': 'output_2'}
        
        step3 = Mock(spec=WorkflowStep)
        step3.name = 'step_3'
        step3.depends_on = ['step_1', 'step_2']
        step3.execute.return_value = {'status': 'success', 'output': 'output_3'}
        
        group = ParallelGroup(
            name='test_group',
            steps=[step3, step1, step2],  # Out of order to test dependency resolution
            execution_mode=ParallelExecutionMode.PIPELINE
        )
        
        results = await parallel_executor.execute_parallel_group(group, mock_context)
        
        # Check execution order
        step1.execute.assert_called_once()
        step2.execute.assert_called_once()
        step3.execute.assert_called_once()
        
        # Check results
        assert len(results) == 3
        assert results['step_1']['output'] == 'output_1'
        assert results['step_2']['output'] == 'output_2' 
        assert results['step_3']['output'] == 'output_3'
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_circular_dependency(self, parallel_executor, mock_context):
        """Test pipeline with circular dependency."""
        # Create steps with circular dependencies
        step1 = Mock(spec=WorkflowStep)
        step1.name = 'step_1'
        step1.depends_on = ['step_2']
        
        step2 = Mock(spec=WorkflowStep)
        step2.name = 'step_2'
        step2.depends_on = ['step_1']
        
        group = ParallelGroup(
            name='test_group',
            steps=[step1, step2],
            execution_mode=ParallelExecutionMode.PIPELINE
        )
        
        with pytest.raises(RuntimeError, match="Circular dependency detected"):
            await parallel_executor.execute_parallel_group(group, mock_context)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, parallel_executor, mock_context):
        """Test error handling in parallel execution."""
        # Create steps with one that fails
        step1 = Mock(spec=WorkflowStep)
        step1.name = 'step_1'
        step1.execute.return_value = {'status': 'success', 'output': 'output_1'}
        
        step2 = Mock(spec=WorkflowStep)
        step2.name = 'step_2'
        step2.execute.side_effect = Exception("Step failed")
        
        group = ParallelGroup(
            name='test_group',
            steps=[step1, step2],
            execution_mode=ParallelExecutionMode.CONCURRENT
        )
        
        with pytest.raises(RuntimeError, match="Parallel execution failed"):
            await parallel_executor.execute_parallel_group(group, mock_context)


class TestCreateParallelGroup:
    """Test create_parallel_group function."""
    
    def test_create_basic_group(self):
        """Test creating a basic parallel group."""
        config = {
            'name': 'test_group',
            'mode': 'concurrent',
            'steps': [
                {
                    'name': 'step_1',
                    'type': 'command',
                    'command': 'echo test'
                }
            ]
        }
        
        group = create_parallel_group(config)
        
        assert group.name == 'test_group'
        assert group.execution_mode == ParallelExecutionMode.CONCURRENT
        assert len(group.steps) == 1
        assert group.steps[0].name == 'step_1'
    
    def test_create_group_with_options(self):
        """Test creating a parallel group with all options."""
        config = {
            'name': 'test_group',
            'mode': 'fork_join',
            'max_workers': 5,
            'join_condition': 'all_success',
            'steps': [
                {
                    'name': 'step_1',
                    'type': 'command',
                    'command': 'echo test'
                },
                {
                    'name': 'step_2',
                    'type': 'command',
                    'command': 'echo test2'
                }
            ]
        }
        
        group = create_parallel_group(config)
        
        assert group.name == 'test_group'
        assert group.execution_mode == ParallelExecutionMode.FORK_JOIN
        assert group.max_workers == 5
        assert group.join_condition == 'all_success'
        assert len(group.steps) == 2


class TestIntegration:
    """Integration tests for parallel workflow execution."""
    
    @pytest.mark.asyncio
    async def test_real_concurrent_execution(self, mock_context):
        """Test real concurrent execution with timing."""
        # Create steps that take time
        steps = []
        for i in range(3):
            step = Mock(spec=WorkflowStep)
            step.name = f'step_{i}'
            async def execute_with_delay(ctx, delay=i):
                await asyncio.sleep(0.1)  # Simulate work
                return {'status': 'success', 'output': f'output_{delay}'}
            step.execute = lambda ctx, i=i: {'status': 'success', 'output': f'output_{i}'}
            steps.append(step)
        
        group = ParallelGroup(
            name='timing_test',
            steps=steps,
            execution_mode=ParallelExecutionMode.CONCURRENT
        )
        
        executor = WorkflowExecutor('test', steps)
        parallel_executor = ParallelWorkflowExecutor(executor)
        
        start_time = time.time()
        results = await parallel_executor.execute_parallel_group(group, mock_context)
        end_time = time.time()
        
        # All steps should complete
        assert len(results) == 3
        
        # Should take less than the sum of individual delays
        # (would take 0.3s serially, should take ~0.1s in parallel)
        assert end_time - start_time < 0.2