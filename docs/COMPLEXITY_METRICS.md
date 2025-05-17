# Complexity Metrics Documentation

VelocityTree provides comprehensive code complexity analysis to help developers understand and improve code quality.

## Metrics Overview

### Cyclomatic Complexity
Measures the number of linearly independent paths through code:
- Formula: M = E - N + 2P (edges - nodes + 2*components)
- Simplified: Count decision points + 1
- Thresholds:
  - 1-10: Simple, low risk
  - 11-20: Complex, moderate risk
  - 21-50: Very complex, high risk
  - 50+: Extremely complex, very high risk

### Cognitive Complexity
Measures how difficult code is to understand:
- Considers nesting depth
- Penalizes complex control flow
- Better reflects human comprehension
- Increases with:
  - Nested conditions
  - Multiple boolean operators
  - Complex loops
  - Exception handling

### Halstead Metrics
Software science metrics based on operators and operands:
- **n1**: Number of distinct operators
- **n2**: Number of distinct operands
- **N1**: Total number of operators
- **N2**: Total number of operands
- **Vocabulary**: n1 + n2
- **Length**: N1 + N2
- **Volume**: N * log2(n)
- **Difficulty**: (n1/2) * (N2/n2)
- **Effort**: D * V
- **Time**: E / 18 (seconds)
- **Bugs**: V / 3000 (estimated)

### Maintainability Index
Composite metric (0-100) indicating how maintainable code is:
- Formula: MI = 171 - 5.2*ln(HV) - 0.23*CC - 16.2*ln(LOC)
- Adjusted for comments: MI + 50*sin(sqrt(2.4*CM))
- Thresholds:
  - 85-100: Good maintainability
  - 65-85: Moderate maintainability
  - <65: Poor maintainability

## Usage

### Command Line

```bash
# Show metrics in analysis
vtree analyze src/ --show-metrics

# Focus on complexity
vtree analyze src/ --metric complexity

# Set thresholds
vtree analyze src/ --max-complexity 10
```

### API Usage

```python
from velocitytree.code_analysis import CodeAnalyzer
from velocitytree.code_analysis.metrics import ComplexityCalculator

# Analyze file metrics
analyzer = CodeAnalyzer()
result = analyzer.analyze_file("example.py")

# Access metrics
metrics = result.metrics
print(f"Cyclomatic Complexity: {metrics.cyclomatic_complexity}")
print(f"Cognitive Complexity: {metrics.cognitive_complexity}")
print(f"Maintainability Index: {metrics.maintainability_index}")

# Calculate specific metrics
calculator = ComplexityCalculator()
import ast
tree = ast.parse(code)

# Halstead metrics
halstead = calculator.calculate_halstead_metrics(tree)
print(f"Halstead Volume: {halstead.volume}")
print(f"Halstead Difficulty: {halstead.difficulty}")
print(f"Estimated Bugs: {halstead.bugs}")
```

## Metric Details

### Lines of Code (LOC)
- Physical lines with code
- Excludes blank lines and comments
- Used in other calculations

### Comment Metrics
- Lines of comments
- Comment ratio
- Docstring coverage
- Impacts maintainability

### Function Metrics
- Average function length
- Maximum function length
- Function count
- Method count

### Technical Debt
- Ratio based on complexity and size
- Indicates refactoring needs
- 0.0 (low) to 1.0 (high)

### Duplicate Code
- Estimated duplicate lines
- Copy-paste indicators
- Refactoring opportunities

## Advanced Analysis

### Per-Function Metrics

```python
for func in module.functions:
    print(f"{func.name}:")
    print(f"  Complexity: {func.complexity}")
    print(f"  Lines: {func.location.line_end - func.location.line_start}")
    print(f"  Parameters: {len(func.parameters)}")
```

### Class-Level Metrics

```python
for cls in module.classes:
    method_count = len(cls.methods)
    total_complexity = sum(m.complexity for m in cls.methods)
    print(f"{cls.name}:")
    print(f"  Methods: {method_count}")
    print(f"  Average Complexity: {total_complexity/method_count}")
```

### Trend Analysis

```python
# Track metrics over time
history = []
for commit in repo.iter_commits():
    result = analyzer.analyze_directory(".")
    history.append({
        "date": commit.committed_date,
        "complexity": result.aggregate_metrics.cyclomatic_complexity,
        "maintainability": result.aggregate_metrics.maintainability_index
    })
```

## Best Practices

### Reducing Cyclomatic Complexity
1. Extract complex conditions
2. Use early returns
3. Replace conditionals with polymorphism
4. Simplify boolean expressions

### Improving Cognitive Complexity
1. Reduce nesting levels
2. Extract nested logic
3. Use guard clauses
4. Simplify control flow

### Enhancing Maintainability
1. Add documentation
2. Reduce function length
3. Decrease complexity
4. Increase test coverage

## Configuration

### Metric Thresholds

```yaml
# .velocitytree/metrics.yaml
thresholds:
  cyclomatic_complexity:
    warning: 10
    error: 20
  
  cognitive_complexity:
    warning: 15
    error: 30
    
  maintainability_index:
    warning: 65
    error: 50
    
  function_length:
    warning: 50
    error: 100
    
  class_size:
    warning: 500
    error: 1000
```

### Custom Calculations

```python
class CustomMetricsCalculator(ComplexityCalculator):
    def calculate_custom_metric(self, node):
        # Your custom metric logic
        return custom_value
```

## Integration

### CI/CD Pipeline

```yaml
# GitHub Actions
- name: Check Complexity
  run: |
    vtree analyze src/ --max-complexity 15
    if [ $? -ne 0 ]; then
      echo "Complexity threshold exceeded"
      exit 1
    fi
```

### Pre-commit Hook

```bash
#!/bin/sh
# .git/hooks/pre-commit
vtree analyze --staged --metric complexity --max-complexity 10
```

### IDE Integration

```json
// VS Code settings
{
  "velocitytree.metrics.showInline": true,
  "velocitytree.metrics.complexity.threshold": 10
}
```

## Visualization

### Metric Reports

```bash
# Generate HTML report
vtree analyze src/ --format html --output metrics.html

# Generate CSV for analysis
vtree analyze src/ --format csv --output metrics.csv
```

### Complexity Graphs

```python
import matplotlib.pyplot as plt

# Plot complexity distribution
complexities = [f.complexity for f in all_functions]
plt.hist(complexities, bins=20)
plt.xlabel('Cyclomatic Complexity')
plt.ylabel('Number of Functions')
plt.title('Complexity Distribution')
plt.show()
```

## Troubleshooting

### High Complexity
- Break down large functions
- Extract helper methods
- Simplify conditionals
- Use design patterns

### Low Maintainability
- Add documentation
- Reduce complexity
- Improve naming
- Increase modularity

### Performance
- Cache metric calculations
- Analyze incrementally
- Use parallel processing
- Limit analysis scope