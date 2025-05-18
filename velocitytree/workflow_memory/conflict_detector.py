"""
Conflict detector for identifying and resolving contradictory decisions.
Helps maintain consistency in workflow decisions over time.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from .memory_store import MemoryStore, WorkflowDecision, DecisionType
from .precedent_engine import PrecedentEngine
from ..utils import logger


class ConflictType(Enum):
    """Types of decision conflicts."""
    CONTRADICTORY_OUTCOME = "contradictory_outcome"
    INCOMPATIBLE_CONTEXT = "incompatible_context"
    POLICY_VIOLATION = "policy_violation"
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"
    RESOURCE_CONFLICT = "resource_conflict"
    DEPENDENCY_CONFLICT = "dependency_conflict"


@dataclass
class DecisionConflict:
    """Represents a conflict between decisions."""
    id: str
    decision1: WorkflowDecision
    decision2: WorkflowDecision
    conflict_type: ConflictType
    severity: float  # 0.0 to 1.0
    description: str
    resolution_suggestions: List[str]
    detected_at: datetime = None
    
    def __post_init__(self):
        if self.detected_at is None:
            self.detected_at = datetime.now()


class ConflictDetector:
    """Detects and helps resolve conflicts between workflow decisions."""
    
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        precedent_engine: Optional[PrecedentEngine] = None
    ):
        """Initialize conflict detector.
        
        Args:
            memory_store: MemoryStore instance
            precedent_engine: PrecedentEngine instance
        """
        self.memory_store = memory_store or MemoryStore()
        self.precedent_engine = precedent_engine or PrecedentEngine(self.memory_store)
        
        # Define conflict detection rules
        self.conflict_rules = {
            ConflictType.CONTRADICTORY_OUTCOME: self._check_contradictory_outcomes,
            ConflictType.INCOMPATIBLE_CONTEXT: self._check_incompatible_contexts,
            ConflictType.POLICY_VIOLATION: self._check_policy_violations,
            ConflictType.TEMPORAL_INCONSISTENCY: self._check_temporal_inconsistency,
            ConflictType.RESOURCE_CONFLICT: self._check_resource_conflicts,
            ConflictType.DEPENDENCY_CONFLICT: self._check_dependency_conflicts
        }
        
        # Severity thresholds
        self.severity_threshold = 0.5  # Minimum severity to report
    
    def detect_conflicts(
        self,
        new_decision: WorkflowDecision,
        check_window_days: int = 30,
        project_id: Optional[str] = None
    ) -> List[DecisionConflict]:
        """Detect conflicts between a new decision and existing ones.
        
        Args:
            new_decision: The new decision to check
            check_window_days: Number of days to look back for conflicts
            project_id: Optional project filter
            
        Returns:
            List of detected conflicts
        """
        # Get relevant existing decisions
        existing_decisions = self.memory_store.get_decisions(
            decision_type=new_decision.decision_type,
            project_id=project_id or new_decision.project_id,
            start_date=datetime.now() - timedelta(days=check_window_days)
        )
        
        conflicts = []
        
        # Check against each existing decision
        for existing in existing_decisions:
            if existing.id == new_decision.id:
                continue  # Skip self
            
            # Apply each conflict detection rule
            for conflict_type, check_func in self.conflict_rules.items():
                conflict = check_func(new_decision, existing)
                
                if conflict and conflict.severity >= self.severity_threshold:
                    conflicts.append(conflict)
        
        # Sort by severity
        conflicts.sort(key=lambda c: c.severity, reverse=True)
        
        return conflicts
    
    def resolve_conflict(
        self,
        conflict: DecisionConflict,
        resolution_method: str = "latest_wins"
    ) -> Dict[str, Any]:
        """Suggest resolution for a detected conflict.
        
        Args:
            conflict: The conflict to resolve
            resolution_method: Method to use for resolution
            
        Returns:
            Resolution recommendation
        """
        resolution = {
            'conflict_id': conflict.id,
            'method': resolution_method,
            'recommendation': '',
            'actions': [],
            'confidence': 0.0
        }
        
        if resolution_method == "latest_wins":
            resolution['recommendation'] = (
                f"Accept the newer decision ({conflict.decision2.id}) "
                f"and update any dependencies from the older decision."
            )
            resolution['actions'] = [
                f"Mark decision {conflict.decision1.id} as superseded",
                f"Update references to use {conflict.decision2.id}",
                "Document the conflict resolution"
            ]
            resolution['confidence'] = 0.8
        
        elif resolution_method == "precedent_based":
            # Use precedent engine to find best resolution
            precedents = self.precedent_engine.find_precedents(
                decision_type=conflict.decision1.decision_type,
                context={
                    'conflict_type': conflict.conflict_type.value,
                    'decisions': [conflict.decision1.id, conflict.decision2.id]
                }
            )
            
            if precedents:
                best_precedent = precedents[0]
                resolution['recommendation'] = (
                    f"Follow precedent {best_precedent.decision.id}: "
                    f"{best_precedent.decision.decision}"
                )
                resolution['confidence'] = best_precedent.relevance_score
            else:
                resolution['recommendation'] = "No clear precedent found"
                resolution['confidence'] = 0.3
        
        elif resolution_method == "merge":
            resolution['recommendation'] = (
                "Merge both decisions by combining their contexts and outcomes"
            )
            resolution['actions'] = [
                "Create a new decision combining both contexts",
                "Reference both original decisions as precedents",
                "Mark originals as merged"
            ]
            resolution['confidence'] = 0.7
        
        elif resolution_method == "manual":
            resolution['recommendation'] = (
                "Requires manual intervention to resolve the conflict"
            )
            resolution['actions'] = [
                "Review both decisions in detail",
                "Consult with stakeholders",
                "Document the resolution rationale"
            ]
            resolution['confidence'] = 0.5
        
        return resolution
    
    def check_consistency(
        self,
        project_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Check overall consistency of decisions in a project.
        
        Args:
            project_id: Project to check
            days: Time window to analyze
            
        Returns:
            Consistency report
        """
        decisions = self.memory_store.get_decisions(
            project_id=project_id,
            start_date=datetime.now() - timedelta(days=days)
        )
        
        all_conflicts = []
        conflict_matrix = {}
        
        # Check all pairs of decisions
        for i, decision1 in enumerate(decisions):
            for decision2 in decisions[i+1:]:
                conflicts = []
                
                # Check each conflict type
                for conflict_type, check_func in self.conflict_rules.items():
                    conflict = check_func(decision1, decision2)
                    if conflict and conflict.severity >= self.severity_threshold:
                        conflicts.append(conflict)
                        all_conflicts.append(conflict)
                
                if conflicts:
                    key = f"{decision1.id}:{decision2.id}"
                    conflict_matrix[key] = conflicts
        
        # Calculate consistency metrics
        total_decisions = len(decisions)
        decisions_with_conflicts = len(set(
            d.id for c in all_conflicts 
            for d in [c.decision1, c.decision2]
        ))
        
        consistency_score = 1.0 - (
            decisions_with_conflicts / total_decisions
            if total_decisions > 0 else 0
        )
        
        # Group conflicts by type
        conflicts_by_type = {}
        for conflict in all_conflicts:
            conflict_type = conflict.conflict_type.value
            if conflict_type not in conflicts_by_type:
                conflicts_by_type[conflict_type] = []
            conflicts_by_type[conflict_type].append(conflict)
        
        return {
            'consistency_score': consistency_score,
            'total_decisions': total_decisions,
            'decisions_with_conflicts': decisions_with_conflicts,
            'total_conflicts': len(all_conflicts),
            'conflicts_by_type': {
                k: len(v) for k, v in conflicts_by_type.items()
            },
            'most_conflicted_decisions': self._identify_most_conflicted(all_conflicts),
            'recommendations': self._generate_consistency_recommendations(
                consistency_score,
                conflicts_by_type
            )
        }
    
    def _check_contradictory_outcomes(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for contradictory outcomes between decisions."""
        # Only check if both have outcomes
        if not decision1.outcome or not decision2.outcome:
            return None
        
        # Similar contexts but different outcomes
        context_similarity = self._calculate_context_similarity(
            decision1.context,
            decision2.context
        )
        
        if context_similarity > 0.8:
            # High context similarity
            outcome_similarity = self._calculate_outcome_similarity(
                decision1.outcome,
                decision2.outcome
            )
            
            if outcome_similarity < 0.3:
                # Low outcome similarity with high context similarity = conflict
                severity = context_similarity * (1 - outcome_similarity)
                
                return DecisionConflict(
                    id=f"conflict_{decision1.id}_{decision2.id}_outcome",
                    decision1=decision1,
                    decision2=decision2,
                    conflict_type=ConflictType.CONTRADICTORY_OUTCOME,
                    severity=severity,
                    description=(
                        f"Similar contexts led to contradictory outcomes: "
                        f"'{decision1.outcome}' vs '{decision2.outcome}'"
                    ),
                    resolution_suggestions=[
                        "Review the decision criteria",
                        "Identify missing context factors",
                        "Establish clearer decision guidelines"
                    ]
                )
        
        return None
    
    def _check_incompatible_contexts(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for incompatible contexts between related decisions."""
        # Check if decisions are related
        if decision1.id in decision2.precedents or decision2.id in decision1.precedents:
            # Related decisions should have compatible contexts
            incompatibilities = self._find_context_incompatibilities(
                decision1.context,
                decision2.context
            )
            
            if incompatibilities:
                severity = len(incompatibilities) / max(
                    len(decision1.context),
                    len(decision2.context),
                    1
                )
                
                return DecisionConflict(
                    id=f"conflict_{decision1.id}_{decision2.id}_context",
                    decision1=decision1,
                    decision2=decision2,
                    conflict_type=ConflictType.INCOMPATIBLE_CONTEXT,
                    severity=severity,
                    description=(
                        f"Related decisions have incompatible contexts: "
                        f"{', '.join(incompatibilities)}"
                    ),
                    resolution_suggestions=[
                        "Reconcile context differences",
                        "Update decision relationships",
                        "Create context transformation rules"
                    ]
                )
        
        return None
    
    def _check_policy_violations(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for policy violations between decisions."""
        # This would check against defined policies
        # For now, we'll check some basic consistency rules
        
        # Example: Check for confidence threshold violations
        if decision1.confidence > 0.9 and decision2.confidence < 0.3:
            if self._calculate_context_similarity(
                decision1.context,
                decision2.context
            ) > 0.7:
                return DecisionConflict(
                    id=f"conflict_{decision1.id}_{decision2.id}_policy",
                    decision1=decision1,
                    decision2=decision2,
                    conflict_type=ConflictType.POLICY_VIOLATION,
                    severity=0.7,
                    description=(
                        "High confidence decision contradicts low confidence decision "
                        "in similar context"
                    ),
                    resolution_suggestions=[
                        "Review low confidence decision",
                        "Update decision confidence thresholds",
                        "Establish confidence policies"
                    ]
                )
        
        return None
    
    def _check_temporal_inconsistency(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for temporal inconsistencies between decisions."""
        # Check if newer decision invalidates older one
        if decision1.timestamp < decision2.timestamp:
            older, newer = decision1, decision2
        else:
            older, newer = decision2, decision1
        
        # Check if they reference the same entity/resource
        entity_match = self._check_entity_match(older.context, newer.context)
        
        if entity_match:
            # Check for state changes that invalidate older decision
            if self._check_state_invalidation(older, newer):
                severity = 0.8
                
                return DecisionConflict(
                    id=f"conflict_{older.id}_{newer.id}_temporal",
                    decision1=older,
                    decision2=newer,
                    conflict_type=ConflictType.TEMPORAL_INCONSISTENCY,
                    severity=severity,
                    description=(
                        f"Newer decision invalidates older decision for {entity_match}"
                    ),
                    resolution_suggestions=[
                        "Update or revoke older decision",
                        "Create temporal validity rules",
                        "Implement decision versioning"
                    ]
                )
        
        return None
    
    def _check_resource_conflicts(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for resource allocation conflicts."""
        # Check if decisions allocate the same resources
        resources1 = self._extract_resources(decision1.context)
        resources2 = self._extract_resources(decision2.context)
        
        conflicting_resources = resources1 & resources2
        
        if conflicting_resources:
            severity = len(conflicting_resources) / max(
                len(resources1),
                len(resources2),
                1
            )
            
            return DecisionConflict(
                id=f"conflict_{decision1.id}_{decision2.id}_resource",
                decision1=decision1,
                decision2=decision2,
                conflict_type=ConflictType.RESOURCE_CONFLICT,
                severity=severity,
                description=(
                    f"Conflicting resource allocation: {', '.join(conflicting_resources)}"
                ),
                resolution_suggestions=[
                    "Implement resource pooling",
                    "Add resource scheduling",
                    "Define resource priorities"
                ]
            )
        
        return None
    
    def _check_dependency_conflicts(
        self,
        decision1: WorkflowDecision,
        decision2: WorkflowDecision
    ) -> Optional[DecisionConflict]:
        """Check for dependency conflicts between decisions."""
        # Check if decisions have conflicting dependencies
        deps1 = set(decision1.precedents)
        deps2 = set(decision2.precedents)
        
        # Check for circular dependencies
        if decision1.id in deps2 and decision2.id in deps1:
            return DecisionConflict(
                id=f"conflict_{decision1.id}_{decision2.id}_circular",
                decision1=decision1,
                decision2=decision2,
                conflict_type=ConflictType.DEPENDENCY_CONFLICT,
                severity=1.0,
                description="Circular dependency detected",
                resolution_suggestions=[
                    "Remove one dependency",
                    "Restructure decision flow",
                    "Create intermediate decision"
                ]
            )
        
        # Check for conflicting dependencies
        common_deps = deps1 & deps2
        if common_deps:
            # Check if the common dependencies have conflicts
            for dep_id in common_deps:
                dep = self.memory_store.get_decision(dep_id)
                if dep and dep.outcome and 'conflict' in dep.outcome.lower():
                    return DecisionConflict(
                        id=f"conflict_{decision1.id}_{decision2.id}_dependency",
                        decision1=decision1,
                        decision2=decision2,
                        conflict_type=ConflictType.DEPENDENCY_CONFLICT,
                        severity=0.7,
                        description=(
                            f"Both decisions depend on conflicted decision {dep_id}"
                        ),
                        resolution_suggestions=[
                            "Resolve upstream conflict first",
                            "Find alternative dependencies",
                            "Isolate from conflicted decision"
                        ]
                    )
        
        return None
    
    def _calculate_context_similarity(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> float:
        """Calculate similarity between two contexts."""
        if not context1 or not context2:
            return 0.0
        
        all_keys = set(context1.keys()) | set(context2.keys())
        if not all_keys:
            return 1.0
        
        matches = 0
        for key in all_keys:
            if key in context1 and key in context2:
                if context1[key] == context2[key]:
                    matches += 1
                elif isinstance(context1[key], str) and isinstance(context2[key], str):
                    # Partial string matching
                    if (context1[key].lower() in context2[key].lower() or
                        context2[key].lower() in context1[key].lower()):
                        matches += 0.5
        
        return matches / len(all_keys)
    
    def _calculate_outcome_similarity(
        self,
        outcome1: str,
        outcome2: str
    ) -> float:
        """Calculate similarity between two outcomes."""
        if outcome1 == outcome2:
            return 1.0
        
        # Simple token-based similarity
        tokens1 = set(outcome1.lower().split())
        tokens2 = set(outcome2.lower().split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        
        return intersection / union if union > 0 else 0.0
    
    def _find_context_incompatibilities(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> List[str]:
        """Find incompatible elements between contexts."""
        incompatibilities = []
        
        # Check for conflicting values
        common_keys = set(context1.keys()) & set(context2.keys())
        
        for key in common_keys:
            value1 = context1[key]
            value2 = context2[key]
            
            # Check for direct conflicts
            if self._are_values_incompatible(value1, value2):
                incompatibilities.append(f"{key}: {value1} vs {value2}")
        
        return incompatibilities
    
    def _are_values_incompatible(self, value1: Any, value2: Any) -> bool:
        """Check if two values are incompatible."""
        # Boolean conflicts
        if isinstance(value1, bool) and isinstance(value2, bool):
            return value1 != value2
        
        # Numeric conflicts (opposite signs)
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            return (value1 > 0 and value2 < 0) or (value1 < 0 and value2 > 0)
        
        # String conflicts (opposites)
        if isinstance(value1, str) and isinstance(value2, str):
            opposites = {
                'yes': 'no', 'true': 'false', 'allow': 'deny',
                'enable': 'disable', 'start': 'stop', 'create': 'delete'
            }
            v1_lower = value1.lower()
            v2_lower = value2.lower()
            
            for word1, word2 in opposites.items():
                if (word1 in v1_lower and word2 in v2_lower) or \
                   (word2 in v1_lower and word1 in v2_lower):
                    return True
        
        return False
    
    def _check_entity_match(
        self,
        context1: Dict[str, Any],
        context2: Dict[str, Any]
    ) -> Optional[str]:
        """Check if contexts refer to the same entity."""
        # Look for common entity identifiers
        entity_keys = ['id', 'name', 'resource', 'target', 'entity']
        
        for key in entity_keys:
            if key in context1 and key in context2:
                if context1[key] == context2[key]:
                    return f"{key}:{context1[key]}"
        
        return None
    
    def _check_state_invalidation(
        self,
        older: WorkflowDecision,
        newer: WorkflowDecision
    ) -> bool:
        """Check if newer decision invalidates older one."""
        # Check for state changes
        if 'state' in older.context and 'state' in newer.context:
            if older.context['state'] != newer.context['state']:
                return True
        
        # Check for deletion/removal indicators
        deletion_keywords = ['delete', 'remove', 'cancel', 'revoke', 'invalidate']
        newer_text = f"{newer.decision} {newer.rationale}".lower()
        
        for keyword in deletion_keywords:
            if keyword in newer_text:
                return True
        
        return False
    
    def _extract_resources(self, context: Dict[str, Any]) -> set:
        """Extract resource identifiers from context."""
        resources = set()
        
        resource_keys = ['resource', 'resources', 'allocation', 'assigned_to']
        
        for key in resource_keys:
            if key in context:
                value = context[key]
                if isinstance(value, str):
                    resources.add(value)
                elif isinstance(value, list):
                    resources.update(str(v) for v in value)
        
        return resources
    
    def _identify_most_conflicted(
        self,
        conflicts: List[DecisionConflict]
    ) -> List[Tuple[str, int]]:
        """Identify decisions with most conflicts."""
        conflict_counts = {}
        
        for conflict in conflicts:
            for decision in [conflict.decision1, conflict.decision2]:
                if decision.id not in conflict_counts:
                    conflict_counts[decision.id] = 0
                conflict_counts[decision.id] += 1
        
        # Sort by conflict count
        sorted_counts = sorted(
            conflict_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_counts[:5]  # Top 5 most conflicted
    
    def _generate_consistency_recommendations(
        self,
        consistency_score: float,
        conflicts_by_type: Dict[str, List[DecisionConflict]]
    ) -> List[str]:
        """Generate recommendations for improving consistency."""
        recommendations = []
        
        if consistency_score < 0.8:
            recommendations.append(
                "Low consistency score. Review and resolve existing conflicts."
            )
        
        # Type-specific recommendations
        for conflict_type, conflicts in conflicts_by_type.items():
            if len(conflicts) > 3:
                if conflict_type == ConflictType.CONTRADICTORY_OUTCOME.value:
                    recommendations.append(
                        "Multiple contradictory outcomes detected. "
                        "Establish clearer decision criteria."
                    )
                elif conflict_type == ConflictType.RESOURCE_CONFLICT.value:
                    recommendations.append(
                        "Resource conflicts are common. "
                        "Implement resource management system."
                    )
                elif conflict_type == ConflictType.TEMPORAL_INCONSISTENCY.value:
                    recommendations.append(
                        "Temporal inconsistencies found. "
                        "Add validity periods to decisions."
                    )
        
        if not recommendations:
            recommendations.append("System shows good consistency.")
        
        return recommendations