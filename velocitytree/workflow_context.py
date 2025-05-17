"""
Workflow variables and context management.
"""

import json
import re
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path


class WorkflowContext:
    """Manages workflow execution context and variables."""
    
    def __init__(self, global_vars: Optional[Dict[str, Any]] = None):
        """Initialize workflow context."""
        self.global_vars = global_vars or {}
        self.step_outputs = {}
        self.current_step = None
        self.workflow_metadata = {
            'start_time': datetime.now(),
            'status': 'initialized',
            'steps_completed': 0,
            'errors': []
        }
        
        # Built-in variables
        self.built_ins = {
            'datetime': datetime,
            'now': lambda: datetime.now().isoformat(),
            'today': lambda: datetime.now().date().isoformat(),
            'cwd': lambda: str(Path.cwd()),
            'home': lambda: str(Path.home())
        }
    
    def set_global_var(self, key: str, value: Any) -> None:
        """Set a global variable."""
        self.global_vars[key] = value
    
    def get_global_var(self, key: str, default: Any = None) -> Any:
        """Get a global variable."""
        return self.global_vars.get(key, default)
    
    def set_step_output(self, step_id: str, output: Dict[str, Any]) -> None:
        """Set the output of a step."""
        self.step_outputs[step_id] = output
    
    def get_step_output(self, step_id: str) -> Optional[Dict[str, Any]]:
        """Get the output of a step."""
        return self.step_outputs.get(step_id)
    
    def resolve_variable(self, var_path: str) -> Any:
        """Resolve a variable path to its value."""
        parts = var_path.split('.')
        
        # Check built-ins first
        if parts[0] in self.built_ins:
            value = self.built_ins[parts[0]]
            if callable(value):
                value = value()
            
            # Navigate nested path if needed
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        
        # Check step outputs
        if parts[0] == 'steps' and len(parts) > 1:
            step_id = parts[1]
            output = self.get_step_output(step_id)
            
            if output:
                value = output
                for part in parts[2:]:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        return None
                return value
        
        # Check workflow metadata
        if parts[0] == 'workflow':
            value = self.workflow_metadata
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        
        # Check global variables
        if parts[0] in self.global_vars:
            value = self.global_vars[parts[0]]
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    return None
            return value
        
        return None
    
    def interpolate_string(self, template: str) -> str:
        """Interpolate variables in a string using advanced syntax."""
        def replace_var(match):
            var_expr = match.group(1)
            
            # Handle ternary operator: {{var ? true_value : false_value}}
            if '?' in var_expr and ':' in var_expr:
                # Handle nested interpolation by finding matching braces
                question_pos = -1
                colon_pos = -1
                brace_count = 0
                
                for i, char in enumerate(var_expr):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                    elif char == '?' and brace_count == 0 and question_pos == -1:
                        question_pos = i
                    elif char == ':' and brace_count == 0 and question_pos != -1 and colon_pos == -1:
                        colon_pos = i
                
                if question_pos != -1 and colon_pos != -1:
                    condition = var_expr[:question_pos].strip()
                    true_val = var_expr[question_pos+1:colon_pos].strip()
                    false_val = var_expr[colon_pos+1:].strip()
                else:
                    # Fallback to simple split
                    parts = var_expr.split('?', 1)
                    condition = parts[0].strip()
                    true_false = parts[1].split(':', 1)
                    true_val = true_false[0].strip()
                    false_val = true_false[1].strip()
                
                # Evaluate condition
                cond_result = self.evaluate_expression(condition)
                
                # Return appropriate value and interpolate if needed
                if cond_result:
                    if '{{' in true_val:
                        return self.interpolate_string(true_val)
                    return true_val
                else:
                    if '{{' in false_val:
                        return self.interpolate_string(false_val)
                    return false_val
            
            # Handle default values: {{var | default_value}}
            if '|' in var_expr:
                parts = var_expr.split('|', 1)
                var_path = parts[0].strip()
                default_val = parts[1].strip()
                
                value = self.resolve_variable(var_path)
                if value is None:
                    return default_val
                return str(value)
            
            # Handle function calls: {{func(arg1, arg2)}}
            if '(' in var_expr and ')' in var_expr:
                return str(self.evaluate_expression(var_expr))
            
            # Simple variable resolution
            value = self.resolve_variable(var_expr.strip())
            return str(value) if value is not None else match.group(0)
        
        # Advanced pattern matching for nested braces and expressions
        pattern = r'\{\{([^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*)\}\}'
        result = template
        depth = 0
        max_depth = 5  # Prevent infinite loops
        
        # Handle nested interpolations
        while '{{' in result and '}}' in result and depth < max_depth:
            new_result = re.sub(pattern, replace_var, result)
            if new_result == result:
                break  # No more substitutions
            result = new_result
            depth += 1
        
        return result
    
    def evaluate_expression(self, expr: str) -> Any:
        """Evaluate a simple expression."""
        # Create safe evaluation context
        safe_context = {
            'true': True,
            'false': False,
            'null': None,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
        }
        
        # Add variables to context
        for key, value in self.global_vars.items():
            safe_context[key] = value
        
        # Add built-ins
        for key, value in self.built_ins.items():
            if callable(value):
                # Don't call datetime directly, just pass the reference
                if key == 'datetime':
                    safe_context[key] = value
                else:
                    safe_context[key] = value()
            else:
                safe_context[key] = value
        
        # Add step outputs
        safe_context['steps'] = self.step_outputs
        safe_context['workflow'] = self.workflow_metadata
        
        try:
            # Simple expression evaluation
            # Note: This is deliberately limited for security
            result = eval(expr, {"__builtins__": {}}, safe_context)
            return result
        except Exception:
            return None
    
    def update_metadata(self, **kwargs) -> None:
        """Update workflow metadata."""
        self.workflow_metadata.update(kwargs)
    
    def add_error(self, error: str) -> None:
        """Add an error to the workflow metadata."""
        self.workflow_metadata['errors'].append({
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'step': self.current_step
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'global_vars': self.global_vars,
            'step_outputs': self.step_outputs,
            'workflow_metadata': self.workflow_metadata
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """Load context from dictionary."""
        self.global_vars = data.get('global_vars', {})
        self.step_outputs = data.get('step_outputs', {})
        self.workflow_metadata = data.get('workflow_metadata', {})
    
    def copy(self) -> 'WorkflowContext':
        """Create a copy of the context."""
        import copy
        new_context = WorkflowContext()
        new_context.global_vars = copy.deepcopy(self.global_vars)
        new_context.step_outputs = copy.deepcopy(self.step_outputs)
        new_context.workflow_metadata = copy.deepcopy(self.workflow_metadata)
        new_context.current_step = self.current_step
        return new_context


class VariableStore:
    """Persistent storage for workflow variables."""
    
    def __init__(self, store_path: Optional[Path] = None):
        """Initialize variable store."""
        self.store_path = store_path or (Path.home() / '.velocitytree' / 'variables.json')
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.variables = self._load_store()
    
    def _load_store(self) -> Dict[str, Any]:
        """Load variables from persistent storage."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_store(self) -> None:
        """Save variables to persistent storage."""
        with open(self.store_path, 'w') as f:
            json.dump(self.variables, f, indent=2, default=str)
    
    def set(self, key: str, value: Any, scope: str = 'global') -> None:
        """Set a variable in the store."""
        if scope not in self.variables:
            self.variables[scope] = {}
        
        self.variables[scope][key] = value
        self._save_store()
    
    def get(self, key: str, scope: str = 'global', default: Any = None) -> Any:
        """Get a variable from the store."""
        if scope in self.variables:
            return self.variables[scope].get(key, default)
        return default
    
    def delete(self, key: str, scope: str = 'global') -> bool:
        """Delete a variable from the store."""
        if scope in self.variables and key in self.variables[scope]:
            del self.variables[scope][key]
            self._save_store()
            return True
        return False
    
    def list_variables(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """List variables in the store."""
        if scope:
            return self.variables.get(scope, {})
        return self.variables
    
    def clear_scope(self, scope: str) -> None:
        """Clear all variables in a scope."""
        if scope in self.variables:
            self.variables[scope] = {}
            self._save_store()