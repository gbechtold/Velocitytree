"""Parallel workflow execution support for Velocitytree."""

import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import yaml
import logging

from .workflows import WorkflowContext, WorkflowExecutor, WorkflowStep
from .workflow_conditions import evaluate_condition


logger = logging.getLogger(__name__)


class ParallelExecutionMode(Enum):
    """Different modes of parallel execution."""
    CONCURRENT = "concurrent"  # Run all steps concurrently
    BATCH = "batch"           # Run in batches with size limit
    FORK_JOIN = "fork_join"   # Fork into parallel branches, then join
    PIPELINE = "pipeline"     # Pipeline processing with dependencies


@dataclass
class ParallelGroup:
    """A group of steps to execute in parallel."""
    name: str
    steps: List[WorkflowStep]
    max_workers: Optional[int] = None
    execution_mode: ParallelExecutionMode = ParallelExecutionMode.CONCURRENT
    join_condition: Optional[str] = None  # Condition for fork-join mode
    
    def __post_init__(self):
        """Validate the parallel group configuration."""
        if not self.steps:
            raise ValueError(f"Parallel group '{self.name}' must have at least one step")
        
        if self.execution_mode == ParallelExecutionMode.FORK_JOIN and not self.join_condition:
            raise ValueError(f"Fork-join mode requires a join_condition")


class ParallelWorkflowExecutor:
    """Executes workflow steps in parallel."""
    
    def __init__(self, executor: WorkflowExecutor):
        """Initialize the parallel executor."""
        self.executor = executor
        self._loop = None
        self._thread_pool = None
    
    async def execute_parallel_group(
        self, 
        group: ParallelGroup, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a group of steps in parallel."""
        if group.execution_mode == ParallelExecutionMode.CONCURRENT:
            return await self._execute_concurrent(group, context)
        elif group.execution_mode == ParallelExecutionMode.BATCH:
            return await self._execute_batch(group, context)
        elif group.execution_mode == ParallelExecutionMode.FORK_JOIN:
            return await self._execute_fork_join(group, context)
        elif group.execution_mode == ParallelExecutionMode.PIPELINE:
            return await self._execute_pipeline(group, context)
        else:
            raise ValueError(f"Unknown execution mode: {group.execution_mode}")
    
    async def _execute_concurrent(
        self, 
        group: ParallelGroup, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute all steps concurrently."""
        logger.info(f"Executing parallel group '{group.name}' concurrently")
        
        # Create tasks for all steps
        tasks = []
        for step in group.steps:
            task = asyncio.create_task(
                self._execute_step_async(step, context.copy())
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        combined_results = {}
        errors = []
        
        for i, result in enumerate(results):
            step = group.steps[i]
            if isinstance(result, Exception):
                errors.append((step.name, result))
                logger.error(f"Step '{step.name}' failed: {result}")
            else:
                combined_results[step.name] = result
                # Update context with results
                context.set_step_output(f"{step.name}_result", result)
        
        if errors:
            error_msg = "; ".join([f"{name}: {error}" for name, error in errors])
            raise RuntimeError(f"Parallel execution failed: {error_msg}")
        
        return combined_results
    
    async def _execute_batch(
        self, 
        group: ParallelGroup, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute steps in batches with limited concurrency."""
        logger.info(f"Executing parallel group '{group.name}' in batches")
        
        max_workers = group.max_workers or 3
        combined_results = {}
        
        # Process steps in batches
        for i in range(0, len(group.steps), max_workers):
            batch = group.steps[i:i + max_workers]
            
            # Execute batch concurrently
            tasks = []
            for step in batch:
                task = asyncio.create_task(
                    self._execute_step_async(step, context.copy())
                )
                tasks.append(task)
            
            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(results):
                step = batch[j]
                if isinstance(result, Exception):
                    raise RuntimeError(f"Step '{step.name}' failed: {result}")
                combined_results[step.name] = result
                context.set_step_output(f"{step.name}_result", result)
        
        return combined_results
    
    async def _execute_fork_join(
        self, 
        group: ParallelGroup, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute fork-join pattern: fork into parallel branches, then join."""
        logger.info(f"Executing parallel group '{group.name}' in fork-join mode")
        
        # Fork: Execute all steps in parallel
        results = await self._execute_concurrent(group, context)
        
        # Join: Evaluate join condition
        if evaluate_condition(group.join_condition, context):
            return results
        else:
            raise RuntimeError(f"Fork-join condition failed: {group.join_condition}")
    
    async def _execute_pipeline(
        self, 
        group: ParallelGroup, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute pipeline pattern with dependencies."""
        logger.info(f"Executing parallel group '{group.name}' in pipeline mode")
        
        # Build dependency graph
        dep_graph = self._build_dependency_graph(group.steps)
        
        # Execute steps respecting dependencies
        results = {}
        completed = set()
        
        while len(completed) < len(group.steps):
            # Find steps ready to execute
            ready_steps = []
            for step in group.steps:
                if step.name not in completed:
                    deps = dep_graph.get(step.name, set())
                    if deps.issubset(completed):
                        ready_steps.append(step)
            
            if not ready_steps:
                raise RuntimeError("Circular dependency detected in pipeline")
            
            # Execute ready steps in parallel
            tasks = []
            for step in ready_steps:
                task = asyncio.create_task(
                    self._execute_step_async(step, context.copy())
                )
                tasks.append((step, task))
            
            # Wait for completion
            for step, task in tasks:
                result = await task
                results[step.name] = result
                context.set_step_output(f"{step.name}_result", result)
                completed.add(step.name)
        
        return results
    
    def _build_dependency_graph(self, steps: List[WorkflowStep]) -> Dict[str, Set[str]]:
        """Build a dependency graph from step definitions."""
        dep_graph = {}
        
        for step in steps:
            deps = set()
            # Look for dependencies in step configuration
            if hasattr(step, 'depends_on'):
                if isinstance(step.depends_on, str):
                    deps.add(step.depends_on)
                elif isinstance(step.depends_on, list):
                    deps.update(step.depends_on)
            dep_graph[step.name] = deps
        
        return dep_graph
    
    async def _execute_step_async(
        self, 
        step: WorkflowStep, 
        context: WorkflowContext
    ) -> Dict[str, Any]:
        """Execute a single step asynchronously."""
        # If the step executor is not async, run it in thread pool
        if not hasattr(self.executor, 'execute_step_async'):
            return await asyncio.get_event_loop().run_in_executor(
                self._get_thread_pool(),
                self.executor.execute_step,
                step,
                context
            )
        else:
            return await self.executor.execute_step_async(step, context)
    
    def _get_thread_pool(self) -> concurrent.futures.ThreadPoolExecutor:
        """Get or create thread pool for blocking operations."""
        if self._thread_pool is None:
            self._thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        return self._thread_pool
    
    def __del__(self):
        """Clean up resources."""
        if self._thread_pool:
            self._thread_pool.shutdown(wait=False)


def create_parallel_group(config: Dict[str, Any]) -> ParallelGroup:
    """Create a parallel group from configuration."""
    from .workflows import WorkflowStep
    
    name = config.get('name', 'unnamed_group')
    execution_mode = ParallelExecutionMode(config.get('mode', 'concurrent'))
    max_workers = config.get('max_workers')
    join_condition = config.get('join_condition')
    
    # Parse steps
    steps = []
    for step_config in config.get('steps', []):
        # WorkflowStep constructor takes a dict, not individual params
        step = WorkflowStep(step_config)
        steps.append(step)
    
    return ParallelGroup(
        name=name,
        steps=steps,
        max_workers=max_workers,
        execution_mode=execution_mode,
        join_condition=join_condition
    )