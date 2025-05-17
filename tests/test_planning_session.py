"""Tests for planning session functionality."""
import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from velocitytree.planning_session import (
    PlanningSession, SessionState, PlanningStage, 
    PlanningMessage, ProjectGoal, Feature, Milestone, ProjectPlan
)
from velocitytree.config import Config


class TestPlanningSession:
    """Test suite for PlanningSession class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        # Mock the nested config structure
        config.config = Mock()
        config.config.ai = Mock()
        config.config.ai.provider = 'openai'
        config.config.ai.model = 'gpt-4'
        config.config.ai.temperature = 0.7
        config.config.ai.max_tokens = 1000
        config.config.ai.api_key = 'test-key'
        
        config.config.ai.providers = Mock()
        config.config.ai.providers.openai = Mock()
        config.config.ai.providers.openai.api_key = 'test-key'
        config.config.ai.providers.openai.model = 'gpt-4'
        config.config.ai.providers.openai.temperature = 0.7
        config.config.ai.providers.openai.max_tokens = 1000
        
        config.config_data = {
            'ai': {
                'default_provider': 'openai',
                'providers': {
                    'openai': {
                        'api_key': 'test-key',
                        'model': 'gpt-4'
                    }
                }
            }
        }
        return config
    
    @pytest.fixture
    def session(self, mock_config, monkeypatch):
        """Create a planning session instance with mocked AI."""
        # Mock the AI assistant to avoid actual API calls
        mock_ai = Mock()
        mock_ai.suggest.return_value = "Mocked AI response"
        
        def mock_ai_init(*args, **kwargs):
            return mock_ai
        
        monkeypatch.setattr("velocitytree.planning_session.AIAssistant", mock_ai_init)
        
        return PlanningSession(mock_config)
    
    def test_initialization(self, session):
        """Test session initialization."""
        assert session.session_id is not None
        assert session.state == SessionState.CREATED
        assert session.stage == PlanningStage.INITIALIZATION
        assert len(session.messages) == 0
        assert session.project_plan is None
    
    def test_start_session(self, session):
        """Test starting a new session."""
        result = session.start_session("Test Project", template="web_app")
        
        assert session.state == SessionState.ACTIVE
        assert session.project_plan is not None
        assert session.project_plan.name == "Test Project"
        assert session.metadata['project_name'] == "Test Project"
        assert session.metadata['template_used'] == "web_app"
        assert 'session_id' in result
        assert 'greeting' in result
        assert len(session.messages) >= 2  # System message + greeting
    
    def test_add_message(self, session):
        """Test adding messages to session."""
        session.start_session("Test Project")
        initial_count = len(session.messages)
        
        session.add_message(role="user", content="Test message", metadata={})
        
        # When we add a user message, _process_user_input is called which adds an assistant message
        assert len(session.messages) >= initial_count + 1
        
        # Find the user message we added
        user_messages = [msg for msg in session.messages if msg.role == "user" and msg.content == "Test message"]
        assert len(user_messages) > 0
        user_msg = user_messages[0]
        assert user_msg.content == "Test message"
        assert isinstance(user_msg.timestamp, datetime)
    
    def test_process_user_input(self, session):
        """Test processing user input."""
        # The AI is already mocked in the session fixture
        session.ai_assistant.suggest.return_value = "AI response"
        
        session.start_session("Test Project")
        response = session._process_user_input("I want to build a web app")
        
        assert response == "AI response"
        session.ai_assistant.suggest.assert_called()
    
    def test_stage_progression(self, session):
        """Test stage progression logic."""
        session.start_session("Test Project")
        
        # Set project description to complete initialization
        session.project_plan.description = "A test project"
        assert session._is_stage_complete() is True
        
        # Progress to next stage
        session._update_stage()
        assert session.stage == PlanningStage.GOAL_SETTING
        
        # Add goals to complete goal setting
        goal = ProjectGoal(
            description="Test goal",
            priority="high",
            success_criteria=["Criterion 1"]
        )
        session.project_plan.goals.append(goal)
        assert session._is_stage_complete() is True
    
    def test_save_and_load_session(self, mock_config, tmp_path, monkeypatch):
        """Test saving and loading session state."""
        # Override session directory
        session_dir = tmp_path / 'planning_sessions'
        session_dir.mkdir()
        
        # Patch the home directory to use our temp path
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)
        
        session = PlanningSession(mock_config)
        session.start_session("Test Project")
        session.add_message(role="user", content="Test message")
        
        # Save session
        session.save_state()
        assert session.session_file.exists()
        
        # Load session
        loaded_session = PlanningSession.load_session(mock_config, session.session_id)
        
        assert loaded_session.session_id == session.session_id
        assert loaded_session.state == session.state
        assert loaded_session.stage == session.stage
        assert len(loaded_session.messages) == len(session.messages)
        assert loaded_session.project_plan.name == session.project_plan.name
    
    def test_pause_and_resume_session(self, session):
        """Test pausing and resuming sessions."""
        session.start_session("Test Project")
        
        # Pause session
        session.pause_session()
        assert session.state == SessionState.PAUSED
        assert 'paused_at' in session.metadata
        
        # Resume session
        result = session.resume_session()
        assert session.state == SessionState.ACTIVE
        assert 'resumed_at' in session.metadata
        assert 'greeting' in result
    
    def test_complete_session(self, session):
        """Test completing a session."""
        session.start_session("Test Project")
        
        # Add some data
        session.project_plan.goals.append(
            ProjectGoal("Test goal", "high", ["Success"])
        )
        session.project_plan.features.append(
            Feature("Test feature", "Description", "high", ["Req1"], "small")
        )
        
        result = session.complete_session()
        
        assert session.state == SessionState.COMPLETED
        assert 'completed_at' in session.metadata
        assert 'summary' in result
        assert result['summary']['goals_defined'] == 1
        assert result['summary']['features_defined'] == 1
    
    def test_export_markdown(self, session):
        """Test exporting plan as Markdown."""
        session.start_session("Test Project")
        
        # Add data
        session.project_plan.description = "A test project description"
        session.project_plan.goals.append(
            ProjectGoal("Build awesome app", "high", ["User satisfaction"])
        )
        session.project_plan.features.append(
            Feature("User auth", "User authentication system", "high", ["Secure"], "medium")
        )
        session.project_plan.tech_stack = {
            "Frontend": ["React", "TypeScript"],
            "Backend": ["Python", "FastAPI"]
        }
        
        markdown = session.export_plan(format='markdown')
        
        assert "# Test Project" in markdown
        assert "Build awesome app" in markdown
        assert "User auth" in markdown
        assert "React" in markdown
        assert "Python" in markdown
    
    def test_export_json(self, session):
        """Test exporting plan as JSON."""
        session.start_session("Test Project")
        session.project_plan.description = "Test description"
        
        json_output = session.export_plan(format='json')
        data = json.loads(json_output)
        
        assert data['name'] == "Test Project"
        assert data['description'] == "Test description"
        assert 'goals' in data
        assert 'features' in data
    
    def test_extract_planning_data(self, session):
        """Test extracting structured data from conversation."""
        session.start_session("Test Project")
        
        # Test goal extraction
        session.stage = PlanningStage.GOAL_SETTING
        user_input = "My goals are: 1. Build a scalable app, 2. Reach 1000 users"
        session._extract_planning_data("", user_input)
        
        # The current implementation does extract goals from numbered lists
        assert len(session.project_plan.goals) >= 1
        
        # Test feature extraction
        session.stage = PlanningStage.FEATURE_DEFINITION
        user_input = """Features needed:
        - User authentication
        - Dashboard with analytics
        - API integration"""
        session._extract_planning_data("", user_input)
        
        # Check that features were extracted
        assert len(session.project_plan.features) >= 1
    
    def test_message_serialization(self):
        """Test message serialization."""
        message = PlanningMessage(
            role="user",
            content="Test content",
            timestamp=datetime.now(),
            metadata={"key": "value"}
        )
        
        # Convert to dict
        data = message.to_dict()
        assert data['role'] == "user"
        assert data['content'] == "Test content"
        assert 'timestamp' in data
        assert data['metadata']['key'] == "value"
        
        # Create from dict
        restored = PlanningMessage.from_dict(data)
        assert restored.role == message.role
        assert restored.content == message.content
        assert restored.metadata == message.metadata
    
    def test_invalid_state_transitions(self, session):
        """Test invalid state transitions."""
        # Can't resume non-paused session
        session.start_session("Test Project")
        
        with pytest.raises(ValueError):
            session.resume_session()
    
    def test_session_not_found(self, mock_config):
        """Test loading non-existent session."""
        with pytest.raises(ValueError, match="Session not found"):
            PlanningSession.load_session(mock_config, "non-existent-id")


class TestDataClasses:
    """Test data classes used in planning."""
    
    def test_project_goal(self):
        """Test ProjectGoal dataclass."""
        goal = ProjectGoal(
            description="Test goal",
            priority="high",
            success_criteria=["Criterion 1", "Criterion 2"],
            constraints=["Budget limit"]
        )
        
        assert goal.description == "Test goal"
        assert goal.priority == "high"
        assert len(goal.success_criteria) == 2
        assert len(goal.constraints) == 1
    
    def test_feature(self):
        """Test Feature dataclass."""
        feature = Feature(
            name="Authentication",
            description="User authentication system",
            priority="high",
            requirements=["OAuth support", "MFA"],
            effort_estimate="large",
            dependencies=["Database"]
        )
        
        assert feature.name == "Authentication"
        assert feature.priority == "high"
        assert len(feature.requirements) == 2
        assert feature.effort_estimate == "large"
    
    def test_milestone(self):
        """Test Milestone dataclass."""
        milestone = Milestone(
            name="MVP Launch",
            description="Launch minimum viable product",
            deliverables=["Core features", "Documentation"],
            estimated_duration="2 months",
            dependencies=["Beta testing"],
            features=["Auth", "Dashboard"]
        )
        
        assert milestone.name == "MVP Launch"
        assert len(milestone.deliverables) == 2
        assert milestone.estimated_duration == "2 months"
    
    def test_project_plan(self):
        """Test ProjectPlan dataclass."""
        plan = ProjectPlan(
            name="Test Project",
            description="A test project",
            goals=[],
            features=[],
            milestones=[],
            tech_stack={},
            timeline={},
            resources={},
            risks=[],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert plan.name == "Test Project"
        assert plan.description == "A test project"
        assert isinstance(plan.created_at, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])