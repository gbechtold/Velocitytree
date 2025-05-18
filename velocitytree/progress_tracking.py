"""Progress tracking and completion percentage calculations."""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import numpy as np
from pathlib import Path
import json

from .feature_graph import FeatureGraph, FeatureNode
from .utils import logger


@dataclass
class FeatureProgress:
    """Progress information for a feature."""
    feature_id: str
    name: str
    status: str
    completion_percentage: float
    dependencies_completed: int
    total_dependencies: int
    estimated_completion_date: Optional[datetime] = None
    velocity: Optional[float] = None  # Features completed per day
    time_spent: Optional[timedelta] = None
    blockers: List[str] = field(default_factory=list)
    critical_path: bool = False


@dataclass
class MilestoneProgress:
    """Progress information for a milestone."""
    milestone_id: str
    name: str
    completion_percentage: float
    features_completed: int
    total_features: int
    estimated_completion_date: Optional[datetime] = None
    velocity: Optional[float] = None
    critical_features: List[str] = field(default_factory=list)
    at_risk_features: List[str] = field(default_factory=list)


@dataclass
class ProjectProgress:
    """Overall project progress information."""
    total_completion: float
    features_completed: int
    total_features: int
    milestones_completed: int
    total_milestones: int
    current_velocity: float
    average_velocity: float
    estimated_completion_date: Optional[datetime] = None
    burndown_data: List[Tuple[datetime, float]] = field(default_factory=list)
    confidence_interval: Optional[Tuple[float, float]] = None  # Lower and upper bounds
    risk_score: float = 0.0  # 0-100 scale


@dataclass
class CompletionPrediction:
    """Machine learning based completion prediction."""
    predicted_date: datetime
    confidence: float  # 0-1 scale
    confidence_interval: Tuple[datetime, datetime]  # Lower and upper bounds
    risk_factors: List[str]
    recommendations: List[str]


class ProgressCalculator:
    """Calculate completion percentages and progress metrics."""
    
    def __init__(self, feature_graph: FeatureGraph):
        """Initialize the progress calculator.
        
        Args:
            feature_graph: The feature graph to analyze
        """
        self.feature_graph = feature_graph
        self._completion_cache = {}
        self._velocity_history = []
        self._model = None
        self._model_path = Path.home() / ".velocitytree" / "models" / "completion_predictor.pkl"
        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_historical_data()
    
    def calculate_feature_progress(self, feature_id: str) -> FeatureProgress:
        """Calculate progress for a single feature.
        
        Args:
            feature_id: ID of the feature
            
        Returns:
            FeatureProgress object with detailed metrics
        """
        if feature_id not in self.feature_graph.features:
            raise ValueError(f"Feature {feature_id} not found")
        
        feature = self.feature_graph.features[feature_id]
        
        # Get dependency information
        dependencies = self.feature_graph.get_dependencies(feature_id)
        all_dependencies = self.feature_graph.get_all_dependencies(feature_id, recursive=True)
        
        # Count completed dependencies
        deps_completed = sum(
            1 for dep_id in dependencies 
            if self.feature_graph.features[dep_id].status == "completed"
        )
        
        all_deps_completed = sum(
            1 for dep_id in all_dependencies
            if self.feature_graph.features[dep_id].status == "completed"
        )
        
        # Calculate completion percentage
        if feature.status == "completed":
            completion = 100.0
        elif not all_dependencies:
            # No dependencies, use status-based estimation
            completion = self._estimate_by_status(feature.status)
        else:
            # Calculate based on dependency completion
            base_completion = self._estimate_by_status(feature.status)
            dep_completion = (all_deps_completed / len(all_dependencies)) * 100
            
            # Weighted average: 70% dependency completion, 30% own status
            completion = (dep_completion * 0.7) + (base_completion * 0.3)
        
        # Find blockers
        blockers = []
        for dep_id in dependencies:
            dep = self.feature_graph.features[dep_id]
            if dep.status not in ["completed", "in_progress"]:
                blockers.append(dep_id)
        
        # Check if on critical path
        critical_path = self._is_on_critical_path(feature_id)
        
        # Estimate completion date
        estimated_date = self._estimate_completion_date(feature_id, completion)
        
        # Calculate velocity if possible
        velocity = self._calculate_feature_velocity(feature_id)
        
        return FeatureProgress(
            feature_id=feature_id,
            name=feature.name,
            status=feature.status,
            completion_percentage=round(completion, 2),
            dependencies_completed=deps_completed,
            total_dependencies=len(dependencies),
            estimated_completion_date=estimated_date,
            velocity=velocity,
            blockers=blockers,
            critical_path=critical_path
        )
    
    def calculate_milestone_progress(self, milestone_features: List[str]) -> MilestoneProgress:
        """Calculate progress for a milestone.
        
        Args:
            milestone_features: List of feature IDs in the milestone
            
        Returns:
            MilestoneProgress object
        """
        if not milestone_features:
            return MilestoneProgress(
                milestone_id="unknown",
                name="Unknown Milestone",
                completion_percentage=0.0,
                features_completed=0,
                total_features=0
            )
        
        # Calculate individual feature progress
        feature_progresses = []
        for feature_id in milestone_features:
            if feature_id in self.feature_graph.features:
                progress = self.calculate_feature_progress(feature_id)
                feature_progresses.append(progress)
        
        # Count completed features
        features_completed = sum(
            1 for p in feature_progresses 
            if p.status == "completed"
        )
        
        # Calculate overall completion
        if feature_progresses:
            completion = statistics.mean(p.completion_percentage for p in feature_progresses)
        else:
            completion = 0.0
        
        # Identify critical and at-risk features
        critical_features = [p.feature_id for p in feature_progresses if p.critical_path]
        at_risk_features = [
            p.feature_id for p in feature_progresses 
            if p.blockers and p.status != "completed"
        ]
        
        # Estimate completion date
        estimated_date = self._estimate_milestone_completion_date(feature_progresses)
        
        # Calculate velocity
        velocity = self._calculate_milestone_velocity(milestone_features)
        
        return MilestoneProgress(
            milestone_id=f"milestone_{len(milestone_features)}",
            name=f"Milestone with {len(milestone_features)} features",
            completion_percentage=round(completion, 2),
            features_completed=features_completed,
            total_features=len(milestone_features),
            estimated_completion_date=estimated_date,
            velocity=velocity,
            critical_features=critical_features,
            at_risk_features=at_risk_features
        )
    
    def calculate_project_progress(self) -> ProjectProgress:
        """Calculate overall project progress.
        
        Returns:
            ProjectProgress object with comprehensive metrics
        """
        all_features = list(self.feature_graph.features.keys())
        
        # Calculate progress for all features
        feature_progresses = []
        for feature_id in all_features:
            progress = self.calculate_feature_progress(feature_id)
            feature_progresses.append(progress)
        
        # Count completed
        features_completed = sum(
            1 for p in feature_progresses 
            if p.status == "completed"
        )
        
        # Calculate overall completion
        total_completion = statistics.mean(
            p.completion_percentage for p in feature_progresses
        ) if feature_progresses else 0.0
        
        # Group features by milestone (simplified - assumes top-level features are milestones)
        milestones = self._group_features_by_milestone()
        milestone_progresses = []
        
        for milestone_features in milestones.values():
            milestone_progress = self.calculate_milestone_progress(milestone_features)
            milestone_progresses.append(milestone_progress)
        
        milestones_completed = sum(
            1 for mp in milestone_progresses 
            if mp.completion_percentage == 100.0
        )
        
        # Calculate velocity metrics
        current_velocity = self._calculate_current_velocity()
        average_velocity = self._calculate_average_velocity()
        
        # Estimate project completion
        estimated_date = self._estimate_project_completion_date(
            total_completion, average_velocity
        )
        
        # Generate burndown data
        burndown_data = self._generate_burndown_data()
        
        return ProjectProgress(
            total_completion=round(total_completion, 2),
            features_completed=features_completed,
            total_features=len(all_features),
            milestones_completed=milestones_completed,
            total_milestones=len(milestones),
            estimated_completion_date=estimated_date,
            current_velocity=current_velocity,
            average_velocity=average_velocity,
            burndown_data=burndown_data
        )
    
    def get_velocity_report(self) -> Dict[str, any]:
        """Generate a velocity tracking report.
        
        Returns:
            Dictionary with velocity metrics and trends
        """
        # Calculate velocity over different time periods
        daily_velocity = self._calculate_velocity_by_period(days=1)
        weekly_velocity = self._calculate_velocity_by_period(days=7)
        monthly_velocity = self._calculate_velocity_by_period(days=30)
        
        # Identify velocity trends
        trend = self._calculate_velocity_trend()
        
        # Find bottlenecks affecting velocity
        bottlenecks = self._identify_bottlenecks()
        
        # Predict future velocity
        predicted_velocity = self._predict_future_velocity()
        
        return {
            "current_velocity": {
                "daily": daily_velocity,
                "weekly": weekly_velocity,
                "monthly": monthly_velocity
            },
            "trend": trend,
            "predicted_velocity": predicted_velocity,
            "bottlenecks": bottlenecks,
            "recommendations": self._generate_velocity_recommendations()
        }
    
    def _estimate_by_status(self, status: str) -> float:
        """Estimate completion percentage based on status."""
        status_percentages = {
            "completed": 100.0,
            "in_progress": 50.0,
            "pending": 0.0,
            "blocked": 25.0,
            "planned": 0.0
        }
        return status_percentages.get(status, 0.0)
    
    def _is_on_critical_path(self, feature_id: str) -> bool:
        """Check if feature is on the critical path."""
        # A feature is on critical path if it blocks the most other features
        dependents = self.feature_graph.get_all_dependents(feature_id, recursive=True)
        total_features = len(self.feature_graph.features)
        
        # If it blocks more than 30% of features, it's critical
        return len(dependents) > (total_features * 0.3)
    
    def _estimate_completion_date(self, feature_id: str, completion: float) -> Optional[datetime]:
        """Estimate when a feature will be completed."""
        if completion == 100.0:
            return None
        
        # Get historical velocity for this feature
        velocity = self._calculate_feature_velocity(feature_id)
        if not velocity:
            return None
        
        # Calculate remaining work
        remaining = 100.0 - completion
        days_needed = remaining / velocity
        
        # Add buffer for dependencies
        dependencies = self.feature_graph.get_dependencies(feature_id)
        if dependencies:
            # Add 20% buffer for each blocking dependency
            blocking_deps = sum(
                1 for dep_id in dependencies
                if self.feature_graph.features[dep_id].status != "completed"
            )
            days_needed *= (1 + (0.2 * blocking_deps))
        
        return datetime.now() + timedelta(days=days_needed)
    
    def _calculate_feature_velocity(self, feature_id: str) -> Optional[float]:
        """Calculate velocity for a specific feature."""
        # This would typically use historical data from git integration
        # For now, return a mock value based on status
        status = self.feature_graph.features[feature_id].status
        
        if status == "in_progress":
            return 5.0  # 5% per day
        elif status == "blocked":
            return 1.0  # 1% per day when blocked
        else:
            return 2.0  # 2% per day average
    
    def _calculate_current_velocity(self) -> float:
        """Calculate current project velocity."""
        # Count features completed in the last 7 days
        # This would typically use actual completion dates
        completed_recently = sum(
            1 for feature in self.feature_graph.features.values()
            if feature.status == "completed"
        )
        
        return completed_recently / 7.0  # Features per day
    
    def _calculate_average_velocity(self) -> float:
        """Calculate average project velocity."""
        # This would use historical data
        # For now, return mock average
        return 0.5  # Half a feature per day
    
    def _estimate_project_completion_date(self, completion: float, velocity: float) -> Optional[datetime]:
        """Estimate project completion date."""
        if completion == 100.0 or velocity == 0:
            return None
        
        remaining_features = (100.0 - completion) / 100.0 * len(self.feature_graph.features)
        days_needed = remaining_features / velocity
        
        return datetime.now() + timedelta(days=days_needed)
    
    def _generate_burndown_data(self) -> List[Tuple[datetime, float]]:
        """Generate burndown chart data."""
        # This would use historical data
        # For now, generate sample data
        data = []
        current_completion = self.calculate_project_progress().total_completion
        
        for i in range(30):
            date = datetime.now() - timedelta(days=30-i)
            completion = max(0, current_completion - (i * 2))  # Mock decreasing completion
            data.append((date, completion))
        
        return data
    
    def _group_features_by_milestone(self) -> Dict[str, List[str]]:
        """Group features by milestone."""
        # Simple grouping - features without dependencies are milestones
        milestones = {}
        
        for feature_id, feature in self.feature_graph.features.items():
            # If it's an epic or has no dependencies, it's a milestone
            if feature.feature_type == "epic" or not self.feature_graph.get_dependencies(feature_id):
                # Get all features that depend on this
                dependent_features = self.feature_graph.get_all_dependents(feature_id, recursive=True)
                milestones[feature_id] = [feature_id] + list(dependent_features)
        
        return milestones
    
    def _calculate_velocity_by_period(self, days: int) -> float:
        """Calculate velocity over a specific period."""
        # This would use actual completion dates
        # Mock implementation
        return self._calculate_average_velocity() * (days / 7.0)
    
    def _calculate_velocity_trend(self) -> str:
        """Determine if velocity is improving or declining."""
        # This would analyze historical velocity data
        # Mock implementation
        current = self._calculate_current_velocity()
        average = self._calculate_average_velocity()
        
        if current > average * 1.1:
            return "improving"
        elif current < average * 0.9:
            return "declining"
        else:
            return "stable"
    
    def _identify_bottlenecks(self) -> List[Dict[str, any]]:
        """Identify features that are blocking progress."""
        bottlenecks = []
        
        for feature_id, feature in self.feature_graph.features.items():
            if feature.status == "blocked" or feature.status == "pending":
                dependents = self.feature_graph.get_dependents(feature_id)
                if len(dependents) > 2:  # Blocking multiple features
                    bottlenecks.append({
                        "feature_id": feature_id,
                        "name": feature.name,
                        "blocking_count": len(dependents),
                        "blocked_features": list(dependents)
                    })
        
        return sorted(bottlenecks, key=lambda x: x["blocking_count"], reverse=True)
    
    def _predict_future_velocity(self) -> float:
        """Predict future velocity based on trends."""
        # Simple prediction based on current trend
        current = self._calculate_current_velocity()
        trend = self._calculate_velocity_trend()
        
        if trend == "improving":
            return current * 1.1
        elif trend == "declining":
            return current * 0.9
        else:
            return current
    
    def _generate_velocity_recommendations(self) -> List[str]:
        """Generate recommendations to improve velocity."""
        recommendations = []
        
        bottlenecks = self._identify_bottlenecks()
        if bottlenecks:
            recommendations.append(
                f"Focus on unblocking {bottlenecks[0]['name']} which is blocking "
                f"{bottlenecks[0]['blocking_count']} other features"
            )
        
        # Check for too many features in progress
        in_progress = sum(
            1 for feature in self.feature_graph.features.values()
            if feature.status == "in_progress"
        )
        
        if in_progress > 5:
            recommendations.append(
                f"Consider limiting work in progress. Currently {in_progress} features "
                "are in progress, which may impact focus and velocity"
            )
        
        # Check for stale features
        pending_count = sum(
            1 for feature in self.feature_graph.features.values()
            if feature.status == "pending"
        )
        
        if pending_count > len(self.feature_graph.features) * 0.5:
            recommendations.append(
                "Many features are still in pending state. Consider breaking them "
                "down into smaller, actionable tasks"
            )
        
        return recommendations
    
    def predict_completion(self, feature_id: Optional[str] = None) -> CompletionPrediction:
        """Generate ML-based completion prediction for a feature or project.
        
        Args:
            feature_id: Optional feature ID. If None, predicts for entire project.
            
        Returns:
            CompletionPrediction with dates, confidence, and risk factors
        """
        if feature_id:
            return self._predict_feature_completion(feature_id)
        else:
            return self._predict_project_completion()
    
    def _predict_feature_completion(self, feature_id: str) -> CompletionPrediction:
        """Predict completion for a specific feature."""
        feature = self.feature_graph.features[feature_id]
        progress = self.calculate_feature_progress(feature_id)
        
        # Extract features for ML model
        ml_features = self._extract_ml_features(feature_id)
        
        # Get prediction from model
        if self._model:
            try:
                prediction_days = self._model.predict([ml_features])[0]
                confidence = self._calculate_prediction_confidence(ml_features)
            except Exception as e:
                logger.warning(f"ML prediction failed: {e}")
                # Fallback to statistical method
                prediction_days = self._statistical_prediction(feature_id)
                confidence = 0.6
        else:
            prediction_days = self._statistical_prediction(feature_id)
            confidence = 0.6
        
        predicted_date = datetime.now() + timedelta(days=max(0, prediction_days))
        
        # Calculate confidence interval
        confidence_interval = self._calculate_confidence_interval(
            prediction_days, confidence
        )
        
        # Identify risk factors
        risk_factors = self._identify_risk_factors(feature_id)
        
        # Generate recommendations
        recommendations = self._generate_completion_recommendations(
            feature_id, prediction_days, risk_factors
        )
        
        return CompletionPrediction(
            predicted_date=predicted_date,
            confidence=confidence,
            confidence_interval=confidence_interval,
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _predict_project_completion(self) -> CompletionPrediction:
        """Predict completion for entire project."""
        project_progress = self.calculate_project_progress()
        
        # Collect predictions for all incomplete features
        incomplete_features = [
            feature_id for feature_id, feature in self.feature_graph.features.items()
            if feature.status != "completed"
        ]
        
        if not incomplete_features:
            # Project already complete
            return CompletionPrediction(
                predicted_date=datetime.now(),
                confidence=1.0,
                confidence_interval=(datetime.now(), datetime.now()),
                risk_factors=[],
                recommendations=["Project is already complete"]
            )
        
        # Get predictions for all incomplete features
        feature_predictions = []
        for feature_id in incomplete_features:
            pred = self._predict_feature_completion(feature_id)
            feature_predictions.append(pred)
        
        # Calculate project completion based on critical path
        critical_path_features = self._identify_critical_path()
        critical_predictions = [
            pred for pred, fid in zip(feature_predictions, incomplete_features)
            if fid in critical_path_features
        ]
        
        if critical_predictions:
            # Project completes when critical path completes
            latest_date = max(pred.predicted_date for pred in critical_predictions)
            avg_confidence = statistics.mean(pred.confidence for pred in critical_predictions)
        else:
            # Use all features if no critical path
            latest_date = max(pred.predicted_date for pred in feature_predictions)
            avg_confidence = statistics.mean(pred.confidence for pred in feature_predictions)
        
        # Calculate project-level confidence interval
        days_to_completion = (latest_date - datetime.now()).days
        confidence_interval = self._calculate_confidence_interval(
            days_to_completion, avg_confidence
        )
        
        # Aggregate risk factors
        all_risk_factors = []
        for pred in feature_predictions:
            all_risk_factors.extend(pred.risk_factors)
        
        # Deduplicate and prioritize risk factors
        risk_factors = self._prioritize_risk_factors(all_risk_factors)
        
        # Generate project-level recommendations
        recommendations = self._generate_project_recommendations(
            feature_predictions, risk_factors
        )
        
        return CompletionPrediction(
            predicted_date=latest_date,
            confidence=avg_confidence,
            confidence_interval=confidence_interval,
            risk_factors=risk_factors,
            recommendations=recommendations
        )
    
    def _extract_ml_features(self, feature_id: str) -> List[float]:
        """Extract features for machine learning model."""
        feature = self.feature_graph.features[feature_id]
        progress = self.calculate_feature_progress(feature_id)
        
        features = [
            # Progress metrics
            progress.completion_percentage,
            progress.dependencies_completed,
            progress.total_dependencies,
            
            # Velocity metrics
            progress.velocity or 0.0,
            self._calculate_feature_velocity(feature_id) or 0.0,
            
            # Structural metrics
            len(self.feature_graph.get_dependents(feature_id)),
            len(self.feature_graph.get_all_dependents(feature_id, recursive=True)),
            
            # Status encoding
            1.0 if feature.status == "in_progress" else 0.0,
            1.0 if feature.status == "blocked" else 0.0,
            
            # Complexity metrics
            self._estimate_complexity(feature_id),
            self._calculate_dependency_complexity(feature_id),
            
            # Historical metrics
            self._get_historical_velocity_variance(feature_id),
            self._get_historical_accuracy(feature_id)
        ]
        
        return features
    
    def _statistical_prediction(self, feature_id: str) -> float:
        """Fallback statistical prediction method."""
        progress = self.calculate_feature_progress(feature_id)
        
        if progress.completion_percentage >= 100:
            return 0.0
        
        velocity = progress.velocity or self._calculate_feature_velocity(feature_id)
        if not velocity or velocity <= 0:
            return 90.0  # Default to 90 days if no velocity
        
        remaining = 100.0 - progress.completion_percentage
        base_days = remaining / velocity
        
        # Add buffer for dependencies
        dependency_buffer = 1.0 + (0.1 * progress.total_dependencies)
        
        # Add buffer for complexity
        complexity_buffer = 1.0 + (0.1 * self._estimate_complexity(feature_id))
        
        return base_days * dependency_buffer * complexity_buffer
    
    def _calculate_prediction_confidence(self, features: List[float]) -> float:
        """Calculate confidence score for prediction."""
        # Factors that increase confidence:
        # - High completion percentage
        # - Few remaining dependencies
        # - Stable velocity
        # - Low complexity
        
        completion = features[0] / 100.0
        dep_ratio = features[1] / max(features[2], 1)
        velocity_variance = features[12]
        complexity = features[10]
        
        confidence = (
            0.3 * completion +
            0.2 * dep_ratio +
            0.2 * max(0, 1 - velocity_variance) +
            0.3 * max(0, 1 - complexity / 10)
        )
        
        return min(max(confidence, 0.1), 0.95)
    
    def _calculate_confidence_interval(
        self, prediction_days: float, confidence: float
    ) -> Tuple[datetime, datetime]:
        """Calculate confidence interval for prediction."""
        # Width of interval inversely proportional to confidence
        interval_width = prediction_days * (1 - confidence) * 0.5
        
        lower_days = max(0, prediction_days - interval_width)
        upper_days = prediction_days + interval_width
        
        now = datetime.now()
        return (
            now + timedelta(days=lower_days),
            now + timedelta(days=upper_days)
        )
    
    def _identify_risk_factors(self, feature_id: str) -> List[str]:
        """Identify risk factors for completion."""
        risk_factors = []
        feature = self.feature_graph.features[feature_id]
        progress = self.calculate_feature_progress(feature_id)
        
        # Check for blocked dependencies
        blocked_deps = [
            dep_id for dep_id in progress.blockers
            if self.feature_graph.features[dep_id].status == "blocked"
        ]
        if blocked_deps:
            risk_factors.append(f"Blocked by {len(blocked_deps)} features")
        
        # Check velocity variance
        variance = self._get_historical_velocity_variance(feature_id)
        if variance > 0.5:
            risk_factors.append("High velocity variance")
        
        # Check for complexity
        complexity = self._estimate_complexity(feature_id)
        if complexity > 7:
            risk_factors.append("High complexity feature")
        
        # Check for long dependency chains
        if progress.total_dependencies > 5:
            risk_factors.append(f"Complex dependency chain ({progress.total_dependencies} total)")
        
        # Check for stale status
        if feature.status == "pending" and progress.completion_percentage > 0:
            risk_factors.append("Stale progress - may be abandoned")
        
        return risk_factors
    
    def _generate_completion_recommendations(
        self, feature_id: str, prediction_days: float, risk_factors: List[str]
    ) -> List[str]:
        """Generate recommendations for feature completion."""
        recommendations = []
        feature = self.feature_graph.features[feature_id]
        progress = self.calculate_feature_progress(feature_id)
        
        # Recommendations based on prediction timeline
        if prediction_days > 60:
            recommendations.append(
                "Consider breaking down this feature into smaller sub-features"
            )
        
        # Recommendations based on risk factors
        if "Blocked by" in " ".join(risk_factors):
            recommendations.append(
                "Prioritize unblocking dependencies to accelerate progress"
            )
        
        if "High velocity variance" in risk_factors:
            recommendations.append(
                "Stabilize development pace with regular progress updates"
            )
        
        if "High complexity" in risk_factors:
            recommendations.append(
                "Allocate additional resources or expertise for complex tasks"
            )
        
        # Status-based recommendations
        if feature.status == "pending" and progress.dependencies_completed > 0:
            recommendations.append(
                "Dependencies are ready - consider starting this feature"
            )
        
        if feature.status == "blocked":
            blocking_features = progress.blockers
            if blocking_features:
                recommendations.append(
                    f"Focus on completing {blocking_features[0]} to unblock this feature"
                )
        
        return recommendations
    
    def _identify_critical_path(self) -> Set[str]:
        """Identify features on the critical path."""
        critical_path = set()
        
        # Features with no dependents (end goals)
        end_features = [
            fid for fid in self.feature_graph.features
            if not self.feature_graph.get_dependents(fid)
        ]
        
        # Trace back from end features
        for end_feature in end_features:
            path = self._trace_critical_path(end_feature)
            critical_path.update(path)
        
        return critical_path
    
    def _trace_critical_path(self, feature_id: str) -> Set[str]:
        """Trace critical path from a feature."""
        path = {feature_id}
        dependencies = self.feature_graph.get_dependencies(feature_id)
        
        # Find the dependency with the longest completion time
        if dependencies:
            dep_predictions = []
            for dep_id in dependencies:
                if self.feature_graph.features[dep_id].status != "completed":
                    pred = self._predict_feature_completion(dep_id)
                    dep_predictions.append((dep_id, pred.predicted_date))
            
            if dep_predictions:
                # Add the longest dependency to critical path
                longest_dep = max(dep_predictions, key=lambda x: x[1])
                path.update(self._trace_critical_path(longest_dep[0]))
        
        return path
    
    def _prioritize_risk_factors(self, risk_factors: List[str]) -> List[str]:
        """Prioritize and deduplicate risk factors."""
        # Count occurrences
        factor_counts = defaultdict(int)
        for factor in risk_factors:
            factor_counts[factor] += 1
        
        # Sort by frequency and severity
        priority_order = {
            "Blocked by": 3,
            "High complexity": 2,
            "Complex dependency": 2,
            "High velocity variance": 1,
            "Stale progress": 1
        }
        
        def get_priority(factor):
            for key, priority in priority_order.items():
                if key in factor:
                    return priority
            return 0
        
        sorted_factors = sorted(
            factor_counts.items(),
            key=lambda x: (get_priority(x[0]), x[1]),
            reverse=True
        )
        
        return [f"{factor} ({count} features)" for factor, count in sorted_factors[:5]]
    
    def _generate_project_recommendations(
        self, feature_predictions: List[CompletionPrediction], risk_factors: List[str]
    ) -> List[str]:
        """Generate project-level recommendations."""
        recommendations = []
        
        # Find the features with latest completion dates
        latest_features = sorted(
            feature_predictions,
            key=lambda x: x.predicted_date,
            reverse=True
        )[:3]
        
        if latest_features:
            recommendations.append(
                f"Focus on accelerating {len(latest_features)} features on critical path"
            )
        
        # Recommendations based on aggregate risk factors
        if any("Blocked by" in factor for factor in risk_factors):
            recommendations.append(
                "Multiple features are blocked - conduct dependency review"
            )
        
        if any("High complexity" in factor for factor in risk_factors):
            recommendations.append(
                "Several high-complexity features - consider technical spike or POC"
            )
        
        # Check for resource allocation
        in_progress_count = sum(
            1 for f in self.feature_graph.features.values()
            if f.status == "in_progress"
        )
        
        if in_progress_count > 10:
            recommendations.append(
                f"Too many features in progress ({in_progress_count}) - consider focusing efforts"
            )
        
        # Check prediction confidence
        low_confidence_count = sum(
            1 for pred in feature_predictions
            if pred.confidence < 0.5
        )
        
        if low_confidence_count > len(feature_predictions) * 0.3:
            recommendations.append(
                "Many uncertain predictions - improve tracking and estimates"
            )
        
        return recommendations
    
    def _estimate_complexity(self, feature_id: str) -> float:
        """Estimate feature complexity (0-10 scale)."""
        feature = self.feature_graph.features[feature_id]
        
        # Factors that increase complexity:
        # - Number of dependencies
        # - Depth of dependency tree
        # - Number of dependents
        # - Feature type
        
        dependencies = self.feature_graph.get_all_dependencies(feature_id, recursive=True)
        dependents = self.feature_graph.get_all_dependents(feature_id, recursive=True)
        
        complexity = (
            min(len(dependencies) / 3, 3) +  # Up to 3 points for dependencies
            min(len(dependents) / 5, 2) +    # Up to 2 points for dependents
            (2 if feature.feature_type == "epic" else 1) +  # Type complexity
            self._calculate_dependency_depth(feature_id) / 2  # Depth complexity
        )
        
        return min(complexity, 10)
    
    def _calculate_dependency_complexity(self, feature_id: str) -> float:
        """Calculate complexity of dependency graph."""
        dependencies = self.feature_graph.get_all_dependencies(feature_id, recursive=True)
        
        if not dependencies:
            return 0.0
        
        # Calculate average connections per dependency
        total_connections = 0
        for dep_id in dependencies:
            connections = (
                len(self.feature_graph.get_dependencies(dep_id)) +
                len(self.feature_graph.get_dependents(dep_id))
            )
            total_connections += connections
        
        return total_connections / len(dependencies)
    
    def _calculate_dependency_depth(self, feature_id: str) -> int:
        """Calculate maximum dependency depth."""
        def get_depth(fid: str, visited: Set[str]) -> int:
            if fid in visited:
                return 0
            visited.add(fid)
            
            dependencies = self.feature_graph.get_dependencies(fid)
            if not dependencies:
                return 0
            
            max_depth = 0
            for dep_id in dependencies:
                depth = get_depth(dep_id, visited)
                max_depth = max(max_depth, depth)
            
            return max_depth + 1
        
        return get_depth(feature_id, set())
    
    def _get_historical_velocity_variance(self, feature_id: str) -> float:
        """Get variance in historical velocity."""
        # This would use actual historical data
        # Mock implementation returns normalized variance
        return np.random.uniform(0.1, 0.7)
    
    def _get_historical_accuracy(self, feature_id: str) -> float:
        """Get historical prediction accuracy."""
        # This would compare past predictions to actual completion
        # Mock implementation returns accuracy score
        return np.random.uniform(0.6, 0.9)
    
    def _load_historical_data(self):
        """Load historical data and train model if needed."""
        history_path = self._model_path.parent / "history.json"
        
        if history_path.exists():
            try:
                with open(history_path, 'r') as f:
                    self._velocity_history = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
                self._velocity_history = []
        
        # Load or train model
        if self._model_path.exists():
            self._load_model()
        else:
            self._train_model()
    
    def _load_model(self):
        """Load trained model from disk."""
        try:
            import pickle
            with open(self._model_path, 'rb') as f:
                self._model = pickle.load(f)
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            self._model = None
    
    def _train_model(self):
        """Train completion prediction model."""
        # This would use historical data to train model
        # For now, create a simple model
        try:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.linear_model import LinearRegression
            
            # Generate synthetic training data
            X_train, y_train = self._generate_training_data()
            
            if len(X_train) > 10:
                # Use RandomForest for sufficient data
                self._model = RandomForestRegressor(
                    n_estimators=50,
                    max_depth=10,
                    random_state=42
                )
            else:
                # Use LinearRegression for limited data
                self._model = LinearRegression()
            
            self._model.fit(X_train, y_train)
            
            # Save model
            import pickle
            with open(self._model_path, 'wb') as f:
                pickle.dump(self._model, f)
            
        except ImportError:
            logger.warning("scikit-learn not available, using statistical predictions")
            self._model = None
        except Exception as e:
            logger.warning(f"Failed to train model: {e}")
            self._model = None
    
    def _generate_training_data(self) -> Tuple[List[List[float]], List[float]]:
        """Generate synthetic training data."""
        X_train = []
        y_train = []
        
        # Generate synthetic examples based on current features
        for feature_id in self.feature_graph.features:
            try:
                features = self._extract_ml_features(feature_id)
                # Synthetic target: days to completion
                completion = features[0]  # completion_percentage
                if completion < 100:
                    days = np.random.uniform(10, 60) * (1 - completion/100)
                    X_train.append(features)
                    y_train.append(days)
            except Exception:
                continue
        
        # Add some random synthetic examples
        for _ in range(20):
            features = [
                np.random.uniform(0, 100),  # completion
                np.random.randint(0, 5),    # deps completed
                np.random.randint(0, 10),   # total deps
                np.random.uniform(0, 10),   # velocity
                np.random.uniform(0, 10),   # feature velocity
                np.random.randint(0, 5),    # dependents
                np.random.randint(0, 10),   # all dependents
                np.random.choice([0, 1]),   # in_progress
                np.random.choice([0, 1]),   # blocked
                np.random.uniform(0, 10),   # complexity
                np.random.uniform(0, 5),    # dep complexity
                np.random.uniform(0, 1),    # velocity variance
                np.random.uniform(0.5, 1)   # historical accuracy
            ]
            
            # Generate realistic target
            days = max(1, (100 - features[0]) / max(features[3], 1))
            days *= (1 + 0.1 * features[2])  # Dependency factor
            days *= (1 + 0.1 * features[9])  # Complexity factor
            
            X_train.append(features)
            y_train.append(days)
        
        return X_train, y_train
    
    def update_completion_history(self, feature_id: str, actual_completion_date: datetime):
        """Update historical data with actual completion."""
        history_entry = {
            "feature_id": feature_id,
            "completion_date": actual_completion_date.isoformat(),
            "features": self._extract_ml_features(feature_id),
            "predicted_date": self._predict_feature_completion(feature_id).predicted_date.isoformat()
        }
        
        self._velocity_history.append(history_entry)
        
        # Save history
        history_path = self._model_path.parent / "history.json"
        with open(history_path, 'w') as f:
            json.dump(self._velocity_history, f, indent=2)
        
        # Retrain model periodically
        if len(self._velocity_history) % 10 == 0:
            self._train_model()