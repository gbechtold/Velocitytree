"""Test advanced dependency tracking functionality."""
import unittest
from velocitytree.feature_graph import (
    FeatureGraph, FeatureNode, RelationType, RelationshipStrength
)


class TestDependencyTracking(unittest.TestCase):
    """Test the advanced dependency tracking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = FeatureGraph("test_project")
        
        # Create a network of features
        self.features = {
            "auth": FeatureNode(
                id="auth",
                name="Authentication",
                description="User authentication",
                type="feature",
                status="completed"
            ),
            "db": FeatureNode(
                id="db",
                name="Database",
                description="Database setup",
                type="feature",
                status="completed"
            ),
            "api": FeatureNode(
                id="api",
                name="API",
                description="REST API",
                type="feature",
                status="in_progress"
            ),
            "dashboard": FeatureNode(
                id="dashboard",
                name="Dashboard",
                description="User dashboard",
                type="feature",
                status="planned"
            ),
            "admin": FeatureNode(
                id="admin",
                name="Admin Panel",
                description="Admin interface",
                type="feature",
                status="planned"
            ),
            "reporting": FeatureNode(
                id="reporting",
                name="Reporting",
                description="Report generation",
                type="feature",
                status="planned"
            ),
            "notifications": FeatureNode(
                id="notifications",
                name="Notifications",
                description="Email/SMS notifications",
                type="feature",
                status="blocked"
            )
        }
        
        # Add all features
        for feature in self.features.values():
            self.graph.add_feature(feature)
        
        # Create dependency network
        self.graph.add_relationship("api", "auth", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
        self.graph.add_relationship("api", "db", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
        self.graph.add_relationship("dashboard", "api", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
        self.graph.add_relationship("dashboard", "auth", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
        self.graph.add_relationship("admin", "dashboard", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
        self.graph.add_relationship("admin", "auth", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
        self.graph.add_relationship("reporting", "api", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
        self.graph.add_relationship("reporting", "db", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
        self.graph.add_relationship("notifications", "api", RelationType.DEPENDS_ON, RelationshipStrength.WEAK)
    
    def test_get_all_dependencies(self):
        """Test getting all dependencies recursively."""
        # Direct dependencies
        direct_deps = self.graph.get_dependencies("dashboard")
        self.assertEqual(set(direct_deps), {"api", "auth"})
        
        # All dependencies (recursive)
        all_deps = self.graph.get_all_dependencies("dashboard")
        self.assertEqual(all_deps, {"api", "auth", "db"})
        
        # Non-recursive
        non_recursive = self.graph.get_all_dependencies("dashboard", recursive=False)
        self.assertEqual(non_recursive, {"api", "auth"})
    
    def test_get_all_dependents(self):
        """Test getting all dependents recursively."""
        # Direct dependents of auth
        direct_deps = self.graph.get_dependents("auth")
        self.assertEqual(set(direct_deps), {"api", "dashboard", "admin"})
        
        # All dependents (recursive) - should include indirect dependents
        all_deps = self.graph.get_all_dependents("auth")
        # auth -> api -> dashboard/reporting/notifications, auth -> dashboard -> admin
        self.assertEqual(all_deps, {"api", "dashboard", "admin", "reporting", "notifications"})
        
        # Dependents of api
        api_deps = self.graph.get_all_dependents("api")
        self.assertEqual(api_deps, {"dashboard", "reporting", "notifications", "admin"})
    
    def test_can_start_feature(self):
        """Test checking if a feature can be started."""
        # Dashboard cannot start (API not complete)
        can_start, issues = self.graph.can_start_feature("dashboard")
        self.assertFalse(can_start)
        self.assertTrue(any("api" in issue for issue in issues))
        
        # Complete API
        self.graph.update_feature_status("api", "completed")
        
        # Now dashboard can start
        can_start, issues = self.graph.can_start_feature("dashboard")
        self.assertTrue(can_start)
        self.assertEqual(len(issues), 0)
        
        # Reporting can start (critical dep on db is complete, normal dep on api is complete)
        can_start, issues = self.graph.can_start_feature("reporting")
        self.assertTrue(can_start)
        
        # Test with blocked feature - first make db in_progress
        self.graph.update_feature_status("db", "in_progress")
        self.graph.add_relationship("db", "notifications", RelationType.BLOCKS)
        self.graph.update_feature_status("notifications", "planned")
        can_start, issues = self.graph.can_start_feature("notifications")
        self.assertFalse(can_start)
        self.assertTrue(any("blocking" in issue for issue in issues))
    
    def test_get_suggested_next_features(self):
        """Test getting suggested next features."""
        # Complete API
        self.graph.update_feature_status("api", "completed")
        
        suggestions = self.graph.get_suggested_next_features()
        
        # Dashboard should be high priority (has dependents)
        self.assertTrue(len(suggestions) > 0)
        
        # Find dashboard in suggestions
        dashboard_suggestion = None
        for feature_id, details in suggestions:
            if feature_id == "dashboard":
                dashboard_suggestion = details
                break
        
        self.assertIsNotNone(dashboard_suggestion)
        self.assertGreater(dashboard_suggestion['priority_score'], 0)
        self.assertGreater(dashboard_suggestion['dependent_count'], 0)
    
    def test_get_dependency_chain(self):
        """Test finding dependency chains between features."""
        # Chain from admin to db
        chains = self.graph.get_dependency_chain("admin", "db")
        
        # Should find multiple paths
        self.assertGreater(len(chains), 0)
        
        # Verify paths
        found_direct = False
        found_through_api = False
        
        for chain in chains:
            if chain == ["admin", "dashboard", "api", "db"]:
                found_through_api = True
        
        self.assertTrue(found_through_api)
        
        # No chain from db to admin (wrong direction)
        chains = self.graph.get_dependency_chain("db", "admin")
        self.assertEqual(len(chains), 0)
    
    def test_weak_dependencies(self):
        """Test weak dependency handling."""
        # Notifications has weak dependency on API
        # Should be able to start even if API is not complete
        self.graph.update_feature_status("api", "in_progress")
        self.graph.update_feature_status("notifications", "planned")
        
        can_start, issues = self.graph.can_start_feature("notifications")
        self.assertTrue(can_start)  # Weak dependency doesn't block
    
    def test_enhanced_validation(self):
        """Test enhanced dependency validation."""
        # Create a new graph for this test to avoid conflicts
        test_graph = FeatureGraph("test_validation")
        
        # Create a deep dependency chain
        for i in range(10):
            feature = FeatureNode(
                id=f"feature_{i}",
                name=f"Feature {i}",
                description=f"Feature {i}",
                type="feature",
                status="planned"
            )
            test_graph.add_feature(feature)
            
            if i > 0:
                test_graph.add_relationship(
                    f"feature_{i}",
                    f"feature_{i-1}",
                    RelationType.DEPENDS_ON
                )
        
        errors = test_graph.validate_dependencies()
        
        # Should have warning about deep dependency chain
        deep_warnings = [e for e in errors if "WARNING:" in e and "deep" in e.lower()]
        self.assertGreater(len(deep_warnings), 0)
        
        # Test conflicting relationships
        # Create features A and B
        test_graph.add_feature(FeatureNode(
            id="feature_a",
            name="Feature A", 
            description="Feature A",
            type="feature",
            status="planned"
        ))
        test_graph.add_feature(FeatureNode(
            id="feature_b",
            name="Feature B",
            description="Feature B", 
            type="feature",
            status="planned"
        ))
        
        # B depends on A, but A also blocks B - this is a conflict
        test_graph.add_relationship("feature_b", "feature_a", RelationType.DEPENDS_ON)
        test_graph.add_relationship("feature_a", "feature_b", RelationType.BLOCKS)
        
        errors = test_graph.validate_dependencies()
        
        # Should detect conflict
        conflicts = [e for e in errors if "Conflicting" in e]
        self.assertGreater(len(conflicts), 0)
    
    def test_status_propagation(self):
        """Test status changes propagating through dependencies."""
        # Complete API
        self.graph.update_feature_status("api", "completed")
        
        # Start dashboard
        self.graph.update_feature_status("dashboard", "in_progress")
        
        # If we un-complete API, dashboard should be blocked
        self.graph.update_feature_status("api", "in_progress")
        
        # Dashboard should now be blocked
        dashboard = self.graph.features["dashboard"]
        self.assertEqual(dashboard.status, "blocked")


if __name__ == "__main__":
    unittest.main()