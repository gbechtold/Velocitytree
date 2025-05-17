"""Progress tracking and completion percentage calculations."""

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

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
    estimated_completion_date: Optional[datetime] = None
    current_velocity: float
    average_velocity: float
    burndown_data: List[Tuple[datetime, float]] = field(default_factory=list)


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