"""
Tests for the workflow memory system.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from velocitytree.workflow_memory import (
    MemoryStore,
    WorkflowDecision,
    DecisionType,
    DecisionTracker,
    PrecedentEngine,
    Precedent,
    ConflictDetector,
    DecisionConflict,
    ConflictType
)


class TestMemoryStore:
    """Test the memory store for workflow decisions."""
    
    def setup_method(self):
        """Create a temporary database for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_memory.db"
        self.store = MemoryStore(self.db_path)
    
    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)
    
    def test_add_decision(self):
        """Test adding a decision to the store."""
        decision = WorkflowDecision(
            decision_type=DecisionType.FEATURE_CREATION,
            context={'feature': 'authentication'},
            decision='Create auth module',
            rationale='User authentication is required',
            confidence=0.9
        )
        
        success = self.store.add_decision(decision)
        assert success is True
        
        # Retrieve and verify
        retrieved = self.store.get_decision(decision.id)
        assert retrieved is not None
        assert retrieved.decision == decision.decision
        assert retrieved.confidence == decision.confidence
    
    def test_get_decisions_filtering(self):
        """Test filtering decisions by various criteria."""
        # Add multiple decisions
        decisions = []
        for i in range(5):
            decision = WorkflowDecision(
                decision_type=DecisionType.FEATURE_CREATION if i % 2 == 0 else DecisionType.REFACTORING,
                context={'index': i},
                decision=f'Decision {i}',
                rationale=f'Rationale {i}',
                confidence=0.8,
                project_id='project1' if i < 3 else 'project2'
            )
            self.store.add_decision(decision)
            decisions.append(decision)
        
        # Test filtering by type
        feature_decisions = self.store.get_decisions(
            decision_type=DecisionType.FEATURE_CREATION
        )
        assert len(feature_decisions) == 3
        
        # Test filtering by project
        project1_decisions = self.store.get_decisions(project_id='project1')
        assert len(project1_decisions) == 3
        
        # Test limit
        limited_decisions = self.store.get_decisions(limit=2)
        assert len(limited_decisions) == 2
    
    def test_update_outcome(self):
        """Test updating decision outcomes."""
        decision = WorkflowDecision(
            decision_type=DecisionType.FEATURE_CREATION,
            context={'feature': 'logging'},
            decision='Add logging system',
            rationale='Need better debugging'
        )
        self.store.add_decision(decision)
        
        # Update outcome
        success = self.store.update_outcome(
            decision.id,
            'Successfully implemented logging',
            success=True,
            metrics={'lines_added': 150}
        )
        assert success is True
        
        # Verify update
        updated = self.store.get_decision(decision.id)
        assert updated.outcome == 'Successfully implemented logging'
    
    def test_relationships(self):
        """Test decision relationships."""
        parent = WorkflowDecision(
            decision_type=DecisionType.ARCHITECTURE,
            decision='Use microservices'
        )
        child = WorkflowDecision(
            decision_type=DecisionType.FEATURE_CREATION,
            decision='Create user service',
            precedents=[parent.id]
        )
        
        self.store.add_decision(parent)
        self.store.add_decision(child)
        
        # Add relationship
        success = self.store.add_relationship(parent.id, child.id)
        assert success is True
        
        # Get related decisions
        children = self.store.get_related_decisions(parent.id, direction='child')
        assert len(children) == 1
        assert children[0].id == child.id
    
    def test_statistics(self):
        """Test statistics calculation."""
        # Add decisions with outcomes
        for i in range(5):
            decision = WorkflowDecision(
                decision_type=DecisionType.FEATURE_CREATION,
                decision=f'Feature {i}',
                confidence=0.7 + (i * 0.05),
                project_id='test_project'
            )
            self.store.add_decision(decision)
            
            # Update outcome for some
            if i < 3:
                self.store.update_outcome(
                    decision.id,
                    'Success' if i < 2 else 'Failed',
                    success=(i < 2)
                )
        
        stats = self.store.get_statistics(project_id='test_project')
        assert stats['total_decisions'] == 5
        assert stats['success_rate'] == 2/3  # 2 out of 3 with outcomes
        assert stats['average_confidence'] > 0.7


class TestDecisionTracker:
    """Test the decision tracking system."""
    
    def setup_method(self):
        """Create test tracker with temporary database."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_tracker.db"
        self.store = MemoryStore(self.db_path)
        self.tracker = DecisionTracker(self.store)
    
    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)
    
    def test_record_decision(self):
        """Test recording a new decision."""
        decision = self.tracker.record_decision(
            decision_type=DecisionType.REFACTORING,
            context={'component': 'database'},
            decision='Switch to PostgreSQL',
            rationale='Better performance for our use case',
            confidence=0.85,
            tags=['database', 'performance']
        )
        
        assert decision.id is not None
        assert decision.tags == ['database', 'performance']
        
        # Verify it was stored
        retrieved = self.store.get_decision(decision.id)
        assert retrieved is not None
    
    def test_analyze_patterns(self):
        """Test pattern analysis in decisions."""
        # Create decisions with patterns
        for i in range(10):
            self.tracker.record_decision(
                decision_type=DecisionType.FEATURE_CREATION if i < 6 else DecisionType.REFACTORING,
                context={'day': i % 7, 'hour': 10 + (i % 4)},
                decision=f'Decision {i}',
                rationale='Test rationale',
                confidence=0.6 + (i * 0.03),
                project_id='test_project'
            )
        
        analysis = self.tracker.analyze_decision_patterns(project_id='test_project')
        
        assert analysis['total_decisions'] == 10
        assert 'patterns' in analysis
        assert 'trends' in analysis
        assert 'recommendations' in analysis
        
        # Check pattern detection
        patterns = analysis['patterns']
        assert 'feature_creation' in patterns
        assert patterns['feature_creation']['count'] == 6
    
    def test_similar_decisions(self):
        """Test finding similar decisions."""
        # Create reference decision
        reference = self.tracker.record_decision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'production', 'service': 'api'},
            decision='Deploy v2.0',
            rationale='New features ready'
        )
        
        # Create similar and dissimilar decisions
        similar = self.tracker.record_decision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'production', 'service': 'api'},
            decision='Deploy v2.1',
            rationale='Bug fixes'
        )
        
        different = self.tracker.record_decision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'staging', 'service': 'frontend'},
            decision='Deploy beta',
            rationale='Testing'
        )
        
        # Find similar decisions
        similar_decisions = self.tracker.get_similar_decisions(
            context={'environment': 'production', 'service': 'api'},
            decision_type=DecisionType.DEPLOYMENT,
            threshold=0.7
        )
        
        assert len(similar_decisions) >= 2
        assert any(d.id == similar.id for d in similar_decisions)
        assert not any(d.id == different.id for d in similar_decisions)
    
    def test_effectiveness_evaluation(self):
        """Test decision effectiveness evaluation."""
        decision = self.tracker.record_decision(
            decision_type=DecisionType.TESTING,
            context={'coverage': 'unit'},
            decision='Add more unit tests',
            rationale='Improve code quality',
            confidence=0.8
        )
        
        # Update with outcome
        self.store.update_outcome(
            decision.id,
            'Increased coverage to 90%',
            success=True
        )
        
        evaluation = self.tracker.evaluate_decision_effectiveness(decision.id)
        
        assert evaluation['confidence'] == 0.8
        assert evaluation['success'] is True
        assert 'recommendations' in evaluation


class TestPrecedentEngine:
    """Test the precedent matching system."""
    
    def setup_method(self):
        """Create test engine with sample data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_precedent.db"
        self.store = MemoryStore(self.db_path)
        self.engine = PrecedentEngine(self.store)
        
        # Add sample precedents
        self.precedents = []
        for i in range(5):
            decision = WorkflowDecision(
                decision_type=DecisionType.ARCHITECTURE,
                context={
                    'scale': 'large' if i < 3 else 'small',
                    'technology': 'python',
                    'performance': 'critical' if i < 2 else 'normal'
                },
                decision=f'Architecture decision {i}',
                rationale=f'Rationale {i}',
                confidence=0.7 + (i * 0.05),
                outcome='Successful implementation' if i < 3 else None
            )
            decision.timestamp = datetime.now() - timedelta(days=i*30)
            self.store.add_decision(decision)
            self.precedents.append(decision)
    
    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)
    
    def test_find_precedents(self):
        """Test finding relevant precedents."""
        # Search for similar context
        precedents = self.engine.find_precedents(
            decision_type=DecisionType.ARCHITECTURE,
            context={
                'scale': 'large',
                'technology': 'python',
                'performance': 'critical'
            }
        )
        
        assert len(precedents) > 0
        
        # Best match should have high relevance
        best = precedents[0]
        assert best.relevance_score > 0.7
        assert best.context_similarity > 0.8
    
    def test_apply_precedent(self):
        """Test applying a precedent to a new situation."""
        # Find precedent
        precedents = self.engine.find_precedents(
            decision_type=DecisionType.ARCHITECTURE,
            context={'scale': 'large', 'technology': 'python'}
        )
        
        best_precedent = precedents[0]
        
        # Apply to new context
        recommendation = self.engine.apply_precedent(
            best_precedent,
            current_context={
                'scale': 'large',
                'technology': 'python',
                'database': 'postgresql'  # New factor
            }
        )
        
        assert 'decision' in recommendation
        assert 'rationale' in recommendation
        assert 'confidence' in recommendation
        assert 'adaptations' in recommendation
        
        # Confidence should be adjusted based on relevance
        assert recommendation['confidence'] < best_precedent.decision.confidence
    
    def test_precedent_statistics(self):
        """Test precedent usage statistics."""
        # Create decisions using precedents
        for i in range(3):
            decision = WorkflowDecision(
                decision_type=DecisionType.ARCHITECTURE,
                decision=f'New decision {i}',
                precedents=[self.precedents[0].id, self.precedents[1].id],
                outcome='Success' if i < 2 else 'Failed'
            )
            self.store.add_decision(decision)
        
        stats = self.engine.get_precedent_statistics(
            decision_type=DecisionType.ARCHITECTURE
        )
        
        assert stats['total_decisions'] > 5
        assert stats['decisions_with_precedents'] == 3
        assert stats['precedent_success_rate'] == 2/3
        assert len(stats['most_used_precedents']) > 0
    
    def test_learn_from_outcome(self):
        """Test learning from decision outcomes."""
        # Create decision with precedent
        precedent = self.precedents[0]
        decision = WorkflowDecision(
            decision_type=DecisionType.ARCHITECTURE,
            decision='New architecture',
            precedents=[precedent.id]
        )
        self.store.add_decision(decision)
        
        # Record outcome
        success = self.engine.learn_from_outcome(
            decision.id,
            'Successfully implemented',
            success=True,
            metrics={'performance': 'improved'}
        )
        
        assert success is True
        
        # Verify outcome was recorded
        updated = self.store.get_decision(decision.id)
        assert updated.outcome == 'Successfully implemented'


class TestConflictDetector:
    """Test the conflict detection system."""
    
    def setup_method(self):
        """Create test detector with sample decisions."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_conflict.db"
        self.store = MemoryStore(self.db_path)
        self.detector = ConflictDetector(self.store)
        
        # Create potentially conflicting decisions
        self.decision1 = WorkflowDecision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'production', 'service': 'api'},
            decision='Deploy immediately',
            rationale='Critical fix needed',
            confidence=0.9,
            outcome='Deployment successful'
        )
        
        self.decision2 = WorkflowDecision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'production', 'service': 'api'},
            decision='Delay deployment',
            rationale='Need more testing',
            confidence=0.8,
            outcome='Deployment postponed'
        )
        
        self.store.add_decision(self.decision1)
        self.store.add_decision(self.decision2)
    
    def teardown_method(self):
        """Clean up temporary database."""
        shutil.rmtree(self.temp_dir)
    
    def test_detect_conflicts(self):
        """Test conflict detection between decisions."""
        # Create new decision that might conflict
        new_decision = WorkflowDecision(
            decision_type=DecisionType.DEPLOYMENT,
            context={'environment': 'production', 'service': 'api'},
            decision='Emergency deployment',
            rationale='Security patch'
        )
        
        conflicts = self.detector.detect_conflicts(new_decision)
        
        assert len(conflicts) > 0
        
        # Should detect contradictory outcomes
        outcome_conflicts = [
            c for c in conflicts
            if c.conflict_type == ConflictType.CONTRADICTORY_OUTCOME
        ]
        assert len(outcome_conflicts) > 0
    
    def test_resolve_conflict(self):
        """Test conflict resolution suggestions."""
        # Create conflict
        conflict = DecisionConflict(
            id='test_conflict',
            decision1=self.decision1,
            decision2=self.decision2,
            conflict_type=ConflictType.CONTRADICTORY_OUTCOME,
            severity=0.8,
            description='Contradictory deployment decisions',
            resolution_suggestions=['Review deployment policy']
        )
        
        # Test different resolution methods
        resolution = self.detector.resolve_conflict(conflict, 'latest_wins')
        
        assert resolution['method'] == 'latest_wins'
        assert 'recommendation' in resolution
        assert 'actions' in resolution
        assert resolution['confidence'] > 0
    
    def test_consistency_check(self):
        """Test overall consistency checking."""
        # Add more decisions
        for i in range(5):
            decision = WorkflowDecision(
                decision_type=DecisionType.FEATURE_CREATION,
                context={'feature': f'feature_{i}'},
                decision=f'Create feature {i}',
                project_id='test_project'
            )
            self.store.add_decision(decision)
        
        report = self.detector.check_consistency(project_id='test_project')
        
        assert 'consistency_score' in report
        assert 'total_decisions' in report
        assert 'conflicts_by_type' in report
        assert 'recommendations' in report
        
        # Score should be between 0 and 1
        assert 0 <= report['consistency_score'] <= 1
    
    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        # Create circular dependency
        decision_a = WorkflowDecision(
            id='decision_a',
            decision_type=DecisionType.ARCHITECTURE,
            decision='Decision A',
            precedents=['decision_b']
        )
        
        decision_b = WorkflowDecision(
            id='decision_b',
            decision_type=DecisionType.ARCHITECTURE,
            decision='Decision B',
            precedents=['decision_a']
        )
        
        self.store.add_decision(decision_a)
        self.store.add_decision(decision_b)
        
        conflicts = self.detector.detect_conflicts(decision_a)
        
        # Should detect circular dependency
        circular_conflicts = [
            c for c in conflicts
            if c.conflict_type == ConflictType.DEPENDENCY_CONFLICT
            and 'circular' in c.description.lower()
        ]
        assert len(circular_conflicts) > 0
    
    def test_resource_conflict_detection(self):
        """Test detection of resource conflicts."""
        # Create resource allocation decisions
        decision1 = WorkflowDecision(
            decision_type=DecisionType.CONFIGURATION,
            context={'resource': 'database_server', 'allocation': '80%'},
            decision='Allocate database resources',
            project_id='project1'
        )
        
        decision2 = WorkflowDecision(
            decision_type=DecisionType.CONFIGURATION,
            context={'resource': 'database_server', 'allocation': '50%'},
            decision='Allocate database for analytics',
            project_id='project1'
        )
        
        self.store.add_decision(decision1)
        self.store.add_decision(decision2)
        
        conflicts = self.detector.detect_conflicts(decision2)
        
        # Should detect resource conflict
        resource_conflicts = [
            c for c in conflicts
            if c.conflict_type == ConflictType.RESOURCE_CONFLICT
        ]
        assert len(resource_conflicts) > 0