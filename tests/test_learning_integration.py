"""
Integration tests for the learning system with real-time suggestions.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

from velocitytree.realtime_suggestions import RealTimeSuggestionEngine, SuggestionType
from velocitytree.code_analysis.analyzer import CodeAnalyzer
from velocitytree.code_analysis.models import (
    ModuleAnalysis, CodeIssue, Severity, IssueCategory, 
    CodeLocation, ComplexityMetrics as CodeMetrics
)
from velocitytree.documentation.quality import DocQualityChecker
from velocitytree.learning.feedback_collector import (
    FeedbackCollector, LearningEngine, FeedbackType
)


class TestLearningIntegration:
    """Test integration between learning system and suggestions."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_module.py"
        
        # Create test file
        self.test_file.write_text("""
def poorly_named_function(x):
    '''Bad docstring'''
    if x > 10:
        return x * 2
    else:
        if x < 0:
            return -x
        else:
            return x
            
class my_class:
    def __init__(self):
        self.value = 0
        
    def another_bad_name(self):
        return self.value
        
def unused_function():
    pass
""")
        
        # Set up components
        self.analyzer = CodeAnalyzer()
        self.quality_checker = DocQualityChecker()
        self.feedback_collector = FeedbackCollector(
            Path(self.temp_dir) / "feedback.db"
        )
        self.learning_engine = LearningEngine(self.feedback_collector.db)
        
        # Create suggestion engine with learning
        self.suggestion_engine = RealTimeSuggestionEngine(
            analyzer=self.analyzer,
            quality_checker=self.quality_checker,
            feedback_collector=self.feedback_collector,
            learning_engine=self.learning_engine
        )
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
    
    def test_suggestions_with_feedback(self):
        """Test that suggestions adapt based on feedback."""
        # Get initial suggestions
        initial_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Find a naming suggestion
        naming_suggestion = next(
            (s for s in initial_suggestions if "naming" in s.message.lower()),
            None
        )
        assert naming_suggestion is not None
        
        initial_priority = naming_suggestion.priority
        
        # Provide positive feedback for naming suggestions
        self.feedback_collector.record_feedback(
            suggestion_id="naming_1",
            feedback_type="accept",
            value=1.0,
            suggestion_type=SuggestionType.STYLE.value
        )
        
        self.feedback_collector.record_feedback(
            suggestion_id="naming_2",
            feedback_type="accept",
            value=1.0,
            suggestion_type=SuggestionType.STYLE.value
        )
        
        # Learn from feedback
        feedbacks = self.feedback_collector.db.get_feedback()
        patterns = self.learning_engine.learn_from_feedback(feedbacks)
        self.learning_engine.update_patterns(patterns)
        
        # Clear cache to force re-analysis
        self.suggestion_engine.clear_cache()
        
        # Get new suggestions
        adapted_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Find the naming suggestion again
        adapted_naming = next(
            (s for s in adapted_suggestions if "naming" in s.message.lower()),
            None
        )
        
        # Priority should be adjusted based on positive feedback
        assert adapted_naming is not None
        assert adapted_naming.priority >= initial_priority
    
    def test_user_preference_filtering(self):
        """Test that user preferences filter suggestions."""
        # Set user preference to filter out low priority suggestions
        self.feedback_collector.set_user_preference("min_priority", 60)
        
        # Get suggestions
        suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Apply adaptive learning (which includes preference filtering)
        adapted = self.suggestion_engine._apply_adaptive_learning(suggestions)
        
        # All suggestions should have priority >= 60
        assert all(s.priority >= 60 for s in adapted)
    
    def test_negative_feedback_reduces_priority(self):
        """Test that negative feedback reduces suggestion priority."""
        # Get initial suggestions
        initial_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Find a documentation suggestion
        doc_suggestion = next(
            (s for s in initial_suggestions if s.type == SuggestionType.DOCUMENTATION),
            None
        )
        assert doc_suggestion is not None
        
        initial_priority = doc_suggestion.priority
        
        # Provide negative feedback for documentation suggestions
        self.feedback_collector.record_feedback(
            suggestion_id="doc_1",
            feedback_type="reject",
            value=0.0,
            suggestion_type=SuggestionType.DOCUMENTATION.value
        )
        
        self.feedback_collector.record_feedback(
            suggestion_id="doc_2",
            feedback_type="reject",
            value=0.0,
            suggestion_type=SuggestionType.DOCUMENTATION.value
        )
        
        # Learn from feedback
        feedbacks = self.feedback_collector.db.get_feedback()
        patterns = self.learning_engine.learn_from_feedback(feedbacks)
        self.learning_engine.update_patterns(patterns)
        
        # Clear cache and re-analyze
        self.suggestion_engine.clear_cache()
        adapted_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Find documentation suggestion again
        adapted_doc = next(
            (s for s in adapted_suggestions if s.type == SuggestionType.DOCUMENTATION),
            None
        )
        
        # Priority should be reduced
        if adapted_doc:
            assert adapted_doc.priority < initial_priority
    
    def test_feedback_persistence(self):
        """Test that feedback persists across sessions."""
        # Record feedback
        self.feedback_collector.record_feedback(
            suggestion_id="test_1",
            feedback_type="accept",
            value=1.0,
            suggestion_type=SuggestionType.REFACTORING.value
        )
        
        # Create new instances with same database
        new_collector = FeedbackCollector(self.feedback_collector.db.db_path)
        new_engine = LearningEngine(new_collector.db)
        
        # Check feedback exists
        feedbacks = new_collector.db.get_feedback()
        assert len(feedbacks) == 1
        assert feedbacks[0].suggestion_id == "test_1"
        
        # Learn from persisted feedback
        patterns = new_engine.learn_from_feedback(feedbacks)
        assert SuggestionType.REFACTORING.value in patterns
        assert patterns[SuggestionType.REFACTORING.value] > 0.5
    
    def test_cache_with_adaptive_learning(self):
        """Test that cached suggestions still get adaptive learning applied."""
        # Analyze file (will be cached)
        first_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Record feedback
        self.feedback_collector.record_feedback(
            suggestion_id="cached_1",
            feedback_type="accept",
            value=1.0,
            suggestion_type=first_suggestions[0].type.value
        )
        
        # Learn from feedback
        feedbacks = self.feedback_collector.db.get_feedback()
        patterns = self.learning_engine.learn_from_feedback(feedbacks)
        self.learning_engine.update_patterns(patterns)
        
        # Analyze again (should use cache but apply learning)
        cached_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text()
        )
        
        # Suggestions should be adapted even though they came from cache
        assert len(cached_suggestions) == len(first_suggestions)
        
        # Check that priorities changed based on feedback
        first_type_priorities = {s.type: s.priority for s in first_suggestions}
        cached_type_priorities = {s.type: s.priority for s in cached_suggestions}
        
        # At least one priority should have changed
        priority_changes = sum(
            1 for t in first_type_priorities
            if first_type_priorities[t] != cached_type_priorities.get(t, 0)
        )
        assert priority_changes > 0
    
    def test_mixed_feedback_learning(self):
        """Test learning from mixed positive and negative feedback."""
        # Record mixed feedback for same suggestion type
        for i in range(3):
            self.feedback_collector.record_feedback(
                suggestion_id=f"style_{i}",
                feedback_type="accept" if i < 2 else "reject",
                value=1.0 if i < 2 else 0.0,
                suggestion_type=SuggestionType.STYLE.value
            )
        
        # Learn from feedback
        feedbacks = self.feedback_collector.db.get_feedback()
        patterns = self.learning_engine.learn_from_feedback(feedbacks)
        
        # Style pattern should be positive but not 1.0 (due to one rejection)
        assert SuggestionType.STYLE.value in patterns
        assert 0.5 < patterns[SuggestionType.STYLE.value] < 1.0
    
    def test_contextual_adaptation(self):
        """Test that suggestions adapt based on context."""
        # Analyze with context indicating hot file
        hot_file_context = {"hot_file": True}
        hot_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text(),
            hot_file_context
        )
        
        # Analyze without hot file context
        normal_suggestions = self.suggestion_engine._analyze_sync(
            self.test_file,
            self.test_file.read_text(),
            {}
        )
        
        # Priorities should be different for hot file
        hot_priorities = [s.priority for s in hot_suggestions]
        normal_priorities = [s.priority for s in normal_suggestions]
        
        # Average priority should be higher for hot file
        assert sum(hot_priorities) / len(hot_priorities) > \
               sum(normal_priorities) / len(normal_priorities)
    
    def test_feedback_summary_generation(self):
        """Test generating feedback summary for analysis."""
        # Record various feedbacks
        suggestion_types = [
            SuggestionType.REFACTORING,
            SuggestionType.STYLE,
            SuggestionType.DOCUMENTATION,
            SuggestionType.SECURITY
        ]
        
        for i, stype in enumerate(suggestion_types):
            # More accepts for refactoring and security
            accepted = i in [0, 3]
            self.feedback_collector.record_feedback(
                suggestion_id=f"summary_{i}",
                feedback_type="accept" if accepted else "reject",
                value=1.0 if accepted else 0.0,
                suggestion_type=stype.value
            )
        
        # Get feedback summary
        summary = self.feedback_collector.get_feedback_summary()
        
        assert summary['total_feedbacks'] == 4
        assert summary['acceptance_rate'] == 0.5
        
        # Check type preferences
        assert summary['type_preferences'][SuggestionType.REFACTORING.value]['acceptance_rate'] == 1.0
        assert summary['type_preferences'][SuggestionType.STYLE.value]['acceptance_rate'] == 0.0
        assert summary['type_preferences'][SuggestionType.SECURITY.value]['acceptance_rate'] == 1.0