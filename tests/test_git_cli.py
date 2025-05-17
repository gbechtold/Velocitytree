"""Tests for git CLI commands."""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from velocitytree import cli as cli_module
from velocitytree.git_manager import ChangeAnalysis


class TestGitCLI:
    """Test suite for git-related CLI commands."""
    
    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()
    
    @patch('velocitytree.git_manager.GitManager')
    def test_feature_command(self, mock_git_manager, runner):
        """Test the git feature command."""
        # Mock GitManager instance
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        mock_instance.create_feature_branch.return_value = "feature/add-user-auth"
        
        # Test basic usage
        result = runner.invoke(cli_module.cli, ['git', 'feature', 'Add user authentication'])
        assert result.exit_code == 0
        assert "Created and switched to branch: feature/add-user-auth" in result.output
        
        # Verify method was called
        mock_instance.create_feature_branch.assert_called_with(
            "Add user authentication", 
            prefix="feature/"
        )
    
    @patch('velocitytree.git_manager.GitManager')
    def test_feature_command_with_ticket(self, mock_git_manager, runner):
        """Test the git feature command with ticket reference."""
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        mock_instance.create_feature_branch.return_value = "feature/proj-123-fix-bug"
        
        result = runner.invoke(cli_module.cli, ['git', 'feature', 'Fix bug', '--ticket', 'PROJ-123'])
        assert result.exit_code == 0
        
        # Verify ticket was added to description
        mock_instance.create_feature_branch.assert_called_with(
            "PROJ-123 Fix bug", 
            prefix="feature/"
        )
    
    @patch('velocitytree.git_manager.GitManager')
    @patch('subprocess.run')
    @patch('click.confirm')
    def test_commit_command(self, mock_confirm, mock_subprocess, mock_git_manager, runner):
        """Test the git commit command."""
        # Mock GitManager instance
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        
        # Mock change analysis
        mock_changes = ChangeAnalysis(
            files_changed=['file1.py', 'file2.py'],
            insertions=50,
            deletions=10,
            change_type='feature',
            components_affected=['src'],
            suggested_message='feat(src): add new functionality',
            impact_level='moderate'
        )
        mock_instance.analyze_changes.return_value = mock_changes
        mock_instance.generate_commit_message.return_value = 'feat(src): add new functionality'
        
        # Mock user confirmation
        mock_confirm.return_value = True
        
        # Mock git command execution
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stderr = ""
        
        result = runner.invoke(cli_module.cli, ['git', 'commit'])
        assert result.exit_code == 0
        assert "Change Analysis:" in result.output
        assert "Files changed: 2" in result.output
        assert "Insertions: +50" in result.output
        assert "Commit created successfully!" in result.output
    
    @patch('velocitytree.git_manager.GitManager')
    def test_tag_command(self, mock_git_manager, runner):
        """Test the git tag command."""
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        mock_instance.tag_version.return_value = "v1.2.0"
        
        # Test default patch bump
        result = runner.invoke(cli_module.cli, ['git', 'tag'])
        assert result.exit_code == 0
        assert "Created tag: v1.2.0" in result.output
        mock_instance.tag_version.assert_called_with(version_type='patch')
        
        # Test minor bump
        result = runner.invoke(cli_module.cli, ['git', 'tag', '--type', 'minor'])
        assert result.exit_code == 0
        mock_instance.tag_version.assert_called_with(version_type='minor')
        
        # Test custom version
        result = runner.invoke(cli_module.cli, ['git', 'tag', '--version', 'v2.0.0'])
        assert result.exit_code == 0
        mock_instance.tag_version.assert_called_with(custom_version='v2.0.0')
    
    @patch('velocitytree.git_manager.GitManager')
    def test_analyze_command(self, mock_git_manager, runner):
        """Test the git analyze command."""
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        
        # Mock change analysis
        mock_changes = ChangeAnalysis(
            files_changed=['file1.py', 'file2.py', 'file3.js'],
            insertions=100,
            deletions=25,
            change_type='feature',
            components_affected=['src', 'tests'],
            suggested_message='feat(src): major update',
            impact_level='major'
        )
        mock_instance.analyze_changes.return_value = mock_changes
        
        result = runner.invoke(cli_module.cli, ['git', 'analyze'])
        assert result.exit_code == 0
        assert "Git Change Analysis" in result.output
        assert "Files Changed" in result.output
        assert "3" in result.output  # 3 files
        assert "+100" in result.output  # insertions
        assert "-25" in result.output  # deletions
        assert "file1.py" in result.output
        assert "Suggested Commit Message:" in result.output
    
    @patch('velocitytree.git_manager.GitManager')
    def test_error_handling(self, mock_git_manager, runner):
        """Test error handling in git commands."""
        mock_instance = MagicMock()
        mock_git_manager.return_value = mock_instance
        
        # Test branch already exists error
        mock_instance.create_feature_branch.side_effect = ValueError("Branch already exists")
        result = runner.invoke(cli_module.cli, ['git', 'feature', 'Test feature'])
        assert result.exit_code == 0
        assert "Error: Branch already exists" in result.output
        
        # Test generic error
        mock_instance.analyze_changes.side_effect = Exception("Git error")
        result = runner.invoke(cli_module.cli, ['git', 'analyze'])
        assert result.exit_code == 0
        assert "Error: Git error" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])