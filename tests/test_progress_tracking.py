"""Test progress tracking and completion calculations."""

import pytest
from datetime import datetime, timedelta

from velocitytree.progress_tracking import (
    ProgressCalculator, FeatureProgress, MilestoneProgress, 
    ProjectProgress
)
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType


class TestProgressCalculator:
    """Test the ProgressCalculator class."""
    
    @pytest.fixture
    def feature_graph(self):
        """Create a test feature graph."""
        graph = FeatureGraph("test_project")
        
        # Add features with different statuses
        features = [
            FeatureNode(id="auth", name="Authentication", feature_type="feature", status="completed"),
            FeatureNode(id="db", name="Database", feature_type="feature", status="completed"),
            FeatureNode(id="api", name="API", feature_type="feature", status="in_progress"),
            FeatureNode(id="ui", name="User Interface", feature_type="epic", status="in_progress"),
            FeatureNode(id="dashboard", name="Dashboard", feature_type="feature", status="pending"),
            FeatureNode(id="reports", name="Reports", feature_type="feature", status="blocked"),
            FeatureNode(id="mobile", name="Mobile App", feature_type="epic", status="planned"),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        # Add dependencies
        graph.add_dependency("api", "auth")
        graph.add_dependency("api", "db")
        graph.add_dependency("dashboard", "ui")
        graph.add_dependency("dashboard", "api")
        graph.add_dependency("reports", "api")
        graph.add_dependency("mobile", "api")
        
        return graph
    
    @pytest.fixture
    def calculator(self, feature_graph):
        """Create a progress calculator."""
        return ProgressCalculator(feature_graph)
    
    def test_calculate_feature_progress_completed(self, calculator):
        """Test progress calculation for completed feature."""
        progress = calculator.calculate_feature_progress("auth")
        
        assert progress.feature_id == "auth"
        assert progress.status == "completed"
        assert progress.completion_percentage == 100.0
        assert progress.dependencies_completed == 0
        assert progress.total_dependencies == 0
        assert len(progress.blockers) == 0
    
    def test_calculate_feature_progress_with_dependencies(self, calculator):
        """Test progress calculation with dependencies."""
        progress = calculator.calculate_feature_progress("api")
        
        assert progress.feature_id == "api"
        assert progress.status == "in_progress"
        assert progress.completion_percentage > 0
        assert progress.completion_percentage < 100
        assert progress.dependencies_completed == 2  # auth and db
        assert progress.total_dependencies == 2
        assert len(progress.blockers) == 0
    
    def test_calculate_feature_progress_blocked(self, calculator):
        """Test progress calculation for blocked feature."""
        progress = calculator.calculate_feature_progress("dashboard")
        
        assert progress.feature_id == "dashboard"
        assert progress.status == "pending"
        assert progress.completion_percentage < 50
        assert progress.dependencies_completed == 0  # api is in progress
        assert progress.total_dependencies == 2
        assert "api" in progress.blockers
    
    def test_critical_path_detection(self, calculator):
        """Test critical path detection."""
        # API should be on critical path as many features depend on it
        api_progress = calculator.calculate_feature_progress("api")
        assert api_progress.critical_path is True
        
        # Reports should not be on critical path
        reports_progress = calculator.calculate_feature_progress("reports")
        assert reports_progress.critical_path is False
    
    def test_calculate_milestone_progress(self, calculator):
        """Test milestone progress calculation."""
        # UI epic and its children
        milestone_features = ["ui", "dashboard"]
        progress = calculator.calculate_milestone_progress(milestone_features)
        
        assert progress.features_completed == 0
        assert progress.total_features == 2
        assert progress.completion_percentage > 0
        assert progress.completion_percentage < 100
        assert len(progress.at_risk_features) > 0  # dashboard is blocked
    
    def test_calculate_project_progress(self, calculator):
        """Test overall project progress calculation."""
        progress = calculator.calculate_project_progress()
        
        assert progress.features_completed == 2  # auth and db
        assert progress.total_features == 7
        assert progress.total_completion > 0
        assert progress.total_completion < 100
        assert progress.current_velocity >= 0
        assert progress.average_velocity >= 0
        assert len(progress.burndown_data) > 0
    
    def test_velocity_report(self, calculator):
        """Test velocity report generation."""
        report = calculator.get_velocity_report()
        
        assert "current_velocity" in report
        assert "trend" in report
        assert "predicted_velocity" in report
        assert "bottlenecks" in report
        assert "recommendations" in report
        
        # Check velocity metrics
        assert report["current_velocity"]["daily"] >= 0
        assert report["current_velocity"]["weekly"] >= 0
        assert report["current_velocity"]["monthly"] >= 0
        
        # Check trend
        assert report["trend"] in ["improving", "stable", "declining"]
        
        # Check bottlenecks
        assert isinstance(report["bottlenecks"], list)
        
    def test_bottleneck_identification(self, calculator):
        """Test bottleneck identification."""
        bottlenecks = calculator._identify_bottlenecks()
        
        # API should be identified as a bottleneck
        api_bottleneck = next(
            (b for b in bottlenecks if b["feature_id"] == "api"), 
            None
        )
        
        assert api_bottleneck is not None
        assert api_bottleneck["blocking_count"] > 2
        assert "dashboard" in api_bottleneck["blocked_features"]
    
    def test_empty_graph(self):
        """Test with empty feature graph."""
        empty_graph = FeatureGraph("empty")
        calculator = ProgressCalculator(empty_graph)
        
        progress = calculator.calculate_project_progress()
        assert progress.total_completion == 0
        assert progress.features_completed == 0
        assert progress.total_features == 0
    
    def test_estimate_completion_date(self, calculator):
        """Test completion date estimation."""
        # Test with in-progress feature
        progress = calculator.calculate_feature_progress("api")
        
        if progress.estimated_completion_date:
            assert progress.estimated_completion_date > datetime.now()
            assert progress.estimated_completion_date < datetime.now() + timedelta(days=365)
    
    def test_milestone_grouping(self, calculator):
        """Test feature grouping by milestone."""
        milestones = calculator._group_features_by_milestone()
        
        # Should identify epics as milestones
        assert "ui" in milestones
        assert "mobile" in milestones
        
        # UI milestone should include dashboard
        assert "dashboard" in milestones.get("ui", [])
    
    def test_velocity_recommendations(self, calculator):
        """Test velocity improvement recommendations."""
        recommendations = calculator._generate_velocity_recommendations()
        
        assert isinstance(recommendations, list)
        
        # Should recommend focusing on bottlenecks
        api_recommendation = any("api" in r.lower() for r in recommendations)
        assert api_recommendation or len(recommendations) > 0