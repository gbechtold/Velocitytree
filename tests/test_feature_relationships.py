"""Test feature relationship mapping functionality."""
import unittest
from datetime import datetime
from velocitytree.feature_graph import (
    FeatureGraph, FeatureNode, FeatureRelationship,
    RelationType, RelationshipStrength
)


class TestFeatureRelationships(unittest.TestCase):
    """Test the feature relationship mapping functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = FeatureGraph("test_project")
        
        # Create test features
        self.auth_feature = FeatureNode(
            id="auth", 
            name="Authentication", 
            description="User authentication system",
            type="feature", 
            status="completed"
        )
        
        self.dashboard_feature = FeatureNode(
            id="dashboard",
            name="Dashboard",
            description="User dashboard",
            type="feature",
            status="in_progress"
        )
        
        self.api_feature = FeatureNode(
            id="api",
            name="API",
            description="REST API",
            type="feature",
            status="planned"
        )
        
        self.profile_feature = FeatureNode(
            id="profile",
            name="User Profile",
            description="User profile management",
            type="feature",
            status="planned"
        )
        
        # Add features to graph
        self.graph.add_feature(self.auth_feature)
        self.graph.add_feature(self.dashboard_feature)
        self.graph.add_feature(self.api_feature)
        self.graph.add_feature(self.profile_feature)
    
    def test_add_relationship(self):
        """Test adding relationships between features."""
        # Add a depends-on relationship
        rel = self.graph.add_relationship(
            "dashboard", "auth",
            RelationType.DEPENDS_ON,
            RelationshipStrength.CRITICAL,
            "Dashboard requires authentication"
        )
        
        self.assertEqual(rel.source_id, "dashboard")
        self.assertEqual(rel.target_id, "auth")
        self.assertEqual(rel.relation_type, RelationType.DEPENDS_ON)
        self.assertEqual(rel.strength, RelationshipStrength.CRITICAL)
        self.assertEqual(rel.description, "Dashboard requires authentication")
        
        # Verify edge in graph
        self.assertTrue(self.graph.graph.has_edge("dashboard", "auth"))
        edge_data = self.graph.graph["dashboard"]["auth"]
        self.assertEqual(edge_data["relation_type"], "depends_on")
        self.assertEqual(edge_data["strength"], "critical")
    
    def test_multiple_relationship_types(self):
        """Test different types of relationships."""
        # Add various relationships
        self.graph.add_relationship("api", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("profile", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("profile", "dashboard", RelationType.RELATED_TO)
        self.graph.add_relationship("dashboard", "api", RelationType.INCLUDES)
        
        # Check relationship counts
        self.assertEqual(len(self.graph.relationships), 4)
        
        # Get relationships for dashboard
        dashboard_rels = self.graph.get_relationships("dashboard")
        self.assertEqual(len(dashboard_rels), 2)  # outgoing: includes, incoming: related_to
    
    def test_get_relationships_with_filters(self):
        """Test getting relationships with filters."""
        # Add relationships
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("api", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("profile", "dashboard", RelationType.RELATED_TO)
        
        # Get only dependencies
        deps = self.graph.get_relationships("auth", RelationType.DEPENDS_ON, "in")
        self.assertEqual(len(deps), 2)
        
        # Get only outgoing relationships
        outgoing = self.graph.get_relationships("dashboard", direction="out")
        self.assertEqual(len(outgoing), 1)
        self.assertEqual(outgoing[0].target_id, "auth")
    
    def test_get_related_features(self):
        """Test getting related features within depth."""
        # Create a chain of dependencies
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("profile", "dashboard", RelationType.DEPENDS_ON)
        self.graph.add_relationship("api", "auth", RelationType.DEPENDS_ON)
        
        # Get features related to auth
        related = self.graph.get_related_features("auth")
        self.assertIn("depends_on", related)
        self.assertEqual(len(related["depends_on"]), 2)  # dashboard and api
        
        # Get features with depth 2
        related_deep = self.graph.get_related_features("auth", max_depth=2)
        all_related = set()
        for features in related_deep.values():
            all_related.update(features)
        self.assertIn("profile", all_related)  # profile depends on dashboard which depends on auth
    
    def test_remove_relationship(self):
        """Test removing relationships."""
        # Add a relationship
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON)
        self.assertEqual(len(self.graph.relationships), 1)
        
        # Remove it
        removed = self.graph.remove_relationship("dashboard", "auth")
        self.assertTrue(removed)
        self.assertEqual(len(self.graph.relationships), 0)
        self.assertFalse(self.graph.graph.has_edge("dashboard", "auth"))
        
        # Try to remove non-existent relationship
        removed = self.graph.remove_relationship("api", "profile")
        self.assertFalse(removed)
    
    def test_update_relationship(self):
        """Test updating relationship properties."""
        # Add a relationship
        self.graph.add_relationship(
            "dashboard", "auth",
            RelationType.DEPENDS_ON,
            RelationshipStrength.NORMAL
        )
        
        # Update it
        updated = self.graph.update_relationship(
            "dashboard", "auth",
            strength=RelationshipStrength.CRITICAL,
            description="Critical dependency for security"
        )
        self.assertTrue(updated)
        
        # Verify update
        rel = self.graph.relationships[("dashboard", "auth")]
        self.assertEqual(rel.strength, RelationshipStrength.CRITICAL)
        self.assertEqual(rel.description, "Critical dependency for security")
    
    def test_relationship_matrix(self):
        """Test getting relationship matrix."""
        # Add relationships
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("api", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("profile", "dashboard", RelationType.RELATED_TO)
        
        # Get matrix
        matrix = self.graph.get_relationship_matrix(["auth", "dashboard", "api"])
        
        self.assertIn("dashboard", matrix)
        self.assertIn("auth", matrix["dashboard"])
        self.assertEqual(matrix["dashboard"]["auth"], ["depends_on"])
        
        self.assertIn("api", matrix)
        self.assertIn("auth", matrix["api"])
        self.assertEqual(matrix["api"]["auth"], ["depends_on"])
    
    def test_validate_dependencies_with_relationships(self):
        """Test dependency validation with new relationship types."""
        # Create circular dependency
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON)
        self.graph.add_relationship("auth", "api", RelationType.DEPENDS_ON)
        self.graph.add_relationship("api", "dashboard", RelationType.DEPENDS_ON)
        
        errors = self.graph.validate_dependencies()
        self.assertTrue(any("Circular dependency" in error for error in errors))
        
        # Test conflicting relationships
        self.graph = FeatureGraph("test_conflict")
        self.graph.add_feature(self.auth_feature)
        self.graph.add_feature(self.dashboard_feature)
        
        self.graph.add_relationship("dashboard", "auth", RelationType.BLOCKS)
        self.graph.add_relationship("auth", "dashboard", RelationType.DEPENDS_ON)
        
        errors = self.graph.validate_dependencies()
        self.assertTrue(any("Conflicting relationships" in error for error in errors))
    
    def test_serialization_with_relationships(self):
        """Test saving and loading graph with relationships."""
        # Add relationships
        self.graph.add_relationship(
            "dashboard", "auth",
            RelationType.DEPENDS_ON,
            RelationshipStrength.CRITICAL,
            "Critical dependency"
        )
        self.graph.add_relationship(
            "api", "auth",
            RelationType.DEPENDS_ON,
            RelationshipStrength.NORMAL
        )
        
        # Convert to dict
        data = self.graph.to_dict()
        self.assertIn("relationships", data)
        self.assertEqual(len(data["relationships"]), 2)
        
        # Save and load
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            self.graph.save(f.name)
            
            # Load back
            loaded_graph = FeatureGraph.load(f.name)
            
            # Verify relationships preserved
            self.assertEqual(len(loaded_graph.relationships), 2)
            rel = loaded_graph.relationships[("dashboard", "auth")]
            self.assertEqual(rel.relation_type, RelationType.DEPENDS_ON)
            self.assertEqual(rel.strength, RelationshipStrength.CRITICAL)
            self.assertEqual(rel.description, "Critical dependency")
    
    def test_relationship_metadata(self):
        """Test relationship metadata handling."""
        # Add relationship with metadata
        metadata = {
            "priority": 1,
            "estimated_effort": "2 days",
            "assignee": "john.doe"
        }
        
        rel = self.graph.add_relationship(
            "dashboard", "auth",
            RelationType.DEPENDS_ON,
            metadata=metadata
        )
        
        self.assertEqual(rel.metadata["priority"], 1)
        self.assertEqual(rel.metadata["estimated_effort"], "2 days")
        self.assertEqual(rel.metadata["assignee"], "john.doe")
        
        # Update metadata
        new_metadata = {"priority": 2}
        self.graph.update_relationship("dashboard", "auth", metadata=new_metadata)
        
        rel = self.graph.relationships[("dashboard", "auth")]
        self.assertEqual(rel.metadata["priority"], 2)
        self.assertEqual(rel.metadata["estimated_effort"], "2 days")  # preserved


if __name__ == "__main__":
    unittest.main()