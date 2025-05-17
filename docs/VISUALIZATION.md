# Feature Graph Visualization

## Overview

Velocitytree provides powerful visualization capabilities for your project's feature graph, allowing you to see at a glance:
- Feature dependencies and relationships
- Project progress and status
- Critical paths and bottlenecks
- Feature hierarchies and groupings

## Visualization Types

### 1. Static SVG

Generate scalable vector graphics that can be embedded in documentation:

```bash
vtree visualize graph --format svg --output project_graph.svg
```

### 2. Interactive HTML

Create interactive HTML visualizations with filtering and exploration capabilities:

```bash
vtree visualize graph --format html --output project_graph.html
```

Features:
- Click nodes to highlight dependencies
- Filter by status (completed, in progress, blocked, planned)
- Hover for feature details
- Zoom and pan support

## Command Line Usage

### Basic Visualization

Generate a visualization with default settings:

```bash
vtree visualize graph
```

This creates an HTML file named `{project_id}_graph.html` in the current directory.

### Advanced Options

```bash
vtree visualize graph \
  --output my_graph.html \
  --format html \
  --layout hierarchical \
  --title "My Project Features" \
  --interactive
```

Options:
- `--output, -o`: Output file path
- `--format, -f`: Output format (svg, html)
- `--layout, -l`: Layout algorithm (hierarchical, spring, circular)
- `--title, -t`: Visualization title
- `--interactive/--static`: Enable/disable interactive features

### Visualizing Planning Sessions

Visualize a specific planning session:

```bash
vtree visualize graph --session <session_id>
```

### Dependency Tree View

Show dependencies for a specific feature:

```bash
vtree visualize dependencies api --depth 3 --format tree
```

Output:
```
Feature: API (api)
Status: in_progress

Dependencies:
└── Authentication (auth)
    └── Database (db)

Dependents:
├── Dashboard (dashboard)
│   └── Admin Panel (admin)
└── Reports (reports)
```

## Layout Algorithms

### Hierarchical Layout

Best for projects with clear dependency chains:
- Features arranged in levels
- Dependencies flow from top to bottom
- Clear parent-child relationships

```bash
vtree visualize graph --layout hierarchical
```

### Spring Layout

Force-directed layout for complex relationships:
- Natural clustering of related features
- Good for detecting feature groups
- Handles circular dependencies well

```bash
vtree visualize graph --layout spring
```

### Circular Layout

Features arranged in a circle:
- Equal visual importance to all features
- Clear view of all relationships
- Good for smaller projects

```bash
vtree visualize graph --layout circular
```

## Visual Elements

### Node Colors by Status

- 🟢 **Green**: Completed features
- 🔵 **Blue**: In-progress features
- 🔴 **Red**: Blocked features
- 🔸 **Gray**: Planned features
- ⚫ **Dark Gray**: Cancelled features

### Node Shapes by Type

- **Rectangle**: Milestones
- **Circle**: Features, tasks, epics

### Relationship Lines

- **Solid**: Direct relationships (parent-child, implements)
- **Dashed**: Soft relationships (related-to, blocks)
- **Thickness**: Relationship strength (critical > strong > normal > weak)

### Line Colors by Type

- **Black**: Dependencies
- **Red**: Blocking relationships
- **Blue**: Related features
- **Green**: Parent-child relationships
- **Purple**: Inclusion relationships

## Interactive Features

### Node Interaction

Click on any node to:
- Highlight all connected features
- Show feature details panel
- Dim unrelated features
- View dependency chains

### Filtering

Use control buttons to:
- Show only completed features
- Show only in-progress features
- Show only blocked features
- Reset to show all features

### Information Panel

Toggle the info panel to see:
- Project progress statistics
- Feature counts by status
- Legend for colors and shapes
- Selected feature details

## Integration with Development Workflow

### 1. Planning Phase

Visualize your project plan:

```bash
# Start planning session
vtree plan start --name "New Feature"

# Generate visualization
vtree visualize graph --session <session_id>
```

### 2. Development Phase

Track progress during development:

```bash
# Update feature status
vtree feature update auth --status completed

# Regenerate visualization
vtree visualize graph
```

### 3. Review Phase

Analyze dependencies before release:

```bash
# Check what depends on API
vtree visualize dependencies api

# Generate report
vtree visualize graph --output release_status.html
```

## Advanced Usage

### Custom Graph Creation

```python
from velocitytree.feature_graph import FeatureGraph, FeatureNode
from velocitytree.visualization import FeatureGraphVisualizer

# Create graph
graph = FeatureGraph("my_project")

# Add features
auth = FeatureNode(
    id="auth",
    name="Authentication",
    type="feature",
    status="completed"
)
graph.add_feature(auth)

# Add more features...

# Create visualizer
viz = FeatureGraphVisualizer(graph, layout="hierarchical")

# Generate HTML
viz.generate_html(
    output_path="custom_graph.html",
    title="My Custom Graph",
    interactive=True
)
```

### Embedding in Documentation

Generate SVG for embedding:

```bash
vtree visualize graph --format svg --output docs/architecture.svg
```

Then in your Markdown:

```markdown
## System Architecture

![Feature Graph](architecture.svg)
```

### Automated Visualization

Add to CI/CD pipeline:

```yaml
- name: Generate Feature Graph
  run: |
    vtree visualize graph \
      --output artifacts/feature_graph.html \
      --title "Build #${{ github.run_number }}"
```

## Best Practices

1. **Regular Updates**: Generate visualizations after major changes
2. **Status Accuracy**: Keep feature statuses up-to-date
3. **Clear Relationships**: Use appropriate relationship types
4. **Meaningful Names**: Use descriptive feature names
5. **Proper Grouping**: Use milestones to group related features

## Troubleshooting

### Large Graphs

For projects with many features:
- Use hierarchical layout for better organization
- Filter by status to focus on relevant features
- Increase output size for better readability

### Circular Dependencies

If you see warnings about circular dependencies:
- The visualizer will use spring layout automatically
- Review your dependencies to resolve cycles
- Use the validation command to identify issues

### Performance

For very large graphs:
- Generate SVG instead of interactive HTML
- Use filtering to reduce displayed nodes
- Consider breaking into sub-graphs by milestone

## Conclusion

Feature graph visualization provides immediate insight into your project structure, making it easier to:
- Understand dependencies
- Track progress
- Identify bottlenecks
- Communicate project status

Use it regularly throughout your development cycle for better project visibility and management.