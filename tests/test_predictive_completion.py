"""Tests for predictive completion estimates."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock

from velocitytree.progress_tracking import (
    ProgressCalculator,
    CompletionPrediction,
    FeatureProgress,
    ProjectProgress
)
from velocitytree.feature_graph import FeatureGraph, FeatureNode


class TestCompletionPrediction:
    """Test completion prediction functionality."""
    
    @pytest.fixture
    def feature_graph(self):
        """Create test feature graph."""
        graph = FeatureGraph("test_project")
        
        # Add test features
        features = [
            FeatureNode(id="f1", name="Feature 1", status="completed",
                       feature_type="feature", priority=1),
            FeatureNode(id="f2", name="Feature 2", status="in_progress",
                       feature_type="feature", priority=2),
            FeatureNode(id="f3", name="Feature 3", status="pending",
                       feature_type="feature", priority=3),
            FeatureNode(id="f4", name="Feature 4", status="blocked",
                       feature_type="feature", priority=4),
            FeatureNode(id="milestone1", name="Milestone 1", status="in_progress",
                       feature_type="epic", priority=5),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        # Add dependencies
        graph.add_dependency("f2", "f1")  # F2 depends on F1
        graph.add_dependency("f3", "f2")  # F3 depends on F2
        graph.add_dependency("f4", "f2")  # F4 depends on F2
        graph.add_dependency("milestone1", "f3")  # Milestone depends on F3
        graph.add_dependency("milestone1", "f4")  # Milestone depends on F4
        
        return graph
    
    @pytest.fixture
    def calculator(self, feature_graph):
        """Create progress calculator with test graph."""
        with patch('velocitytree.progress_tracking.ProgressCalculator._load_historical_data'):
            return ProgressCalculator(feature_graph)
    
    def test_predict_feature_completion_without_ml(self, calculator):
        """Test feature completion prediction without ML model."""
        # Mock no ML model available
        calculator._model = None
        
        prediction = calculator.predict_completion(feature_id="f2")
        
        assert isinstance(prediction, CompletionPrediction)
        assert prediction.predicted_date > datetime.now()
        assert 0.0 <= prediction.confidence <= 1.0
        assert len(prediction.confidence_interval) == 2
        assert prediction.confidence_interval[0] <= prediction.predicted_date
        assert prediction.predicted_date <= prediction.confidence_interval[1]
    
    def test_predict_project_completion(self, calculator):
        """Test project completion prediction."""
        prediction = calculator.predict_completion()
        
        assert isinstance(prediction, CompletionPrediction)
        assert prediction.predicted_date > datetime.now()
        assert prediction.recommendations
    
    def test_ml_features_extraction(self, calculator):
        """Test ML feature extraction."""
        features = calculator._extract_ml_features("f2")
        
        assert isinstance(features, list)
        assert len(features) == 14  # Number of features defined
        assert all(isinstance(f, (int, float)) for f in features)
    
    def test_confidence_calculation(self, calculator):
        """Test confidence score calculation."""
        # High completion, few dependencies, low complexity
        features = [80.0, 2, 3, 5.0, 5.0, 1, 2, 1.0, 0.0, 3.0, 2.0, 0.2, 0.8]
        confidence = calculator._calculate_prediction_confidence(features)
        
        assert 0.7 <= confidence <= 0.95  # Should be high confidence
        
        # Low completion, many dependencies, high complexity
        features = [20.0, 0, 5, 1.0, 1.0, 3, 5, 0.0, 1.0, 8.0, 4.0, 0.7, 0.6]
        confidence = calculator._calculate_prediction_confidence(features)
        
        assert 0.1 <= confidence <= 0.5  # Should be low confidence
    
    def test_risk_factor_identification(self, calculator):
        """Test risk factor identification."""
        risk_factors = calculator._identify_risk_factors("f4")
        
        assert isinstance(risk_factors, list)
        # F4 is blocked, should have risk factors
        assert any("Blocked" in factor for factor in risk_factors)
    
    def test_critical_path_identification(self, calculator):
        """Test critical path identification."""
        critical_path = calculator._identify_critical_path()
        
        assert isinstance(critical_path, set)
        # Milestone should be on critical path as it's an end goal
        assert "milestone1" in critical_path
    
    def test_recommendations_generation(self, calculator):
        """Test recommendation generation."""
        predictions = []
        risk_factors = ["Blocked by 2 features", "High complexity feature"]
        
        recommendations = calculator._generate_project_recommendations(
            predictions, risk_factors
        )
        
        assert isinstance(recommendations, list)
        assert any("blocked" in rec.lower() for rec in recommendations)
    
    def test_historical_data_update(self, calculator, tmp_path):
        """Test updating historical data."""
        calculator._model_path = tmp_path / "model.pkl"
        calculator._model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Update history
        completion_date = datetime.now()
        calculator.update_completion_history("f1", completion_date)
        
        assert len(calculator._velocity_history) == 1
        assert calculator._velocity_history[0]["feature_id"] == "f1"
    
    def test_model_training(self, calculator):
        """Test model training with synthetic data."""
        with patch('sklearn.ensemble.RandomForestRegressor') as mock_rf:
            mock_model = MagicMock()
            mock_rf.return_value = mock_model
            
            calculator._train_model()
            
            # Should have called fit
            mock_model.fit.assert_called_once()
    
    def test_confidence_interval_calculation(self, calculator):
        """Test confidence interval calculation."""
        prediction_days = 30
        confidence = 0.8
        
        interval = calculator._calculate_confidence_interval(
            prediction_days, confidence
        )
        
        lower, upper = interval
        assert lower < datetime.now() + timedelta(days=prediction_days)
        assert upper > datetime.now() + timedelta(days=prediction_days)
        
        # Higher confidence should mean narrower interval
        high_conf_interval = calculator._calculate_confidence_interval(
            prediction_days, 0.95
        )
        low_conf_interval = calculator._calculate_confidence_interval(
            prediction_days, 0.5
        )
        
        high_width = (high_conf_interval[1] - high_conf_interval[0]).days
        low_width = (low_conf_interval[1] - low_conf_interval[0]).days
        assert high_width < low_width
    
    def test_complexity_estimation(self, calculator):
        """Test feature complexity estimation."""
        # Simple feature
        complexity = calculator._estimate_complexity("f1")
        assert 0 <= complexity <= 10
        
        # Complex feature (milestone with dependencies)
        milestone_complexity = calculator._estimate_complexity("milestone1")
        assert milestone_complexity > complexity
    
    def test_dependency_depth_calculation(self, calculator):
        """Test dependency depth calculation."""
        # F1 has no dependencies
        depth_f1 = calculator._calculate_dependency_depth("f1")
        assert depth_f1 == 0
        
        # Milestone has deep dependency chain
        depth_milestone = calculator._calculate_dependency_depth("milestone1")
        assert depth_milestone > 0
    
    def test_statistical_prediction_fallback(self, calculator):
        """Test statistical prediction when ML fails."""
        days = calculator._statistical_prediction("f2")
        
        assert isinstance(days, float)
        assert days > 0
        
        # Completed feature should return 0
        completed_days = calculator._statistical_prediction("f1")
        assert completed_days == 0
    
    def test_empty_project_prediction(self):
        """Test prediction for empty project."""
        empty_graph = FeatureGraph("empty")
        calculator = ProgressCalculator(empty_graph)
        
        prediction = calculator.predict_completion()
        
        assert prediction.predicted_date == datetime.now()
        assert prediction.confidence == 1.0
        assert prediction.recommendations == ["Project is already complete"]
    
    def test_prediction_with_all_features_complete(self, calculator):
        """Test prediction when all features are complete."""
        # Mark all features as complete
        for feature in calculator.feature_graph.features.values():
            feature.status = "completed"
        
        prediction = calculator.predict_completion()
        
        assert prediction.confidence == 1.0
        assert prediction.recommendations == ["Project is already complete"]
    
    def test_velocity_variance_calculation(self, calculator):
        """Test historical velocity variance calculation."""
        variance = calculator._get_historical_velocity_variance("f2")
        
        assert 0.0 <= variance <= 1.0
    
    def test_training_data_generation(self, calculator):
        """Test synthetic training data generation."""
        X_train, y_train = calculator._generate_training_data()
        
        assert len(X_train) == len(y_train)
        assert len(X_train) > 0
        
        # Check feature dimensions
        if X_train:
            assert len(X_train[0]) == 14  # Number of ML features
    
    def test_prioritize_risk_factors(self, calculator):
        """Test risk factor prioritization."""
        risk_factors = [
            "Blocked by 3 features",
            "High complexity feature",
            "Blocked by 2 features",
            "High velocity variance",
            "High complexity feature"
        ]
        
        prioritized = calculator._prioritize_risk_factors(risk_factors)
        
        assert len(prioritized) <= 5
        # Blocked features should be prioritized
        assert any("Blocked by" in factor for factor in prioritized[:2])
        # Should include counts
        assert any("features)" in factor for factor in prioritized)


class TestCLIIntegration:
    """Test CLI integration for predictive features."""
    
    def test_predict_command_json_output(self, runner, feature_graph):
        """Test predict command with JSON output."""
        with patch('velocitytree.core.VelocityTree') as mock_vt:
            mock_vt.return_value.feature_graph = feature_graph
            
            result = runner.invoke(['progress', 'predict', '--format', 'json'])
            
            assert result.exit_code == 0
            # Should be valid JSON
            output = json.loads(result.output)
            assert 'predicted_date' in output
            assert 'confidence' in output
    
    def test_predict_specific_feature(self, runner, feature_graph):
        """Test predicting specific feature completion."""
        with patch('velocitytree.core.VelocityTree') as mock_vt:
            mock_vt.return_value.feature_graph = feature_graph
            
            result = runner.invoke(['progress', 'predict', '--feature', 'f2'])
            
            assert result.exit_code == 0
            assert "Feature: Feature 2" in result.output
            assert "Predicted completion:" in result.output
    
    def test_train_command(self, runner, feature_graph, tmp_path):
        """Test train command."""
        history_file = tmp_path / "history.json"
        history_data = [
            {
                "feature_id": "f1",
                "completion_date": datetime.now().isoformat()
            }
        ]
        history_file.write_text(json.dumps(history_data))
        
        with patch('velocitytree.core.VelocityTree') as mock_vt:
            mock_vt.return_value.feature_graph = feature_graph
            
            result = runner.invoke([
                'progress', 'train',
                '--history', str(history_file)
            ])
            
            assert result.exit_code == 0
            assert "Model trained successfully" in result.output