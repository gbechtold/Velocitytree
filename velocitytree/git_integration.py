"""Git integration for automatic feature status updates."""

import git
import re
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from .feature_graph import FeatureGraph, FeatureNode
from .utils import logger


@dataclass
class CommitInfo:
    """Information about a git commit."""
    sha: str
    message: str
    author: str
    date: datetime
    branch: str
    files_changed: List[str]


@dataclass
class BranchInfo:
    """Information about a git branch."""
    name: str
    is_merged: bool
    commits_ahead: int
    commits_behind: int
    last_commit: Optional[CommitInfo]


class GitFeatureTracker:
    """Track feature progress through git activity."""
    
    def __init__(self, repo_path: str, feature_graph: FeatureGraph):
        """Initialize the git feature tracker.
        
        Args:
            repo_path: Path to the git repository
            feature_graph: Feature graph to update
        """
        self.repo_path = Path(repo_path)
        self.feature_graph = feature_graph
        self.repo = git.Repo(repo_path)
        
        # Patterns for detecting feature references in commits/branches
        self.feature_patterns = [
            r'(?:feat|feature)[:\s]*(\w+)',  # feat: auth, feature: api
            r'(?:#|issue[:\s]*)(\d+)',       # #123, issue: 456
            r'\[(\w+)\]',                    # [auth], [api]
            r'(?:implement|add|create)[:\s]+(\w+)',  # implement: dashboard
        ]
        
        # Branch naming patterns
        self.branch_patterns = [
            r'feature/(\w+)',                # feature/auth
            r'feat/(\w+)',                   # feat/api
            r'(\w+)-feature',                # auth-feature
            r'impl-(\w+)',                   # impl-dashboard
        ]
        
        # Completion indicators in commit messages
        self.completion_patterns = [
            r'(?:complete|finish|done)[:\s]*(\w+)',
            r'(\w+)[:\s]*(?:complete|finished|done)',
            r'✓\s*(\w+)',                    # ✓ auth
            r'(?:close|closes|fix|fixes)[:\s]*#?(\d+)',
        ]
    
    def scan_repository(self) -> Dict[str, List[CommitInfo]]:
        """Scan repository for feature-related activity.
        
        Returns:
            Dictionary mapping feature IDs to related commits
        """
        feature_commits = {}
        
        # Scan all branches
        for branch in self.repo.branches:
            branch_name = branch.name
            
            # Check if branch name matches feature pattern
            feature_id = self._extract_feature_from_branch(branch_name)
            
            # Scan commits in branch
            for commit in branch.commit.iter_items(self.repo, f'{branch_name}'):
                commit_info = self._parse_commit(commit, branch_name)
                
                # Extract feature references from commit message
                feature_ids = self._extract_features_from_message(commit.message)
                
                # Include branch-based feature ID if found
                if feature_id:
                    feature_ids.add(feature_id)
                
                # Map commits to features
                for fid in feature_ids:
                    if fid not in feature_commits:
                        feature_commits[fid] = []
                    feature_commits[fid].append(commit_info)
        
        return feature_commits
    
    def update_feature_status(self) -> Dict[str, str]:
        """Update feature status based on git activity.
        
        Returns:
            Dictionary of feature ID to new status
        """
        updates = {}
        feature_commits = self.scan_repository()
        
        for feature_id, commits in feature_commits.items():
            if feature_id not in self.feature_graph.features:
                continue
            
            feature = self.feature_graph.features[feature_id]
            current_status = feature.status
            new_status = self._determine_status(feature_id, commits)
            
            if new_status and new_status != current_status:
                self.feature_graph.update_feature_status(feature_id, new_status)
                updates[feature_id] = new_status
                logger.info(f"Updated feature {feature_id} status: {current_status} -> {new_status}")
        
        return updates
    
    def get_feature_branches(self) -> Dict[str, BranchInfo]:
        """Get information about feature-related branches.
        
        Returns:
            Dictionary mapping feature IDs to branch information
        """
        feature_branches = {}
        default_branch = self.repo.active_branch.name
        
        for branch in self.repo.branches:
            feature_id = self._extract_feature_from_branch(branch.name)
            if not feature_id:
                continue
            
            # Get branch information
            branch_info = BranchInfo(
                name=branch.name,
                is_merged=self._is_branch_merged(branch.name, default_branch),
                commits_ahead=len(list(self.repo.iter_commits(f'{default_branch}..{branch.name}'))),
                commits_behind=len(list(self.repo.iter_commits(f'{branch.name}..{default_branch}'))),
                last_commit=self._parse_commit(branch.commit, branch.name) if branch.commit else None
            )
            
            feature_branches[feature_id] = branch_info
        
        return feature_branches
    
    def monitor_repository(self, callback=None):
        """Monitor repository for changes and update features automatically.
        
        Args:
            callback: Optional callback function to call on updates
        """
        import time
        import threading
        
        def check_updates():
            last_commit = self.repo.head.commit.hexsha
            
            while True:
                try:
                    # Fetch latest changes
                    self.repo.remotes.origin.fetch()
                    
                    # Check for new commits
                    current_commit = self.repo.head.commit.hexsha
                    if current_commit != last_commit:
                        logger.info("Detected new commits, updating feature status")
                        updates = self.update_feature_status()
                        
                        if updates and callback:
                            callback(updates)
                        
                        last_commit = current_commit
                    
                except Exception as e:
                    logger.error(f"Error monitoring repository: {e}")
                
                time.sleep(30)  # Check every 30 seconds
        
        monitor_thread = threading.Thread(target=check_updates, daemon=True)
        monitor_thread.start()
        logger.info("Started repository monitoring")
    
    def _parse_commit(self, commit: git.Commit, branch: str) -> CommitInfo:
        """Parse commit information."""
        return CommitInfo(
            sha=commit.hexsha,
            message=commit.message,
            author=str(commit.author),
            date=datetime.fromtimestamp(commit.committed_date),
            branch=branch,
            files_changed=[item.path for item in commit.stats.files.keys()]
        )
    
    def _extract_feature_from_branch(self, branch_name: str) -> Optional[str]:
        """Extract feature ID from branch name."""
        for pattern in self.branch_patterns:
            match = re.search(pattern, branch_name, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None
    
    def _extract_features_from_message(self, message: str) -> Set[str]:
        """Extract feature IDs from commit message."""
        features = set()
        
        for pattern in self.feature_patterns:
            matches = re.findall(pattern, message, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                features.add(match.lower())
        
        return features
    
    def _is_feature_complete(self, message: str) -> bool:
        """Check if commit message indicates feature completion."""
        for pattern in self.completion_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False
    
    def _determine_status(self, feature_id: str, commits: List[CommitInfo]) -> Optional[str]:
        """Determine feature status based on commits."""
        if not commits:
            return None
        
        # Check if any commit indicates completion
        for commit in commits:
            if self._is_feature_complete(commit.message):
                return "completed"
        
        # Check if feature branch is merged
        feature_branches = self.get_feature_branches()
        if feature_id in feature_branches:
            branch_info = feature_branches[feature_id]
            if branch_info.is_merged:
                return "completed"
        
        # If there are recent commits, mark as in progress
        latest_commit = max(commits, key=lambda c: c.date)
        days_since_commit = (datetime.now() - latest_commit.date).days
        
        if days_since_commit < 7:  # Active within last week
            return "in_progress"
        elif days_since_commit < 30:  # Stale
            return "blocked"
        
        return None
    
    def _is_branch_merged(self, branch_name: str, target_branch: str) -> bool:
        """Check if a branch is merged into target branch."""
        try:
            merge_base = self.repo.merge_base(branch_name, target_branch)[0]
            branch_commit = self.repo.commit(branch_name)
            return merge_base.hexsha == branch_commit.hexsha
        except Exception:
            return False
    
    def suggest_feature_relationships(self) -> List[Tuple[str, str, str]]:
        """Suggest feature relationships based on git activity.
        
        Returns:
            List of tuples (source, target, relationship_type)
        """
        suggestions = []
        feature_commits = self.scan_repository()
        
        # Find features that are often committed together
        for feature1, commits1 in feature_commits.items():
            if feature1 not in self.feature_graph.features:
                continue
            
            for feature2, commits2 in feature_commits.items():
                if feature2 == feature1 or feature2 not in self.feature_graph.features:
                    continue
                
                # Check for overlapping commits
                files1 = set()
                files2 = set()
                
                for commit in commits1:
                    files1.update(commit.files_changed)
                
                for commit in commits2:
                    files2.update(commit.files_changed)
                
                # If features touch similar files, they might be related
                overlap = files1.intersection(files2)
                if len(overlap) > 3:  # Significant overlap
                    suggestions.append((feature1, feature2, "RELATED_TO"))
                
                # Check temporal relationships
                dates1 = [c.date for c in commits1]
                dates2 = [c.date for c in commits2]
                
                if dates1 and dates2:
                    avg_date1 = sum(d.timestamp() for d in dates1) / len(dates1)
                    avg_date2 = sum(d.timestamp() for d in dates2) / len(dates2)
                    
                    # If one feature is consistently worked on before another
                    if avg_date1 < avg_date2 - 86400:  # More than a day difference
                        suggestions.append((feature2, feature1, "DEPENDS_ON"))
        
        return suggestions


class GitWorkflowIntegration:
    """Integrate git workflow with feature tracking."""
    
    def __init__(self, repo_path: str, feature_graph: FeatureGraph):
        """Initialize git workflow integration.
        
        Args:
            repo_path: Path to the git repository
            feature_graph: Feature graph to integrate with
        """
        self.tracker = GitFeatureTracker(repo_path, feature_graph)
        self.repo = git.Repo(repo_path)
    
    def create_feature_branch(self, feature_id: str) -> str:
        """Create a new branch for a feature.
        
        Args:
            feature_id: ID of the feature
            
        Returns:
            Name of the created branch
        """
        if feature_id not in self.tracker.feature_graph.features:
            raise ValueError(f"Feature {feature_id} not found")
        
        feature = self.tracker.feature_graph.features[feature_id]
        branch_name = f"feature/{feature_id}"
        
        # Create and checkout branch
        if branch_name not in [b.name for b in self.repo.branches]:
            self.repo.create_head(branch_name)
            logger.info(f"Created branch: {branch_name}")
        
        return branch_name
    
    def complete_feature(self, feature_id: str, commit_message: str = None) -> bool:
        """Mark a feature as complete and handle git workflow.
        
        Args:
            feature_id: ID of the feature to complete
            commit_message: Optional custom commit message
            
        Returns:
            True if successful
        """
        if feature_id not in self.tracker.feature_graph.features:
            raise ValueError(f"Feature {feature_id} not found")
        
        feature = self.tracker.feature_graph.features[feature_id]
        
        # Generate commit message if not provided
        if not commit_message:
            commit_message = f"Complete feature: {feature.name} ({feature_id})\n\nFeature completed and tested."
        
        # Create commit if there are changes
        if self.repo.is_dirty():
            self.repo.index.add('.')
            self.repo.index.commit(commit_message)
            logger.info(f"Created commit for feature completion: {feature_id}")
        
        # Update feature status
        self.tracker.feature_graph.update_feature_status(feature_id, "completed")
        
        return True
    
    def generate_feature_report(self) -> Dict[str, any]:
        """Generate a report of feature progress based on git activity.
        
        Returns:
            Report dictionary with feature progress information
        """
        feature_commits = self.tracker.scan_repository()
        feature_branches = self.tracker.get_feature_branches()
        
        report = {
            "features": {},
            "summary": {
                "total_features": len(self.tracker.feature_graph.features),
                "active_features": 0,
                "completed_features": 0,
                "stale_features": 0,
            }
        }
        
        for feature_id, feature in self.tracker.feature_graph.features.items():
            commits = feature_commits.get(feature_id, [])
            branch_info = feature_branches.get(feature_id)
            
            feature_report = {
                "name": feature.name,
                "status": feature.status,
                "commits": len(commits),
                "last_activity": max(c.date for c in commits) if commits else None,
                "branch": branch_info.name if branch_info else None,
                "is_merged": branch_info.is_merged if branch_info else False,
            }
            
            report["features"][feature_id] = feature_report
            
            # Update summary
            if feature.status == "completed":
                report["summary"]["completed_features"] += 1
            elif feature.status == "in_progress":
                report["summary"]["active_features"] += 1
            elif commits and feature_report["last_activity"]:
                days_inactive = (datetime.now() - feature_report["last_activity"]).days
                if days_inactive > 30:
                    report["summary"]["stale_features"] += 1
        
        return report