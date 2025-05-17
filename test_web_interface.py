"""Test script for the interactive web interface."""

from velocitytree.web_server import FeatureGraphWebServer
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType, RelationshipStrength


def main():
    """Test the web server with demo data."""
    # Create demo feature graph
    graph = FeatureGraph("demo_project")
    
    # Add features
    features = [
        FeatureNode(id="core", name="Core Framework", description="Core system components",
                   feature_type="epic", status="completed"),
        FeatureNode(id="auth", name="Authentication", description="User authentication system",
                   feature_type="feature", status="completed"),
        FeatureNode(id="db", name="Database Layer", description="Database abstraction",
                   feature_type="feature", status="completed"),
        FeatureNode(id="api", name="REST API", description="RESTful API endpoints",
                   feature_type="feature", status="in_progress"),
        FeatureNode(id="ui", name="User Interface", description="Frontend application",
                   feature_type="epic", status="in_progress"),
        FeatureNode(id="dashboard", name="Dashboard", description="Main dashboard view",
                   feature_type="feature", status="pending"),
        FeatureNode(id="reports", name="Reports Module", description="Reporting system",
                   feature_type="feature", status="pending"),
        FeatureNode(id="admin", name="Admin Panel", description="Administrative interface",
                   feature_type="feature", status="pending"),
        FeatureNode(id="mobile", name="Mobile App", description="Mobile application",
                   feature_type="epic", status="pending"),
    ]
    
    for feature in features:
        graph.add_feature(feature)
    
    # Add relationships
    relationships = [
        ("auth", "core", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL),
        ("db", "core", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL),
        ("api", "auth", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL),
        ("api", "db", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL),
        ("ui", "api", RelationType.DEPENDS_ON, RelationshipStrength.STRONG),
        ("dashboard", "ui", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL),
        ("reports", "api", RelationType.DEPENDS_ON, RelationshipStrength.STRONG),
        ("reports", "dashboard", RelationType.DEPENDS_ON, RelationshipStrength.WEAK),
        ("admin", "ui", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL),
        ("admin", "auth", RelationType.DEPENDS_ON, RelationshipStrength.STRONG),
        ("mobile", "api", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL),
    ]
    
    for source, target, rel_type, strength in relationships:
        graph.add_relationship(source, target, rel_type, strength)
    
    # Create web server
    server = FeatureGraphWebServer(port=5000)
    server.feature_graph = graph
    
    print("Starting demo web server at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    
    # Run server
    server.run()


if __name__ == "__main__":
    main()