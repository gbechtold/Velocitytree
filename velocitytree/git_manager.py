"""Git Manager for Velocitytree - Natural language git operations."""
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import git
    from git import Repo, GitCommandError
except ImportError:
    raise ImportError("GitPython is required. Install with: pip install GitPython")

from .utils import logger


class ActionType(Enum):
    """Types of actions that can be performed on a feature."""
    ADD = "add"
    FIX = "fix"
    UPDATE = "update"
    REFACTOR = "refactor"
    REMOVE = "remove"
    ENHANCE = "enhance"
    IMPLEMENT = "implement"


@dataclass
class FeatureSpec:
    """Specification for a feature derived from natural language."""
    description: str
    action_type: ActionType
    component: Optional[str] = None
    branch_name: str = ""
    ticket_ref: Optional[str] = None


@dataclass
class ChangeAnalysis:
    """Analysis of git changes."""
    files_changed: List[str]
    insertions: int
    deletions: int
    change_type: str  # feature, fix, refactor, etc.
    components_affected: List[str]
    suggested_message: str
    impact_level: str  # minor, moderate, major


class GitManager:
    """Manages git operations with natural language support."""
    
    def __init__(self, repo_path: Optional[str] = None):
        """Initialize GitManager with repository path."""
        self.repo_path = Path(repo_path or os.getcwd())
        self.repo: Optional[Repo] = None
        self._initialize_repo()
    
    def _initialize_repo(self) -> None:
        """Initialize git repository object."""
        try:
            self.repo = Repo(self.repo_path)
            logger.info(f"Initialized GitManager for repository: {self.repo_path}")
        except git.InvalidGitRepositoryError:
            logger.warning(f"No git repository found at {self.repo_path}")
            self.repo = None
    
    def ensure_repo(self) -> Repo:
        """Ensure we have a valid repository."""
        if not self.repo:
            raise ValueError("No git repository found. Initialize a git repo first.")
        return self.repo
    
    def create_feature_branch(self, description: str, 
                            prefix: str = "feature/") -> str:
        """Create a feature branch from natural language description."""
        repo = self.ensure_repo()
        
        # Parse the description
        spec = self._parse_feature_description(description)
        
        # Generate branch name
        branch_name = self._generate_branch_name(spec, prefix)
        
        try:
            # Check if branch already exists
            if branch_name in [b.name for b in repo.branches]:
                logger.error(f"Branch {branch_name} already exists")
                raise ValueError(f"Branch {branch_name} already exists")
                
            # Create and checkout new branch
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()
            
            logger.info(f"Created and checked out branch: {branch_name}")
            return branch_name
            
        except GitCommandError as e:
            logger.error(f"Git error creating branch: {e}")
            raise e
    
    def _parse_feature_description(self, description: str) -> FeatureSpec:
        """Parse natural language description into feature specification."""
        # Simple keyword-based parsing (will be enhanced with NLP)
        description_lower = description.lower()
        
        # Detect action type
        action_type = ActionType.ADD  # default
        for action in ActionType:
            if action.value in description_lower:
                action_type = action
                break
        
        # Extract component (simple heuristic for now)
        component = None
        if "component" in description_lower:
            # Extract word after "component"
            parts = description_lower.split("component")
            if len(parts) > 1:
                component = parts[1].strip().split()[0]
        
        # Look for ticket references
        ticket_ref = None
        ticket_pattern = r'#(\d+)|([A-Z]+-\d+)'
        ticket_match = re.search(ticket_pattern, description)
        if ticket_match:
            ticket_ref = ticket_match.group(0)
        
        return FeatureSpec(
            description=description,
            action_type=action_type,
            component=component,
            ticket_ref=ticket_ref
        )
    
    def _generate_branch_name(self, spec: FeatureSpec, prefix: str) -> str:
        """Generate branch name from feature specification."""
        # Clean description for branch name
        desc = spec.description.lower()
        
        # Remove ticket reference from description if it exists
        if spec.ticket_ref:
            desc = desc.replace(spec.ticket_ref.lower(), '').strip()
        
        # Remove common words
        stop_words = {'a', 'an', 'the', 'for', 'to', 'in', 'of', 'and', 'or'}
        words = [w for w in desc.split() if w not in stop_words]
        
        # Take first few meaningful words
        meaningful_words = []
        for word in words:
            # Clean word
            clean_word = re.sub(r'[^a-z0-9]', '', word)
            if clean_word and len(meaningful_words) < 4:
                meaningful_words.append(clean_word)
        
        # Create branch name
        base_name = '-'.join(meaningful_words)
        
        # For fix action type, check if 'fix' is not already in the meaningful words
        if spec.action_type != ActionType.ADD:
            # Don't add action type if it's already the first word
            if not meaningful_words or meaningful_words[0] != spec.action_type.value:
                base_name = f"{spec.action_type.value}-{base_name}"
        
        # Add ticket reference if available (without the # symbol)
        if spec.ticket_ref:
            ticket_ref_clean = spec.ticket_ref.lstrip('#').lower()
            base_name = f"{ticket_ref_clean}-{base_name}"
        
        branch_name = f"{prefix}{base_name}"
        
        # Ensure branch name is valid
        branch_name = re.sub(r'[^a-zA-Z0-9/_-]', '-', branch_name)
        branch_name = re.sub(r'-+', '-', branch_name)  # Remove multiple dashes
        branch_name = branch_name.strip('-/')  # Remove leading/trailing dashes
        
        return branch_name
    
    def analyze_changes(self) -> ChangeAnalysis:
        """Analyze current changes in the repository."""
        repo = self.ensure_repo()
        
        # Get diff between HEAD and working directory
        diff_index = repo.head.commit.diff(None)
        
        files_changed = []
        insertions = 0
        deletions = 0
        components = set()
        
        for diff_item in diff_index:
            files_changed.append(diff_item.a_path or diff_item.b_path)
            
            # Count insertions and deletions
            if diff_item.diff:
                diff_lines = diff_item.diff.decode('utf-8').split('\n')
                for line in diff_lines:
                    if line.startswith('+') and not line.startswith('+++'):
                        insertions += 1
                    elif line.startswith('-') and not line.startswith('---'):
                        deletions += 1
            
            # Extract component from file path
            path_parts = (diff_item.a_path or diff_item.b_path).split('/')
            if len(path_parts) > 1:
                components.add(path_parts[0])
        
        # Determine change type
        change_type = self._determine_change_type(files_changed, insertions, deletions)
        
        # Calculate impact level
        total_changes = insertions + deletions
        if total_changes < 10:
            impact_level = "minor"
        elif total_changes < 50:
            impact_level = "moderate"
        else:
            impact_level = "major"
        
        # Generate suggested commit message
        suggested_message = self._generate_commit_message_suggestion(
            change_type, files_changed, components
        )
        
        return ChangeAnalysis(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            change_type=change_type,
            components_affected=list(components),
            suggested_message=suggested_message,
            impact_level=impact_level
        )
    
    def _determine_change_type(self, files: List[str], 
                              insertions: int, deletions: int) -> str:
        """Determine the type of change based on files and metrics."""
        # Simple heuristics for now
        if any('test' in f.lower() for f in files):
            return "test"
        elif any('doc' in f.lower() or 'readme' in f.lower() for f in files):
            return "docs"
        elif insertions > deletions * 2:
            return "feature"
        elif deletions > insertions * 2:
            return "remove"
        elif any('fix' in f.lower() for f in files):
            return "fix"
        else:
            return "update"
    
    def _generate_commit_message_suggestion(self, change_type: str,
                                          files: List[str],
                                          components: set) -> str:
        """Generate a suggested commit message based on changes."""
        # Map change types to conventional commit prefixes
        prefix_map = {
            "feature": "feat",
            "fix": "fix",
            "docs": "docs",
            "test": "test",
            "remove": "refactor",
            "update": "chore"
        }
        
        prefix = prefix_map.get(change_type, "chore")
        
        # Determine scope
        if len(components) == 1:
            scope = list(components)[0]
        elif len(components) > 1:
            scope = "multiple"
        else:
            scope = "core"
        
        # Create description based on files
        if len(files) == 1:
            desc = f"update {files[0]}"
        elif change_type == "feature":
            desc = "add new functionality"
        elif change_type == "fix":
            desc = "fix issues"
        else:
            desc = f"{change_type} changes"
        
        return f"{prefix}({scope}): {desc}"
    
    def generate_commit_message(self, changes: Optional[ChangeAnalysis] = None,
                              custom_message: Optional[str] = None) -> str:
        """Generate a commit message based on changes or custom input."""
        if custom_message:
            # Enhance custom message with conventional format
            return self._enhance_commit_message(custom_message)
        
        if not changes:
            changes = self.analyze_changes()
        
        return changes.suggested_message
    
    def _enhance_commit_message(self, message: str) -> str:
        """Enhance a user-provided message to follow conventions."""
        # If already in conventional format, return as-is
        if re.match(r'^(feat|fix|docs|test|chore|refactor)\(.*\):', message):
            return message
        
        # Try to detect the type from the message
        message_lower = message.lower()
        if 'add' in message_lower or 'implement' in message_lower:
            prefix = "feat"
        elif 'fix' in message_lower or 'bug' in message_lower:
            prefix = "fix"
        elif 'doc' in message_lower or 'readme' in message_lower:
            prefix = "docs"
        elif 'test' in message_lower:
            prefix = "test"
        else:
            prefix = "chore"
        
        return f"{prefix}: {message}"
    
    def tag_version(self, version_type: str = "patch",
                   custom_version: Optional[str] = None) -> str:
        """Create a version tag based on semantic versioning."""
        repo = self.ensure_repo()
        
        # Get latest tag
        try:
            tags = sorted(repo.tags, key=lambda t: t.commit.committed_date)
            if tags:
                latest_tag = tags[-1].name
                current_version = self._parse_version(latest_tag)
            else:
                current_version = (0, 0, 0)
        except Exception:
            current_version = (0, 0, 0)
        
        if custom_version:
            new_version = custom_version
        else:
            # Calculate new version
            major, minor, patch = current_version
            
            if version_type == "major":
                new_version = f"v{major + 1}.0.0"
            elif version_type == "minor":
                new_version = f"v{major}.{minor + 1}.0"
            else:  # patch
                new_version = f"v{major}.{minor}.{patch + 1}"
        
        # Create tag
        try:
            repo.create_tag(new_version, message=f"Release {new_version}")
            logger.info(f"Created tag: {new_version}")
            return new_version
        except GitCommandError as e:
            logger.error(f"Failed to create tag: {e}")
            raise
    
    def _parse_version(self, tag: str) -> Tuple[int, int, int]:
        """Parse version string into tuple."""
        # Remove 'v' prefix if present
        version = tag.lstrip('v')
        
        try:
            parts = version.split('.')
            return (int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return (0, 0, 0)
    
    def get_current_branch(self) -> str:
        """Get the name of the current branch."""
        repo = self.ensure_repo()
        return repo.active_branch.name
    
    def list_branches(self) -> List[str]:
        """List all branches in the repository."""
        repo = self.ensure_repo()
        return [branch.name for branch in repo.branches]
    
    def switch_branch(self, branch_name: str) -> None:
        """Switch to a different branch."""
        repo = self.ensure_repo()
        
        try:
            branch = repo.branches[branch_name]
            branch.checkout()
            logger.info(f"Switched to branch: {branch_name}")
        except IndexError:
            raise ValueError(f"Branch {branch_name} does not exist")
    
    def delete_branch(self, branch_name: str, force: bool = False) -> None:
        """Delete a branch."""
        repo = self.ensure_repo()
        
        if repo.active_branch.name == branch_name:
            raise ValueError("Cannot delete the currently active branch")
        
        try:
            repo.delete_head(branch_name, force=force)
            logger.info(f"Deleted branch: {branch_name}")
        except GitCommandError as e:
            logger.error(f"Failed to delete branch: {e}")
            raise


if __name__ == "__main__":
    # Example usage
    git_mgr = GitManager()
    
    # Create a feature branch from description
    branch = git_mgr.create_feature_branch("Add user authentication with OAuth")
    print(f"Created branch: {branch}")
    
    # Analyze changes
    changes = git_mgr.analyze_changes()
    print(f"Analysis: {changes}")
    
    # Generate commit message
    message = git_mgr.generate_commit_message(changes)
    print(f"Suggested commit: {message}")