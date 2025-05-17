# Pattern Detection Documentation

VelocityTree's code analysis includes sophisticated pattern detection to identify design patterns, anti-patterns, and code smells in your codebase.

## Supported Patterns

### Design Patterns

#### Singleton
Detects classes implementing the singleton pattern:
- Classes with `_instance` or `__instance` attributes
- `getInstance()` or similar methods
- `__new__` method overrides for singleton behavior

#### Factory
Identifies factory pattern implementations:
- Classes with `create`, `make`, or `build` methods
- Methods that return instances of other classes
- Abstract factory patterns

#### Observer
Recognizes observer/subscriber patterns:
- Classes with observer/listener lists
- `notify`, `publish`, or `emit` methods
- `subscribe`, `attach`, or `register` methods

#### Strategy
Detects strategy pattern usage:
- Abstract base classes with multiple implementations
- Context classes that use strategy objects
- Runtime algorithm selection

#### Decorator
Identifies both types of decorators:
- Python function decorators (`@decorator`)
- Structural decorator pattern in classes
- Classes that wrap other objects

### Anti-Patterns

#### God Class
Classes that do too much:
- Excessive number of methods (>20)
- Too many attributes (>15)
- Very long class definitions (>500 lines)

#### Spaghetti Code
Overly complex code structure:
- High cyclomatic complexity (>15)
- Deep nesting levels (>4)
- Tangled control flow

#### Long Parameter List
Functions with too many parameters:
- More than 5 parameters
- Suggests need for parameter objects

### Code Smells

#### Duplicate Code
Similar code in multiple locations:
- Functionally equivalent code blocks
- Copy-paste programming
- Missing abstraction opportunities

#### Magic Numbers
Hard-coded numeric values:
- Numbers without clear meaning
- Should be named constants
- Excludes common values (0, 1, 2)

#### Feature Envy
Methods that use other objects more than their own:
- Excessive access to other object's data
- Suggests method belongs in different class

#### Data Clump
Groups of data that travel together:
- Same parameters in multiple methods
- Suggests need for data class

## Usage

### Command Line

```bash
# Analyze with pattern detection
vtree analyze src/ --show-patterns

# Filter by pattern type
vtree analyze src/ --pattern-type design_pattern
vtree analyze src/ --pattern-type anti_pattern
vtree analyze src/ --pattern-type code_smell

# Show specific patterns
vtree analyze src/ --pattern "God Class"
```

### API Usage

```python
from velocitytree.code_analysis import CodeAnalyzer

analyzer = CodeAnalyzer()
result = analyzer.analyze_file("example.py")

# Get all patterns
for pattern in result.patterns:
    print(f"{pattern.name}: {pattern.description}")
    print(f"Confidence: {pattern.confidence}")
    print(f"Location: {pattern.location.file_path}:{pattern.location.line_start}")

# Filter by pattern type
design_patterns = [p for p in result.patterns 
                  if p.pattern_type == PatternType.DESIGN_PATTERN]

anti_patterns = [p for p in result.patterns 
                if p.pattern_type == PatternType.ANTI_PATTERN]

code_smells = [p for p in result.patterns 
              if p.pattern_type == PatternType.CODE_SMELL]
```

## Pattern Details

### Confidence Scores

Each detected pattern has a confidence score (0.0 to 1.0):
- 0.9+ : Very high confidence
- 0.7-0.9 : High confidence  
- 0.5-0.7 : Medium confidence
- <0.5 : Low confidence

### Metadata

Patterns include metadata with additional information:
- Method/attribute counts
- Parameter lists
- Related classes
- Violation details

### Custom Patterns

Add custom pattern detectors:

```python
from velocitytree.code_analysis.patterns import PatternDetector

class MyCustomPattern(PatternDetector):
    def detect(self, module_analysis, content):
        patterns = []
        # Custom detection logic
        return patterns

# Register the pattern
from velocitytree.code_analysis.patterns import pattern_registry
pattern_registry.register(PatternDefinition(
    name="Custom Pattern",
    pattern_type=PatternType.CODE_SMELL,
    languages=[LanguageSupport.PYTHON],
    detector=MyCustomPattern()
))
```

## Best Practices

### Design Patterns
- Use patterns appropriately, not everywhere
- Document pattern usage
- Consider simpler solutions first

### Anti-Pattern Resolution
- Refactor god classes into smaller units
- Simplify complex methods
- Extract parameter objects

### Code Smell Fixes
- Extract constants for magic numbers
- Create data classes for data clumps
- Move methods to appropriate classes
- Extract common code into shared functions

## Configuration

Configure pattern detection in `.velocitytree/analysis.yaml`:

```yaml
patterns:
  enabled: true
  confidence_threshold: 0.7
  
  design_patterns:
    detect: true
    include:
      - Singleton
      - Factory
      - Observer
    
  anti_patterns:
    detect: true
    thresholds:
      god_class_methods: 20
      god_class_attributes: 15
      complexity_threshold: 15
  
  code_smells:
    detect: true
    ignore:
      - "tests/**"  # Don't check test files
```

## Integration

### Pull Request Comments

```yaml
# GitHub Actions
- name: Pattern Analysis
  run: |
    vtree analyze src/ --format json > patterns.json
    # Post patterns as PR comments
```

### IDE Integration

```json
// VS Code settings
{
  "velocitytree.patterns.showInline": true,
  "velocitytree.patterns.minConfidence": 0.7
}
```

## Troubleshooting

### False Positives
- Adjust confidence thresholds
- Add pattern-specific ignores
- Fine-tune detection parameters

### Performance
- Limit pattern detection to specific types
- Use caching for large codebases
- Run pattern detection separately

### Language Support
- Currently supports Python fully
- JavaScript/TypeScript support in progress
- Extensible to other languages