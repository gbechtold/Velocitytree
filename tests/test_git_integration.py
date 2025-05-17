"""Test git integration functionality."""

import pytest
import git
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from velocitytree.git_integration import GitFeatureTracker, GitWorkflowIntegration, CommitInfo, BranchInfo
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType


class TestGitFeatureTracker:
    """Test the GitFeatureTracker class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        repo = git.Repo.init(temp_dir)
        
        # Create initial commit
        readme = Path(temp_dir) / "README.md"
        readme.write_text("# Test Project")
        repo.index.add(['README.md'])
        repo.index.commit("Initial commit")
        
        yield repo
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def feature_graph(self):
        """Create a test feature graph."""
        graph = FeatureGraph("test_project")
        
        features = [
            FeatureNode(id="auth", name="Authentication", feature_type="feature", status="pending"),
            FeatureNode(id="api", name="API", feature_type="feature", status="pending"),
            FeatureNode(id="db", name="Database", feature_type="feature", status="pending"),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        return graph
    
    @pytest.fixture
    def tracker(self, temp_repo, feature_graph):
        """Create a GitFeatureTracker instance."""
        return GitFeatureTracker(temp_repo.working_dir, feature_graph)
    
    def test_initialization(self, tracker, temp_repo):
        """Test tracker initialization."""
        assert tracker.repo_path == Path(temp_repo.working_dir)
        assert tracker.feature_graph is not None
        assert tracker.repo is not None
    
    def test_extract_feature_from_branch(self, tracker):
        """Test extracting feature ID from branch names."""
        assert tracker._extract_feature_from_branch("feature/auth") == "auth"
        assert tracker._extract_feature_from_branch("feat/api") == "api"
        assert tracker._extract_feature_from_branch("db-feature") == "db"
        assert tracker._extract_feature_from_branch("impl-dashboard") == "dashboard"
        assert tracker._extract_feature_from_branch("main") is None
    
    def test_extract_features_from_message(self, tracker):
        """Test extracting feature IDs from commit messages."""
        message = "feat: auth implementation"
        features = tracker._extract_features_from_message(message)
        assert "auth" in features
        
        message = "Implement: api endpoints #123"
        features = tracker._extract_features_from_message(message)
        assert "api" in features
        assert "123" in features
        
        message = "[db] Add database migrations"
        features = tracker._extract_features_from_message(message)
        assert "db" in features
    
    def test_is_feature_complete(self, tracker):
        """Test detecting feature completion from messages."""
        assert tracker._is_feature_complete("Complete: auth feature")
        assert tracker._is_feature_complete("auth: finished and tested")
        assert tracker._is_feature_complete("✓ api implementation")
        assert tracker._is_feature_complete("Closes #123")
        assert not tracker._is_feature_complete("WIP: auth feature")
    
    def test_scan_repository(self, tracker, temp_repo):
        """Test scanning repository for feature activity."""
        # Create feature branches and commits
        auth_branch = temp_repo.create_head("feature/auth")
        api_branch = temp_repo.create_head("feat/api")
        
        # Switch to auth branch and make commits
        temp_repo.head.reference = auth_branch
        temp_repo.head.reset(index=True, working_tree=True)
        
        auth_file = Path(temp_repo.working_dir) / "auth.py"
        auth_file.write_text("# Authentication module")
        temp_repo.index.add(['auth.py'])
        temp_repo.index.commit("feat: auth - initial implementation")
        
        # Switch to api branch and make commits
        temp_repo.head.reference = api_branch
        temp_repo.head.reset(index=True, working_tree=True)
        
        api_file = Path(temp_repo.working_dir) / "api.py"
        api_file.write_text("# API module")
        temp_repo.index.add(['api.py'])
        temp_repo.index.commit("Implement: api endpoints")
        
        # Scan repository
        feature_commits = tracker.scan_repository()
        
        assert "auth" in feature_commits
        assert "api" in feature_commits
        assert len(feature_commits["auth"]) > 0
        assert len(feature_commits["api"]) > 0
    
    def test_update_feature_status(self, tracker, temp_repo):
        """Test updating feature status based on git activity."""
        # Create completed feature
        auth_branch = temp_repo.create_head("feature/auth")
        temp_repo.head.reference = auth_branch
        
        auth_file = Path(temp_repo.working_dir) / "auth.py"
        auth_file.write_text("# Complete auth implementation")
        temp_repo.index.add(['auth.py'])
        temp_repo.index.commit("Complete: auth feature")
        
        # Update status
        updates = tracker.update_feature_status()
        
        assert "auth" in updates
        assert updates["auth"] == "completed"
        assert tracker.feature_graph.features["auth"].status == "completed"
    
    def test_get_feature_branches(self, tracker, temp_repo):
        """Test getting feature branch information."""
        # Create feature branches
        auth_branch = temp_repo.create_head("feature/auth")
        api_branch = temp_repo.create_head("feat/api")
        
        # Get branch info
        branches = tracker.get_feature_branches()
        
        assert "auth" in branches
        assert "api" in branches
        assert branches["auth"].name == "feature/auth"
        assert branches["api"].name == "feat/api"
        assert not branches["auth"].is_merged
    
    def test_suggest_feature_relationships(self, tracker, temp_repo):
        """Test suggesting feature relationships."""
        # Create commits that touch same files
        auth_file = Path(temp_repo.working_dir) / "shared.py"
        
        # Commit for auth feature
        auth_branch = temp_repo.create_head("feature/auth")
        temp_repo.head.reference = auth_branch
        auth_file.write_text("# Auth code")
        temp_repo.index.add(['shared.py'])
        temp_repo.index.commit("feat: auth implementation")
        
        # Commit for api feature  
        api_branch = temp_repo.create_head("feat/api")
        temp_repo.head.reference = api_branch
        auth_file.write_text("# Auth + API code")
        temp_repo.index.add(['shared.py'])
        temp_repo.index.commit("feat: api implementation")
        
        # Get suggestions
        suggestions = tracker.suggest_feature_relationships()
        
        # Should suggest relationship between auth and api
        assert len(suggestions) > 0


class TestGitWorkflowIntegration:
    """Test the GitWorkflowIntegration class."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary git repository."""
        temp_dir = tempfile.mkdtemp()
        repo = git.Repo.init(temp_dir)
        
        # Create initial commit
        readme = Path(temp_dir) / "README.md"
        readme.write_text("# Test Project")
        repo.index.add(['README.md'])
        repo.index.commit("Initial commit")
        
        yield repo
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def feature_graph(self):
        """Create a test feature graph."""
        graph = FeatureGraph("test_project")
        
        features = [
            FeatureNode(id="auth", name="Authentication", feature_type="feature", status="pending"),
            FeatureNode(id="api", name="API", feature_type="feature", status="in_progress"),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        return graph
    
    @pytest.fixture
    def integration(self, temp_repo, feature_graph):
        """Create GitWorkflowIntegration instance."""
        return GitWorkflowIntegration(temp_repo.working_dir, feature_graph)
    
    def test_create_feature_branch(self, integration, temp_repo):
        """Test creating feature branches."""
        branch_name = integration.create_feature_branch("auth")
        
        assert branch_name == "feature/auth"
        assert branch_name in [b.name for b in temp_repo.branches]
    
    def test_create_feature_branch_invalid(self, integration):
        """Test creating branch for non-existent feature."""
        with pytest.raises(ValueError):
            integration.create_feature_branch("invalid")
    
    def test_complete_feature(self, integration, temp_repo):
        """Test completing a feature."""
        # Make a change
        test_file = Path(temp_repo.working_dir) / "test.py"
        test_file.write_text("# Test file")
        temp_repo.index.add(['test.py'])
        
        # Complete feature
        result = integration.complete_feature("auth")
        
        assert result is True
        assert integration.tracker.feature_graph.features["auth"].status == "completed"
        
        # Check commit was created
        last_commit = temp_repo.head.commit
        assert "Complete feature: Authentication" in last_commit.message
    
    def test_generate_feature_report(self, integration, temp_repo):
        """Test generating feature progress report."""
        # Create some activity
        auth_branch = temp_repo.create_head("feature/auth")
        temp_repo.head.reference = auth_branch
        
        auth_file = Path(temp_repo.working_dir) / "auth.py"
        auth_file.write_text("# Auth implementation")
        temp_repo.index.add(['auth.py'])
        temp_repo.index.commit("feat: auth progress")
        
        # Generate report
        report = integration.generate_feature_report()
        
        assert "features" in report
        assert "summary" in report
        assert "auth" in report["features"]
        assert report["features"]["auth"]["commits"] > 0
        assert report["summary"]["total_features"] == 2