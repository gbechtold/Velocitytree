"""
Memory store for workflow decisions and history.
Provides persistent storage and retrieval of decision data.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

from ..utils import logger


class DecisionType(Enum):
    """Types of workflow decisions."""
    FEATURE_CREATION = "feature_creation"
    BRANCH_MANAGEMENT = "branch_management"
    COMMIT_MESSAGE = "commit_message"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"


@dataclass
class WorkflowDecision:
    """Represents a workflow decision made by the system."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    decision_type: DecisionType = DecisionType.FEATURE_CREATION
    context: Dict[str, Any] = field(default_factory=dict)
    decision: str = ""
    rationale: str = ""
    outcome: Optional[str] = None
    confidence: float = 0.0
    precedents: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary for storage."""
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'decision_type': self.decision_type.value,
            'context': json.dumps(self.context),
            'decision': self.decision,
            'rationale': self.rationale,
            'outcome': self.outcome,
            'confidence': self.confidence,
            'precedents': json.dumps(self.precedents),
            'tags': json.dumps(self.tags),
            'user_id': self.user_id,
            'project_id': self.project_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDecision':
        """Create decision from dictionary."""
        return cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            decision_type=DecisionType(data['decision_type']),
            context=json.loads(data['context']) if data['context'] else {},
            decision=data['decision'],
            rationale=data['rationale'],
            outcome=data['outcome'],
            confidence=data['confidence'],
            precedents=json.loads(data['precedents']) if data['precedents'] else [],
            tags=json.loads(data['tags']) if data['tags'] else [],
            user_id=data['user_id'],
            project_id=data['project_id']
        )


class MemoryStore:
    """Persistent storage for workflow decisions."""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize memory store.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path.home() / ".velocitytree" / "workflow_memory.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                decision_type TEXT NOT NULL,
                context TEXT,
                decision TEXT NOT NULL,
                rationale TEXT,
                outcome TEXT,
                confidence REAL,
                precedents TEXT,
                tags TEXT,
                user_id TEXT,
                project_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for efficient querying
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_timestamp 
            ON decisions(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_type 
            ON decisions(decision_type)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_project 
            ON decisions(project_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_decisions_user 
            ON decisions(user_id)
        """)
        
        # Create decision_outcomes table for tracking results
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                decision_id TEXT NOT NULL,
                outcome_timestamp TEXT NOT NULL,
                success BOOLEAN,
                metrics TEXT,
                feedback TEXT,
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        """)
        
        # Create decision_relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id TEXT NOT NULL,
                child_id TEXT NOT NULL,
                relationship_type TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES decisions(id),
                FOREIGN KEY (child_id) REFERENCES decisions(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_decision(self, decision: WorkflowDecision) -> bool:
        """Add a new decision to the store.
        
        Args:
            decision: WorkflowDecision to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            data = decision.to_dict()
            
            cursor.execute("""
                INSERT INTO decisions (
                    id, timestamp, decision_type, context, decision,
                    rationale, outcome, confidence, precedents, tags,
                    user_id, project_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['id'], data['timestamp'], data['decision_type'],
                data['context'], data['decision'], data['rationale'],
                data['outcome'], data['confidence'], data['precedents'],
                data['tags'], data['user_id'], data['project_id']
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added decision {decision.id} to memory store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add decision: {e}")
            return False
    
    def get_decision(self, decision_id: str) -> Optional[WorkflowDecision]:
        """Retrieve a specific decision by ID.
        
        Args:
            decision_id: ID of the decision to retrieve
            
        Returns:
            WorkflowDecision if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM decisions WHERE id = ?
            """, (decision_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_decision(row)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get decision: {e}")
            return None
    
    def get_decisions(
        self,
        decision_type: Optional[DecisionType] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[WorkflowDecision]:
        """Retrieve decisions based on filters.
        
        Args:
            decision_type: Filter by decision type
            project_id: Filter by project
            user_id: Filter by user
            start_date: Filter by date range start
            end_date: Filter by date range end
            tags: Filter by tags (any match)
            limit: Maximum number of results
            
        Returns:
            List of matching WorkflowDecisions
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM decisions WHERE 1=1"
            params = []
            
            if decision_type:
                query += " AND decision_type = ?"
                params.append(decision_type.value)
            
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if tags:
                # Check if any of the provided tags are in the stored tags
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
                query += f" AND ({' OR '.join(tag_conditions)})"
            
            query += " ORDER BY timestamp DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_decision(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get decisions: {e}")
            return []
    
    def update_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool = True,
        metrics: Optional[Dict[str, Any]] = None,
        feedback: Optional[str] = None
    ) -> bool:
        """Update the outcome of a decision.
        
        Args:
            decision_id: ID of the decision to update
            outcome: Outcome description
            success: Whether the outcome was successful
            metrics: Optional metrics about the outcome
            feedback: Optional feedback text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update the decision outcome
            cursor.execute("""
                UPDATE decisions SET outcome = ? WHERE id = ?
            """, (outcome, decision_id))
            
            # Add outcome record
            cursor.execute("""
                INSERT INTO decision_outcomes (
                    decision_id, outcome_timestamp, success, metrics, feedback
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                decision_id,
                datetime.now().isoformat(),
                success,
                json.dumps(metrics) if metrics else None,
                feedback
            ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Updated outcome for decision {decision_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update outcome: {e}")
            return False
    
    def add_relationship(
        self,
        parent_id: str,
        child_id: str,
        relationship_type: str = "derived_from"
    ) -> bool:
        """Add a relationship between decisions.
        
        Args:
            parent_id: ID of parent decision
            child_id: ID of child decision
            relationship_type: Type of relationship
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO decision_relationships (
                    parent_id, child_id, relationship_type
                ) VALUES (?, ?, ?)
            """, (parent_id, child_id, relationship_type))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Added relationship {parent_id} -> {child_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            return False
    
    def get_related_decisions(
        self,
        decision_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[WorkflowDecision]:
        """Get decisions related to a specific decision.
        
        Args:
            decision_id: ID of the decision
            relationship_type: Filter by relationship type
            direction: "parent", "child", or "both"
            
        Returns:
            List of related decisions
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            related_ids = set()
            
            # Get parent relationships
            if direction in ["parent", "both"]:
                query = """
                    SELECT parent_id FROM decision_relationships 
                    WHERE child_id = ?
                """
                params = [decision_id]
                
                if relationship_type:
                    query += " AND relationship_type = ?"
                    params.append(relationship_type)
                
                cursor.execute(query, params)
                parent_ids = cursor.fetchall()
                related_ids.update(row[0] for row in parent_ids)
            
            # Get child relationships
            if direction in ["child", "both"]:
                query = """
                    SELECT child_id FROM decision_relationships 
                    WHERE parent_id = ?
                """
                params = [decision_id]
                
                if relationship_type:
                    query += " AND relationship_type = ?"
                    params.append(relationship_type)
                
                cursor.execute(query, params)
                child_ids = cursor.fetchall()
                related_ids.update(row[0] for row in child_ids)
            
            # Get the actual decisions
            decisions = []
            for rel_id in related_ids:
                decision = self.get_decision(rel_id)
                if decision:
                    decisions.append(decision)
            
            conn.close()
            return decisions
            
        except Exception as e:
            logger.error(f"Failed to get related decisions: {e}")
            return []
    
    def get_statistics(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistics about stored decisions.
        
        Args:
            project_id: Filter by project
            user_id: Filter by user
            
        Returns:
            Dictionary of statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            conditions = ["1=1"]
            params = []
            
            if project_id:
                conditions.append("project_id = ?")
                params.append(project_id)
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            where_clause = " AND ".join(conditions)
            
            # Total decisions
            cursor.execute(f"""
                SELECT COUNT(*) FROM decisions WHERE {where_clause}
            """, params)
            total_decisions = cursor.fetchone()[0]
            
            # Decisions by type
            cursor.execute(f"""
                SELECT decision_type, COUNT(*) 
                FROM decisions 
                WHERE {where_clause}
                GROUP BY decision_type
            """, params)
            decisions_by_type = dict(cursor.fetchall())
            
            # Success rate
            cursor.execute(f"""
                SELECT 
                    COUNT(CASE WHEN o.success = 1 THEN 1 END) as successful,
                    COUNT(o.id) as total
                FROM decisions d
                JOIN decision_outcomes o ON d.id = o.decision_id
                WHERE {where_clause}
            """, params)
            
            success_data = cursor.fetchone()
            success_rate = (
                success_data[0] / success_data[1] if success_data[1] > 0 else 0
            )
            
            # Average confidence
            cursor.execute(f"""
                SELECT AVG(confidence) FROM decisions WHERE {where_clause}
            """, params)
            avg_confidence = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_decisions': total_decisions,
                'decisions_by_type': decisions_by_type,
                'success_rate': success_rate,
                'average_confidence': avg_confidence
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def _row_to_decision(self, row: Tuple) -> WorkflowDecision:
        """Convert database row to WorkflowDecision object."""
        columns = [
            'id', 'timestamp', 'decision_type', 'context', 'decision',
            'rationale', 'outcome', 'confidence', 'precedents', 'tags',
            'user_id', 'project_id', 'created_at'
        ]
        
        data = dict(zip(columns, row))
        return WorkflowDecision.from_dict(data)