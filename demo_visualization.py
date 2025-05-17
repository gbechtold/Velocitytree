#!/usr/bin/env python3
"""Demo script to generate a sample visualization."""
from pathlib import Path
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType, RelationshipStrength
from velocitytree.visualization import FeatureGraphVisualizer


def create_demo_graph():
    """Create a demo feature graph."""
    graph = FeatureGraph("velocitytree_demo")
    
    # Add milestones
    milestones = [
        FeatureNode(id="m1", name="Core Features", type="milestone", 
                   status="completed", description="Basic functionality"),
        FeatureNode(id="m2", name="Advanced Features", type="milestone",
                   status="in_progress", description="Enhanced capabilities"),
        FeatureNode(id="m3", name="Future Vision", type="milestone",
                   status="planned", description="Long-term goals"),
    ]
    
    for milestone in milestones:
        graph.add_feature(milestone)
    
    # Add features
    features = [
        # Core features
        FeatureNode(id="auth", name="Authentication", type="feature",
                   status="completed", description="User authentication system"),
        FeatureNode(id="git", name="Git Integration", type="feature",
                   status="completed", description="Natural language git commands"),
        FeatureNode(id="planning", name="Planning Sessions", type="feature",
                   status="completed", description="Conversational project planning"),
        
        # Advanced features
        FeatureNode(id="graph", name="Feature Graphs", type="feature",
                   status="completed", description="Dependency visualization"),
        FeatureNode(id="ai", name="AI Assistant", type="feature",
                   status="in_progress", description="Smart code suggestions"),
        FeatureNode(id="plugins", name="Plugin System", type="feature",
                   status="in_progress", description="Extensible architecture"),
        
        # Future features
        FeatureNode(id="auto", name="Autonomous Agents", type="feature",
                   status="planned", description="Self-directed development"),
        FeatureNode(id="cloud", name="Cloud Sync", type="feature",
                   status="planned", description="Multi-device synchronization"),
        FeatureNode(id="collab", name="Collaboration", type="feature",
                   status="blocked", description="Team features"),
    ]
    
    for feature in features:
        graph.add_feature(feature)
    
    # Add relationships
    # Milestone includes
    graph.add_relationship("m1", "auth", RelationType.INCLUDES, RelationshipStrength.STRONG)
    graph.add_relationship("m1", "git", RelationType.INCLUDES, RelationshipStrength.STRONG)
    graph.add_relationship("m1", "planning", RelationType.INCLUDES, RelationshipStrength.STRONG)
    
    graph.add_relationship("m2", "graph", RelationType.INCLUDES, RelationshipStrength.STRONG)
    graph.add_relationship("m2", "ai", RelationType.INCLUDES, RelationshipStrength.STRONG)
    graph.add_relationship("m2", "plugins", RelationType.INCLUDES, RelationshipStrength.STRONG)
    
    graph.add_relationship("m3", "auto", RelationType.INCLUDES, RelationshipStrength.NORMAL)
    graph.add_relationship("m3", "cloud", RelationType.INCLUDES, RelationshipStrength.NORMAL)
    graph.add_relationship("m3", "collab", RelationType.INCLUDES, RelationshipStrength.NORMAL)
    
    # Dependencies
    graph.add_relationship("git", "auth", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
    graph.add_relationship("planning", "auth", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
    graph.add_relationship("graph", "planning", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
    graph.add_relationship("ai", "planning", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
    graph.add_relationship("ai", "git", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
    graph.add_relationship("plugins", "auth", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
    graph.add_relationship("auto", "ai", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
    graph.add_relationship("cloud", "auth", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
    graph.add_relationship("collab", "cloud", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
    
    # Relationships
    graph.add_relationship("graph", "git", RelationType.RELATED_TO, RelationshipStrength.NORMAL)
    graph.add_relationship("auto", "plugins", RelationType.RELATED_TO, RelationshipStrength.NORMAL)
    
    # Blocking (removed to avoid conflict with dependency)
    
    return graph


def main():
    """Generate demo visualizations."""
    print("Creating demo feature graph...")
    graph = create_demo_graph()
    
    # Validate the graph
    errors = graph.validate_dependencies()
    if errors:
        print("Validation issues found:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✓ Graph validation passed")
    
    # Calculate progress
    progress = graph.calculate_progress()
    print(f"\nProject Progress: {progress.completion_percentage:.1f}%")
    print(f"  - Completed: {progress.completed_features}")
    print(f"  - In Progress: {progress.in_progress_features}")
    print(f"  - Blocked: {progress.blocked_features}")
    print(f"  - Planned: {progress.planned_features}")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    layouts = ["hierarchical", "spring", "circular"]
    
    for layout in layouts:
        print(f"  - Creating {layout} layout...")
        visualizer = FeatureGraphVisualizer(graph, layout=layout)
        
        # Generate SVG
        svg_path = Path(f"demo_{layout}.svg")
        visualizer.generate_svg(output_path=svg_path)
        print(f"    ✓ SVG saved to {svg_path}")
        
        # Generate HTML
        html_path = Path(f"demo_{layout}.html")
        visualizer.generate_html(
            output_path=html_path,
            title=f"Velocitytree Demo - {layout.title()} Layout",
            interactive=True
        )
        print(f"    ✓ HTML saved to {html_path}")
    
    print("\nDemo visualizations created successfully!")
    print("Open the HTML files in your browser to explore the interactive features.")


if __name__ == "__main__":
    main()