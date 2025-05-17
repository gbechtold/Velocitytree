"""Tests for GitManager functionality."""
import os
import tempfile
import shutil
from pathlib import Path
import pytest
from git import Repo

from velocitytree.git_manager import (
    GitManager, ActionType, FeatureSpec, ChangeAnalysis
)


class TestGitManager:
    """Test suite for GitManager class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository for testing."""
        temp_dir = tempfile.mkdtemp()
        repo = Repo.init(temp_dir)
        
        # Create initial commit
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Initial content")
        repo.index.add([str(test_file)])
        repo.index.commit("Initial commit")
        
        yield temp_dir, repo
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    def test_initialization(self, temp_repo):
        """Test GitManager initialization."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        assert git_mgr.repo is not None
        assert git_mgr.repo_path == Path(temp_dir)
    
    def test_initialization_no_repo(self):
        """Test GitManager initialization without git repo."""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_mgr = GitManager(temp_dir)
            assert git_mgr.repo is None
    
    def test_create_feature_branch(self, temp_repo):
        """Test feature branch creation from natural language."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Test simple feature description
        branch_name = git_mgr.create_feature_branch("Add user authentication")
        assert branch_name == "feature/add-user-authentication"
        assert git_mgr.get_current_branch() == branch_name
        
        # Test with action keyword
        git_mgr.switch_branch("master")
        branch_name = git_mgr.create_feature_branch("Fix login bug")
        assert branch_name == "feature/fix-login-bug"
    
    def test_branch_name_generation(self, temp_repo):
        """Test branch name generation from various descriptions."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        test_cases = [
            ("Add OAuth support for Google", "feature/add-oauth-support-google"),
            ("Fix critical security issue", "feature/fix-critical-security-issue"),
            ("Update documentation for API", "feature/update-documentation-api"),
            ("Remove deprecated methods", "feature/remove-deprecated-methods"),
            ("#123 Add payment gateway", "feature/123-add-payment-gateway"),
            ("JIRA-456 Fix database connection", "feature/jira-456-fix-database-connection"),
        ]
        
        for description, expected in test_cases:
            spec = git_mgr._parse_feature_description(description)
            branch_name = git_mgr._generate_branch_name(spec, "feature/")
            assert branch_name == expected
    
    def test_parse_feature_description(self, temp_repo):
        """Test parsing of feature descriptions."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Test action type detection
        spec = git_mgr._parse_feature_description("Fix login issue")
        assert spec.action_type == ActionType.FIX
        
        spec = git_mgr._parse_feature_description("Add new feature")
        assert spec.action_type == ActionType.ADD
        
        spec = git_mgr._parse_feature_description("Update existing code")
        assert spec.action_type == ActionType.UPDATE
        
        # Test ticket reference extraction
        spec = git_mgr._parse_feature_description("#123 Fix bug")
        assert spec.ticket_ref == "#123"
        
        spec = git_mgr._parse_feature_description("PROJ-456 Add feature")
        assert spec.ticket_ref == "PROJ-456"
    
    def test_analyze_changes(self, temp_repo):
        """Test change analysis functionality."""
        temp_dir, repo = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Make some changes
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("Modified content\nNew line")
        
        new_file = Path(temp_dir) / "new_file.py"
        new_file.write_text("def hello():\n    print('Hello')")
        
        # Stage the new file to ensure it's included in the diff
        repo.index.add([str(new_file)])
        
        # Analyze changes
        analysis = git_mgr.analyze_changes()
        
        # At least one file should be changed (test.txt is tracked)
        assert len(analysis.files_changed) >= 1
        assert analysis.insertions >= 0
        assert analysis.deletions >= 0
        assert analysis.change_type in ["feature", "update", "test", "docs"]
        assert analysis.impact_level in ["minor", "moderate", "major"]
    
    def test_commit_message_generation(self, temp_repo):
        """Test commit message generation."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Test with custom message
        message = git_mgr.generate_commit_message(custom_message="Add new feature")
        assert message.startswith("feat:")
        
        message = git_mgr.generate_commit_message(custom_message="Fix bug in login")
        assert message.startswith("fix:")
        
        # Test enhancement of conventional format
        message = git_mgr.generate_commit_message(
            custom_message="feat(auth): add OAuth support"
        )
        assert message == "feat(auth): add OAuth support"
    
    def test_version_tagging(self, temp_repo):
        """Test semantic version tagging."""
        temp_dir, repo = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # First tag (no existing tags)
        version = git_mgr.tag_version("patch")
        assert version == "v0.0.1"
        
        # Increment patch
        version = git_mgr.tag_version("patch")
        assert version == "v0.0.2"
        
        # Increment minor
        version = git_mgr.tag_version("minor")
        assert version == "v0.1.0"
        
        # Increment major
        version = git_mgr.tag_version("major")
        assert version == "v1.0.0"
        
        # Custom version
        version = git_mgr.tag_version(custom_version="v2.5.0")
        assert version == "v2.5.0"
    
    def test_branch_operations(self, temp_repo):
        """Test branch listing and switching."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Create multiple branches
        git_mgr.create_feature_branch("Add feature one")
        git_mgr.switch_branch("master")
        git_mgr.create_feature_branch("Add feature two")
        
        # List branches
        branches = git_mgr.list_branches()
        assert "master" in branches
        assert "feature/add-feature-one" in branches
        assert "feature/add-feature-two" in branches
        
        # Switch branches
        git_mgr.switch_branch("feature/add-feature-one")
        assert git_mgr.get_current_branch() == "feature/add-feature-one"
        
        # Delete branch
        git_mgr.switch_branch("master")
        git_mgr.delete_branch("feature/add-feature-two")
        branches = git_mgr.list_branches()
        assert "feature/add-feature-two" not in branches
    
    def test_error_handling(self, temp_repo):
        """Test error handling in various scenarios."""
        temp_dir, _ = temp_repo
        git_mgr = GitManager(temp_dir)
        
        # Try to create duplicate branch
        git_mgr.create_feature_branch("Test feature")
        git_mgr.switch_branch("master")
        
        with pytest.raises(ValueError, match="already exists"):
            git_mgr.create_feature_branch("Test feature")
        
        # Try to switch to non-existent branch
        with pytest.raises(ValueError, match="does not exist"):
            git_mgr.switch_branch("non-existent-branch")
        
        # Try to delete current branch
        with pytest.raises(ValueError, match="Cannot delete the currently active branch"):
            git_mgr.delete_branch(git_mgr.get_current_branch())
    
    def test_no_repo_error(self):
        """Test operations without a git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            git_mgr = GitManager(temp_dir)
            
            with pytest.raises(ValueError, match="No git repository found"):
                git_mgr.create_feature_branch("Test")
            
            with pytest.raises(ValueError, match="No git repository found"):
                git_mgr.analyze_changes()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])