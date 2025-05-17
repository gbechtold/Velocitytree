"""Workflow condition evaluation for Velocitytree."""

import ast
import re
from typing import Any, Union, List, Optional
from enum import Enum, auto

from .workflow_context import WorkflowContext


class ConditionOperator(Enum):
    """Supported condition operators."""
    AND = auto()
    OR = auto()
    NOT = auto()
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    IN = auto()
    NOT_IN = auto()
    MATCHES = auto()
    CONTAINS = auto()
    VALUE = auto()


class ConditionNode:
    """A node in the condition AST."""
    def __init__(self, operator: ConditionOperator, 
                 left: Optional['ConditionNode'] = None,
                 right: Optional['ConditionNode'] = None,
                 value: Any = None):
        self.operator = operator
        self.left = left
        self.right = right
        self.value = value


class ConditionParser:
    """Parses condition strings into an AST."""
    
    # Operator mapping
    OPERATORS = {
        'and': ConditionOperator.AND,
        '&&': ConditionOperator.AND,
        'or': ConditionOperator.OR,
        '||': ConditionOperator.OR,
        'not': ConditionOperator.NOT,
        '!': ConditionOperator.NOT,
        '==': ConditionOperator.EQ,
        '!=': ConditionOperator.NE,
        '<': ConditionOperator.LT,
        '<=': ConditionOperator.LE,
        '>': ConditionOperator.GT,
        '>=': ConditionOperator.GE,
        'in': ConditionOperator.IN,
        'not in': ConditionOperator.NOT_IN,
        'matches': ConditionOperator.MATCHES,
        'contains': ConditionOperator.CONTAINS,
    }
    
    def parse(self, condition: str) -> ConditionNode:
        """Parse a condition string into an AST."""
        # Pre-process the condition
        condition = self._preprocess_condition(condition)
        
        # Try to parse as Python expression
        try:
            tree = ast.parse(condition, mode='eval')
            return self._ast_to_condition_node(tree.body)
        except SyntaxError:
            # Fall back to simple parsing for basic conditions
            return self._parse_simple_condition(condition)
    
    def _preprocess_condition(self, condition: str) -> str:
        """Pre-process condition string for parsing."""
        # Replace 'not in' with a temporary placeholder to avoid parsing issues
        condition = condition.replace('not in', '__NOT_IN__')
        
        # Replace logical operators with Python equivalents
        replacements = {
            '&&': ' and ',
            '||': ' or ',
            '!': ' not ',
        }
        
        for old, new in replacements.items():
            condition = condition.replace(old, new)
        
        # Replace the placeholder back
        condition = condition.replace('__NOT_IN__', 'not in')
        
        return condition
    
    def _ast_to_condition_node(self, node: ast.expr) -> ConditionNode:
        """Convert Python AST node to ConditionNode."""
        if isinstance(node, ast.BoolOp):
            # Boolean operations (and, or)
            if isinstance(node.op, ast.And):
                op = ConditionOperator.AND
            elif isinstance(node.op, ast.Or):
                op = ConditionOperator.OR
            else:
                raise ValueError(f"Unsupported boolean operator: {node.op}")
            
            # Create a tree from the values
            result = self._ast_to_condition_node(node.values[0])
            for value in node.values[1:]:
                result = ConditionNode(
                    operator=op,
                    left=result,
                    right=self._ast_to_condition_node(value)
                )
            return result
        
        elif isinstance(node, ast.UnaryOp):
            # Unary operations (not)
            if isinstance(node.op, ast.Not):
                return ConditionNode(
                    operator=ConditionOperator.NOT,
                    left=self._ast_to_condition_node(node.operand)
                )
            else:
                raise ValueError(f"Unsupported unary operator: {node.op}")
        
        elif isinstance(node, ast.Compare):
            # Comparison operations
            left = self._ast_to_condition_node(node.left)
            
            for i, (op, right_node) in enumerate(zip(node.ops, node.comparators)):
                right = self._ast_to_condition_node(right_node)
                
                if isinstance(op, ast.Eq):
                    op_type = ConditionOperator.EQ
                elif isinstance(op, ast.NotEq):
                    op_type = ConditionOperator.NE
                elif isinstance(op, ast.Lt):
                    op_type = ConditionOperator.LT
                elif isinstance(op, ast.LtE):
                    op_type = ConditionOperator.LE
                elif isinstance(op, ast.Gt):
                    op_type = ConditionOperator.GT
                elif isinstance(op, ast.GtE):
                    op_type = ConditionOperator.GE
                elif isinstance(op, ast.In):
                    op_type = ConditionOperator.IN
                elif isinstance(op, ast.NotIn):
                    op_type = ConditionOperator.NOT_IN
                else:
                    raise ValueError(f"Unsupported comparison operator: {op}")
                
                result = ConditionNode(operator=op_type, left=left, right=right)
                
                # Chain multiple comparisons
                if i < len(node.ops) - 1:
                    left = right
                    result = ConditionNode(
                        operator=ConditionOperator.AND,
                        left=result,
                        right=None  # Will be set in next iteration
                    )
            
            return result
        
        elif isinstance(node, ast.Name):
            # Variable reference
            return ConditionNode(operator=ConditionOperator.VALUE, value=node.id)
        
        elif isinstance(node, ast.Constant):
            # Literal value
            return ConditionNode(operator=ConditionOperator.VALUE, value=node.value)
        
        elif isinstance(node, ast.Attribute):
            # Attribute access (e.g., obj.attr)
            obj = self._ast_to_condition_node(node.value)
            return ConditionNode(
                operator=ConditionOperator.VALUE,
                value=f"{obj.value}.{node.attr}"
            )
        
        elif isinstance(node, ast.BinOp):
            # Binary operations (for arithmetic if needed)
            left = self._ast_to_condition_node(node.left)
            right = self._ast_to_condition_node(node.right)
            # For now, just return the left value (simplified)
            return left
        
        else:
            raise ValueError(f"Unsupported AST node type: {type(node)}")
    
    def _parse_simple_condition(self, condition: str) -> ConditionNode:
        """Parse simple conditions that don't parse as Python expressions."""
        # Handle custom operators like 'matches' and 'contains'
        patterns = [
            (r'(.+?)\s+matches\s+["\'](.+?)["\']', ConditionOperator.MATCHES),
            (r'(.+?)\s+contains\s+(.+)', ConditionOperator.CONTAINS),
        ]
        
        for pattern, op in patterns:
            match = re.match(pattern, condition.strip())
            if match:
                left_val = match.group(1).strip()
                right_val = match.group(2).strip()
                
                left = ConditionNode(operator=ConditionOperator.VALUE, value=left_val)
                right = ConditionNode(operator=ConditionOperator.VALUE, value=right_val)
                
                return ConditionNode(operator=op, left=left, right=right)
        
        # Fall back to treating the whole thing as a value
        return ConditionNode(operator=ConditionOperator.VALUE, value=condition)


class ConditionEvaluator:
    """Evaluates condition ASTs against a context."""
    
    def __init__(self, context: WorkflowContext):
        self.context = context
    
    def evaluate(self, node: ConditionNode) -> Any:
        """Evaluate a condition node."""
        if node.operator == ConditionOperator.VALUE:
            return self._resolve_value(node.value)
        
        elif node.operator == ConditionOperator.AND:
            left_result = self.evaluate(node.left)
            # Short-circuit evaluation
            if not left_result:
                return False
            return bool(self.evaluate(node.right))
        
        elif node.operator == ConditionOperator.OR:
            left_result = self.evaluate(node.left)
            # Short-circuit evaluation
            if left_result:
                return True
            return bool(self.evaluate(node.right))
        
        elif node.operator == ConditionOperator.NOT:
            return not self.evaluate(node.left)
        
        # Binary operators
        left = self.evaluate(node.left)
        right = self.evaluate(node.right)
        
        if node.operator == ConditionOperator.EQ:
            return self._compare_values(left, right, lambda a, b: a == b)
        elif node.operator == ConditionOperator.NE:
            return self._compare_values(left, right, lambda a, b: a != b)
        elif node.operator == ConditionOperator.LT:
            return self._compare_values(left, right, lambda a, b: a < b)
        elif node.operator == ConditionOperator.LE:
            return self._compare_values(left, right, lambda a, b: a <= b)
        elif node.operator == ConditionOperator.GT:
            return self._compare_values(left, right, lambda a, b: a > b)
        elif node.operator == ConditionOperator.GE:
            return self._compare_values(left, right, lambda a, b: a >= b)
        elif node.operator == ConditionOperator.IN:
            return left in right
        elif node.operator == ConditionOperator.NOT_IN:
            return left not in right
        elif node.operator == ConditionOperator.MATCHES:
            # Regex matching
            import re
            pattern = str(right)
            text = str(left)
            return bool(re.match(pattern, text))
        elif node.operator == ConditionOperator.CONTAINS:
            return str(right) in str(left)
        else:
            raise ValueError(f"Unknown operator: {node.operator}")
    
    def _resolve_value(self, value: Any) -> Any:
        """Resolve a value from the context."""
        if isinstance(value, str):
            # Check if it's a template variable
            if value.startswith('{{') and value.endswith('}}'):
                return self.context.interpolate_string(value)
            
            # Check if it's a variable path (e.g., "steps.previous.status")
            if '.' in value:
                parts = value.split('.')
                current = None
                
                # Start from context globals or steps
                if parts[0] == 'steps':
                    current = self.context.step_outputs
                    parts = parts[1:]
                elif parts[0] == 'workflow':
                    current = self.context.workflow_metadata
                    parts = parts[1:]
                else:
                    # Try to get from global vars first
                    current = self.context.global_vars.get(parts[0])
                    if current is None:
                        # Try from step outputs
                        current = self.context.step_outputs.get(parts[0])
                    parts = parts[1:]
                
                # Navigate through the path
                for part in parts:
                    if current is None:
                        break
                    if isinstance(current, dict):
                        current = current.get(part)
                    else:
                        current = getattr(current, part, None)
                
                if current is not None:
                    return current
            
            # Try to resolve as a simple variable
            # First try string interpolation (for backward compatibility)
            interpolated = self.context.interpolate_string(f"{{{{{value}}}}}")
            if interpolated != f"{{{{{value}}}}}":
                return self._normalize_value(interpolated)
            
            # Then try direct lookup
            if value in self.context.global_vars:
                return self.context.global_vars[value]
            if value in self.context.step_outputs:
                return self.context.step_outputs[value]
            
            # Return the string value itself
            return self._normalize_value(value)
        
        return value
    
    def _normalize_value(self, value: str) -> Any:
        """Normalize string values to proper types."""
        # Handle boolean strings
        if value.lower() in ('true', 'yes', 'on'):
            return True
        elif value.lower() in ('false', 'no', 'off'):
            return False
        elif value.lower() in ('null', 'none'):
            return None
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        return value
    
    def _compare_values(self, left: Any, right: Any, comparator) -> bool:
        """Compare values with type coercion."""
        # If types match, compare directly
        if type(left) == type(right):
            return comparator(left, right)
        
        # Handle None comparisons
        if left is None or right is None:
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
        
        # Try string comparison
        try:
            left_str = str(left).lower()
            right_str = str(right).lower()
            
            # Special handling for boolean strings
            if left_str in ('true', 'false') or right_str in ('true', 'false'):
                left_bool = left_str == 'true' if left_str in ('true', 'false') else left
                right_bool = right_str == 'true' if right_str in ('true', 'false') else right
                return comparator(left_bool, right_bool)
            
            return comparator(left_str, right_str)
        except:
            pass
        
        # Fall back to string comparison
        return comparator(str(left), str(right))


def evaluate_condition(condition: str, context: WorkflowContext) -> bool:
    """Evaluate a condition string against a workflow context."""
    if not condition:
        return True
    
    # Simple boolean check
    if condition.lower() in ('true', 'yes', 'on'):
        return True
    elif condition.lower() in ('false', 'no', 'off'):
        return False
    
    # Parse and evaluate the condition
    parser = ConditionParser()
    evaluator = ConditionEvaluator(context)
    
    try:
        ast = parser.parse(condition)
        result = evaluator.evaluate(ast)
        return bool(result)
    except Exception as e:
        # Log error and return False on evaluation failure
        import logging
        logging.error(f"Error evaluating condition '{condition}': {e}")
        return False