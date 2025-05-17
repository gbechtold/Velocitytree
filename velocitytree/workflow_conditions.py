"""
Advanced conditional expressions for workflows.
"""

import re
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from .workflow_context import WorkflowContext


class ConditionOperator(Enum):
    """Logical operators for conditions."""
    AND = "and"
    OR = "or"
    NOT = "not"
    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    IN = "in"
    NOT_IN = "not in"
    CONTAINS = "contains"
    MATCHES = "matches"  # regex match
    TRUE = "true"
    FALSE = "false"


@dataclass
class ConditionNode:
    """A node in the condition expression tree."""
    operator: Optional[ConditionOperator] = None
    left: Optional[Union['ConditionNode', str]] = None
    right: Optional[Union['ConditionNode', str]] = None
    value: Optional[Any] = None
    
    def evaluate(self, context: WorkflowContext) -> bool:
        """Evaluate this condition node."""
        if self.operator is None and self.value is not None:
            # This is a simple value node
            resolved = self._resolve_value(self.value, context)
            return bool(resolved)
        elif self.operator == ConditionOperator.TRUE:
            return True
        elif self.operator == ConditionOperator.FALSE:
            return False
        elif self.operator == ConditionOperator.AND:
            left_result = self._evaluate_operand(self.left, context)
            right_result = self._evaluate_operand(self.right, context)
            return left_result and right_result
        elif self.operator == ConditionOperator.OR:
            left_result = self._evaluate_operand(self.left, context)
            right_result = self._evaluate_operand(self.right, context)
            return left_result or right_result
        elif self.operator == ConditionOperator.NOT:
            return not self._evaluate_operand(self.left, context)
        else:
            # Binary comparison operators
            left_value = self._resolve_value(self.left, context)
            right_value = self._resolve_value(self.right, context)
            
            if self.operator == ConditionOperator.EQUALS:
                return self._compare_values(left_value, right_value, lambda a, b: a == b)
            elif self.operator == ConditionOperator.NOT_EQUALS:
                return self._compare_values(left_value, right_value, lambda a, b: a != b)
            elif self.operator == ConditionOperator.GREATER_THAN:
                return self._compare_values(left_value, right_value, lambda a, b: a > b)
            elif self.operator == ConditionOperator.LESS_THAN:
                return self._compare_values(left_value, right_value, lambda a, b: a < b)
            elif self.operator == ConditionOperator.GREATER_EQUAL:
                return self._compare_values(left_value, right_value, lambda a, b: a >= b)
            elif self.operator == ConditionOperator.LESS_EQUAL:
                return self._compare_values(left_value, right_value, lambda a, b: a <= b)
            elif self.operator == ConditionOperator.IN:
                return left_value in right_value
            elif self.operator == ConditionOperator.NOT_IN:
                return left_value not in right_value
            elif self.operator == ConditionOperator.CONTAINS:
                return str(right_value) in str(left_value)
            elif self.operator == ConditionOperator.MATCHES:
                return bool(re.match(str(right_value), str(left_value)))
        
        return False
    
    def _compare_values(self, left: Any, right: Any, comparator) -> bool:
        """Compare values with type coercion."""
        # If types match, compare directly
        if type(left) == type(right):
            return comparator(left, right)
        
        # Try to coerce types for comparison
        try:
            # Try numeric comparison
            if isinstance(left, (int, float)) or isinstance(right, (int, float)):
                left_num = float(left) if not isinstance(left, (int, float)) else left
                right_num = float(right) if not isinstance(right, (int, float)) else right
                return comparator(left_num, right_num)
        except (ValueError, TypeError):
            pass
        
        # Fall back to string comparison
        return comparator(str(left), str(right))
    
    def _evaluate_operand(self, operand: Union['ConditionNode', str], context: WorkflowContext) -> bool:
        """Evaluate an operand (either a node or a value)."""
        if isinstance(operand, ConditionNode):
            return operand.evaluate(context)
        else:
            # Simple expression evaluation
            return bool(context.evaluate_expression(str(operand)))
    
    def _resolve_value(self, value: Union['ConditionNode', str], context: WorkflowContext) -> Any:
        """Resolve a value (interpolate variables, evaluate expressions)."""
        if isinstance(value, ConditionNode):
            return value.evaluate(context)
        elif isinstance(value, str):
            # First try to interpolate variables
            interpolated = context.interpolate_string(value)
            
            # If interpolation changed the value, we got a variable value
            if interpolated != value:
                # For string operators (contains, matches), don't evaluate arithmetic
                if self.operator in [ConditionOperator.CONTAINS, ConditionOperator.MATCHES]:
                    return interpolated
                    
                # Try to evaluate the result
                try:
                    # Handle special string comparisons
                    if interpolated.startswith('"') and interpolated.endswith('"'):
                        return interpolated[1:-1]
                    elif interpolated.startswith("'") and interpolated.endswith("'"):
                        return interpolated[1:-1]
                    else:
                        # Don't evaluate arithmetic on strings that look like phone numbers, etc
                        if isinstance(interpolated, str) and any(c in interpolated for c in '- /.'):
                            return interpolated
                        # Handle boolean comparison - convert Python bool representations to lowercase
                        if interpolated in ['True', 'False']:
                            return interpolated.lower()
                        result = context.evaluate_expression(interpolated)
                        return result if result is not None else interpolated
                except:
                    return interpolated
            
            # Check if it's a quoted string
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                return value[1:-1]
            
            # For literals, return as-is without evaluation
            return value
        else:
            return value


class ConditionParser:
    """Parse condition expressions into an AST."""
    
    def __init__(self):
        self.operators = {
            'and': ConditionOperator.AND,
            'or': ConditionOperator.OR,
            'not': ConditionOperator.NOT,
            '==': ConditionOperator.EQUALS,
            '!=': ConditionOperator.NOT_EQUALS,
            '>': ConditionOperator.GREATER_THAN,
            '<': ConditionOperator.LESS_THAN,
            '>=': ConditionOperator.GREATER_EQUAL,
            '<=': ConditionOperator.LESS_EQUAL,
            'in': ConditionOperator.IN,
            'not in': ConditionOperator.NOT_IN,
            'contains': ConditionOperator.CONTAINS,
            'matches': ConditionOperator.MATCHES,
        }
        # Order matters for parsing - longest first
        self.ordered_operators = sorted(self.operators.items(), key=lambda x: -len(x[0]))
    
    def parse(self, expression: str) -> ConditionNode:
        """Parse a condition expression into an AST."""
        # Remove extra whitespace
        expression = ' '.join(expression.split())
        
        # Handle special cases
        if expression.lower() == 'true':
            return ConditionNode(operator=ConditionOperator.TRUE)
        elif expression.lower() == 'false':
            return ConditionNode(operator=ConditionOperator.FALSE)
        
        # Parse the expression
        return self._parse_or(expression)
    
    def _parse_or(self, expression: str) -> ConditionNode:
        """Parse OR expressions."""
        # Split on ' or ' not inside quotes or parentheses
        parts = self._split_on_operator(expression, ' or ')
        
        if len(parts) == 1:
            return self._parse_and(parts[0])
        
        # Build OR tree
        left = self._parse_and(parts[0])
        for part in parts[1:]:
            right = self._parse_and(part)
            left = ConditionNode(operator=ConditionOperator.OR, left=left, right=right)
        
        return left
    
    def _parse_and(self, expression: str) -> ConditionNode:
        """Parse AND expressions."""
        # Split on ' and ' not inside quotes or parentheses
        parts = self._split_on_operator(expression, ' and ')
        
        if len(parts) == 1:
            return self._parse_not(parts[0])
        
        # Build AND tree
        left = self._parse_not(parts[0])
        for part in parts[1:]:
            right = self._parse_not(part)
            left = ConditionNode(operator=ConditionOperator.AND, left=left, right=right)
        
        return left
    
    def _parse_not(self, expression: str) -> ConditionNode:
        """Parse NOT expressions."""
        expression = expression.strip()
        
        if expression.startswith('not '):
            inner = expression[4:].strip()
            if inner.startswith('(') and inner.endswith(')'):
                inner = inner[1:-1]
            return ConditionNode(operator=ConditionOperator.NOT, left=self._parse_or(inner))
        
        return self._parse_comparison(expression)
    
    def _parse_comparison(self, expression: str) -> ConditionNode:
        """Parse comparison expressions."""
        # Check for comparison operators
        for op_text, op_enum in self.ordered_operators:
            if op_text in ['and', 'or', 'not']:  # Skip logical operators
                continue
            
            parts = self._split_on_operator(expression, op_text)
            if len(parts) == 2:
                return ConditionNode(
                    operator=op_enum,
                    left=parts[0].strip(),
                    right=parts[1].strip()
                )
        
        # Handle parentheses
        if expression.startswith('(') and expression.endswith(')'):
            return self._parse_or(expression[1:-1])
        
        # Return as a simple value/expression
        return ConditionNode(value=expression)
    
    def _split_on_operator(self, expression: str, operator: str) -> List[str]:
        """Split expression on operator, respecting quotes and parentheses."""
        parts = []
        current = ""
        quote_char = None
        paren_count = 0
        i = 0
        
        while i < len(expression):
            char = expression[i]
            
            # Handle quotes
            if char in ['"', "'"] and paren_count == 0:
                if quote_char is None:
                    quote_char = char
                elif quote_char == char:
                    quote_char = None
            
            # Handle parentheses
            elif char == '(' and quote_char is None:
                paren_count += 1
            elif char == ')' and quote_char is None:
                paren_count -= 1
            
            # Check for operator
            if (quote_char is None and paren_count == 0 and 
                expression[i:i+len(operator)] == operator):
                # Special handling for 'not in' to avoid splitting on 'not'
                if operator == 'not' and i + 3 < len(expression) and expression[i:i+6] == 'not in':
                    current += char
                    i += 1
                    continue
                    
                parts.append(current)
                current = ""
                i += len(operator)
                continue
            
            current += char
            i += 1
        
        if current:
            parts.append(current)
        
        return parts if parts else [expression]


class ConditionalStep:
    """A conditional step that can contain multiple conditions and actions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.conditions = []
        self.then_steps = []
        self.else_steps = []
        
        # Parse configuration
        if 'if' in config:
            self.conditions.append(config['if'])
        elif 'when' in config:
            self.conditions.append(config['when'])
        
        # Parse then/else blocks
        if 'then' in config:
            self.then_steps = config['then'] if isinstance(config['then'], list) else [config['then']]
        
        if 'else' in config:
            self.else_steps = config['else'] if isinstance(config['else'], list) else [config['else']]
    
    def evaluate(self, context: WorkflowContext) -> bool:
        """Evaluate if this conditional step should execute."""
        parser = ConditionParser()
        
        for condition in self.conditions:
            if isinstance(condition, str):
                node = parser.parse(condition)
                if not node.evaluate(context):
                    return False
            elif isinstance(condition, dict):
                # Complex condition with multiple parts
                for key, value in condition.items():
                    expr = f"{key} == {value}"
                    node = parser.parse(expr)
                    if not node.evaluate(context):
                        return False
        
        return True
    
    def get_steps_to_execute(self, context: WorkflowContext) -> List[Dict[str, Any]]:
        """Get the steps to execute based on condition evaluation."""
        if self.evaluate(context):
            return self.then_steps
        else:
            return self.else_steps


def evaluate_condition(condition: Union[str, Dict[str, Any]], context: WorkflowContext) -> bool:
    """Evaluate a condition expression."""
    if isinstance(condition, str):
        parser = ConditionParser()
        node = parser.parse(condition)
        return node.evaluate(context)
    elif isinstance(condition, dict):
        # Dictionary-based conditions (all must be true)
        for key, value in condition.items():
            if key == 'all':
                # All conditions must be true
                for sub_condition in value:
                    if not evaluate_condition(sub_condition, context):
                        return False
                return True
            elif key == 'any':
                # Any condition must be true
                for sub_condition in value:
                    if evaluate_condition(sub_condition, context):
                        return True
                return False
            elif key == 'not':
                # Negate the condition
                return not evaluate_condition(value, context)
            else:
                # Key-value comparison
                actual_value = context.resolve_variable(key)
                if actual_value != value:
                    return False
        return True
    else:
        # Boolean value
        return bool(condition)