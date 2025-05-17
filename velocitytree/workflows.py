"""
Workflow management for Velocitytree.
"""

import os
import yaml
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from .config import Config
from .utils import logger, run_command, ensure_directory
from .core import TreeFlattener, ContextManager
from .ai import AIAssistant
from .templates import WORKFLOW_TEMPLATES
from .workflow_context import WorkflowContext, VariableStore

console = Console()


class WorkflowStep:
    """Represents a single step in a workflow."""
    
    def __init__(self, config: Dict[str, Any]):
        self.type = config.get('type', 'command')
        self.name = config.get('name', 'Unnamed Step')
        self.command = config.get('command')
        self.args = config.get('args', [])
        self.env = config.get('env', {})
        self.cwd = config.get('cwd')
        self.continue_on_error = config.get('continue_on_error', False)
        self.condition = config.get('condition')
        self.timeout = config.get('timeout', 300)  # 5 minutes default
    
    def execute(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute the workflow step."""
        # Set current step in context
        context.current_step = self.name
        
        # Check condition if specified
        if self.condition:
            if not self._evaluate_condition(self.condition, context):
                return {
                    'status': 'skipped',
                    'reason': 'Condition not met',
                    'output': ''
                }
        
        try:
            if self.type == 'command':
                return self._execute_command(context)
            elif self.type == 'python':
                return self._execute_python(context)
            elif self.type == 'velocitytree':
                return self._execute_velocitytree_command(context)
            else:
                raise ValueError(f"Unknown step type: {self.type}")
        except Exception as e:
            if self.continue_on_error:
                return {
                    'status': 'error',
                    'error': str(e),
                    'output': ''
                }
            raise
    
    def _execute_command(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute a shell command."""
        command = context.interpolate_string(self.command)
        
        # Set up environment
        env = os.environ.copy()
        for key, value in self.env.items():
            env[key] = context.interpolate_string(str(value))
        
        # Run command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=self.cwd,
            timeout=self.timeout
        )
        
        return {
            'status': 'success' if result.returncode == 0 else 'error',
            'exit_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'output': result.stdout
        }
    
    def _execute_python(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute Python code."""
        code = context.interpolate_string(self.command)
        
        # Capture output
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = output_buffer = StringIO()
        
        # Create a sandboxed environment
        globals_dict = {
            'context': context,
            'print': print,
            '__builtins__': __builtins__
        }
        
        try:
            exec(code, globals_dict)
            captured_output = output_buffer.getvalue()
            return {
                'status': 'success',
                'output': captured_output or globals_dict.get('output', ''),
                'stdout': captured_output,
                'stderr': ''
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'output': '',
                'stdout': '',
                'stderr': str(e)
            }
        finally:
            sys.stdout = old_stdout
    
    def _execute_velocitytree_command(self, context: WorkflowContext) -> Dict[str, Any]:
        """Execute a Velocitytree command."""
        command = self.command
        args = self.args
        
        # Map to internal functions
        if command == 'flatten':
            flattener = TreeFlattener(**args)
            result = flattener.flatten()
            return {
                'status': 'success',
                'output': result
            }
        elif command == 'context':
            manager = ContextManager()
            result = manager.generate_context(**args)
            return {
                'status': 'success',
                'output': result
            }
        elif command == 'ai':
            config = Config()
            assistant = AIAssistant(config)
            method = args.pop('method', 'suggest')
            result = getattr(assistant, method)(**args)
            return {
                'status': 'success',
                'output': result
            }
        else:
            raise ValueError(f"Unknown Velocitytree command: {command}")
    
    def _interpolate_string(self, template: str, context: WorkflowContext) -> str:
        """Interpolate variables in a string."""
        # Use context's interpolation method
        return context.interpolate_string(template)
    
    def _evaluate_condition(self, condition: str, context: WorkflowContext) -> bool:
        """Evaluate a condition."""
        # Use context's evaluation method
        return bool(context.evaluate_expression(condition))


class Workflow:
    """Represents a complete workflow."""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.description = config.get('description', '')
        self.steps = [WorkflowStep(step) for step in config.get('steps', [])]
        self.env = config.get('env', {})
        self.on_error = config.get('on_error', 'stop')  # stop, continue, or cleanup
        self.cleanup_steps = [WorkflowStep(step) for step in config.get('cleanup', [])]
    
    def execute(self, context: Optional[WorkflowContext] = None) -> Dict[str, Any]:
        """Execute the workflow."""
        if context is None:
            context = WorkflowContext()
        
        # Add workflow metadata to context
        context.update_metadata(
            name=self.name,
            status='running'
        )
        
        # Set global environment variables
        for key, value in self.env.items():
            context.set_global_var(key, value)
        
        results = []
        error_occurred = False
        
        with Progress() as progress:
            task = progress.add_task(f"Running workflow: {self.name}", total=len(self.steps))
            
            for i, step in enumerate(self.steps):
                console.print(f"[blue]Executing step {i+1}/{len(self.steps)}: {step.name}[/blue]")
                
                try:
                    result = step.execute(context)
                    results.append({
                        'step': i,
                        'name': step.name,
                        'result': result
                    })
                    
                    # Update context with step results
                    context.set_step_output(f'step_{i}', result)
                    context.set_step_output(step.name, result)
                    context.update_metadata(steps_completed=i+1)
                    
                    progress.update(task, advance=1)
                    
                    if result['status'] == 'error' and self.on_error == 'stop':
                        error_occurred = True
                        break
                        
                except Exception as e:
                    error_occurred = True
                    context.add_error(str(e))
                    results.append({
                        'step': i,
                        'name': step.name,
                        'result': {
                            'status': 'error',
                            'error': str(e)
                        }
                    })
                    
                    if self.on_error == 'stop':
                        break
        
        # Run cleanup steps if configured
        if self.cleanup_steps and (error_occurred or self.on_error == 'cleanup'):
            console.print("[yellow]Running cleanup steps...[/yellow]")
            for step in self.cleanup_steps:
                try:
                    step.execute(context)
                except Exception as e:
                    logger.error(f"Cleanup step failed: {e}")
        
        # Update workflow status
        context.update_metadata(
            end_time=datetime.now(),
            status='error' if error_occurred else 'success'
        )
        
        return {
            'workflow': self.name,
            'status': context.workflow_metadata['status'],
            'results': results,
            'context': context.to_dict()
        }


class WorkflowManager:
    """Manages workflow creation, storage, and execution."""
    
    def __init__(self, config: Config):
        self.config = config
        self.workflows_dir = Path.home() / '.velocitytree' / 'workflows'
        ensure_directory(self.workflows_dir)
        
        # Load workflows from config
        self.workflows = {}
        for name, workflow_config in config.config.workflows.items():
            self.workflows[name] = Workflow(name, workflow_config)
        
        # Load custom workflows from directory
        self._load_custom_workflows()
    
    def _load_custom_workflows(self):
        """Load custom workflows from the workflows directory."""
        for workflow_file in self.workflows_dir.glob('*.yaml'):
            try:
                with open(workflow_file, 'r') as f:
                    workflow_config = yaml.safe_load(f)
                
                name = workflow_file.stem
                self.workflows[name] = Workflow(name, workflow_config)
                
            except Exception as e:
                logger.error(f"Error loading workflow {workflow_file}: {e}")
    
    def create_workflow(self, name: str, config: Optional[Dict[str, Any]] = None, template: Optional[str] = None):
        """Create a new workflow, optionally from a template."""
        if config is None:
            if template and template in WORKFLOW_TEMPLATES:
                # Use template
                template_config = WORKFLOW_TEMPLATES[template]
                config = {
                    'description': template_config.get('description', f'Workflow {name}'),
                    'steps': template_config.get('steps', []),
                    'env': template_config.get('env', {}),
                    'on_error': template_config.get('on_error', 'stop')
                }
                logger.info(f"Creating workflow '{name}' from template '{template}'")
            else:
                # Create a basic workflow
                config = {
                    'description': f'Workflow {name}',
                    'steps': [
                        {
                            'name': 'Step 1',
                            'type': 'command',
                            'command': 'echo "Hello from workflow!"'
                        }
                    ]
                }
        
        workflow = Workflow(name, config)
        self.workflows[name] = workflow
        
        # Save to file
        workflow_file = self.workflows_dir / f'{name}.yaml'
        with open(workflow_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Created workflow: {name}")
        return workflow
    
    def delete_workflow(self, name: str):
        """Delete a workflow."""
        if name in self.workflows:
            del self.workflows[name]
            
            # Remove file if it exists
            workflow_file = self.workflows_dir / f'{name}.yaml'
            if workflow_file.exists():
                workflow_file.unlink()
            
            logger.info(f"Deleted workflow: {name}")
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all available workflows."""
        workflows = []
        
        for name, workflow in self.workflows.items():
            workflows.append({
                'name': name,
                'description': workflow.description,
                'steps': len(workflow.steps),
                'source': 'config' if name in self.config.config.workflows else 'custom'
            })
        
        return workflows
    
    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name."""
        return self.workflows.get(name)
    
    def run_workflow(self, name: str, context: Optional[WorkflowContext] = None, global_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a workflow."""
        workflow = self.get_workflow(name)
        
        if not workflow:
            raise ValueError(f"Workflow not found: {name}")
        
        # Create context if not provided
        if context is None:
            context = WorkflowContext(global_vars=global_vars)
        
        logger.info(f"Starting workflow: {name}")
        result = workflow.execute(context)
        logger.info(f"Workflow completed: {name} - Status: {result['status']}")
        
        return result
    
    def export_workflow(self, name: str, output_path: Path):
        """Export a workflow to a file."""
        workflow = self.get_workflow(name)
        
        if not workflow:
            raise ValueError(f"Workflow not found: {name}")
        
        # Convert workflow to config format
        config = {
            'description': workflow.description,
            'env': workflow.env,
            'on_error': workflow.on_error,
            'steps': [],
            'cleanup': []
        }
        
        # Export steps
        for step in workflow.steps:
            step_config = {
                'name': step.name,
                'type': step.type,
                'command': step.command
            }
            
            if step.args:
                step_config['args'] = step.args
            if step.env:
                step_config['env'] = step.env
            if step.cwd:
                step_config['cwd'] = step.cwd
            if step.condition:
                step_config['condition'] = step.condition
            if step.continue_on_error:
                step_config['continue_on_error'] = step.continue_on_error
            
            config['steps'].append(step_config)
        
        # Export cleanup steps
        for step in workflow.cleanup_steps:
            # Similar to above
            config['cleanup'].append({
                'name': step.name,
                'type': step.type,
                'command': step.command
            })
        
        # Save to file
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        logger.info(f"Exported workflow {name} to {output_path}")
    
    def import_workflow(self, path: Path, name: Optional[str] = None):
        """Import a workflow from a file."""
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        
        workflow_name = name or path.stem
        self.create_workflow(workflow_name, config)
        
        logger.info(f"Imported workflow: {workflow_name}")
    
    def show_workflow_details(self, name: str):
        """Display detailed information about a workflow."""
        workflow = self.get_workflow(name)
        
        if not workflow:
            console.print(f"[red]Workflow not found: {name}[/red]")
            return
        
        console.print(f"[bold]Workflow: {name}[/bold]")
        console.print(f"Description: {workflow.description}")
        console.print(f"Error handling: {workflow.on_error}")
        console.print()
        
        # Show steps
        table = Table(title="Steps")
        table.add_column("#", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Type", style="green")
        table.add_column("Command", style="blue")
        
        for i, step in enumerate(workflow.steps):
            table.add_row(
                str(i + 1),
                step.name,
                step.type,
                step.command[:50] + "..." if len(step.command) > 50 else step.command
            )
        
        console.print(table)
        
        # Show cleanup steps if any
        if workflow.cleanup_steps:
            console.print()
            cleanup_table = Table(title="Cleanup Steps")
            cleanup_table.add_column("#", style="cyan")
            cleanup_table.add_column("Name", style="yellow")
            cleanup_table.add_column("Type", style="green")
            
            for i, step in enumerate(workflow.cleanup_steps):
                cleanup_table.add_row(
                    str(i + 1),
                    step.name,
                    step.type
                )
            
            console.print(cleanup_table)
    
    def list_templates(self) -> List[Dict[str, str]]:
        """List available workflow templates."""
        templates = []
        for template_id, template_config in WORKFLOW_TEMPLATES.items():
            templates.append({
                'id': template_id,
                'name': template_config.get('name', template_id),
                'description': template_config.get('description', ''),
                'steps': len(template_config.get('steps', []))
            })
        return templates