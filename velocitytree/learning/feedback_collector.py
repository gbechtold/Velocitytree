"""
Feedback collection and learning system for VelocityTree.
Collects user feedback on suggestions and learns to improve recommendations.
"""

import json
import sqlite3
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
import hashlib
import pickle
import numpy as np
from collections import defaultdict, Counter

from velocitytree.realtime_suggestions import (
    CodeSuggestion, SuggestionType, Severity
)
from velocitytree.refactoring import RefactoringType
from velocitytree.utils import logger


class FeedbackType(Enum):
    """Types of user feedback."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    MODIFIED = "modified"
    POSTPONED = "postponed"
    IGNORED = "ignored"


class FeedbackReason(Enum):
    """Reasons for feedback."""
    # Positive reasons
    HELPFUL = "helpful"
    ACCURATE = "accurate"
    WELL_EXPLAINED = "well_explained"
    TIME_SAVING = "time_saving"
    
    # Negative reasons
    NOT_APPLICABLE = "not_applicable"
    INCORRECT = "incorrect"
    TOO_RISKY = "too_risky"
    TOO_COMPLEX = "too_complex"
    ALREADY_IMPLEMENTED = "already_implemented"
    PERFORMANCE_CONCERN = "performance_concern"
    STYLE_PREFERENCE = "style_preference"
    
    # Neutral reasons
    NOT_NOW = "not_now"
    NEED_MORE_INFO = "need_more_info"
    CUSTOM = "custom"


@dataclass
class FeedbackEntry:
    """A single feedback entry from a user."""
    id: str
    timestamp: datetime
    user_id: str
    session_id: str
    suggestion_hash: str
    suggestion_type: SuggestionType
    severity: Severity
    feedback_type: FeedbackType
    reasons: List[FeedbackReason] = field(default_factory=list)
    custom_reason: Optional[str] = None
    applied_changes: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    file_path: str = ""
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['suggestion_type'] = self.suggestion_type.value
        data['severity'] = self.severity.value
        data['feedback_type'] = self.feedback_type.value
        data['reasons'] = [r.value for r in self.reasons]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeedbackEntry':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['suggestion_type'] = SuggestionType(data['suggestion_type'])
        data['severity'] = Severity(data['severity'])
        data['feedback_type'] = FeedbackType(data['feedback_type'])
        data['reasons'] = [FeedbackReason(r) for r in data['reasons']]
        return cls(**data)


@dataclass
class LearnedPattern:
    """A pattern learned from user feedback."""
    pattern_id: str
    pattern_type: str  # e.g., "suggestion_preference", "refactoring_style"
    conditions: Dict[str, Any]
    action: Dict[str, Any]
    confidence: float
    support_count: int
    last_updated: datetime
    
    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if pattern matches given context."""
        for key, value in self.conditions.items():
            if key not in context:
                return False
            if isinstance(value, list):
                if context[key] not in value:
                    return False
            elif context[key] != value:
                return False
        return True


class FeedbackDatabase:
    """Database for storing feedback and learned patterns."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    suggestion_hash TEXT NOT NULL,
                    suggestion_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    feedback_type TEXT NOT NULL,
                    reasons TEXT NOT NULL,
                    custom_reason TEXT,
                    applied_changes TEXT,
                    context TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    line_number INTEGER NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    conditions TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    support_count INTEGER NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id TEXT PRIMARY KEY,
                    preferences TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS team_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_data TEXT NOT NULL,
                    team_id TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(suggestion_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_feedback_hash ON feedback(suggestion_hash)")
    
    def add_feedback(self, entry: FeedbackEntry):
        """Add a feedback entry."""
        with sqlite3.connect(self.db_path) as conn:
            data = entry.to_dict()
            conn.execute("""
                INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'],
                data['timestamp'],
                data['user_id'],
                data['session_id'],
                data['suggestion_hash'],
                data['suggestion_type'],
                data['severity'],
                data['feedback_type'],
                json.dumps(data['reasons']),
                data['custom_reason'],
                data['applied_changes'],
                json.dumps(data['context']),
                data['file_path'],
                data['line_number']
            ))
    
    def get_feedback_for_suggestion(self, suggestion_hash: str) -> List[FeedbackEntry]:
        """Get all feedback for a specific suggestion."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM feedback WHERE suggestion_hash = ?
                ORDER BY timestamp DESC
            """, (suggestion_hash,))
            
            entries = []
            for row in cursor:
                data = {
                    'id': row[0],
                    'timestamp': row[1],
                    'user_id': row[2],
                    'session_id': row[3],
                    'suggestion_hash': row[4],
                    'suggestion_type': row[5],
                    'severity': row[6],
                    'feedback_type': row[7],
                    'reasons': json.loads(row[8]),
                    'custom_reason': row[9],
                    'applied_changes': row[10],
                    'context': json.loads(row[11]),
                    'file_path': row[12],
                    'line_number': row[13]
                }
                entries.append(FeedbackEntry.from_dict(data))
            
            return entries
    
    def add_learned_pattern(self, pattern: LearnedPattern):
        """Add or update a learned pattern."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO learned_patterns VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.pattern_type,
                json.dumps(pattern.conditions),
                json.dumps(pattern.action),
                pattern.confidence,
                pattern.support_count,
                pattern.last_updated.isoformat()
            ))
    
    def get_learned_patterns(self, pattern_type: Optional[str] = None) -> List[LearnedPattern]:
        """Get learned patterns, optionally filtered by type."""
        with sqlite3.connect(self.db_path) as conn:
            if pattern_type:
                cursor = conn.execute("""
                    SELECT * FROM learned_patterns WHERE pattern_type = ?
                    ORDER BY confidence DESC
                """, (pattern_type,))
            else:
                cursor = conn.execute("""
                    SELECT * FROM learned_patterns
                    ORDER BY confidence DESC
                """)
            
            patterns = []
            for row in cursor:
                patterns.append(LearnedPattern(
                    pattern_id=row[0],
                    pattern_type=row[1],
                    conditions=json.loads(row[2]),
                    action=json.loads(row[3]),
                    confidence=row[4],
                    support_count=row[5],
                    last_updated=datetime.fromisoformat(row[6])
                ))
            
            return patterns
    
    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]):
        """Update user preferences."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_preferences VALUES (?, ?, ?)
            """, (
                user_id,
                json.dumps(preferences),
                datetime.now().isoformat()
            ))
    
    def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT preferences FROM user_preferences WHERE user_id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None


class FeedbackCollector:
    """Collects and processes user feedback on suggestions."""
    
    def __init__(self, db_path: Optional[Path] = None):
        db_path = db_path or Path.home() / ".velocitytree" / "feedback.db"
        self.db = FeedbackDatabase(db_path)
        self.current_session_id = self._generate_session_id()
        self.current_user_id = self._get_user_id()
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}-{id(self)}".encode()
        ).hexdigest()[:16]
    
    def _get_user_id(self) -> str:
        """Get or generate user ID."""
        # In a real implementation, this would get from config or system
        user_file = Path.home() / ".velocitytree" / "user_id"
        
        if user_file.exists():
            return user_file.read_text().strip()
        
        user_id = hashlib.sha256(
            f"{Path.home()}-{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text(user_id)
        
        return user_id
    
    def _hash_suggestion(self, suggestion: CodeSuggestion) -> str:
        """Create hash for suggestion to track it."""
        key_parts = [
            suggestion.type.value,
            suggestion.severity.value,
            suggestion.message,
            str(suggestion.file_path),
            str(suggestion.range.start.line),
            str(suggestion.range.start.column)
        ]
        return hashlib.sha256("-".join(key_parts).encode()).hexdigest()[:16]
    
    def record_feedback(
        self,
        suggestion: CodeSuggestion,
        feedback_type: FeedbackType,
        reasons: List[FeedbackReason],
        custom_reason: Optional[str] = None,
        applied_changes: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackEntry:
        """Record user feedback for a suggestion."""
        entry = FeedbackEntry(
            id=hashlib.sha256(
                f"{self.current_session_id}-{datetime.now().isoformat()}".encode()
            ).hexdigest()[:16],
            timestamp=datetime.now(),
            user_id=self.current_user_id,
            session_id=self.current_session_id,
            suggestion_hash=self._hash_suggestion(suggestion),
            suggestion_type=suggestion.type,
            severity=suggestion.severity,
            feedback_type=feedback_type,
            reasons=reasons,
            custom_reason=custom_reason,
            applied_changes=applied_changes,
            context=context or {},
            file_path=str(suggestion.file_path),
            line_number=suggestion.range.start.line
        )
        
        self.db.add_feedback(entry)
        logger.debug(f"Recorded feedback: {feedback_type.value} for {suggestion.type.value}")
        
        return entry
    
    def get_suggestion_history(self, suggestion: CodeSuggestion) -> List[FeedbackEntry]:
        """Get feedback history for a specific suggestion."""
        suggestion_hash = self._hash_suggestion(suggestion)
        return self.db.get_feedback_for_suggestion(suggestion_hash)
    
    def get_user_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a user's feedback."""
        user_id = user_id or self.current_user_id
        
        # This would query the database for comprehensive stats
        # For now, return a placeholder
        return {
            "total_feedback": 0,
            "acceptance_rate": 0.0,
            "most_accepted_types": [],
            "most_rejected_types": [],
            "common_reasons": []
        }


class LearningEngine:
    """Learns from user feedback to improve suggestions."""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.collector = feedback_collector
        self.db = feedback_collector.db
        self.model_cache: Dict[str, Any] = {}
    
    def learn_from_feedback(self, min_support: int = 5, min_confidence: float = 0.6):
        """Learn patterns from collected feedback."""
        patterns = []
        
        # Learn suggestion preferences
        patterns.extend(self._learn_suggestion_preferences(min_support, min_confidence))
        
        # Learn refactoring preferences
        patterns.extend(self._learn_refactoring_preferences(min_support, min_confidence))
        
        # Learn context-based patterns
        patterns.extend(self._learn_context_patterns(min_support, min_confidence))
        
        # Store learned patterns
        for pattern in patterns:
            self.db.add_learned_pattern(pattern)
        
        logger.info(f"Learned {len(patterns)} patterns from feedback")
        
        return patterns
    
    def _learn_suggestion_preferences(
        self, 
        min_support: int, 
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Learn which types of suggestions are preferred."""
        patterns = []
        
        # Analyze acceptance rates by suggestion type
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT suggestion_type, feedback_type, COUNT(*) as count
                FROM feedback
                GROUP BY suggestion_type, feedback_type
                HAVING count >= ?
            """, (min_support,))
            
            type_feedback = defaultdict(Counter)
            for row in cursor:
                suggestion_type = row[0]
                feedback_type = row[1]
                count = row[2]
                type_feedback[suggestion_type][feedback_type] = count
            
            # Create patterns for high acceptance rates
            for sug_type, feedback_counts in type_feedback.items():
                total = sum(feedback_counts.values())
                accepted = feedback_counts.get(FeedbackType.ACCEPTED.value, 0)
                rejection_rate = feedback_counts.get(FeedbackType.REJECTED.value, 0) / total
                
                if accepted / total >= min_confidence:
                    patterns.append(LearnedPattern(
                        pattern_id=f"pref_{sug_type}_accepted",
                        pattern_type="suggestion_preference",
                        conditions={"suggestion_type": sug_type},
                        action={
                            "boost_priority": 1.2,
                            "auto_suggest": True
                        },
                        confidence=accepted / total,
                        support_count=accepted,
                        last_updated=datetime.now()
                    ))
                elif rejection_rate >= min_confidence:
                    patterns.append(LearnedPattern(
                        pattern_id=f"pref_{sug_type}_rejected",
                        pattern_type="suggestion_preference",
                        conditions={"suggestion_type": sug_type},
                        action={
                            "reduce_priority": 0.5,
                            "require_confirmation": True
                        },
                        confidence=rejection_rate,
                        support_count=feedback_counts[FeedbackType.REJECTED.value],
                        last_updated=datetime.now()
                    ))
        
        return patterns
    
    def _learn_refactoring_preferences(
        self, 
        min_support: int, 
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Learn refactoring style preferences."""
        patterns = []
        
        # Analyze refactoring feedback
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT context, feedback_type, reasons, COUNT(*) as count
                FROM feedback
                WHERE suggestion_type = 'refactoring'
                GROUP BY context, feedback_type
                HAVING count >= ?
            """, (min_support,))
            
            refactoring_patterns = defaultdict(lambda: defaultdict(int))
            for row in cursor:
                context = json.loads(row[0])
                feedback_type = row[1]
                reasons = json.loads(row[2])
                count = row[3]
                
                if 'refactoring_type' in context:
                    ref_type = context['refactoring_type']
                    refactoring_patterns[ref_type][feedback_type] += count
                    
                    # Look for specific reason patterns
                    for reason in reasons:
                        if reason == FeedbackReason.TOO_RISKY.value:
                            patterns.append(LearnedPattern(
                                pattern_id=f"refactor_{ref_type}_risky",
                                pattern_type="refactoring_preference",
                                conditions={
                                    "refactoring_type": ref_type,
                                    "risk_score_min": 0.7
                                },
                                action={
                                    "reduce_priority": 0.3,
                                    "add_warning": "User finds this type of refactoring risky"
                                },
                                confidence=0.8,
                                support_count=count,
                                last_updated=datetime.now()
                            ))
        
        return patterns
    
    def _learn_context_patterns(
        self, 
        min_support: int, 
        min_confidence: float
    ) -> List[LearnedPattern]:
        """Learn patterns based on context (file type, project phase, etc.)."""
        patterns = []
        
        # Analyze context-based patterns
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT file_path, suggestion_type, feedback_type, COUNT(*) as count
                FROM feedback
                GROUP BY file_path, suggestion_type, feedback_type
                HAVING count >= ?
            """, (min_support,))
            
            file_patterns = defaultdict(lambda: defaultdict(Counter))
            for row in cursor:
                file_path = row[0]
                suggestion_type = row[1]
                feedback_type = row[2]
                count = row[3]
                
                # Extract file type
                file_ext = Path(file_path).suffix
                file_patterns[file_ext][suggestion_type][feedback_type] = count
            
            # Create patterns for file type preferences
            for file_ext, type_feedback in file_patterns.items():
                for sug_type, feedback_counts in type_feedback.items():
                    total = sum(feedback_counts.values())
                    accepted = feedback_counts.get(FeedbackType.ACCEPTED.value, 0)
                    
                    if total >= min_support and accepted / total >= min_confidence:
                        patterns.append(LearnedPattern(
                            pattern_id=f"context_{file_ext}_{sug_type}",
                            pattern_type="context_preference",
                            conditions={
                                "file_extension": file_ext,
                                "suggestion_type": sug_type
                            },
                            action={
                                "boost_priority": 1.1,
                                "confidence_multiplier": accepted / total
                            },
                            confidence=accepted / total,
                            support_count=accepted,
                            last_updated=datetime.now()
                        ))
        
        return patterns
    
    def predict_feedback(
        self, 
        suggestion: CodeSuggestion, 
        context: Dict[str, Any]
    ) -> Tuple[FeedbackType, float]:
        """Predict likely user feedback for a suggestion."""
        # Get all relevant patterns
        patterns = self.db.get_learned_patterns()
        
        # Build context for matching
        match_context = {
            "suggestion_type": suggestion.type.value,
            "severity": suggestion.severity.value,
            "file_extension": Path(suggestion.file_path).suffix,
            **context
        }
        
        # Find matching patterns
        matching_patterns = [
            p for p in patterns 
            if p.matches(match_context)
        ]
        
        if not matching_patterns:
            return FeedbackType.IGNORED, 0.5
        
        # Aggregate predictions
        predictions = defaultdict(float)
        total_confidence = 0
        
        for pattern in matching_patterns:
            # Simple voting based on pattern actions
            if pattern.action.get("auto_suggest"):
                predictions[FeedbackType.ACCEPTED] += pattern.confidence
            elif pattern.action.get("require_confirmation"):
                predictions[FeedbackType.REJECTED] += pattern.confidence
            else:
                predictions[FeedbackType.POSTPONED] += pattern.confidence
            
            total_confidence += pattern.confidence
        
        # Normalize and return highest prediction
        if total_confidence > 0:
            for feedback_type in predictions:
                predictions[feedback_type] /= total_confidence
            
            best_prediction = max(predictions.items(), key=lambda x: x[1])
            return best_prediction[0], best_prediction[1]
        
        return FeedbackType.IGNORED, 0.5
    
    def update_user_model(self, user_id: str):
        """Update personalized model for a user."""
        # Get user's feedback history
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT suggestion_type, severity, feedback_type, reasons
                FROM feedback
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 1000
            """, (user_id,))
            
            # Build user profile
            user_profile = {
                "preferred_types": Counter(),
                "rejected_types": Counter(),
                "severity_preferences": defaultdict(Counter),
                "common_reasons": Counter()
            }
            
            for row in cursor:
                suggestion_type = row[0]
                severity = row[1]
                feedback_type = row[2]
                reasons = json.loads(row[3])
                
                if feedback_type == FeedbackType.ACCEPTED.value:
                    user_profile["preferred_types"][suggestion_type] += 1
                    user_profile["severity_preferences"][severity]["accepted"] += 1
                elif feedback_type == FeedbackType.REJECTED.value:
                    user_profile["rejected_types"][suggestion_type] += 1
                    user_profile["severity_preferences"][severity]["rejected"] += 1
                
                for reason in reasons:
                    user_profile["common_reasons"][reason] += 1
            
            # Store user preferences
            self.db.update_user_preferences(user_id, {
                "profile": user_profile,
                "last_updated": datetime.now().isoformat()
            })


class TeamLearningAggregator:
    """Aggregates learning across team members."""
    
    def __init__(self, feedback_collector: FeedbackCollector):
        self.collector = feedback_collector
        self.db = feedback_collector.db
    
    def aggregate_team_patterns(
        self, 
        team_id: str,
        min_support: int = 10,
        min_agreement: float = 0.7
    ) -> List[LearnedPattern]:
        """Aggregate patterns across team members."""
        patterns = []
        
        # Get team members (in real implementation, from team management system)
        team_members = self._get_team_members(team_id)
        
        # Aggregate feedback across team
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT suggestion_type, feedback_type, COUNT(DISTINCT user_id) as users,
                       COUNT(*) as total_count
                FROM feedback
                WHERE user_id IN ({})
                GROUP BY suggestion_type, feedback_type
                HAVING users >= ?
            """.format(','.join('?' * len(team_members))), 
            team_members + [int(len(team_members) * min_agreement)])
            
            for row in cursor:
                suggestion_type = row[0]
                feedback_type = row[1]
                user_count = row[2]
                total_count = row[3]
                
                agreement_rate = user_count / len(team_members)
                
                if agreement_rate >= min_agreement and total_count >= min_support:
                    pattern_id = f"team_{team_id}_{suggestion_type}_{feedback_type}"
                    
                    patterns.append(LearnedPattern(
                        pattern_id=pattern_id,
                        pattern_type="team_preference",
                        conditions={
                            "suggestion_type": suggestion_type,
                            "team_id": team_id
                        },
                        action={
                            "team_preference": feedback_type,
                            "agreement_rate": agreement_rate,
                            "apply_to_all": True
                        },
                        confidence=agreement_rate,
                        support_count=total_count,
                        last_updated=datetime.now()
                    ))
                    
                    # Store team pattern
                    with sqlite3.connect(self.db.db_path) as store_conn:
                        store_conn.execute("""
                            INSERT OR REPLACE INTO team_patterns VALUES (?, ?, ?, ?, ?)
                        """, (
                            pattern_id,
                            json.dumps(asdict(patterns[-1])),
                            team_id,
                            agreement_rate,
                            datetime.now().isoformat()
                        ))
        
        return patterns
    
    def _get_team_members(self, team_id: str) -> List[str]:
        """Get team members for a team ID."""
        # In real implementation, this would query team management system
        # For now, return mock data
        return ["user1", "user2", "user3"]
    
    def get_team_preferences(self, team_id: str) -> Dict[str, Any]:
        """Get aggregated team preferences."""
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("""
                SELECT pattern_data FROM team_patterns
                WHERE team_id = ?
                ORDER BY confidence DESC
            """, (team_id,))
            
            preferences = {
                "patterns": [],
                "consensus_areas": [],
                "disagreement_areas": []
            }
            
            for row in cursor:
                pattern_data = json.loads(row[0])
                preferences["patterns"].append(pattern_data)
                
                if pattern_data["confidence"] >= 0.8:
                    preferences["consensus_areas"].append(
                        pattern_data["conditions"]["suggestion_type"]
                    )
                elif pattern_data["confidence"] <= 0.6:
                    preferences["disagreement_areas"].append(
                        pattern_data["conditions"]["suggestion_type"]
                    )
            
            return preferences


class AdaptiveSuggestionEngine:
    """Suggestion engine that adapts based on learned feedback."""
    
    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        learning_engine: LearningEngine
    ):
        self.collector = feedback_collector
        self.learner = learning_engine
        self.user_preferences_cache: Dict[str, Dict[str, Any]] = {}
    
    def adjust_suggestions(
        self,
        suggestions: List[CodeSuggestion],
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[CodeSuggestion]:
        """Adjust suggestions based on learned patterns and user preferences."""
        user_id = user_id or self.collector.current_user_id
        context = context or {}
        
        # Get user preferences
        if user_id not in self.user_preferences_cache:
            prefs = self.collector.db.get_user_preferences(user_id)
            if prefs:
                self.user_preferences_cache[user_id] = prefs
            else:
                self.user_preferences_cache[user_id] = {}
        
        user_prefs = self.user_preferences_cache.get(user_id, {})
        
        # Get learned patterns
        patterns = self.collector.db.get_learned_patterns()
        
        # Adjust each suggestion
        adjusted_suggestions = []
        for suggestion in suggestions:
            # Create context for pattern matching
            match_context = {
                "suggestion_type": suggestion.type.value,
                "severity": suggestion.severity.value,
                "file_extension": Path(suggestion.file_path).suffix,
                **context
            }
            
            # Apply user preferences
            if user_prefs.get("profile"):
                profile = user_prefs["profile"]
                
                # Boost preferred types
                if suggestion.type.value in profile.get("preferred_types", {}):
                    pref_count = profile["preferred_types"][suggestion.type.value]
                    boost = min(1.5, 1.0 + (pref_count / 100))
                    suggestion.priority = int(suggestion.priority * boost)
                
                # Reduce rejected types
                if suggestion.type.value in profile.get("rejected_types", {}):
                    reject_count = profile["rejected_types"][suggestion.type.value]
                    reduction = max(0.5, 1.0 - (reject_count / 100))
                    suggestion.priority = int(suggestion.priority * reduction)
            
            # Apply learned patterns
            matching_patterns = [p for p in patterns if p.matches(match_context)]
            
            for pattern in matching_patterns:
                action = pattern.action
                
                if "boost_priority" in action:
                    suggestion.priority = int(suggestion.priority * action["boost_priority"])
                
                if "reduce_priority" in action:
                    suggestion.priority = int(suggestion.priority * action["reduce_priority"])
                
                if "add_warning" in action and "metadata" in suggestion.__dict__:
                    suggestion.metadata["warnings"] = suggestion.metadata.get("warnings", [])
                    suggestion.metadata["warnings"].append(action["add_warning"])
                
                if "require_confirmation" in action and "metadata" in suggestion.__dict__:
                    suggestion.metadata["requires_confirmation"] = True
            
            # Predict likely feedback
            predicted_feedback, confidence = self.learner.predict_feedback(
                suggestion, match_context
            )
            
            if "metadata" in suggestion.__dict__:
                suggestion.metadata["predicted_feedback"] = predicted_feedback.value
                suggestion.metadata["prediction_confidence"] = confidence
            
            adjusted_suggestions.append(suggestion)
        
        # Re-sort by adjusted priorities
        adjusted_suggestions.sort(key=lambda s: s.priority, reverse=True)
        
        return adjusted_suggestions
    
    def get_personalized_thresholds(self, user_id: Optional[str] = None) -> Dict[str, float]:
        """Get personalized confidence thresholds for different suggestion types."""
        user_id = user_id or self.collector.current_user_id
        
        # Default thresholds
        thresholds = {
            SuggestionType.ERROR_FIX: 0.7,
            SuggestionType.WARNING_FIX: 0.6,
            SuggestionType.SECURITY: 0.8,
            SuggestionType.PERFORMANCE: 0.6,
            SuggestionType.STYLE: 0.5,
            SuggestionType.DOCUMENTATION: 0.5,
            SuggestionType.REFACTORING: 0.7,
            SuggestionType.MAINTAINABILITY: 0.6
        }
        
        # Adjust based on user history
        prefs = self.collector.db.get_user_preferences(user_id)
        if prefs and "profile" in prefs:
            profile = prefs["profile"]
            
            for sug_type in SuggestionType:
                type_str = sug_type.value
                
                # Calculate acceptance rate for this type
                accepted = profile.get("preferred_types", {}).get(type_str, 0)
                rejected = profile.get("rejected_types", {}).get(type_str, 0)
                
                if accepted + rejected > 10:  # Enough data
                    acceptance_rate = accepted / (accepted + rejected)
                    
                    # Adjust threshold inversely to acceptance rate
                    # High acceptance = lower threshold (show more)
                    # Low acceptance = higher threshold (show fewer)
                    if acceptance_rate > 0.7:
                        thresholds[sug_type] *= 0.8
                    elif acceptance_rate < 0.3:
                        thresholds[sug_type] *= 1.2
                    
                    # Clamp to reasonable range
                    thresholds[sug_type] = max(0.3, min(0.9, thresholds[sug_type]))
        
        return thresholds