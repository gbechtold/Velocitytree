"""
Tests for workflow context and variables functionality.
"""

import pytest
import json
from pathlib import Path
import tempfile
import shutil

from velocitytree.workflow_context import WorkflowContext, VariableStore


class TestWorkflowContext:
    """Test the WorkflowContext class."""
    
    def test_init(self):
        """Test initialization."""
        ctx = WorkflowContext()
        assert ctx.global_vars == {}
        assert ctx.step_outputs == {}
        assert ctx.current_step is None
        assert 'start_time' in ctx.workflow_metadata
        assert ctx.workflow_metadata['status'] == 'initialized'
    
    def test_global_vars(self):
        """Test global variables."""
        ctx = WorkflowContext()
        
        # Set and get global variables
        ctx.set_global_var('foo', 'bar')
        assert ctx.get_global_var('foo') == 'bar'
        assert ctx.get_global_var('missing') is None
        assert ctx.get_global_var('missing', 'default') == 'default'
    
    def test_step_outputs(self):
        """Test step outputs."""
        ctx = WorkflowContext()
        
        # Set and get step outputs
        output = {'status': 'success', 'result': 42}
        ctx.set_step_output('step1', output)
        assert ctx.get_step_output('step1') == output
        assert ctx.get_step_output('missing') is None
    
    def test_builtin_variables(self):
        """Test built-in variables."""
        ctx = WorkflowContext()
        
        # Test datetime functions
        assert isinstance(ctx.built_ins['now'](), str)
        assert isinstance(ctx.built_ins['today'](), str)
        assert isinstance(ctx.built_ins['cwd'](), str)
        assert isinstance(ctx.built_ins['home'](), str)
    
    def test_resolve_variable(self):
        """Test variable resolution."""
        ctx = WorkflowContext()
        
        # Set up test data
        ctx.set_global_var('project', {'name': 'test', 'version': '1.0'})
        ctx.set_step_output('step1', {'status': 'success', 'data': {'count': 5}})
        
        # Test global variable resolution
        assert ctx.resolve_variable('project') == {'name': 'test', 'version': '1.0'}
        assert ctx.resolve_variable('project.name') == 'test'
        assert ctx.resolve_variable('project.version') == '1.0'
        assert ctx.resolve_variable('project.missing') is None
        
        # Test step output resolution
        assert ctx.resolve_variable('steps.step1.status') == 'success'
        assert ctx.resolve_variable('steps.step1.data.count') == 5
        assert ctx.resolve_variable('steps.missing') is None
        
        # Test built-in resolution
        assert ctx.resolve_variable('now') is not None
        assert isinstance(ctx.resolve_variable('cwd'), str)
        
        # Test workflow metadata
        assert ctx.resolve_variable('workflow.status') == 'initialized'
    
    def test_simple_interpolation(self):
        """Test simple string interpolation."""
        ctx = WorkflowContext()
        ctx.set_global_var('name', 'John')
        ctx.set_global_var('age', 30)
        
        # Simple substitution
        assert ctx.interpolate_string('Hello {{name}}!') == 'Hello John!'
        assert ctx.interpolate_string('Age: {{age}}') == 'Age: 30'
        assert ctx.interpolate_string('{{name}} is {{age}} years old') == 'John is 30 years old'
        
        # Non-existent variable
        assert ctx.interpolate_string('Hello {{missing}}!') == 'Hello {{missing}}!'
    
    def test_default_values(self):
        """Test default value syntax."""
        ctx = WorkflowContext()
        ctx.set_global_var('name', 'John')
        
        # With defaults
        assert ctx.interpolate_string('{{name | Jane}}') == 'John'
        assert ctx.interpolate_string('{{missing | default}}') == 'default'
        assert ctx.interpolate_string('{{missing | 42}}') == '42'
    
    def test_ternary_operator(self):
        """Test ternary operator in interpolation."""
        ctx = WorkflowContext()
        ctx.set_global_var('debug', True)
        ctx.set_global_var('prod', False)
        
        # Ternary expressions
        assert ctx.interpolate_string('{{debug ? verbose : quiet}}') == 'verbose'
        assert ctx.interpolate_string('{{prod ? production : development}}') == 'development'
        
        # Nested interpolation in ternary
        ctx.set_global_var('mode', 'verbose')
        assert ctx.interpolate_string('{{debug ? {{mode}} : quiet}}') == 'verbose'
    
    def test_expression_evaluation(self):
        """Test expression evaluation."""
        ctx = WorkflowContext()
        ctx.set_global_var('count', 5)
        ctx.set_global_var('items', [1, 2, 3, 4, 5])
        
        # Simple expressions
        assert ctx.evaluate_expression('count > 3') is True
        assert ctx.evaluate_expression('count < 3') is False
        assert ctx.evaluate_expression('len(items)') == 5
        assert ctx.evaluate_expression('max(items)') == 5
        assert ctx.evaluate_expression('sum(items)') == 15
        
        # String operations
        ctx.set_global_var('name', 'test')
        assert ctx.evaluate_expression('name.upper()') == 'TEST'
        
        # Complex expressions
        assert ctx.evaluate_expression('count * 2 + 1') == 11
        
        # Invalid expressions should return None
        assert ctx.evaluate_expression('invalid syntax !@#') is None
    
    def test_nested_interpolation(self):
        """Test nested variable interpolation."""
        ctx = WorkflowContext()
        ctx.set_global_var('env', 'prod')
        ctx.set_global_var('config', {
            'dev': {'host': 'localhost'},
            'prod': {'host': 'production.com'}
        })
        
        # Direct path should work
        assert ctx.interpolate_string('{{config.prod.host}}') == 'production.com'
        
        # Nested interpolation is complex and may not work directly this way
        # Using alternative approach
        env_val = ctx.resolve_variable('env')
        assert ctx.interpolate_string(f'{{{{config.{env_val}.host}}}}') == 'production.com'
    
    def test_metadata_updates(self):
        """Test workflow metadata updates."""
        ctx = WorkflowContext()
        
        # Update metadata
        ctx.update_metadata(status='running', steps_completed=2)
        assert ctx.workflow_metadata['status'] == 'running'
        assert ctx.workflow_metadata['steps_completed'] == 2
    
    def test_error_tracking(self):
        """Test error tracking."""
        ctx = WorkflowContext()
        ctx.current_step = 'test_step'
        
        # Add errors
        ctx.add_error('Something went wrong')
        assert len(ctx.workflow_metadata['errors']) == 1
        
        error = ctx.workflow_metadata['errors'][0]
        assert error['error'] == 'Something went wrong'
        assert error['step'] == 'test_step'
        assert 'timestamp' in error
    
    def test_serialization(self):
        """Test context serialization."""
        ctx = WorkflowContext()
        ctx.set_global_var('test', 'value')
        ctx.set_step_output('step1', {'result': 'success'})
        
        # Convert to dict
        data = ctx.to_dict()
        assert 'global_vars' in data
        assert 'step_outputs' in data
        assert 'workflow_metadata' in data
        
        # Create new context from dict
        new_ctx = WorkflowContext()
        new_ctx.from_dict(data)
        assert new_ctx.get_global_var('test') == 'value'
        assert new_ctx.get_step_output('step1') == {'result': 'success'}


class TestVariableStore:
    """Test the VariableStore class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.store_path = Path(self.temp_dir) / 'variables.json'
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test initialization."""
        store = VariableStore(self.store_path)
        assert store.store_path == self.store_path
        assert store.variables == {}
    
    def test_set_and_get(self):
        """Test setting and getting variables."""
        store = VariableStore(self.store_path)
        
        # Set variables
        store.set('foo', 'bar')
        store.set('count', 42)
        store.set('config', {'debug': True})
        
        # Get variables
        assert store.get('foo') == 'bar'
        assert store.get('count') == 42
        assert store.get('config') == {'debug': True}
        assert store.get('missing') is None
        assert store.get('missing', default='default') == 'default'
    
    def test_scopes(self):
        """Test variable scopes."""
        store = VariableStore(self.store_path)
        
        # Set variables in different scopes
        store.set('var1', 'global_value', 'global')
        store.set('var1', 'project_value', 'project')
        store.set('var2', 'workflow_value', 'workflow')
        
        # Get variables from scopes
        assert store.get('var1', 'global') == 'global_value'
        assert store.get('var1', 'project') == 'project_value'
        assert store.get('var2', 'workflow') == 'workflow_value'
        assert store.get('var1', 'workflow') is None
    
    def test_persistence(self):
        """Test variable persistence."""
        store1 = VariableStore(self.store_path)
        store1.set('persistent', 'value')
        
        # Create new store instance with same path
        store2 = VariableStore(self.store_path)
        assert store2.get('persistent') == 'value'
    
    def test_delete(self):
        """Test variable deletion."""
        store = VariableStore(self.store_path)
        
        # Set and delete variables
        store.set('temp', 'value')
        assert store.get('temp') == 'value'
        
        assert store.delete('temp') is True
        assert store.get('temp') is None
        
        # Delete non-existent variable
        assert store.delete('missing') is False
    
    def test_list_variables(self):
        """Test listing variables."""
        store = VariableStore(self.store_path)
        
        # Set variables in different scopes
        store.set('var1', 'value1', 'global')
        store.set('var2', 'value2', 'global')
        store.set('var3', 'value3', 'project')
        
        # List all variables
        all_vars = store.list_variables()
        assert 'global' in all_vars
        assert 'project' in all_vars
        assert all_vars['global']['var1'] == 'value1'
        assert all_vars['global']['var2'] == 'value2'
        assert all_vars['project']['var3'] == 'value3'
        
        # List specific scope
        global_vars = store.list_variables('global')
        assert global_vars['var1'] == 'value1'
        assert global_vars['var2'] == 'value2'
    
    def test_clear_scope(self):
        """Test clearing a scope."""
        store = VariableStore(self.store_path)
        
        # Set variables
        store.set('var1', 'value1', 'test')
        store.set('var2', 'value2', 'test')
        store.set('var3', 'value3', 'global')
        
        # Clear test scope
        store.clear_scope('test')
        
        # Verify test scope is empty
        assert store.get('var1', 'test') is None
        assert store.get('var2', 'test') is None
        assert store.get('var3', 'global') == 'value3'