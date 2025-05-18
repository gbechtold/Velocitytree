"""
Decision tracker for monitoring and analyzing workflow decisions.
Provides insights into decision patterns and effectiveness.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics

from .memory_store import MemoryStore, WorkflowDecision, DecisionType
from ..utils import logger


class DecisionTracker:
    """Tracks and analyzes workflow decisions over time."""
    
    def __init__(self, memory_store: Optional[MemoryStore] = None):
        """Initialize decision tracker.
        
        Args:
            memory_store: MemoryStore instance to use
        """
        self.memory_store = memory_store or MemoryStore()
    
    def record_decision(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        decision: str,
        rationale: str,
        confidence: float = 0.8,
        precedents: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> WorkflowDecision:
        """Record a new workflow decision.
        
        Args:
            decision_type: Type of decision
            context: Decision context information
            decision: The actual decision made
            rationale: Reasoning behind the decision
            confidence: Confidence level (0-1)
            precedents: IDs of precedent decisions
            tags: Optional tags for categorization
            user_id: User who triggered the decision
            project_id: Project context
            
        Returns:
            The created WorkflowDecision
        """
        workflow_decision = WorkflowDecision(
            decision_type=decision_type,
            context=context,
            decision=decision,
            rationale=rationale,
            confidence=confidence,
            precedents=precedents or [],
            tags=tags or [],
            user_id=user_id,
            project_id=project_id
        )
        
        success = self.memory_store.add_decision(workflow_decision)
        
        if success:
            logger.info(f"Recorded {decision_type.value} decision: {decision[:50]}...")
        else:
            logger.error("Failed to record decision")
        
        return workflow_decision
    
    def get_decision_history(
        self,
        decision_type: Optional[DecisionType] = None,
        days: int = 30,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[WorkflowDecision]:
        """Get decision history for analysis.
        
        Args:
            decision_type: Filter by type
            days: Number of days to look back
            project_id: Filter by project
            user_id: Filter by user
            
        Returns:
            List of decisions
        """
        start_date = datetime.now() - timedelta(days=days)
        
        return self.memory_store.get_decisions(
            decision_type=decision_type,
            project_id=project_id,
            user_id=user_id,
            start_date=start_date
        )
    
    def analyze_decision_patterns(
        self,
        project_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Analyze patterns in decision-making.
        
        Args:
            project_id: Project to analyze
            days: Time period to analyze
            
        Returns:
            Analysis results including patterns and trends
        """
        decisions = self.get_decision_history(days=days, project_id=project_id)
        
        if not decisions:
            return {
                'total_decisions': 0,
                'patterns': {},
                'trends': {},
                'recommendations': []
            }
        
        # Group by type
        by_type = defaultdict(list)
        for decision in decisions:
            by_type[decision.decision_type.value].append(decision)
        
        # Analyze patterns
        patterns = {}
        for decision_type, type_decisions in by_type.items():
            patterns[decision_type] = {
                'count': len(type_decisions),
                'average_confidence': statistics.mean(
                    d.confidence for d in type_decisions
                ),
                'success_rate': self._calculate_success_rate(type_decisions),
                'common_contexts': self._extract_common_contexts(type_decisions),
                'time_distribution': self._analyze_time_distribution(type_decisions)
            }
        
        # Analyze trends
        trends = {
            'decision_frequency': self._calculate_frequency_trend(decisions),
            'confidence_trend': self._calculate_confidence_trend(decisions),
            'success_trend': self._calculate_success_trend(decisions)
        }
        
        # Generate recommendations
        recommendations = self._generate_recommendations(patterns, trends)
        
        return {
            'total_decisions': len(decisions),
            'patterns': patterns,
            'trends': trends,
            'recommendations': recommendations
        }
    
    def get_similar_decisions(
        self,
        context: Dict[str, Any],
        decision_type: Optional[DecisionType] = None,
        threshold: float = 0.7,
        limit: int = 5
    ) -> List[WorkflowDecision]:
        """Find similar past decisions based on context.
        
        Args:
            context: Context to match against
            decision_type: Filter by type
            threshold: Similarity threshold (0-1)
            limit: Maximum number of results
            
        Returns:
            List of similar decisions sorted by relevance
        """
        # Get candidate decisions
        candidates = self.memory_store.get_decisions(
            decision_type=decision_type,
            limit=100  # Get more candidates for filtering
        )
        
        # Calculate similarity scores
        scored_decisions = []
        for decision in candidates:
            similarity = self._calculate_context_similarity(
                context,
                decision.context
            )
            
            if similarity >= threshold:
                scored_decisions.append((similarity, decision))
        
        # Sort by similarity and return top results
        scored_decisions.sort(key=lambda x: x[0], reverse=True)
        return [decision for _, decision in scored_decisions[:limit]]
    
    def evaluate_decision_effectiveness(
        self,
        decision_id: str
    ) -> Dict[str, Any]:
        """Evaluate the effectiveness of a specific decision.
        
        Args:
            decision_id: ID of decision to evaluate
            
        Returns:
            Evaluation metrics and insights
        """
        decision = self.memory_store.get_decision(decision_id)
        if not decision:
            return {'error': 'Decision not found'}
        
        # Get related decisions
        related = self.memory_store.get_related_decisions(decision_id)
        
        # Get decision statistics
        stats = self.memory_store.get_statistics(
            project_id=decision.project_id
        )
        
        # Calculate effectiveness metrics
        return {
            'decision': decision.decision,
            'confidence': decision.confidence,
            'outcome': decision.outcome,
            'success': decision.outcome is not None and 'success' in decision.outcome.lower(),
            'related_decisions': len(related),
            'type_success_rate': stats.get('success_rate', 0),
            'recommendations': self._generate_effectiveness_recommendations(decision)
        }
    
    def _calculate_success_rate(self, decisions: List[WorkflowDecision]) -> float:
        """Calculate success rate for a set of decisions."""
        if not decisions:
            return 0.0
        
        successful = sum(
            1 for d in decisions
            if d.outcome and 'success' in d.outcome.lower()
        )
        
        return successful / len(decisions)
    
    def _extract_common_contexts(
        self,
        decisions: List[WorkflowDecision]
    ) -> Dict[str, Any]:
        """Extract common context patterns from decisions."""
        context_keys = defaultdict(list)
        
        for decision in decisions:
            for key, value in decision.context.items():
                context_keys[key].append(value)
        
        # Find most common values for each key
        common_contexts = {}
        for key, values in context_keys.items():
            # For string values, find most common
            if all(isinstance(v, str) for v in values):
                common_value = max(set(values), key=values.count)
                common_contexts[key] = {
                    'most_common': common_value,
                    'frequency': values.count(common_value) / len(values)
                }
        
        return common_contexts
    
    def _analyze_time_distribution(
        self,
        decisions: List[WorkflowDecision]
    ) -> Dict[str, Any]:
        """Analyze when decisions are typically made."""
        hour_distribution = defaultdict(int)
        day_distribution = defaultdict(int)
        
        for decision in decisions:
            hour = decision.timestamp.hour
            day = decision.timestamp.weekday()
            
            hour_distribution[hour] += 1
            day_distribution[day] += 1
        
        return {
            'hourly': dict(hour_distribution),
            'daily': dict(day_distribution),
            'peak_hour': max(hour_distribution.items(), key=lambda x: x[1])[0],
            'peak_day': max(day_distribution.items(), key=lambda x: x[1])[0]
        }
    
    def _calculate_frequency_trend(
        self,
        decisions: List[WorkflowDecision]
    ) -> Dict[str, Any]:
        """Calculate decision frequency trend over time."""
        if not decisions:
            return {}
        
        # Group by day
        daily_counts = defaultdict(int)
        for decision in decisions:
            day = decision.timestamp.date()
            daily_counts[day] += 1
        
        # Calculate trend
        sorted_days = sorted(daily_counts.items())
        if len(sorted_days) < 2:
            return {'trend': 'stable', 'change': 0}
        
        # Simple linear trend
        first_week = sum(count for day, count in sorted_days[:7])
        last_week = sum(count for day, count in sorted_days[-7:])
        
        change = (last_week - first_week) / max(first_week, 1)
        
        return {
            'trend': 'increasing' if change > 0.1 else 'decreasing' if change < -0.1 else 'stable',
            'change': change,
            'daily_average': len(decisions) / len(daily_counts)
        }
    
    def _calculate_confidence_trend(
        self,
        decisions: List[WorkflowDecision]
    ) -> Dict[str, Any]:
        """Calculate confidence level trend over time."""
        if not decisions:
            return {}
        
        # Sort by timestamp
        sorted_decisions = sorted(decisions, key=lambda d: d.timestamp)
        
        # Calculate rolling average
        window_size = min(10, len(decisions) // 3)
        if window_size < 2:
            return {'trend': 'stable', 'change': 0}
        
        early_confidence = statistics.mean(
            d.confidence for d in sorted_decisions[:window_size]
        )
        late_confidence = statistics.mean(
            d.confidence for d in sorted_decisions[-window_size:]
        )
        
        change = late_confidence - early_confidence
        
        return {
            'trend': 'increasing' if change > 0.05 else 'decreasing' if change < -0.05 else 'stable',
            'change': change,
            'current_average': late_confidence
        }
    
    def _calculate_success_trend(
        self,
        decisions: List[WorkflowDecision]
    ) -> Dict[str, Any]:
        """Calculate success rate trend over time."""
        # Only consider decisions with outcomes
        decisions_with_outcomes = [
            d for d in decisions if d.outcome is not None
        ]
        
        if len(decisions_with_outcomes) < 5:
            return {'trend': 'insufficient_data', 'change': 0}
        
        # Sort by timestamp
        sorted_decisions = sorted(decisions_with_outcomes, key=lambda d: d.timestamp)
        
        # Calculate rolling success rate
        window_size = min(10, len(decisions_with_outcomes) // 3)
        
        early_success = self._calculate_success_rate(sorted_decisions[:window_size])
        late_success = self._calculate_success_rate(sorted_decisions[-window_size:])
        
        change = late_success - early_success
        
        return {
            'trend': 'improving' if change > 0.1 else 'declining' if change < -0.1 else 'stable',
            'change': change,
            'current_rate': late_success
        }
    
    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two contexts."""
        if not context1 or not context2:
            return 0.0
        
        # Get all keys
        all_keys = set(context1.keys()) | set(context2.keys())
        if not all_keys:
            return 0.0
        
        # Calculate matches
        matches = 0
        for key in all_keys:
            if key in context1 and key in context2:
                if context1[key] == context2[key]:
                    matches += 1
                elif isinstance(context1[key], str) and isinstance(context2[key], str):
                    # Partial string matching
                    if context1[key].lower() in context2[key].lower() or \
                       context2[key].lower() in context1[key].lower():
                        matches += 0.5
        
        return matches / len(all_keys)
    
    def _generate_recommendations(
        self,
        patterns: Dict[str, Any],
        trends: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on patterns and trends."""
        recommendations = []
        
        # Check confidence trends
        if trends.get('confidence_trend', {}).get('trend') == 'decreasing':
            recommendations.append(
                "Decision confidence is declining. Consider reviewing decision criteria "
                "and providing more context for decisions."
            )
        
        # Check success trends
        if trends.get('success_trend', {}).get('trend') == 'declining':
            recommendations.append(
                "Success rate is declining. Review recent failed decisions and "
                "adjust decision-making strategies."
            )
        
        # Check for low confidence patterns
        for decision_type, pattern in patterns.items():
            if pattern['average_confidence'] < 0.6:
                recommendations.append(
                    f"Low confidence in {decision_type} decisions. "
                    f"Consider gathering more information or using precedents."
                )
            
            if pattern['success_rate'] < 0.7:
                recommendations.append(
                    f"{decision_type} decisions have low success rate ({pattern['success_rate']:.1%}). "
                    f"Review and improve decision criteria."
                )
        
        # Check decision frequency
        freq_trend = trends.get('decision_frequency', {})
        if freq_trend.get('trend') == 'increasing' and freq_trend.get('change', 0) > 0.5:
            recommendations.append(
                "Rapid increase in decision frequency. Ensure quality is maintained "
                "and consider automation for repetitive decisions."
            )
        
        return recommendations
    
    def _generate_effectiveness_recommendations(
        self,
        decision: WorkflowDecision
    ) -> List[str]:
        """Generate recommendations for a specific decision."""
        recommendations = []
        
        if decision.confidence < 0.6:
            recommendations.append(
                "Low confidence decision. Consider gathering more information "
                "or consulting similar precedents."
            )
        
        if not decision.precedents:
            recommendations.append(
                "No precedents used. Consider reviewing similar past decisions "
                "for better context."
            )
        
        if not decision.outcome:
            recommendations.append(
                "No outcome recorded. Track the results of this decision "
                "to improve future decision-making."
            )
        
        return recommendations