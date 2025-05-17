# Advanced Dependency Tracking

## Overview

Velocitytree provides comprehensive dependency tracking capabilities that go beyond simple dependency chains. The system analyzes relationships between features, validates dependency integrity, suggests optimal work order, and helps identify bottlenecks or issues in your project structure.

## Core Concepts

### Dependency Types

1. **Direct Dependencies**: Features that directly depend on each other
2. **Transitive Dependencies**: Dependencies inherited through a chain
3. **Blocking Relationships**: Features that prevent others from starting
4. **Weak Dependencies**: Optional dependencies that don't block progress

### Relationship Strengths

Dependencies can have different strengths that affect how they're evaluated:

- **CRITICAL**: Must be completed before dependent can start
- **STRONG**: Should be completed, but in-progress is acceptable
- **NORMAL**: Standard dependency, some flexibility allowed
- **WEAK**: Nice-to-have, doesn't block progress

## Key Features

### 1. Can Start Analysis

Before starting work on a feature, the system checks if all prerequisites are met:

```python
from velocitytree.feature_graph import FeatureGraph

graph = FeatureGraph("my_project")
# ... add features and dependencies ...

can_start, issues = graph.can_start_feature("new_feature")
if can_start:
    print("Feature can be started!")
else:
    print("Cannot start because:")
    for issue in issues:
        print(f"  - {issue}")
```

The system checks:
- All critical/strong dependencies are satisfied
- No features are blocking this one
- The feature isn't already in progress or completed

### 2. Recursive Dependency Analysis

Get all dependencies (direct and transitive) for a feature:

```python
# Get all dependencies recursively
all_deps = graph.get_all_dependencies("my_feature")
print(f"Total dependencies: {len(all_deps)}")

# Get only direct dependencies
direct_deps = graph.get_all_dependencies("my_feature", recursive=False)
print(f"Direct dependencies: {len(direct_deps)}")

# Get all features that depend on this one
dependents = graph.get_all_dependents("core_feature")
print(f"Features depending on this: {len(dependents)}")
```

### 3. Smart Feature Suggestions

The system can suggest which features to work on next based on:
- Dependency satisfaction
- Number of dependent features
- Relationship strengths
- Overall project impact

```python
suggestions = graph.get_suggested_next_features()

print("Suggested features to work on:")
for feature_id, details in suggestions[:5]:
    print(f"  {details['name']}")
    print(f"    Priority Score: {details['priority_score']}")
    print(f"    Blocks {details['dependent_count']} other features")
    print(f"    Depends on {details['dependency_count']} features")
    print()
```

### 4. Dependency Chain Analysis

Find all possible paths between two features:

```python
# Find all ways feature_a depends on feature_b
chains = graph.get_dependency_chain("feature_a", "feature_b")

for i, chain in enumerate(chains):
    print(f"Path {i + 1}: {' -> '.join(chain)}")
```

### 5. Enhanced Validation

The validation system detects various issues:

```python
errors = graph.validate_dependencies()

for error in errors:
    if error.startswith("WARNING:"):
        print(f"⚠️  {error}")
    else:
        print(f"❌ {error}")
```

Detected issues include:
- Circular dependencies
- Conflicting relationships (A blocks B, but B depends on A)
- Missing dependencies
- Orphaned features
- Deep dependency chains
- Weak dependencies on critical paths

## Practical Examples

### Example 1: Project Planning

```python
# Create a project with complex dependencies
graph = FeatureGraph("web_app")

# Add features
features = {
    "auth": FeatureNode(id="auth", name="Authentication", type="feature", status="completed"),
    "database": FeatureNode(id="database", name="Database Setup", type="feature", status="completed"),
    "api": FeatureNode(id="api", name="REST API", type="feature", status="in_progress"),
    "frontend": FeatureNode(id="frontend", name="React Frontend", type="feature", status="planned"),
    "admin": FeatureNode(id="admin", name="Admin Panel", type="feature", status="planned"),
}

for feature in features.values():
    graph.add_feature(feature)

# Define relationships
graph.add_relationship("api", "auth", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
graph.add_relationship("api", "database", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
graph.add_relationship("frontend", "api", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
graph.add_relationship("admin", "frontend", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
graph.add_relationship("admin", "api", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)

# Check what can be worked on
suggestions = graph.get_suggested_next_features()
for feature_id, details in suggestions:
    print(f"Can work on: {details['name']}")
```

### Example 2: Handling Blocked Features

```python
# Feature A is blocking Feature B
graph.add_relationship("feature_a", "feature_b", RelationType.BLOCKS)

# Check if B can start
can_start, issues = graph.can_start_feature("feature_b")
if not can_start:
    print("Feature B is blocked by:")
    for issue in issues:
        if "blocking" in issue:
            print(f"  - {issue}")

# Complete feature A
graph.update_feature_status("feature_a", "completed")

# Now check again
can_start, issues = graph.can_start_feature("feature_b")
print(f"Can start now: {can_start}")
```

### Example 3: Impact Analysis

```python
# See what would be affected if we remove or delay a feature
feature_to_analyze = "core_api"

# Get all dependents
all_dependents = graph.get_all_dependents(feature_to_analyze)
direct_dependents = graph.get_dependents(feature_to_analyze)

print(f"Impact of delaying {feature_to_analyze}:")
print(f"  - Directly affects: {len(direct_dependents)} features")
print(f"  - Total impact: {len(all_dependents)} features")

# List critical dependents
for dep_id in all_dependents:
    rel_key = (dep_id, feature_to_analyze)
    if rel_key in graph.relationships:
        rel = graph.relationships[rel_key]
        if rel.strength == RelationshipStrength.CRITICAL:
            print(f"  - CRITICAL: {graph.features[dep_id].name}")
```

## Best Practices

1. **Use Appropriate Relationship Strengths**
   - Mark truly critical dependencies as CRITICAL
   - Use STRONG for important but flexible dependencies
   - Reserve WEAK for nice-to-have relationships

2. **Regular Validation**
   ```python
   # Run validation after major changes
   errors = graph.validate_dependencies()
   if errors:
       print("Found issues:")
       for error in errors:
           print(f"  - {error}")
   ```

3. **Update Status Promptly**
   ```python
   # Update feature status as work progresses
   graph.update_feature_status("my_feature", "in_progress")
   # Dependencies are automatically checked and updated
   ```

4. **Analyze Before Major Decisions**
   ```python
   # Before starting a new feature
   can_start, issues = graph.can_start_feature("new_feature")
   
   # Before removing a feature
   dependents = graph.get_all_dependents("feature_to_remove")
   ```

5. **Monitor Dependency Depth**
   ```python
   # Check for overly complex dependency chains
   errors = graph.validate_dependencies()
   deep_chains = [e for e in errors if "deep dependency chain" in e.lower()]
   if deep_chains:
       print("Warning: Complex dependency chains detected")
   ```

## API Reference

### Key Methods

- `can_start_feature(feature_id)`: Check if a feature can be started
- `get_all_dependencies(feature_id, recursive=True)`: Get all dependencies
- `get_all_dependents(feature_id, recursive=True)`: Get all dependent features
- `get_suggested_next_features()`: Get prioritized list of features to work on
- `get_dependency_chain(from_id, to_id)`: Find paths between features
- `validate_dependencies()`: Comprehensive validation of graph integrity

### Return Types

- `can_start_feature`: Returns `(bool, List[str])` - can start flag and list of issues
- `get_suggested_next_features`: Returns `List[Tuple[str, Dict]]` - feature IDs with metadata
- `validate_dependencies`: Returns `List[str]` - errors and warnings

## Conclusion

Advanced dependency tracking in Velocitytree provides the intelligence needed to manage complex projects effectively. By understanding dependencies, detecting issues early, and suggesting optimal work order, it helps teams deliver projects more efficiently and with fewer surprises.