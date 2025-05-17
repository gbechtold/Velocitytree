"""
Tests for workflow templates functionality.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from velocitytree.workflows import WorkflowManager
from velocitytree.config import Config
from velocitytree.templates import WORKFLOW_TEMPLATES


class TestWorkflowTemplates:
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = Config()
        self.manager = WorkflowManager(self.config)
    
    def teardown_method(self):
        """Clean up test environment."""
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
    
    def test_list_templates(self):
        """Test listing available templates."""
        templates = self.manager.list_templates()
        
        assert len(templates) > 0
        assert all('id' in t for t in templates)
        assert all('name' in t for t in templates)
        assert all('description' in t for t in templates)
        assert all('steps' in t for t in templates)
        
        # Check specific templates exist
        template_ids = [t['id'] for t in templates]
        assert 'daily-standup' in template_ids
        assert 'code-review' in template_ids
        assert 'release-prep' in template_ids
    
    def test_create_workflow_from_template(self):
        """Test creating a workflow from a template."""
        # Create workflow from template
        workflow = self.manager.create_workflow(
            'test-standup', 
            template='daily-standup'
        )
        
        assert workflow is not None
        assert workflow.name == 'test-standup'
        assert 'daily standup' in workflow.description.lower()
        assert len(workflow.steps) > 0
        
        # Check steps from template
        template_steps = WORKFLOW_TEMPLATES['daily-standup']['steps']
        assert len(workflow.steps) == len(template_steps)
    
    def test_create_workflow_invalid_template(self):
        """Test creating workflow with invalid template."""
        # Should create basic workflow if template doesn't exist
        workflow = self.manager.create_workflow(
            'test-invalid',
            template='non-existent-template'
        )
        
        assert workflow is not None
        assert workflow.name == 'test-invalid'
        assert len(workflow.steps) == 1  # Basic template step
    
    def test_workflow_template_structure(self):
        """Test that all templates have proper structure."""
        for template_id, template in WORKFLOW_TEMPLATES.items():
            assert 'name' in template, f"Template {template_id} missing 'name'"
            assert 'description' in template, f"Template {template_id} missing 'description'"
            assert 'steps' in template, f"Template {template_id} missing 'steps'"
            assert len(template['steps']) > 0, f"Template {template_id} has no steps"
            
            # Check each step
            for i, step in enumerate(template['steps']):
                assert 'name' in step, f"Step {i} in {template_id} missing 'name'"
                assert 'type' in step, f"Step {i} in {template_id} missing 'type'"
                assert 'command' in step, f"Step {i} in {template_id} missing 'command'"
    
    def test_daily_standup_template(self):
        """Test daily standup template specifics."""
        workflow = self.manager.create_workflow(
            'test-daily', 
            template='daily-standup'
        )
        
        # Check for git status step
        step_names = [step.name for step in workflow.steps]
        assert any('git' in name.lower() for name in step_names)
        assert any('analyze' in name.lower() for name in step_names)
    
    def test_code_review_template(self):
        """Test code review template specifics."""
        workflow = self.manager.create_workflow(
            'test-review',
            template='code-review'
        )
        
        # Check for linting and test steps
        step_names = [step.name for step in workflow.steps]
        assert any('lint' in name.lower() for name in step_names)
        assert any('test' in name.lower() for name in step_names)
        assert any('flatten' in name.lower() for name in step_names)
    
    def test_release_prep_template(self):
        """Test release preparation template."""
        workflow = self.manager.create_workflow(
            'test-release',
            template='release-prep'
        )
        
        # Check for version and build steps
        step_names = [step.name for step in workflow.steps]
        assert any('version' in name.lower() for name in step_names)
        assert any('test' in name.lower() for name in step_names)
        assert any('build' in name.lower() for name in step_names)