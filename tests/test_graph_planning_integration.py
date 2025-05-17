"""Test integration between feature graph and planning session."""
import unittest
from datetime import datetime
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch
from velocitytree.feature_graph import (
    FeatureGraph, FeatureNode, RelationType, RelationshipStrength
)
from velocitytree.planning_session import (
    PlanningSession, Feature, Milestone, ProjectPlan, ProjectGoal
)
from velocitytree.config import Config


class TestGraphPlanningIntegration(unittest.TestCase):
    """Test the integration between feature graph and planning session."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config()
        
        # Mock AI assistant to avoid API key requirements
        with patch('velocitytree.planning_session.AIAssistant') as mock_ai:
            mock_instance = Mock()
            mock_ai.return_value = mock_instance
            self.session = PlanningSession(self.config)
            self.session.ai_assistant = mock_instance
        
        self.graph = FeatureGraph("test_project")
        
        # Create a sample project plan
        self.plan = ProjectPlan(
            name="Task Management System",
            description="A comprehensive task management application",
            goals=[
                ProjectGoal(
                    description="Build a task management system",
                    priority="high",
                    success_criteria=["User can manage tasks", "Multiple projects supported"],
                    constraints=["6-week deadline", "2-person team"]
                )
            ],
            milestones=[
                Milestone(
                    name="Core Features",
                    description="Basic task management functionality",
                    deliverables=["User auth", "Task CRUD", "Project organization"],
                    estimated_duration="3 weeks"
                ),
                Milestone(
                    name="Enhanced Features",
                    description="Advanced task management features",
                    deliverables=["Collaboration", "Notifications", "Analytics"],
                    estimated_duration="3 weeks"
                )
            ],
            features=[
                Feature(
                    name="User Authentication",
                    description="Secure user login and registration",
                    requirements=["JWT tokens", "Password hashing"],
                    priority="high",
                    effort_estimate="1 week"
                ),
                Feature(
                    name="Task Management",
                    description="Create, read, update, delete tasks",
                    requirements=["Database models", "API endpoints"],
                    dependencies=["User Authentication"],
                    priority="high",
                    effort_estimate="2 weeks"
                ),
                Feature(
                    name="Project Dashboard",
                    description="Visualize project progress",
                    requirements=["Charts library", "Real-time updates"],
                    dependencies=["Task Management"],
                    priority="medium",
                    effort_estimate="1.5 weeks"
                ),
                Feature(
                    name="Notifications",
                    description="Email and in-app notifications",
                    requirements=["Email service", "WebSocket"],
                    dependencies=["User Authentication", "Task Management"],
                    priority="medium",
                    effort_estimate="1 week"
                )
            ],
            tech_stack={
                "backend": ["Python 3.8+", "FastAPI"],
                "database": ["PostgreSQL", "Redis"],
                "frontend": ["React", "TypeScript"]
            },
            timeline={
                "start_date": "2024-01-01",
                "end_date": "2024-02-12",
                "milestones": {"Core Features": "2024-01-22", "Enhanced Features": "2024-02-12"}
            },
            resources={
                "team_size": 2,
                "roles": ["Backend Developer", "Frontend Developer"]
            },
            risks=[
                {"name": "Scope creep", "mitigation": "Clear requirements and regular reviews"},
                {"name": "Performance at scale", "mitigation": "Load testing and optimization"}
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def test_build_graph_from_plan(self):
        """Test building a feature graph from a project plan."""
        # Build graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Verify milestones added
        self.assertEqual(len(self.graph.milestones), 2)
        self.assertIn("milestone_core_features", self.graph.milestones)
        self.assertIn("milestone_enhanced_features", self.graph.milestones)
        
        # Verify features added
        self.assertEqual(len(self.graph.features), 4 + 2)  # 4 features + 2 milestones
        self.assertIn("feature_user_authentication", self.graph.features)
        self.assertIn("feature_task_management", self.graph.features)
        
        # Verify dependencies
        deps = self.graph.get_dependencies("feature_task_management")
        self.assertIn("feature_user_authentication", deps)
    
    def test_enhance_graph_with_relationships(self):
        """Test enhancing the graph with additional relationships."""
        # Build initial graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Add additional relationships
        self.graph.add_relationship(
            "feature_project_dashboard",
            "feature_notifications",
            RelationType.RELATED_TO,
            RelationshipStrength.NORMAL,
            "Both display project activity"
        )
        
        self.graph.add_relationship(
            "milestone_core_features",
            "feature_user_authentication",
            RelationType.INCLUDES,
            RelationshipStrength.STRONG
        )
        
        self.graph.add_relationship(
            "milestone_core_features",
            "feature_task_management",
            RelationType.INCLUDES,
            RelationshipStrength.STRONG
        )
        
        # Verify relationships
        milestone_rels = self.graph.get_relationships(
            "milestone_core_features",
            direction="out"
        )
        self.assertEqual(len(milestone_rels), 2)
        
        # Check related features
        related = self.graph.get_related_features("feature_project_dashboard")
        self.assertIn("related_to", related)
        self.assertIn("feature_notifications", related["related_to"])
    
    def test_session_graph_roundtrip(self):
        """Test saving session plan to graph and back."""
        # Create session with plan
        self.session.start_session("Task Management System")
        self.session.project_plan = self.plan
        
        # Export to graph
        self.graph.from_project_plan(self.plan)
        
        # Add some progress
        self.graph.update_feature_status("feature_user_authentication", "completed")
        self.graph.update_feature_status("feature_task_management", "in_progress")
        
        # Calculate progress
        progress = self.graph.calculate_progress()
        self.assertEqual(progress.completed_features, 1)
        self.assertEqual(progress.in_progress_features, 1)
        
        # Save both session and graph
        self.session.save_state()
        
        # Graph can be saved directly
        with tempfile.TemporaryDirectory() as tmpdir:
            graph_path = Path(tmpdir) / "graph.json"
            self.graph.save(graph_path)
            
            # Load back
            loaded_graph = FeatureGraph.load(graph_path)
            
            # Verify consistency
            self.assertEqual(len(self.plan.features), 4)
            self.assertEqual(len(loaded_graph.features), 6)  # includes milestones
            
            # Check status preserved
            auth_feature = loaded_graph.features["feature_user_authentication"]
            self.assertEqual(auth_feature.status, "completed")
    
    def test_milestone_progress_tracking(self):
        """Test tracking milestone progress through feature completion."""
        # Build graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Link features to milestones
        self.graph.add_relationship(
            "milestone_core_features",
            "feature_user_authentication",
            RelationType.INCLUDES
        )
        self.graph.add_relationship(
            "milestone_core_features",
            "feature_task_management",
            RelationType.INCLUDES
        )
        
        # Tag features with milestone
        auth_feature = self.graph.features["feature_user_authentication"]
        auth_feature.tags.append("milestone_core_features")
        
        task_feature = self.graph.features["feature_task_management"]
        task_feature.tags.append("milestone_core_features")
        
        # Get initial milestone progress
        progress = self.graph.get_milestone_progress("milestone_core_features")
        self.assertEqual(progress["completed_features"], 0)
        self.assertEqual(progress["total_features"], 2)
        
        # Complete one feature
        self.graph.update_feature_status("feature_user_authentication", "completed")
        
        # Check updated progress
        progress = self.graph.get_milestone_progress("milestone_core_features")
        self.assertEqual(progress["completed_features"], 1)
        self.assertEqual(progress["completion_percentage"], 50.0)
    
    def test_feature_blocking_relationships(self):
        """Test handling of blocking relationships."""
        # Build graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Add a blocking relationship
        self.graph.add_relationship(
            "feature_task_management",
            "feature_project_dashboard",
            RelationType.BLOCKS,
            RelationshipStrength.CRITICAL,
            "Dashboard cannot start until task management is complete"
        )
        
        # Mark dashboard as blocked
        self.graph.update_feature_status("feature_project_dashboard", "blocked")
        
        # Complete task management
        self.graph.update_feature_status("feature_task_management", "completed")
        
        # Check if dashboard can be unblocked
        dashboard_deps = self.graph.get_dependencies("feature_project_dashboard")
        task_mgmt = self.graph.features["feature_task_management"]
        self.assertEqual(task_mgmt.status, "completed")
        
        # Unblock dashboard
        self.graph.update_feature_status("feature_project_dashboard", "planned")
        self.assertEqual(self.graph.features["feature_project_dashboard"].status, "planned")
    
    def test_critical_path_calculation(self):
        """Test critical path calculation with relationships."""
        # Build graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Create a chain of critical dependencies
        self.graph.add_relationship(
            "feature_user_authentication",
            "feature_task_management",
            RelationType.PRECEDES,
            RelationshipStrength.CRITICAL
        )
        self.graph.add_relationship(
            "feature_task_management",
            "feature_project_dashboard",
            RelationType.PRECEDES,
            RelationshipStrength.CRITICAL
        )
        
        # Calculate progress (includes critical path)
        progress = self.graph.calculate_progress()
        
        # The critical path should include our chain
        self.assertIsNotNone(progress.critical_path)
        # Note: Exact path ordering depends on algorithm implementation
    
    def test_graph_statistics(self):
        """Test graph statistics with relationships."""
        # Build graph from plan
        self.graph.from_project_plan(self.plan)
        
        # Add various relationships
        self.graph.add_relationship(
            "milestone_core_features",
            "feature_user_authentication",
            RelationType.INCLUDES
        )
        self.graph.add_relationship(
            "feature_project_dashboard",
            "feature_notifications",
            RelationType.RELATED_TO
        )
        
        # Get statistics
        stats = self.graph.get_graph_statistics()
        
        self.assertGreater(stats["total_nodes"], 0)
        self.assertGreater(stats["total_edges"], 0)
        self.assertGreaterEqual(stats["avg_dependencies"], 0)


if __name__ == "__main__":
    unittest.main()