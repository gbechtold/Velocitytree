# Learning from User Feedback

The VelocityTree learning system adapts code suggestions based on user feedback, creating a personalized analysis experience that improves over time.

## Overview

The learning system collects feedback on code suggestions and uses machine learning to:
- Adjust suggestion priorities based on acceptance patterns
- Filter suggestions according to user preferences
- Learn team-wide patterns for collaborative environments
- Decay old patterns to adapt to changing preferences

## Architecture

### Core Components

1. **FeedbackCollector**: Records user feedback on suggestions
2. **LearningEngine**: Processes feedback and learns patterns
3. **AdaptiveSuggestionEngine**: Applies learned patterns to suggestions
4. **TeamLearningAggregator**: Combines learning across team members

### Data Flow

```
User Feedback → FeedbackCollector → Database
                                     ↓
                              LearningEngine
                                     ↓
                           Pattern Extraction
                                     ↓
                         AdaptiveSuggestionEngine
                                     ↓
                          Personalized Suggestions
```

## Usage

### Command Line Interface

Enable feedback collection during analysis:

```bash
vtree suggestions realtime myfile.py --feedback
```

Interactive analysis with feedback:

```bash
vtree suggestions realtime myproject/ --interactive --feedback
```

Batch processing with feedback:

```bash
vtree suggestions realtime src/ --batch --feedback --output report.json
```

### Feedback Types

The system collects several types of feedback:

1. **Acceptance/Rejection**: Whether a suggestion was helpful
2. **Ratings**: 1-5 star ratings for suggestion quality
3. **Comments**: Free-form text feedback
4. **Implicit**: Actions taken (applying fixes, dismissing suggestions)

### User Preferences

Set personal preferences for suggestion filtering:

```python
# Minimum priority threshold
feedback_collector.set_user_preference("min_priority", 50)

# Filter out specific suggestion types
feedback_collector.set_user_preference("filtered_types", ["style", "documentation"])

# Custom thresholds
feedback_collector.set_user_preference("complexity_threshold", 10)
```

## Learning Algorithm

### Pattern Recognition

The learning engine identifies patterns in user feedback:

```python
def learn_from_feedback(self, feedbacks: List[FeedbackItem]) -> Dict[str, float]:
    """Learn patterns from user feedback."""
    pattern_scores = {}
    
    # Group feedback by suggestion type
    grouped = self._group_by_type(feedbacks)
    
    for suggestion_type, type_feedbacks in grouped.items():
        # Calculate acceptance rate
        accepted = sum(1 for f in type_feedbacks 
                      if f.feedback_type == FeedbackType.ACCEPTED)
        total = len(type_feedbacks)
        
        # Weighted by recency and confidence
        acceptance_rate = accepted / total if total > 0 else 0.5
        confidence = min(1.0, total / 10)  # Confidence grows with more data
        
        pattern_scores[suggestion_type] = (
            acceptance_rate * confidence + 0.5 * (1 - confidence)
        )
    
    return pattern_scores
```

### Confidence Adjustment

Suggestions are adjusted based on learned patterns:

```python
def adjust_suggestion_confidence(self, suggestion_type: str, 
                               original_confidence: float) -> float:
    """Adjust confidence based on learned patterns."""
    if suggestion_type in self.learned_patterns:
        pattern_confidence = self.learned_patterns[suggestion_type]
        # Blend original and learned confidence
        return original_confidence * pattern_confidence
    return original_confidence
```

### Pattern Decay

Old patterns decay over time to adapt to changing preferences:

```python
def _decay_old_patterns(self):
    """Decay confidence of old patterns."""
    current_time = datetime.now()
    
    for pattern_id, last_updated in self.pattern_timestamps.items():
        age_days = (current_time - last_updated).days
        
        if age_days > 30:  # Start decay after 30 days
            decay_factor = 0.95 ** (age_days / 30)
            self.learned_patterns[pattern_id] *= decay_factor
```

## Team Learning

### Aggregating Team Feedback

The system can aggregate learning across team members:

```python
aggregator = TeamLearningAggregator(team_databases)
team_patterns = aggregator.get_team_learned_patterns()
```

### Weighted Averaging

Team patterns use weighted averaging based on:
- Feedback volume per user
- Recency of feedback
- User expertise level (if configured)

## Database Schema

### Feedback Table

```sql
CREATE TABLE feedback (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    suggestion_id TEXT NOT NULL,
    feedback_type TEXT NOT NULL,
    value REAL,
    timestamp TEXT NOT NULL,
    metadata TEXT
);
```

### User Preferences Table

```sql
CREATE TABLE user_preferences (
    user_id TEXT NOT NULL,
    preference_key TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    PRIMARY KEY (user_id, preference_key)
);
```

### Learned Patterns Table

```sql
CREATE TABLE learned_patterns (
    pattern_id TEXT PRIMARY KEY,
    confidence_adjustment REAL NOT NULL,
    last_updated TEXT NOT NULL,
    metadata TEXT
);
```

## Integration with Suggestions

### Real-time Adaptation

The suggestion engine applies learning in real-time:

```python
def _apply_adaptive_learning(self, suggestions: List[CodeSuggestion]) -> List[CodeSuggestion]:
    """Apply adaptive learning to suggestions."""
    adapted_suggestions = []
    
    for suggestion in suggestions:
        # Get confidence adjustment
        confidence_adjustment = self.learning_engine.get_pattern_confidence(
            suggestion.type.value,
            suggestion.priority / 100.0
        )
        
        # Create adjusted suggestion
        adjusted_suggestion = CodeSuggestion(
            type=suggestion.type,
            severity=suggestion.severity,
            message=suggestion.message,
            range=suggestion.range,
            file_path=suggestion.file_path,
            quick_fixes=suggestion.quick_fixes,
            metadata=suggestion.metadata,
            priority=int(confidence_adjustment * 100)
        )
        
        # Apply user preference filtering
        if not self._should_filter_suggestion(adjusted_suggestion):
            adapted_suggestions.append(adjusted_suggestion)
    
    return adapted_suggestions
```

### Cache Integration

Learning is applied even to cached suggestions:

```python
if cache_key in self.cache:
    cached_content, cached_suggestions = self.cache[cache_key]
    if cached_content == content:
        # Apply adaptive learning to cached suggestions
        adapted_suggestions = self._apply_adaptive_learning(cached_suggestions)
        return adapted_suggestions
```

## API Reference

### FeedbackCollector

```python
class FeedbackCollector:
    def record_feedback(
        self,
        suggestion_id: str,
        feedback_type: str,
        value: Optional[float] = None,
        suggestion_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record user feedback for a suggestion."""
        
    def get_feedback_summary(
        self,
        user_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get summary of feedback data."""
        
    def set_user_preference(self, key: str, value: Any) -> None:
        """Set a user preference."""
        
    def get_user_preferences(self) -> Dict[str, Any]:
        """Get all user preferences with defaults."""
```

### LearningEngine

```python
class LearningEngine:
    def learn_from_feedback(
        self,
        feedbacks: List[FeedbackItem]
    ) -> Dict[str, float]:
        """Learn patterns from feedback data."""
        
    def get_pattern_confidence(
        self,
        pattern_type: str,
        base_confidence: float
    ) -> float:
        """Get adjusted confidence for a pattern."""
        
    def update_patterns(
        self,
        patterns: Dict[str, float]
    ) -> None:
        """Update learned patterns in database."""
```

### AdaptiveSuggestionEngine

```python
class AdaptiveSuggestionEngine:
    def adjust_suggestion_confidence(
        self,
        suggestion_type: str,
        original_confidence: float
    ) -> float:
        """Adjust confidence based on learned patterns."""
        
    def filter_suggestions(
        self,
        suggestions: List[Any],
        user_preferences: Dict[str, Any]
    ) -> List[Any]:
        """Filter suggestions based on user preferences."""
        
    def get_personalized_suggestions(
        self,
        suggestions: List[Any],
        user_id: str
    ) -> List[Any]:
        """Get personalized suggestions for a user."""
```

## Examples

### Basic Feedback Collection

```python
# Initialize components
feedback_collector = FeedbackCollector()
learning_engine = LearningEngine(feedback_collector.db)

# Record feedback
feedback_collector.record_feedback(
    suggestion_id="ref_001",
    feedback_type="accept",
    value=4.0,  # 4 out of 5 rating
    suggestion_type="refactoring"
)

# Learn from feedback
feedbacks = feedback_collector.db.get_feedback()
patterns = learning_engine.learn_from_feedback(feedbacks)
```

### Team Learning

```python
# Set up team databases
team_dbs = {
    "alice": FeedbackDatabase("alice_feedback.db"),
    "bob": FeedbackDatabase("bob_feedback.db"),
    "charlie": FeedbackDatabase("charlie_feedback.db")
}

# Aggregate team learning
aggregator = TeamLearningAggregator(team_dbs)
team_patterns = aggregator.get_team_learned_patterns()

# Apply team patterns
team_engine = LearningEngine()
team_engine.update_patterns(team_patterns)
```

### Preference-based Filtering

```python
# Set user preferences
feedback_collector.set_user_preference("min_priority", 60)
feedback_collector.set_user_preference("filtered_types", ["style"])

# Get filtered suggestions
suggestions = suggestion_engine.analyze_file(file_path)
personalized = adaptive_engine.get_personalized_suggestions(
    suggestions,
    user_id="current_user"
)
```

## Best Practices

1. **Provide Consistent Feedback**: Regular feedback improves learning accuracy
2. **Review Learned Patterns**: Periodically check what the system has learned
3. **Adjust Preferences**: Fine-tune filtering preferences as needed
4. **Team Coordination**: Share learning insights with team members
5. **Privacy Considerations**: Feedback data may contain sensitive information

## Performance Considerations

- Feedback is stored locally in SQLite for fast access
- Learning computations are lightweight and real-time
- Pattern decay runs periodically, not on every request
- Team aggregation can be run asynchronously

## Future Enhancements

Planned improvements include:
- Neural network-based pattern recognition
- Cross-project learning transfer
- Automatic preference discovery
- Feedback quality metrics
- Integration with IDE plugins