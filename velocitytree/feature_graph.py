"""Feature graph visualization and management for project tracking."""
import networkx as nx
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from pathlib import Path
import json
import logging
from enum import Enum

from .utils import logger
from .planning_session import Feature, Milestone, ProjectPlan

class RelationType(Enum):
    """Types of relationships between features."""
    PARENT_CHILD = "parent_child"
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    RELATED_TO = "related_to"
    DUPLICATES = "duplicates"
    IMPLEMENTS = "implements"
    INCLUDES = "includes"
    PRECEDES = "precedes"
    FOLLOWS = "follows"

class RelationshipStrength(Enum):
    """Strength of a relationship."""
    CRITICAL = "critical"
    STRONG = "strong"
    NORMAL = "normal"
    WEAK = "weak"

@dataclass
class FeatureRelationship:
    """Represents a relationship between features."""
    source_id: str
    target_id: str
    relation_type: RelationType
    strength: RelationshipStrength = RelationshipStrength.NORMAL
    description: Optional[str] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

# Data models for the feature graph
@dataclass
class FeatureNode:
    """Represents a node in the feature graph."""
    id: str
    name: str
    description: str
    type: str  # feature, milestone, epic, task
    status: str  # planned, in_progress, completed, blocked
    assignee: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    parent_id: Optional[str] = None
    dependencies: List[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProgressMetrics:
    """Metrics for tracking feature progress."""
    total_features: int
    completed_features: int
    in_progress_features: int
    blocked_features: int
    planned_features: int
    completion_percentage: float
    average_velocity: float
    estimated_completion: Optional[datetime]
    blockers: List[str]
    critical_path: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_features': self.total_features,
            'completed_features': self.completed_features,
            'in_progress_features': self.in_progress_features,
            'blocked_features': self.blocked_features,
            'planned_features': self.planned_features,
            'completion_percentage': self.completion_percentage,
            'average_velocity': self.average_velocity,
            'estimated_completion': self.estimated_completion.isoformat() if self.estimated_completion else None,
            'blockers': self.blockers,
            'critical_path': self.critical_path
        }


class FeatureGraph:
    """Manages the feature dependency graph for project visualization."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize the feature graph."""
        self.project_id = project_id or "default"
        self.graph = nx.DiGraph()
        self.features: Dict[str, FeatureNode] = {}
        self.milestones: Dict[str, FeatureNode] = {}
        self.relationships: Dict[Tuple[str, str], FeatureRelationship] = {}
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'version': 1
        }
        logger.info(f"Initialized FeatureGraph for project: {self.project_id}")
    
    def add_feature(self, feature: FeatureNode) -> None:
        """Add a feature to the graph."""
        self.features[feature.id] = feature
        
        # Add node to graph with attributes
        self.graph.add_node(
            feature.id,
            **asdict(feature)
        )
        
        # Add parent relationship if exists
        if feature.parent_id and feature.parent_id in self.graph:
            self.graph.add_edge(feature.parent_id, feature.id, 
                              relation_type="parent_child")
        
        # Track milestones separately
        if feature.type == "milestone":
            self.milestones[feature.id] = feature
        
        self.metadata['updated_at'] = datetime.now()
        logger.debug(f"Added feature: {feature.id} - {feature.name}")
    
    def add_dependency(self, from_id: str, to_id: str) -> None:
        """Add a dependency between features (from depends on to)."""
        self.add_relationship(from_id, to_id, RelationType.DEPENDS_ON)
    
    def add_relationship(self, source_id: str, target_id: str, 
                        relation_type: RelationType,
                        strength: RelationshipStrength = RelationshipStrength.NORMAL,
                        description: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> FeatureRelationship:
        """Add a generic relationship between features."""
        if source_id not in self.graph:
            raise ValueError(f"Source feature {source_id} not found in graph")
        if target_id not in self.graph:
            raise ValueError(f"Target feature {target_id} not found in graph")
        
        # Create relationship object
        relationship = FeatureRelationship(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            strength=strength,
            description=description,
            metadata=metadata or {}
        )
        
        # Store relationship
        key = (source_id, target_id)
        self.relationships[key] = relationship
        
        # Add edge to graph
        self.graph.add_edge(
            source_id, 
            target_id,
            relation_type=relation_type.value,
            strength=strength.value,
            description=description,
            **relationship.metadata
        )
        
        # Update dependency list for backward compatibility
        if relation_type == RelationType.DEPENDS_ON and source_id in self.features:
            if target_id not in self.features[source_id].dependencies:
                self.features[source_id].dependencies.append(target_id)
        
        self.metadata['updated_at'] = datetime.now()
        logger.debug(f"Added relationship: {source_id} {relation_type.value} {target_id}")
        return relationship
    
    def get_relationships(self, feature_id: str, 
                         relation_type: Optional[RelationType] = None,
                         direction: str = "both") -> List[FeatureRelationship]:
        """Get all relationships for a feature."""
        relationships = []
        
        # Outgoing relationships
        if direction in ["out", "both"]:
            for target in self.graph.neighbors(feature_id):
                key = (feature_id, target)
                if key in self.relationships:
                    rel = self.relationships[key]
                    if relation_type is None or rel.relation_type == relation_type:
                        relationships.append(rel)
        
        # Incoming relationships
        if direction in ["in", "both"]:
            for source in self.graph.predecessors(feature_id):
                key = (source, feature_id)
                if key in self.relationships:
                    rel = self.relationships[key]
                    if relation_type is None or rel.relation_type == relation_type:
                        relationships.append(rel)
        
        return relationships
    
    def get_related_features(self, feature_id: str,
                           relation_types: Optional[List[RelationType]] = None,
                           max_depth: int = 1) -> Dict[str, List[str]]:
        """Get features related to the given feature within specified depth."""
        if feature_id not in self.graph:
            return {}
        
        related = {}
        visited = {feature_id}
        
        def traverse(node_id: str, depth: int):
            if depth > max_depth:
                return
            
            # Get all relationships
            rels = self.get_relationships(node_id)
            
            for rel in rels:
                if relation_types and rel.relation_type not in relation_types:
                    continue
                
                # Get the other node in the relationship
                other_id = rel.target_id if rel.source_id == node_id else rel.source_id
                
                if other_id in visited:
                    continue
                
                visited.add(other_id)
                
                # Add to results
                rel_type = rel.relation_type.value
                if rel_type not in related:
                    related[rel_type] = []
                related[rel_type].append(other_id)
                
                # Recursive traversal
                traverse(other_id, depth + 1)
        
        traverse(feature_id, 1)
        return related
    
    def remove_relationship(self, source_id: str, target_id: str) -> bool:
        """Remove a relationship between features."""
        key = (source_id, target_id)
        
        if key not in self.relationships:
            return False
        
        relationship = self.relationships[key]
        
        # Remove from graph
        if self.graph.has_edge(source_id, target_id):
            self.graph.remove_edge(source_id, target_id)
        
        # Remove from relationship store
        del self.relationships[key]
        
        # Update dependency list if necessary
        if (relationship.relation_type == RelationType.DEPENDS_ON and 
            source_id in self.features and 
            target_id in self.features[source_id].dependencies):
            self.features[source_id].dependencies.remove(target_id)
        
        self.metadata['updated_at'] = datetime.now()
        logger.debug(f"Removed relationship: {source_id} -> {target_id}")
        return True
    
    def update_relationship(self, source_id: str, target_id: str,
                          strength: Optional[RelationshipStrength] = None,
                          description: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update an existing relationship."""
        key = (source_id, target_id)
        
        if key not in self.relationships:
            return False
        
        relationship = self.relationships[key]
        
        # Update fields
        if strength is not None:
            relationship.strength = strength
        if description is not None:
            relationship.description = description
        if metadata is not None:
            relationship.metadata.update(metadata)
        
        # Update graph edge
        if self.graph.has_edge(source_id, target_id):
            edge_data = self.graph[source_id][target_id]
            if strength is not None:
                edge_data['strength'] = strength.value
            if description is not None:
                edge_data['description'] = description
            if metadata is not None:
                edge_data.update(metadata)
        
        self.metadata['updated_at'] = datetime.now()
        return True
    
    def get_relationship_matrix(self, features: Optional[List[str]] = None) -> Dict[str, Dict[str, List[str]]]:
        """Get a matrix showing all relationships between features."""
        if features is None:
            features = list(self.features.keys())
        
        matrix = {}
        for f1 in features:
            matrix[f1] = {}
            for f2 in features:
                if f1 == f2:
                    continue
                
                # Check if there's a relationship
                key = (f1, f2)
                if key in self.relationships:
                    rel = self.relationships[key]
                    if f2 not in matrix[f1]:
                        matrix[f1][f2] = []
                    matrix[f1][f2].append(rel.relation_type.value)
        
        return matrix
    
    def validate_dependencies(self) -> List[str]:
        """Check for circular dependencies and other issues."""
        errors = []
        warnings = []
        
        # Check for circular dependencies with specific relationship types
        try:
            # Create subgraph with only dependency relationships
            dep_graph = nx.DiGraph()
            dep_graph.add_nodes_from(self.graph.nodes())
            
            for u, v, data in self.graph.edges(data=True):
                if data.get('relation_type') in ['depends_on', 'blocks', 'precedes']:
                    dep_graph.add_edge(u, v)
            
            cycles = list(nx.simple_cycles(dep_graph))
            for cycle in cycles:
                errors.append(f"Circular dependency detected: {' -> '.join(cycle)}")
        except Exception as e:
            logger.error(f"Error checking for cycles: {e}")
        
        # Check for conflicting relationships
        for (source, target), rel in self.relationships.items():
            # Check for conflicting opposite relationships
            opposite_key = (target, source)
            if opposite_key in self.relationships:
                opposite_rel = self.relationships[opposite_key]
                if (rel.relation_type == RelationType.BLOCKS and 
                    opposite_rel.relation_type == RelationType.DEPENDS_ON):
                    errors.append(f"Conflicting relationships: {source} blocks {target} but {target} depends on {source}")
                elif (rel.relation_type == RelationType.PRECEDES and 
                      opposite_rel.relation_type == RelationType.FOLLOWS):
                    warnings.append(f"Redundant relationships: {source} precedes {target} and {target} follows {source}")
                elif (rel.relation_type == RelationType.INCLUDES and
                      opposite_rel.relation_type == RelationType.DEPENDS_ON):
                    warnings.append(f"Potential issue: {source} includes {target} but {target} depends on {source}")
        
        # Check for missing nodes in relationships
        for node_id, data in self.graph.nodes(data=True):
            node_data = data
            for dep_id in node_data.get('dependencies', []):
                if dep_id not in self.graph:
                    errors.append(f"Missing dependency: {node_id} depends on non-existent {dep_id}")
        
        # Check for orphaned nodes (no parent and no dependencies)
        for node_id in self.graph.nodes():
            if (self.graph.in_degree(node_id) == 0 and 
                self.graph.out_degree(node_id) == 0 and
                node_id not in self.milestones):
                warnings.append(f"Orphaned node: {node_id} has no relationships")
        
        # Check relationship strength consistency
        for rel in self.relationships.values():
            if (rel.relation_type == RelationType.DEPENDS_ON and 
                rel.strength == RelationshipStrength.WEAK):
                warnings.append(f"Weak dependency: {rel.source_id} -> {rel.target_id} may cause issues")
            elif (rel.relation_type == RelationType.BLOCKS and
                  rel.strength not in [RelationshipStrength.CRITICAL, RelationshipStrength.STRONG]):
                warnings.append(f"Blocking relationship should be stronger: {rel.source_id} blocks {rel.target_id}")
        
        # Check for dependency depth
        if dep_graph.number_of_nodes() > 0:
            try:
                # Only check longest path if there are no cycles
                if not cycles:
                    longest_path = nx.dag_longest_path_length(dep_graph)
                    if longest_path > 5:
                        warnings.append(f"Deep dependency chain detected: {longest_path} levels deep")
            except (nx.NetworkXError, nx.NetworkXUnfeasible):
                pass  # Graph has cycles or other issues, already reported
        
        # Combine errors and warnings
        return errors + [f"WARNING: {w}" for w in warnings]
    
    def get_feature_tree(self) -> nx.DiGraph:
        """Get the complete feature tree."""
        return self.graph.copy()
    
    def get_subtree(self, root_id: str) -> nx.DiGraph:
        """Get a subtree starting from a specific node."""
        if root_id not in self.graph:
            raise ValueError(f"Root node {root_id} not found")
        
        # Get all descendants
        descendants = nx.descendants(self.graph, root_id)
        descendants.add(root_id)
        
        # Create subgraph
        return self.graph.subgraph(descendants).copy()
    
    def get_dependencies(self, feature_id: str) -> List[str]:
        """Get all dependencies for a feature."""
        if feature_id not in self.graph:
            return []
        
        # Get nodes that this feature depends on
        dependencies = []
        for _, target, data in self.graph.out_edges(feature_id, data=True):
            if data.get('relation_type') == 'depends_on':
                dependencies.append(target)
        
        return dependencies
    
    def get_dependents(self, feature_id: str) -> List[str]:
        """Get all features that depend on this feature."""
        if feature_id not in self.graph:
            return []
        
        # Get nodes that depend on this feature
        dependents = []
        for source, _, data in self.graph.in_edges(feature_id, data=True):
            if data.get('relation_type') == 'depends_on':
                dependents.append(source)
        
        return dependents
    
    def get_all_dependencies(self, feature_id: str, recursive: bool = True) -> Set[str]:
        """Get all dependencies of a feature, optionally recursive."""
        if feature_id not in self.graph:
            return set()
        
        dependencies = set()
        to_process = {feature_id}
        processed = set()
        
        while to_process:
            current = to_process.pop()
            if current in processed:
                continue
            
            processed.add(current)
            
            # Get direct dependencies
            for dep in self.get_dependencies(current):
                dependencies.add(dep)
                if recursive and dep not in processed:
                    to_process.add(dep)
        
        return dependencies
    
    def get_all_dependents(self, feature_id: str, recursive: bool = True) -> Set[str]:
        """Get all features that depend on this feature, optionally recursive."""
        if feature_id not in self.graph:
            return set()
        
        dependents = set()
        to_process = {feature_id}
        processed = set()
        
        while to_process:
            current = to_process.pop()
            if current in processed:
                continue
            
            processed.add(current)
            
            # Get direct dependents
            for dep in self.get_dependents(current):
                dependents.add(dep)
                if recursive and dep not in processed:
                    to_process.add(dep)
        
        return dependents
    
    def update_feature_status(self, feature_id: str, status: str) -> None:
        """Update the status of a feature."""
        if feature_id not in self.features:
            raise ValueError(f"Feature {feature_id} not found")
        
        old_status = self.features[feature_id].status
        self.features[feature_id].status = status
        self.features[feature_id].updated_at = datetime.now()
        
        # Update graph node data
        self.graph.nodes[feature_id]['status'] = status
        self.graph.nodes[feature_id]['updated_at'] = datetime.now()
        
        # Check if status change affects dependencies
        if status == "completed":
            self._check_unblock_dependents(feature_id)
        elif old_status == "completed" and status != "completed":
            self._check_block_dependents(feature_id)
        
        self.metadata['updated_at'] = datetime.now()
        logger.info(f"Updated feature {feature_id} status: {old_status} -> {status}")
    
    def _check_unblock_dependents(self, feature_id: str) -> None:
        """Check if completing this feature unblocks any dependents."""
        dependents = self.get_dependents(feature_id)
        
        for dep_id in dependents:
            if dep_id in self.features and self.features[dep_id].status == "blocked":
                # Check if all dependencies are now satisfied
                deps = self.get_dependencies(dep_id)
                if all(self.features.get(d, {}).status == "completed" for d in deps):
                    self.update_feature_status(dep_id, "planned")
                    logger.info(f"Unblocked feature {dep_id}")
    
    def _check_block_dependents(self, feature_id: str) -> None:
        """Check if un-completing this feature blocks any dependents."""
        dependents = self.get_dependents(feature_id)
        
        for dep_id in dependents:
            if dep_id in self.features and self.features[dep_id].status != "blocked":
                self.update_feature_status(dep_id, "blocked")
                logger.info(f"Blocked feature {dep_id}")
    
    def can_start_feature(self, feature_id: str) -> Tuple[bool, List[str]]:
        """Check if a feature can be started based on its dependencies."""
        if feature_id not in self.features:
            return False, [f"Feature {feature_id} not found"]
        
        feature = self.features[feature_id]
        if feature.status not in ["planned", "blocked"]:
            return False, [f"Feature is already {feature.status}"]
        
        # Check all dependencies
        issues = []
        dependencies = self.get_dependencies(feature_id)
        
        for dep_id in dependencies:
            if dep_id not in self.features:
                issues.append(f"Missing dependency: {dep_id}")
                continue
            
            dep_feature = self.features[dep_id]
            rel_key = (feature_id, dep_id)
            
            # Check dependency status based on relationship strength
            if rel_key in self.relationships:
                rel = self.relationships[rel_key]
                if rel.strength in [RelationshipStrength.CRITICAL, RelationshipStrength.STRONG]:
                    if dep_feature.status != "completed":
                        issues.append(f"Critical dependency {dep_id} is not completed (status: {dep_feature.status})")
                elif rel.strength == RelationshipStrength.NORMAL:
                    if dep_feature.status not in ["completed", "in_progress"]:
                        issues.append(f"Dependency {dep_id} is not ready (status: {dep_feature.status})")
                # WEAK dependencies don't block start
            else:
                # Default to normal strength if relationship not found
                if dep_feature.status not in ["completed", "in_progress"]:
                    issues.append(f"Dependency {dep_id} is not ready (status: {dep_feature.status})")
        
        # Check for blocking relationships
        for (source, target), rel in self.relationships.items():
            if target == feature_id and rel.relation_type == RelationType.BLOCKS:
                blocker = self.features.get(source)
                if blocker and blocker.status not in ["completed", "cancelled"]:
                    issues.append(f"Feature {source} is blocking this feature (status: {blocker.status})")
        
        return len(issues) == 0, issues
    
    def get_suggested_next_features(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Get suggested features to work on next based on dependencies."""
        suggestions = []
        
        for feature_id, feature in self.features.items():
            if feature.status != "planned":
                continue
            
            can_start, issues = self.can_start_feature(feature_id)
            
            if can_start:
                # Calculate priority score
                priority_score = 0
                
                # Higher score for features with more dependents
                dependents = self.get_all_dependents(feature_id)
                priority_score += len(dependents) * 10
                
                # Higher score for critical features
                incoming_critical = 0
                for (_, target), rel in self.relationships.items():
                    if target == feature_id and rel.strength == RelationshipStrength.CRITICAL:
                        incoming_critical += 1
                priority_score += incoming_critical * 5
                
                # Lower score for features with many dependencies
                dependencies = self.get_all_dependencies(feature_id)
                priority_score -= len(dependencies) * 2
                
                suggestions.append((feature_id, {
                    'name': feature.name,
                    'description': feature.description,
                    'priority_score': priority_score,
                    'dependent_count': len(dependents),
                    'dependency_count': len(dependencies),
                    'type': feature.type
                }))
        
        # Sort by priority score
        suggestions.sort(key=lambda x: x[1]['priority_score'], reverse=True)
        return suggestions
    
    def get_dependency_chain(self, from_id: str, to_id: str) -> List[List[str]]:
        """Find all dependency chains between two features."""
        if from_id not in self.graph or to_id not in self.graph:
            return []
        
        # Create dependency-only subgraph
        dep_graph = nx.DiGraph()
        dep_graph.add_nodes_from(self.graph.nodes())
        
        for u, v, data in self.graph.edges(data=True):
            if data.get('relation_type') == 'depends_on':
                dep_graph.add_edge(u, v)
        
        try:
            # Find all paths
            paths = list(nx.all_simple_paths(dep_graph, from_id, to_id))
            return paths
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []
    
    def calculate_progress(self) -> ProgressMetrics:
        """Calculate overall project progress metrics."""
        total = len(self.features)
        if total == 0:
            return ProgressMetrics(
                total_features=0,
                completed_features=0,
                in_progress_features=0,
                blocked_features=0,
                planned_features=0,
                completion_percentage=0.0,
                average_velocity=0.0,
                estimated_completion=None,
                blockers=[],
                critical_path=[]
            )
        
        # Count by status
        status_counts = {'completed': 0, 'in_progress': 0, 'blocked': 0, 'planned': 0}
        for feature in self.features.values():
            status_counts[feature.status] = status_counts.get(feature.status, 0) + 1
        
        # Calculate completion percentage
        completion_percentage = (status_counts['completed'] / total) * 100
        
        # Calculate velocity (simplified - would need historical data)
        velocity = self._calculate_velocity()
        
        # Estimate completion (simplified)
        estimated_completion = self._estimate_completion(
            status_counts['completed'],
            status_counts['in_progress'],
            status_counts['planned'] + status_counts['blocked'],
            velocity
        )
        
        # Find blockers
        blockers = [fid for fid, f in self.features.items() if f.status == 'blocked']
        
        # Calculate critical path
        critical_path = self._find_critical_path()
        
        return ProgressMetrics(
            total_features=total,
            completed_features=status_counts['completed'],
            in_progress_features=status_counts['in_progress'],
            blocked_features=status_counts['blocked'],
            planned_features=status_counts['planned'],
            completion_percentage=completion_percentage,
            average_velocity=velocity,
            estimated_completion=estimated_completion,
            blockers=blockers,
            critical_path=critical_path
        )
    
    def _calculate_velocity(self) -> float:
        """Calculate average velocity (features per day)."""
        # This is a simplified version - in practice would use historical data
        completed = [f for f in self.features.values() if f.status == 'completed']
        if not completed:
            return 0.0
        
        # Calculate based on completed features and time
        earliest = min(f.created_at for f in completed)
        latest = max(f.updated_at for f in completed)
        days = (latest - earliest).days or 1
        
        return len(completed) / days
    
    def _estimate_completion(self, completed: int, in_progress: int, 
                           remaining: int, velocity: float) -> Optional[datetime]:
        """Estimate project completion date."""
        if velocity <= 0 or remaining == 0:
            return None
        
        # Simple estimation
        days_remaining = remaining / velocity
        return datetime.now() + timedelta(days=int(days_remaining))
    
    def _find_critical_path(self) -> List[str]:
        """Find the critical path through the project."""
        # Find longest path in the dependency graph
        try:
            # Create a weighted graph based on feature complexity
            weighted_graph = nx.DiGraph()
            for node in self.graph.nodes():
                weighted_graph.add_node(node)
            
            for u, v, data in self.graph.edges(data=True):
                if data.get('relation_type') == 'depends_on':
                    # Weight based on feature complexity (simplified)
                    weight = 1  # Could be based on effort estimates
                    weighted_graph.add_edge(v, u, weight=weight)
            
            # Find longest path
            if weighted_graph.number_of_nodes() > 0:
                try:
                    path = nx.dag_longest_path(weighted_graph, weight='weight')
                    return path
                except nx.NetworkXError:
                    # Graph has cycles or other issues
                    return []
            return []
        except Exception as e:
            logger.error(f"Error finding critical path: {e}")
            return []
    
    def get_milestone_progress(self, milestone_id: str) -> Dict[str, Any]:
        """Get progress for a specific milestone."""
        if milestone_id not in self.milestones:
            raise ValueError(f"Milestone {milestone_id} not found")
        
        # Find all features belonging to this milestone
        milestone_features = []
        for fid, feature in self.features.items():
            if feature.parent_id == milestone_id or milestone_id in feature.tags:
                milestone_features.append(fid)
        
        if not milestone_features:
            return {
                'milestone_id': milestone_id,
                'total_features': 0,
                'completed_features': 0,
                'completion_percentage': 0.0
            }
        
        # Calculate progress
        total = len(milestone_features)
        completed = sum(1 for fid in milestone_features 
                       if self.features[fid].status == 'completed')
        
        return {
            'milestone_id': milestone_id,
            'total_features': total,
            'completed_features': completed,
            'completion_percentage': (completed / total) * 100,
            'features': milestone_features
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary for serialization."""
        # Convert relationships for serialization
        relationships_data = []
        for rel in self.relationships.values():
            rel_dict = {
                'source_id': rel.source_id,
                'target_id': rel.target_id,
                'relation_type': rel.relation_type.value,
                'strength': rel.strength.value,
                'description': rel.description,
                'metadata': rel.metadata,
                'created_at': rel.created_at.isoformat() if rel.created_at else None
            }
            relationships_data.append(rel_dict)
        
        return {
            'project_id': self.project_id,
            'metadata': self.metadata,
            'features': {fid: asdict(f) for fid, f in self.features.items()},
            'milestones': list(self.milestones.keys()),
            'relationships': relationships_data,
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'relation_type': data.get('relation_type')
                }
                for u, v, data in self.graph.edges(data=True)
            ]
        }
    
    def save(self, filepath: Path) -> None:
        """Save graph to file."""
        data = self.to_dict()
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Saved feature graph to {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> 'FeatureGraph':
        """Load graph from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        graph = cls(project_id=data.get('project_id'))
        graph.metadata = data.get('metadata', {})
        
        # Restore features
        for fid, fdata in data.get('features', {}).items():
            # Convert string dates back to datetime
            if 'created_at' in fdata:
                fdata['created_at'] = datetime.fromisoformat(fdata['created_at'])
            if 'updated_at' in fdata:
                fdata['updated_at'] = datetime.fromisoformat(fdata['updated_at'])
            
            feature = FeatureNode(**fdata)
            graph.add_feature(feature)
        
        # Restore relationships
        for rel_data in data.get('relationships', []):
            if 'created_at' in rel_data and rel_data['created_at']:
                rel_data['created_at'] = datetime.fromisoformat(rel_data['created_at'])
            
            # Convert string enums back to enum objects
            rel_data['relation_type'] = RelationType(rel_data['relation_type'])
            rel_data['strength'] = RelationshipStrength(rel_data['strength'])
            
            relationship = FeatureRelationship(**rel_data)
            key = (relationship.source_id, relationship.target_id)
            graph.relationships[key] = relationship
            
            # Add to graph
            graph.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                relation_type=relationship.relation_type.value,
                strength=relationship.strength.value,
                description=relationship.description,
                **relationship.metadata
            )
        
        # Fallback to old edge format if no relationships
        if not data.get('relationships') and data.get('edges'):
            for edge in data.get('edges', []):
                if edge['relation_type'] == 'depends_on':
                    graph.add_dependency(edge['source'], edge['target'])
        
        logger.info(f"Loaded feature graph from {filepath}")
        return graph
    
    def from_project_plan(self, plan: ProjectPlan) -> None:
        """Build graph from a project plan."""
        # Add milestones
        for milestone in plan.milestones:
            node = FeatureNode(
                id=f"milestone_{milestone.name.lower().replace(' ', '_')}",
                name=milestone.name,
                description=milestone.description,
                type="milestone",
                status="planned",
                metadata={'deliverables': milestone.deliverables}
            )
            self.add_feature(node)
        
        # Add features
        for feature in plan.features:
            node = FeatureNode(
                id=f"feature_{feature.name.lower().replace(' ', '_')}",
                name=feature.name,
                description=feature.description,
                type="feature",
                status="planned",
                metadata={
                    'priority': feature.priority,
                    'effort_estimate': feature.effort_estimate,
                    'requirements': feature.requirements
                }
            )
            self.add_feature(node)
            
            # Add dependencies if specified
            if feature.dependencies:
                for dep in feature.dependencies:
                    dep_id = f"feature_{dep.lower().replace(' ', '_')}"
                    if dep_id in self.features:
                        self.add_dependency(node.id, dep_id)
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph structure."""
        stats = {
            'total_nodes': self.graph.number_of_nodes(),
            'total_edges': self.graph.number_of_edges(),
            'max_depth': 0,
            'avg_dependencies': 0,
            'isolated_nodes': 0,
            'strongly_connected_components': 0
        }
        
        if stats['total_nodes'] > 0:
            # Calculate max depth
            if nx.is_directed_acyclic_graph(self.graph):
                stats['max_depth'] = nx.dag_longest_path_length(self.graph)
            
            # Average dependencies
            dep_counts = [self.graph.out_degree(n) for n in self.graph.nodes()]
            stats['avg_dependencies'] = sum(dep_counts) / len(dep_counts)
            
            # Isolated nodes
            stats['isolated_nodes'] = len(list(nx.isolates(self.graph)))
            
            # Strongly connected components
            stats['strongly_connected_components'] = len(list(
                nx.strongly_connected_components(self.graph)
            ))
        
        return stats


# Add missing import
from datetime import timedelta

if __name__ == "__main__":
    # Example usage
    graph = FeatureGraph("example_project")
    
    # Create some features
    f1 = FeatureNode(id="f1", name="User Auth", description="User authentication system", 
                     type="feature", status="completed")
    f2 = FeatureNode(id="f2", name="Dashboard", description="User dashboard",
                     type="feature", status="in_progress")
    f3 = FeatureNode(id="f3", name="API", description="REST API",
                     type="feature", status="planned")
    
    # Add features
    graph.add_feature(f1)
    graph.add_feature(f2)
    graph.add_feature(f3)
    
    # Add dependencies (f2 depends on f1, f3 depends on f1)
    graph.add_dependency("f2", "f1")
    graph.add_dependency("f3", "f1")
    
    # Calculate progress
    progress = graph.calculate_progress()
    print(f"Project progress: {progress.completion_percentage:.1f}%")
    
    # Validate dependencies
    errors = graph.validate_dependencies()
    if errors:
        print(f"Dependency errors: {errors}")
    else:
        print("No dependency errors found")