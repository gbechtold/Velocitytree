# Feature Relationship Mapping

## Overview

The feature relationship mapping system in Velocitytree provides a comprehensive way to model complex relationships between features, milestones, and other project elements. This goes beyond simple parent-child and dependency relationships to capture the full spectrum of project interconnections.

## Relationship Types

### Core Relationships

1. **PARENT_CHILD**: Hierarchical relationship between features
   - Example: "User Management" → "User Authentication"
   - Used for breaking down larger features into sub-features

2. **DEPENDS_ON**: One feature requires another to function
   - Example: "Dashboard" depends on "Authentication"
   - Critical for determining build order and testing sequences

3. **BLOCKS**: One feature prevents progress on another
   - Example: "Legacy Migration" blocks "New Feature Development"
   - Helps identify bottlenecks in development

### Extended Relationships

4. **RELATED_TO**: Features that share common concerns
   - Example: "User Profile" related to "Settings Page"
   - Useful for grouping related work

5. **DUPLICATES**: Features that overlap significantly
   - Example: "Quick Search" duplicates "Advanced Search"
   - Helps identify redundant work

6. **IMPLEMENTS**: Feature implements a specification or interface
   - Example: "OAuth Login" implements "Authentication Interface"
   - Tracks implementation relationships

7. **INCLUDES**: Feature includes another as a component
   - Example: "Admin Panel" includes "User Management"
   - Shows composition relationships

8. **PRECEDES/FOLLOWS**: Temporal relationships
   - Example: "Database Migration" precedes "API Update"
   - Defines execution order

## Relationship Strength

Each relationship can have one of four strength levels:

- **CRITICAL**: Essential relationship, failure impacts project success
- **STRONG**: Important relationship, significant impact if broken
- **NORMAL**: Standard relationship, moderate impact
- **WEAK**: Optional relationship, minimal impact

## Usage Examples

### Adding Relationships

```python
from velocitytree.feature_graph import (
    FeatureGraph, RelationType, RelationshipStrength
)

# Create graph
graph = FeatureGraph("my_project")

# Add features
graph.add_feature(auth_feature)
graph.add_feature(dashboard_feature)

# Add a critical dependency
graph.add_relationship(
    source_id="dashboard",
    target_id="auth",
    relation_type=RelationType.DEPENDS_ON,
    strength=RelationshipStrength.CRITICAL,
    description="Dashboard requires user authentication",
    metadata={"security": "required"}
)

# Add a related feature
graph.add_relationship(
    source_id="profile",
    target_id="settings",
    relation_type=RelationType.RELATED_TO,
    strength=RelationshipStrength.NORMAL,
    description="Both handle user preferences"
)
```

### Querying Relationships

```python
# Get all relationships for a feature
relationships = graph.get_relationships("dashboard")

# Get only dependencies
dependencies = graph.get_relationships(
    "dashboard", 
    RelationType.DEPENDS_ON,
    direction="out"
)

# Find related features within 2 degrees
related = graph.get_related_features(
    "auth",
    relation_types=[RelationType.RELATED_TO, RelationType.DEPENDS_ON],
    max_depth=2
)
```

### Validating Relationships

```python
# Check for issues
errors = graph.validate_dependencies()
for error in errors:
    print(f"Issue found: {error}")

# Example errors:
# - Circular dependency: A → B → C → A
# - Conflicting relationships: A blocks B but B depends on A
# - Orphaned nodes with no relationships
```

### Relationship Matrix

```python
# Get a complete view of relationships
matrix = graph.get_relationship_matrix()

# Example output:
# {
#     "dashboard": {
#         "auth": ["depends_on"],
#         "api": ["depends_on", "includes"]
#     },
#     "profile": {
#         "settings": ["related_to"],
#         "auth": ["depends_on"]
#     }
# }
```

## Integration with Planning Sessions

The feature graph can be automatically built from a planning session:

```python
from velocitytree.planning_session import PlanningSession

# Create session and plan
session = PlanningSession(config)
session.start_session("My Project")
# ... develop plan ...

# Build graph from plan
graph = FeatureGraph("my_project")
graph.from_project_plan(session.project_plan)

# Enhance with additional relationships
graph.add_relationship(
    "milestone_core",
    "feature_auth",
    RelationType.INCLUDES,
    RelationshipStrength.STRONG
)
```

## Visualization Support

The relationship data can be exported for visualization tools:

```python
# Export for D3.js visualization
data = graph.to_dict()

# Access specific visualization data
nodes = data['features']
edges = data['relationships']

# Create custom visualizations
import matplotlib.pyplot as plt
import networkx as nx

# Convert to NetworkX for visualization
nx_graph = graph.get_feature_tree()
nx.draw(nx_graph, with_labels=True)
plt.show()
```

## Best Practices

1. **Use Appropriate Relationship Types**
   - Choose the most specific relationship type
   - Don't overuse RELATED_TO for everything

2. **Set Meaningful Strengths**
   - Mark critical paths appropriately
   - Use WEAK for nice-to-have connections

3. **Validate Regularly**
   - Check for circular dependencies
   - Identify conflicting relationships
   - Find orphaned nodes

4. **Document Relationships**
   - Always include descriptions
   - Use metadata for additional context
   - Keep relationship purposes clear

5. **Maintain Consistency**
   - Update relationships when features change
   - Remove obsolete relationships
   - Keep bidirectional relationships synchronized

## API Reference

### RelationType Enum
- `PARENT_CHILD`
- `DEPENDS_ON`
- `BLOCKS`
- `RELATED_TO`
- `DUPLICATES`
- `IMPLEMENTS`
- `INCLUDES`
- `PRECEDES`
- `FOLLOWS`

### RelationshipStrength Enum
- `CRITICAL`
- `STRONG`
- `NORMAL`
- `WEAK`

### Key Methods
- `add_relationship()`: Create a new relationship
- `get_relationships()`: Query existing relationships
- `remove_relationship()`: Delete a relationship
- `update_relationship()`: Modify relationship properties
- `get_related_features()`: Find connected features
- `get_relationship_matrix()`: Get complete relationship view
- `validate_dependencies()`: Check for relationship issues

## Conclusion

The feature relationship mapping system provides a rich model for capturing project complexity. By using appropriate relationship types and strengths, you can create a comprehensive map of your project's structure that aids in planning, development, and maintenance.