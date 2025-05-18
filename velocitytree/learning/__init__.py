"""Learning and feedback system for VelocityTree."""

from .feedback_collector import (
    FeedbackCollector,
    FeedbackType,
    FeedbackReason,
    FeedbackEntry,
    LearnedPattern,
    LearningEngine,
    TeamLearningAggregator,
    AdaptiveSuggestionEngine
)

__all__ = [
    'FeedbackCollector',
    'FeedbackType',
    'FeedbackReason',
    'FeedbackEntry',
    'LearnedPattern',
    'LearningEngine',
    'TeamLearningAggregator',
    'AdaptiveSuggestionEngine'
]