"""
Tests for conditional workflow steps.
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
import shutil

from velocitytree.workflow_conditions import (
    ConditionOperator, ConditionNode, ConditionParser, 
    evaluate_condition, ConditionalStep
)
from velocitytree.workflow_context import WorkflowContext
from velocitytree.workflows import Workflow, WorkflowStep


class TestConditionNode:
    """Test the ConditionNode class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.context = WorkflowContext()
        self.context.set_global_var('debug', True)
        self.context.set_global_var('env', 'production')
        self.context.set_global_var('count', 5)
        self.context.set_global_var('users', ['alice', 'bob', 'charlie'])
    
    def test_true_false_operators(self):
        """Test TRUE and FALSE operators."""
        true_node = ConditionNode(operator=ConditionOperator.TRUE)
        assert true_node.evaluate(self.context) is True
        
        false_node = ConditionNode(operator=ConditionOperator.FALSE)
        assert false_node.evaluate(self.context) is False
    
    def test_logical_operators(self):
        """Test AND, OR, NOT operators."""
        # AND
        and_node = ConditionNode(
            operator=ConditionOperator.AND,
            left=ConditionNode(operator=ConditionOperator.TRUE),
            right=ConditionNode(operator=ConditionOperator.TRUE)
        )
        assert and_node.evaluate(self.context) is True
        
        and_node.right = ConditionNode(operator=ConditionOperator.FALSE)
        assert and_node.evaluate(self.context) is False
        
        # OR
        or_node = ConditionNode(
            operator=ConditionOperator.OR,
            left=ConditionNode(operator=ConditionOperator.FALSE),
            right=ConditionNode(operator=ConditionOperator.TRUE)
        )
        assert or_node.evaluate(self.context) is True
        
        # NOT
        not_node = ConditionNode(
            operator=ConditionOperator.NOT,
            left=ConditionNode(operator=ConditionOperator.FALSE)
        )
        assert not_node.evaluate(self.context) is True
    
    def test_comparison_operators(self):
        """Test comparison operators."""
        # EQUALS
        eq_node = ConditionNode(
            operator=ConditionOperator.EQUALS,
            left='{{count}}',
            right='5'
        )
        assert eq_node.evaluate(self.context) is True
        
        # NOT_EQUALS
        ne_node = ConditionNode(
            operator=ConditionOperator.NOT_EQUALS,
            left='{{env}}',
            right='development'
        )
        assert ne_node.evaluate(self.context) is True
        
        # GREATER_THAN
        gt_node = ConditionNode(
            operator=ConditionOperator.GREATER_THAN,
            left='{{count}}',
            right='3'
        )
        assert gt_node.evaluate(self.context) is True
        
        # LESS_THAN
        lt_node = ConditionNode(
            operator=ConditionOperator.LESS_THAN,
            left='{{count}}',
            right='10'
        )
        assert lt_node.evaluate(self.context) is True
    
    def test_membership_operators(self):
        """Test IN and NOT IN operators."""
        # IN
        in_node = ConditionNode(
            operator=ConditionOperator.IN,
            left='alice',
            right='{{users}}'
        )
        assert in_node.evaluate(self.context) is True
        
        # NOT IN
        not_in_node = ConditionNode(
            operator=ConditionOperator.NOT_IN,
            left='dave',
            right='{{users}}'
        )
        assert not_in_node.evaluate(self.context) is True
    
    def test_string_operators(self):
        """Test CONTAINS and MATCHES operators."""
        self.context.set_global_var('message', 'Hello, World!')
        self.context.set_global_var('pattern', r'^\d{3}-\d{3}-\d{4}$')
        self.context.set_global_var('phone', '123-456-7890')
        
        # CONTAINS
        contains_node = ConditionNode(
            operator=ConditionOperator.CONTAINS,
            left='{{message}}',
            right='World'
        )
        assert contains_node.evaluate(self.context) is True
        
        # MATCHES
        matches_node = ConditionNode(
            operator=ConditionOperator.MATCHES,
            left='{{phone}}',
            right='{{pattern}}'
        )
        assert matches_node.evaluate(self.context) is True


class TestConditionParser:
    """Test the ConditionParser class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.parser = ConditionParser()
        self.context = WorkflowContext()
        self.context.set_global_var('x', 10)
        self.context.set_global_var('y', 20)
        self.context.set_global_var('name', 'test')
        self.context.set_global_var('active', True)
    
    def test_simple_conditions(self):
        """Test parsing simple conditions."""
        # Boolean literals
        node = self.parser.parse('true')
        assert node.evaluate(self.context) is True
        
        node = self.parser.parse('false')
        assert node.evaluate(self.context) is False
        
        # Variable reference
        node = self.parser.parse('{{active}}')
        assert node.evaluate(self.context) is True
    
    def test_comparison_conditions(self):
        """Test parsing comparison conditions."""
        node = self.parser.parse('{{x}} > 5')
        assert node.evaluate(self.context) is True
        
        node = self.parser.parse('{{y}} == 20')
        assert node.evaluate(self.context) is True
        
        node = self.parser.parse('{{name}} != "other"')
        assert node.evaluate(self.context) is True
    
    def test_logical_conditions(self):
        """Test parsing logical conditions."""
        # AND
        node = self.parser.parse('{{x}} > 5 and {{y}} < 30')
        assert node.evaluate(self.context) is True
        
        # OR
        node = self.parser.parse('{{x}} < 5 or {{y}} == 20')
        assert node.evaluate(self.context) is True
        
        # NOT
        node = self.parser.parse('not {{x}} < 5')
        assert node.evaluate(self.context) is True
    
    def test_complex_conditions(self):
        """Test parsing complex nested conditions."""
        # Mixed operators
        node = self.parser.parse('({{x}} > 5 and {{y}} == 20) or {{name}} == "other"')
        assert node.evaluate(self.context) is True
        
        # Nested parentheses
        node = self.parser.parse('not ({{x}} < 5 or ({{y}} > 30 and {{active}}))')
        assert node.evaluate(self.context) is True
    
    def test_string_conditions(self):
        """Test string-based conditions."""
        self.context.set_global_var('env', 'production')
        self.context.set_global_var('features', ['auth', 'api', 'ui'])
        
        # IN operator
        node = self.parser.parse('"auth" in {{features}}')
        assert node.evaluate(self.context) is True
        
        # CONTAINS operator
        node = self.parser.parse('{{env}} contains "prod"')
        assert node.evaluate(self.context) is True


class TestConditionalWorkflowSteps:
    """Test conditional workflow steps integration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_simple_conditional_step(self):
        """Test a simple conditional step."""
        context = WorkflowContext()
        context.set_global_var('deploy', True)
        
        step_config = {
            'name': 'conditional_deploy',
            'type': 'command',
            'command': 'echo "Deploying"',
            'condition': '{{deploy}} == true'
        }
        
        step = WorkflowStep(step_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Deploying'
            mock_run.return_value.stderr = ''
            
            result = step.execute(context)
            assert result['status'] == 'success'
            mock_run.assert_called_once()
        
        # Test with condition not met
        context.set_global_var('deploy', False)
        result = step.execute(context)
        assert result['status'] == 'skipped'
        assert result['reason'] == 'Condition not met'
    
    def test_if_then_else_block(self):
        """Test if/then/else conditional blocks."""
        context = WorkflowContext()
        context.set_global_var('env', 'production')
        
        step_config = {
            'name': 'env_specific_deploy',
            'if': '{{env}} == "production"',
            'then': [
                {
                    'name': 'prod_deploy',
                    'type': 'command',
                    'command': 'echo "Production deployment"'
                }
            ],
            'else': [
                {
                    'name': 'dev_deploy',
                    'type': 'command',
                    'command': 'echo "Development deployment"'
                }
            ]
        }
        
        step = WorkflowStep(step_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Production deployment'
            mock_run.return_value.stderr = ''
            
            result = step.execute(context)
            assert result['status'] == 'success'
            assert result['condition_met'] is True
            assert 'Production deployment' in result['output']
            mock_run.assert_called_once()
        
        # Test else branch
        context.set_global_var('env', 'development')
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Development deployment'
            mock_run.return_value.stderr = ''
            
            result = step.execute(context)
            assert result['status'] == 'success'
            assert result['condition_met'] is False
            assert 'Development deployment' in result['output']
            mock_run.assert_called_once()
    
    def test_complex_workflow_conditions(self):
        """Test complex conditions in a workflow."""
        workflow_config = {
            'description': 'Complex conditional workflow',
            'steps': [
                {
                    'name': 'check_environment',
                    'type': 'command',
                    'command': 'echo "Checking environment"'
                },
                {
                    'name': 'conditional_build',
                    'if': '{{env}} == "production" and {{deploy}} == true',
                    'then': [
                        {
                            'name': 'production_build',
                            'type': 'command',
                            'command': 'echo "Building for production"'
                        },
                        {
                            'name': 'minify_assets',
                            'type': 'command',
                            'command': 'echo "Minifying assets"'
                        }
                    ],
                    'else': [
                        {
                            'name': 'development_build',
                            'type': 'command',
                            'command': 'echo "Building for development"'
                        }
                    ]
                },
                {
                    'name': 'notify',
                    'type': 'command',
                    'command': 'echo "Build complete"',
                    'condition': '{{steps.step_0.status}} == "success"'
                }
            ]
        }
        
        workflow = Workflow('test', workflow_config)
        context = WorkflowContext()
        context.set_global_var('env', 'production')
        context.set_global_var('deploy', True)
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                Mock(returncode=0, stdout='Checking environment', stderr=''),
                Mock(returncode=0, stdout='Building for production', stderr=''),
                Mock(returncode=0, stdout='Minifying assets', stderr=''),
                Mock(returncode=0, stdout='Build complete', stderr='')
            ]
            
            result = workflow.execute(context)
            assert result['status'] == 'success'
            assert mock_run.call_count == 4
    
    def test_nested_conditions(self):
        """Test nested conditional blocks."""
        step_config = {
            'name': 'nested_conditions',
            'if': '{{platform}} == "aws"',
            'then': [
                {
                    'name': 'aws_region_check',
                    'if': '{{region}} in ["us-east-1", "us-west-2"]',
                    'then': [
                        {
                            'name': 'deploy_to_region',
                            'type': 'command',
                            'command': 'echo "Deploying to {{region}}"'
                        }
                    ],
                    'else': [
                        {
                            'name': 'invalid_region',
                            'type': 'command',
                            'command': 'echo "Invalid AWS region"'
                        }
                    ]
                }
            ],
            'else': [
                {
                    'name': 'unsupported_platform',
                    'type': 'command',
                    'command': 'echo "Platform not supported"'
                }
            ]
        }
        
        context = WorkflowContext()
        context.set_global_var('platform', 'aws')
        context.set_global_var('region', 'us-east-1')
        
        step = WorkflowStep(step_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = 'Deploying to us-east-1'
            mock_run.return_value.stderr = ''
            
            result = step.execute(context)
            assert result['status'] == 'success'
            assert 'Deploying to us-east-1' in result['output']


class TestEvaluateConditionFunction:
    """Test the evaluate_condition function."""
    
    def test_string_conditions(self):
        """Test string-based conditions."""
        context = WorkflowContext()
        context.set_global_var('status', 'active')
        
        assert evaluate_condition('{{status}} == "active"', context) is True
        assert evaluate_condition('{{status}} != "inactive"', context) is True
    
    def test_dict_conditions(self):
        """Test dictionary-based conditions."""
        context = WorkflowContext()
        context.set_global_var('env', 'prod')
        context.set_global_var('debug', False)
        
        # Simple key-value
        condition = {'env': 'prod'}
        assert evaluate_condition(condition, context) is True
        
        # All conditions
        condition = {
            'all': [
                '{{env}} == "prod"',
                '{{debug}} == false'
            ]
        }
        assert evaluate_condition(condition, context) is True
        
        # Any conditions
        condition = {
            'any': [
                '{{env}} == "dev"',
                '{{debug}} == true',
                '{{env}} == "prod"'
            ]
        }
        assert evaluate_condition(condition, context) is True
        
        # Not condition
        condition = {
            'not': '{{debug}} == true'
        }
        assert evaluate_condition(condition, context) is True
    
    def test_bool_conditions(self):
        """Test boolean conditions."""
        context = WorkflowContext()
        
        assert evaluate_condition(True, context) is True
        assert evaluate_condition(False, context) is False