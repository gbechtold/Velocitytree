"""
Tests for the learning from user feedback system.
"""

import pytest
from pathlib import Path
import tempfile
import sqlite3
from datetime import datetime, timedelta

from velocitytree.learning.feedback_collector import (
    FeedbackCollector,
    LearningEngine,
    TeamLearningAggregator,
    AdaptiveSuggestionEngine,
    FeedbackDatabase,
    FeedbackType,
    FeedbackItem
)
from velocitytree.realtime_suggestions import SuggestionType


class TestFeedbackDatabase:
    """Test the feedback database operations."""
    
    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.db = FeedbackDatabase(self.db_path)
    
    def teardown_method(self):
        """Clean up temporary database."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_database_creation(self):
        """Test that database tables are created correctly."""
        # Check if tables exist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'feedback' in tables
        assert 'user_preferences' in tables
        assert 'learned_patterns' in tables
    
    def test_add_feedback(self):
        """Test adding feedback to database."""
        # Add feedback
        self.db.add_feedback(
            user_id="test_user",
            session_id="test_session",
            suggestion_id="test_suggestion",
            feedback_type=FeedbackType.ACCEPTED,
            value=1.0,
            metadata={'test': 'data'}
        )
        
        # Retrieve feedback
        feedbacks = self.db.get_feedback()
        assert len(feedbacks) == 1
        
        feedback = feedbacks[0]
        assert feedback.user_id == "test_user"
        assert feedback.session_id == "test_session"
        assert feedback.suggestion_id == "test_suggestion"
        assert feedback.feedback_type == FeedbackType.ACCEPTED
        assert feedback.value == 1.0
        assert feedback.metadata['test'] == 'data'
    
    def test_get_feedback_filtering(self):
        """Test filtering feedback retrieval."""
        # Add multiple feedbacks
        self.db.add_feedback(
            user_id="user1",
            session_id="session1",
            suggestion_id="suggestion1",
            feedback_type=FeedbackType.ACCEPTED,
            value=1.0
        )
        
        self.db.add_feedback(
            user_id="user2",
            session_id="session2",
            suggestion_id="suggestion2",
            feedback_type=FeedbackType.REJECTED,
            value=0.0
        )
        
        # Test filtering by user
        user1_feedback = self.db.get_feedback(user_id="user1")
        assert len(user1_feedback) == 1
        assert user1_feedback[0].user_id == "user1"
        
        # Test filtering by session
        session2_feedback = self.db.get_feedback(session_id="session2")
        assert len(session2_feedback) == 1
        assert session2_feedback[0].session_id == "session2"
        
        # Test filtering by feedback type
        accepted_feedback = self.db.get_feedback(
            feedback_type=FeedbackType.ACCEPTED
        )
        assert len(accepted_feedback) == 1
        assert accepted_feedback[0].feedback_type == FeedbackType.ACCEPTED
    
    def test_user_preferences(self):
        """Test setting and getting user preferences."""
        # Set preferences
        self.db.set_user_preference(
            user_id="test_user",
            key="suggestion_thresholds",
            value={'min_priority': 50}
        )
        
        # Get preferences
        prefs = self.db.get_user_preferences("test_user")
        assert 'suggestion_thresholds' in prefs
        assert prefs['suggestion_thresholds']['min_priority'] == 50
        
        # Update preferences
        self.db.set_user_preference(
            user_id="test_user",
            key="suggestion_thresholds",
            value={'min_priority': 75}
        )
        
        updated_prefs = self.db.get_user_preferences("test_user")
        assert updated_prefs['suggestion_thresholds']['min_priority'] == 75
    
    def test_learned_patterns(self):
        """Test adding and retrieving learned patterns."""
        # Add pattern
        self.db.add_learned_pattern(
            pattern_id="test_pattern",
            confidence_adjustment=0.8,
            metadata={'type': 'test'}
        )
        
        # Get patterns
        patterns = self.db.get_learned_patterns()
        assert len(patterns) == 1
        assert patterns[0][0] == "test_pattern"
        assert patterns[0][1] == 0.8
        assert patterns[0][3]['type'] == 'test'
        
        # Update pattern
        self.db.add_learned_pattern(
            pattern_id="test_pattern",
            confidence_adjustment=0.9,
            metadata={'type': 'test', 'updated': True}
        )
        
        updated_patterns = self.db.get_learned_patterns()
        assert len(updated_patterns) == 1
        assert updated_patterns[0][1] == 0.9
        assert updated_patterns[0][3]['updated'] is True


class TestFeedbackCollector:
    """Test the feedback collector."""
    
    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.collector = FeedbackCollector(self.db_path)
    
    def teardown_method(self):
        """Clean up temporary database."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_record_feedback(self):
        """Test recording feedback."""
        # Record feedback
        self.collector.record_feedback(
            suggestion_id="test_suggestion",
            feedback_type="accept",
            value=1.0,
            suggestion_type="refactoring",
            metadata={'extra': 'data'}
        )
        
        # Check if feedback was recorded
        feedbacks = self.collector.db.get_feedback()
        assert len(feedbacks) == 1
        
        feedback = feedbacks[0]
        assert feedback.suggestion_id == "test_suggestion"
        assert feedback.feedback_type == FeedbackType.ACCEPTED
        assert feedback.value == 1.0
        assert feedback.metadata['suggestion_type'] == "refactoring"
        assert feedback.metadata['extra'] == 'data'
    
    def test_get_feedback_summary(self):
        """Test getting feedback summary."""
        # Record multiple feedbacks
        self.collector.record_feedback(
            suggestion_id="s1",
            feedback_type="accept",
            value=1.0,
            suggestion_type="refactoring"
        )
        
        self.collector.record_feedback(
            suggestion_id="s2",
            feedback_type="reject",
            value=0.0,
            suggestion_type="refactoring"
        )
        
        self.collector.record_feedback(
            suggestion_id="s3",
            feedback_type="accept",
            value=1.0,
            suggestion_type="security"
        )
        
        # Get summary
        summary = self.collector.get_feedback_summary()
        
        assert summary['total_feedbacks'] == 3
        assert summary['acceptance_rate'] == 2/3
        assert summary['average_rating'] == 2/3
        assert summary['type_preferences']['refactoring']['acceptance_rate'] == 0.5
        assert summary['type_preferences']['security']['acceptance_rate'] == 1.0
    
    def test_set_user_preferences(self):
        """Test setting user preferences."""
        # Set preferences
        self.collector.set_user_preference(
            "min_priority",
            50
        )
        
        # Check if preferences were set
        prefs = self.collector.db.get_user_preferences(
            self.collector.current_user_id
        )
        assert prefs['min_priority'] == 50
    
    def test_get_user_preferences(self):
        """Test getting user preferences with defaults."""
        # Get preferences without setting any
        prefs = self.collector.get_user_preferences()
        
        # Should return defaults
        assert 'min_priority' in prefs
        assert 'filtered_types' in prefs
        assert prefs['min_priority'] == 0  # Default
        assert prefs['filtered_types'] == []  # Default
        
        # Set some preferences
        self.collector.set_user_preference("min_priority", 75)
        
        # Get updated preferences
        updated_prefs = self.collector.get_user_preferences()
        assert updated_prefs['min_priority'] == 75
        assert updated_prefs['filtered_types'] == []  # Still default


class TestLearningEngine:
    """Test the learning engine."""
    
    def setup_method(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.db = FeedbackDatabase(self.db_path)
        self.engine = LearningEngine(self.db)
    
    def teardown_method(self):
        """Clean up temporary database."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_learn_from_feedback(self):
        """Test learning from feedback."""
        # Add feedback data
        feedbacks = [
            FeedbackItem(
                user_id="user1",
                session_id="session1",
                suggestion_id="s1",
                feedback_type=FeedbackType.ACCEPTED,
                value=1.0,
                metadata={'suggestion_type': 'refactoring'},
                timestamp=datetime.now()
            ),
            FeedbackItem(
                user_id="user1",
                session_id="session1",
                suggestion_id="s2",
                feedback_type=FeedbackType.REJECTED,
                value=0.0,
                metadata={'suggestion_type': 'refactoring'},
                timestamp=datetime.now()
            ),
            FeedbackItem(
                user_id="user1",
                session_id="session1",
                suggestion_id="s3",
                feedback_type=FeedbackType.ACCEPTED,
                value=1.0,
                metadata={'suggestion_type': 'security'},
                timestamp=datetime.now()
            )
        ]
        
        # Learn from feedback
        patterns = self.engine.learn_from_feedback(feedbacks)
        
        # Check learned patterns
        assert len(patterns) == 2  # refactoring and security
        assert 'refactoring' in patterns
        assert 'security' in patterns
        assert patterns['refactoring'] < 1.0  # Should be lower due to rejection
        assert patterns['security'] == 1.0  # Should be high due to acceptance
    
    def test_get_pattern_confidence(self):
        """Test getting pattern confidence."""
        # Add some learned patterns directly
        self.db.add_learned_pattern("refactoring", 0.7)
        self.db.add_learned_pattern("security", 0.9)
        
        # Re-create engine to load patterns
        self.engine = LearningEngine(self.db)
        
        # Test getting confidence
        refactor_conf = self.engine.get_pattern_confidence("refactoring", 0.5)
        security_conf = self.engine.get_pattern_confidence("security", 0.5)
        unknown_conf = self.engine.get_pattern_confidence("unknown", 0.5)
        
        assert refactor_conf < 0.5  # Should be adjusted down
        assert security_conf > 0.5  # Should be adjusted up
        assert unknown_conf == 0.5  # Should remain unchanged
    
    def test_decay_old_patterns(self):
        """Test pattern decay over time."""
        # Add old pattern
        old_timestamp = datetime.now() - timedelta(days=40)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            INSERT INTO learned_patterns 
            (pattern_id, confidence_adjustment, last_updated, metadata)
            VALUES (?, ?, ?, ?)
            """,
            ("old_pattern", 0.9, old_timestamp.isoformat(), "{}")
        )
        conn.commit()
        
        # Decay patterns
        self.engine._decay_old_patterns()
        
        # Check if pattern was decayed
        patterns = self.db.get_learned_patterns()
        old_pattern = next((p for p in patterns if p[0] == "old_pattern"), None)
        
        assert old_pattern is not None
        assert old_pattern[1] < 0.9  # Should be decayed
    
    def test_update_patterns(self):
        """Test updating patterns."""
        # Update patterns
        test_patterns = {
            "pattern1": 0.8,
            "pattern2": 0.6
        }
        
        self.engine.update_patterns(test_patterns)
        
        # Check if patterns were saved
        patterns = self.db.get_learned_patterns()
        assert len(patterns) == 2
        
        pattern_dict = {p[0]: p[1] for p in patterns}
        assert pattern_dict["pattern1"] == 0.8
        assert pattern_dict["pattern2"] == 0.6


class TestTeamLearningAggregator:
    """Test team learning aggregation."""
    
    def setup_method(self):
        """Create temporary databases for team members."""
        self.temp_dir = tempfile.mkdtemp()
        self.team_dbs = {}
        
        # Create databases for team members
        for member in ["alice", "bob", "charlie"]:
            db_path = Path(self.temp_dir) / f"{member}_feedback.db"
            self.team_dbs[member] = FeedbackDatabase(db_path)
        
        self.aggregator = TeamLearningAggregator(self.team_dbs)
    
    def teardown_method(self):
        """Clean up temporary databases."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_aggregate_team_feedback(self):
        """Test aggregating feedback from team members."""
        # Add feedback for different team members
        self.team_dbs["alice"].add_feedback(
            user_id="alice",
            session_id="s1",
            suggestion_id="sug1",
            feedback_type=FeedbackType.ACCEPTED,
            value=1.0,
            metadata={'suggestion_type': 'refactoring'}
        )
        
        self.team_dbs["bob"].add_feedback(
            user_id="bob",
            session_id="s2",
            suggestion_id="sug2",
            feedback_type=FeedbackType.ACCEPTED,
            value=1.0,
            metadata={'suggestion_type': 'refactoring'}
        )
        
        self.team_dbs["charlie"].add_feedback(
            user_id="charlie",
            session_id="s3",
            suggestion_id="sug3",
            feedback_type=FeedbackType.REJECTED,
            value=0.0,
            metadata={'suggestion_type': 'refactoring'}
        )
        
        # Aggregate team preferences
        team_prefs = self.aggregator.get_team_preferences()
        
        assert 'refactoring' in team_prefs['type_preferences']
        acceptance_rate = team_prefs['type_preferences']['refactoring']['acceptance_rate']
        assert acceptance_rate == pytest.approx(2/3, rel=0.01)
    
    def test_get_team_learned_patterns(self):
        """Test getting aggregated team patterns."""
        # Add patterns for different team members
        self.team_dbs["alice"].add_learned_pattern("pattern1", 0.8)
        self.team_dbs["bob"].add_learned_pattern("pattern1", 0.7)
        self.team_dbs["charlie"].add_learned_pattern("pattern1", 0.9)
        
        self.team_dbs["alice"].add_learned_pattern("pattern2", 0.6)
        self.team_dbs["bob"].add_learned_pattern("pattern2", 0.5)
        
        # Get aggregated patterns
        team_patterns = self.aggregator.get_team_learned_patterns()
        
        assert "pattern1" in team_patterns
        assert "pattern2" in team_patterns
        
        # Check weighted averages
        assert team_patterns["pattern1"] == pytest.approx(0.8, rel=0.01)
        assert team_patterns["pattern2"] == pytest.approx(0.55, rel=0.01)
    
    def test_aggregate_new_patterns(self):
        """Test aggregating new patterns from single member."""
        # Create aggregator with Alice having new patterns
        alice_db = self.team_dbs["alice"]
        alice_db.add_learned_pattern("new_pattern", 0.85)
        
        # Get aggregated patterns
        team_patterns = self.aggregator.get_team_learned_patterns()
        
        # New pattern should be included but with reduced confidence
        assert "new_pattern" in team_patterns
        assert team_patterns["new_pattern"] < 0.85


class TestAdaptiveSuggestionEngine:
    """Test the adaptive suggestion engine."""
    
    def setup_method(self):
        """Create a temporary database and learning engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_feedback.db"
        self.db = FeedbackDatabase(self.db_path)
        self.learning_engine = LearningEngine(self.db)
        self.adaptive_engine = AdaptiveSuggestionEngine(self.learning_engine)
    
    def teardown_method(self):
        """Clean up temporary database."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_adjust_suggestion_confidence(self):
        """Test adjusting suggestion confidence based on learned patterns."""
        # Add learned pattern
        self.db.add_learned_pattern("refactoring", 0.8)
        self.learning_engine = LearningEngine(self.db)  # Reload
        
        # Test adjustment
        original_confidence = 0.6
        adjusted = self.adaptive_engine.adjust_suggestion_confidence(
            SuggestionType.REFACTORING.value,
            original_confidence
        )
        
        # Should be adjusted based on pattern
        expected = 0.6 * 0.8
        assert adjusted == pytest.approx(expected, rel=0.01)
    
    def test_filter_suggestions_by_user_preferences(self):
        """Test filtering suggestions based on user preferences."""
        # Create test suggestions
        from dataclasses import dataclass
        
        @dataclass
        class TestSuggestion:
            type: str
            priority: int
            confidence: float
        
        suggestions = [
            TestSuggestion(type=SuggestionType.REFACTORING.value, priority=80, confidence=0.8),
            TestSuggestion(type=SuggestionType.STYLE.value, priority=40, confidence=0.6),
            TestSuggestion(type=SuggestionType.SECURITY.value, priority=90, confidence=0.9),
        ]
        
        # Set user preferences
        prefs = {
            'min_priority': 50,
            'filtered_types': [SuggestionType.STYLE.value]
        }
        
        # Filter suggestions
        filtered = self.adaptive_engine.filter_suggestions(suggestions, prefs)
        
        # Should filter out style and low priority
        assert len(filtered) == 2
        assert all(s.type != SuggestionType.STYLE.value for s in filtered)
        assert all(s.priority >= 50 for s in filtered)
    
    def test_get_personalized_suggestions(self):
        """Test getting personalized suggestions."""
        # Add some feedback and patterns
        self.db.add_feedback(
            user_id="test_user",
            session_id="session1",
            suggestion_id="s1",
            feedback_type=FeedbackType.ACCEPTED,
            value=1.0,
            metadata={'suggestion_type': SuggestionType.REFACTORING.value}
        )
        
        self.db.add_learned_pattern(SuggestionType.REFACTORING.value, 0.9)
        self.learning_engine = LearningEngine(self.db)  # Reload
        
        # Create test suggestions
        from dataclasses import dataclass
        
        @dataclass
        class TestSuggestion:
            type: str
            priority: int
            confidence: float
        
        suggestions = [
            TestSuggestion(type=SuggestionType.REFACTORING.value, priority=70, confidence=0.7),
            TestSuggestion(type=SuggestionType.STYLE.value, priority=50, confidence=0.5),
        ]
        
        # Get personalized suggestions
        personalized = self.adaptive_engine.get_personalized_suggestions(
            suggestions,
            "test_user"
        )
        
        # Refactoring suggestion should have higher confidence
        refactor_sug = next(s for s in personalized if s.type == SuggestionType.REFACTORING.value)
        style_sug = next(s for s in personalized if s.type == SuggestionType.STYLE.value)
        
        assert refactor_sug.confidence > 0.7  # Should be adjusted up
        assert style_sug.confidence == 0.5  # Should remain unchanged