"""
Precedent engine for finding and applying past decisions to new situations.
Uses similarity matching to identify relevant precedents.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
from collections import defaultdict
from datetime import datetime

from .memory_store import MemoryStore, WorkflowDecision, DecisionType
from .decision_tracker import DecisionTracker
from ..utils import logger


@dataclass
class Precedent:
    """Represents a precedent decision with relevance score."""
    decision: WorkflowDecision
    relevance_score: float
    matching_factors: Dict[str, float]
    context_similarity: float
    outcome_success: bool


class PrecedentEngine:
    """Engine for finding and applying precedents to new decisions."""
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        decision_tracker: Optional[DecisionTracker] = None
    ):
        """Initialize precedent engine.
        
        Args:
            memory_store: MemoryStore instance
            decision_tracker: DecisionTracker instance
        """
        self.memory_store = memory_store or MemoryStore()
        self.decision_tracker = decision_tracker or DecisionTracker(self.memory_store)
        
        # Weights for different matching factors
        self.weights = {
            'context_similarity': 0.4,
            'type_match': 0.2,
            'recency': 0.1,
            'success': 0.2,
            'confidence': 0.1
        }
    
    def find_precedents(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        limit: int = 5,
        min_relevance: float = 0.5,
        project_id: Optional[str] = None
    ) -> List[Precedent]:
        """Find relevant precedents for a new decision.
        
        Args:
            decision_type: Type of decision
            context: Context for the new decision
            limit: Maximum number of precedents to return
            min_relevance: Minimum relevance score threshold
            project_id: Optional project filter
            
        Returns:
            List of relevant precedents sorted by relevance
        """
        # Get candidate decisions
        candidates = self.memory_store.get_decisions(
            decision_type=decision_type,
            project_id=project_id,
            limit=100  # Get more candidates for scoring
        )
        
        # Score each candidate
        scored_precedents = []
        for candidate in candidates:
            precedent = self._score_precedent(candidate, context, decision_type)
            
            if precedent.relevance_score >= min_relevance:
                scored_precedents.append(precedent)
        
        # Sort by relevance and return top results
        scored_precedents.sort(key=lambda p: p.relevance_score, reverse=True)
        return scored_precedents[:limit]
    
    def apply_precedent(
        self,
        precedent: Precedent,
        current_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a precedent to generate a new decision recommendation.
        
        Args:
            precedent: The precedent to apply
            current_context: Current decision context
            
        Returns:
            Decision recommendation based on precedent
        """
        decision = precedent.decision
        
        # Extract key elements from precedent
        recommendation = {
            'decision': self._adapt_decision(decision.decision, current_context),
            'rationale': self._adapt_rationale(
                decision.rationale,
                precedent,
                current_context
            ),
            'confidence': self._adjust_confidence(
                decision.confidence,
                precedent.relevance_score
            ),
            'precedent_id': decision.id,
            'adaptations': self._identify_adaptations(
                decision.context,
                current_context
            )
        }
        
        return recommendation
    
    def learn_from_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool,
        metrics: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Learn from the outcome of a decision that used precedents.
        
        Args:
            decision_id: ID of the decision
            outcome: Outcome description
            success: Whether the outcome was successful
            metrics: Optional performance metrics
            
        Returns:
            True if learning was successful
        """
        # Update the decision outcome
        self.memory_store.update_outcome(
            decision_id,
            outcome,
            success,
            metrics
        )
        
        # Get the decision
        decision = self.memory_store.get_decision(decision_id)
        if not decision:
            return False
        
        # Update precedent effectiveness
        for precedent_id in decision.precedents:
            self._update_precedent_effectiveness(precedent_id, success)
        
        logger.info(f"Learned from outcome of decision {decision_id}")
        return True
    
    def get_precedent_statistics(
        self,
        decision_type: Optional[DecisionType] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics about precedent usage and effectiveness.
        
        Args:
            decision_type: Optional filter by type
            project_id: Optional filter by project
            
        Returns:
            Statistics about precedent usage
        """
        decisions = self.memory_store.get_decisions(
            decision_type=decision_type,
            project_id=project_id
        )
        
        total_decisions = len(decisions)
        decisions_with_precedents = sum(
            1 for d in decisions if d.precedents
        )
        
        # Calculate precedent effectiveness
        precedent_success = []
        for decision in decisions:
            if decision.precedents and decision.outcome:
                success = 'success' in decision.outcome.lower()
                precedent_success.append(success)
        
        success_rate = (
            sum(precedent_success) / len(precedent_success)
            if precedent_success else 0
        )
        
        # Most used precedents
        precedent_usage = defaultdict(int)
        for decision in decisions:
            for precedent_id in decision.precedents:
                precedent_usage[precedent_id] += 1
        
        most_used = sorted(
            precedent_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            'total_decisions': total_decisions,
            'decisions_with_precedents': decisions_with_precedents,
            'precedent_usage_rate': (
                decisions_with_precedents / total_decisions
                if total_decisions > 0 else 0
            ),
            'precedent_success_rate': success_rate,
            'most_used_precedents': most_used,
            'average_precedents_per_decision': (
                sum(len(d.precedents) for d in decisions) / total_decisions
                if total_decisions > 0 else 0
            )
        }
    
    def _score_precedent(
        self,
        candidate: WorkflowDecision,
        context: Dict[str, Any],
        decision_type: DecisionType
    ) -> Precedent:
        """Score a candidate decision as a potential precedent."""
        # Calculate matching factors
        matching_factors = {}
        
        # Context similarity
        context_similarity = self._calculate_context_similarity(
            candidate.context,
            context
        )
        matching_factors['context_similarity'] = context_similarity
        
        # Type match (already filtered, so this is 1.0)
        matching_factors['type_match'] = 1.0
        
        # Recency (newer decisions score higher)
        age_days = (datetime.now() - candidate.timestamp).days
        recency_score = max(0, 1 - (age_days / 365))  # Linear decay over a year
        matching_factors['recency'] = recency_score
        
        # Success (decisions with positive outcomes score higher)
        outcome_success = False
        if candidate.outcome:
            outcome_success = 'success' in candidate.outcome.lower()
            matching_factors['success'] = 1.0 if outcome_success else 0.5
        else:
            matching_factors['success'] = 0.7  # Unknown outcome
        
        # Confidence (higher confidence decisions score higher)
        matching_factors['confidence'] = candidate.confidence
        
        # Calculate weighted relevance score
        relevance_score = sum(
            self.weights[factor] * score
            for factor, score in matching_factors.items()
        )
        
        return Precedent(
            decision=candidate,
            relevance_score=relevance_score,
            matching_factors=matching_factors,
            context_similarity=context_similarity,
            outcome_success=outcome_success
        )
    
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
            return 1.0  # Both empty contexts are similar
        
        # Calculate similarity for each key
        similarities = []
        for key in all_keys:
            if key in context1 and key in context2:
                similarity = self._compare_values(context1[key], context2[key])
                similarities.append(similarity)
            else:
                # Key missing in one context
                similarities.append(0.0)
        
        # Average similarity across all keys
        return sum(similarities) / len(similarities)
    
    def _compare_values(self, value1: Any, value2: Any) -> float:
        """Compare two values and return similarity score."""
        if value1 == value2:
            return 1.0
        
        # String comparison
        if isinstance(value1, str) and isinstance(value2, str):
            # Case-insensitive partial matching
            v1_lower = value1.lower()
            v2_lower = value2.lower()
            
            if v1_lower == v2_lower:
                return 1.0
            elif v1_lower in v2_lower or v2_lower in v1_lower:
                return 0.7
            else:
                # Token-based similarity
                tokens1 = set(v1_lower.split())
                tokens2 = set(v2_lower.split())
                
                if not tokens1 or not tokens2:
                    return 0.0
                
                intersection = len(tokens1 & tokens2)
                union = len(tokens1 | tokens2)
                
                return intersection / union if union > 0 else 0.0
        
        # Numeric comparison
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            # Calculate relative difference
            if value1 == 0 and value2 == 0:
                return 1.0
            
            max_val = max(abs(value1), abs(value2))
            diff = abs(value1 - value2)
            
            return max(0, 1 - (diff / max_val))
        
        # List comparison
        if isinstance(value1, list) and isinstance(value2, list):
            if not value1 and not value2:
                return 1.0
            if not value1 or not value2:
                return 0.0
            
            # Calculate Jaccard similarity
            set1 = set(str(v) for v in value1)
            set2 = set(str(v) for v in value2)
            
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            
            return intersection / union if union > 0 else 0.0
        
        # Different types
        return 0.0
    
    def _adapt_decision(
        self,
        original_decision: str,
        current_context: Dict[str, Any]
    ) -> str:
        """Adapt a precedent decision to current context."""
        adapted = original_decision
        
        # Replace context-specific values
        for key, value in current_context.items():
            if isinstance(value, str):
                # Simple placeholder replacement
                placeholder = f"{{{key}}}"
                if placeholder in adapted:
                    adapted = adapted.replace(placeholder, value)
        
        return adapted
    
    def _adapt_rationale(
        self,
        original_rationale: str,
        precedent: Precedent,
        current_context: Dict[str, Any]
    ) -> str:
        """Adapt precedent rationale to current situation."""
        adapted = (
            f"Based on similar precedent with {precedent.relevance_score:.0%} relevance. "
            f"Original rationale: {original_rationale}"
        )
        
        # Add context differences
        differences = self._identify_adaptations(
            precedent.decision.context,
            current_context
        )
        
        if differences:
            adapted += f"\n\nContext adaptations: {', '.join(differences)}"
        
        return adapted
    
    def _adjust_confidence(
        self,
        original_confidence: float,
        relevance_score: float
    ) -> float:
        """Adjust confidence based on precedent relevance."""
        # Lower confidence for less relevant precedents
        adjusted = original_confidence * (0.7 + 0.3 * relevance_score)
        return min(adjusted, 0.95)  # Cap at 95% for precedent-based decisions
    
    def _identify_adaptations(
        self,
        original_context: Dict[str, Any],
        current_context: Dict[str, Any]
    ) -> List[str]:
        """Identify key differences between contexts."""
        adaptations = []
        
        # Check for missing keys
        missing_in_current = set(original_context.keys()) - set(current_context.keys())
        for key in missing_in_current:
            adaptations.append(f"Missing {key} in current context")
        
        # Check for new keys
        new_in_current = set(current_context.keys()) - set(original_context.keys())
        for key in new_in_current:
            adaptations.append(f"New factor: {key}")
        
        # Check for different values
        for key in set(original_context.keys()) & set(current_context.keys()):
            if original_context[key] != current_context[key]:
                adaptations.append(
                    f"{key} changed from {original_context[key]} to {current_context[key]}"
                )
        
        return adaptations
    
    def _update_precedent_effectiveness(
        self,
        precedent_id: str,
        success: bool
    ):
        """Update the effectiveness tracking for a precedent."""
        # This could be expanded to maintain a separate effectiveness score
        # For now, we just log the usage
        logger.info(
            f"Precedent {precedent_id} used with "
            f"{'successful' if success else 'unsuccessful'} outcome"
        )
        
        # Could implement a more sophisticated tracking system here
        # that influences future precedent scoring