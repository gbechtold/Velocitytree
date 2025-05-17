"""Tests for conversation engine functionality."""
import pytest
from unittest.mock import Mock

from velocitytree.conversation_engine import (
    ConversationEngine, IntentType, ConversationContext
)
from velocitytree.planning_session import PlanningStage, PlanningSession


class TestConversationEngine:
    """Test suite for ConversationEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a conversation engine instance."""
        return ConversationEngine()
    
    @pytest.fixture
    def context(self):
        """Create a sample conversation context."""
        return ConversationContext(
            current_stage=PlanningStage.GOAL_SETTING,
            last_prompt="What are the main goals for this project?",
            expecting_response="project_goals",
            validation_rules={}
        )
    
    def test_initialization(self, engine):
        """Test engine initialization."""
        assert engine.stage_flow is not None
        assert engine.stage_prompts is not None
        assert engine.validation_rules is not None
    
    def test_detect_intent_commands(self, engine, context):
        """Test intent detection for commands."""
        test_cases = [
            ("cancel", IntentType.CANCEL),
            ("quit", IntentType.CANCEL),
            ("exit", IntentType.CANCEL),
            ("back", IntentType.BACK),
            ("previous", IntentType.BACK),
            ("help", IntentType.HELP),
            ("?", IntentType.HELP),
            ("skip", IntentType.SKIP),
            ("next", IntentType.SKIP),
            ("done", IntentType.COMPLETE),
            ("complete", IntentType.COMPLETE),
            ("finish", IntentType.COMPLETE),
        ]
        
        for user_input, expected_intent in test_cases:
            intent = engine.detect_intent(user_input, context)
            assert intent == expected_intent
    
    def test_detect_intent_responses(self, engine, context):
        """Test intent detection for responses."""
        test_cases = [
            ("yes", IntentType.CONFIRM),
            ("yeah", IntentType.CONFIRM),
            ("sure", IntentType.CONFIRM),
            ("ok", IntentType.CONFIRM),
            ("no", IntentType.DENY),
            ("nope", IntentType.DENY),
            ("How do I do this?", IntentType.ASK_QUESTION),
            ("What does that mean?", IntentType.ASK_QUESTION),
            ("I want to change the name", IntentType.MODIFY),
            ("Let me update that", IntentType.MODIFY),
            ("I want to build a web app", IntentType.PROVIDE_INFO),
        ]
        
        for user_input, expected_intent in test_cases:
            intent = engine.detect_intent(user_input, context)
            assert intent == expected_intent
    
    def test_validate_input_length(self, engine):
        """Test input validation for length."""
        # Test minimum length
        valid, error = engine.validate_input("Hi", "project_description")
        assert valid is False
        assert "too short" in error
        
        # Test maximum length
        long_text = "x" * 1000
        valid, error = engine.validate_input(long_text, "project_description")
        assert valid is False
        assert "too long" in error
        
        # Test valid length
        valid_text = "This is a valid project description that meets the requirements."
        valid, error = engine.validate_input(valid_text, "project_description")
        assert valid is True
        assert error is None
    
    def test_validate_input_list(self, engine):
        """Test input validation for lists."""
        # Test minimum items
        valid, error = engine.validate_input("", "project_goals")
        assert valid is False
        assert "at least" in error
        
        # Test valid list
        goals = """1. Build a scalable app
2. Reach 1000 users
3. Generate revenue"""
        valid, error = engine.validate_input(goals, "project_goals")
        assert valid is True
        assert error is None
        
        # Test item length
        short_goals = "1. Goal\n2. Aim"
        valid, error = engine.validate_input(short_goals, "project_goals")
        assert valid is False
        assert "too short" in error
    
    def test_extract_structured_data_goals(self, engine):
        """Test extracting structured data for goals."""
        user_input = """My goals are:
1. Build a scalable web application
2. Reach 10,000 active users
3. Generate $100k in revenue"""
        
        data = engine.extract_structured_data(user_input, "project_goals")
        
        assert 'goals' in data
        assert len(data['goals']) >= 1  # At least one goal extracted
        # Check for any goal containing expected text
        descriptions = [g['description'] for g in data['goals']]
        assert any('scalable' in d.lower() for d in descriptions)
    
    def test_extract_structured_data_features(self, engine):
        """Test extracting structured data for features."""
        user_input = """Core features:
- User authentication with OAuth
- Dashboard with real-time analytics
- API integration for third-party services"""
        
        data = engine.extract_structured_data(user_input, "core_features")
        
        assert 'features' in data
        assert len(data['features']) >= 1  # At least one feature extracted
        # Check for any feature containing expected text
        descriptions = [f['description'] for f in data['features']]
        assert any('authentication' in d.lower() for d in descriptions)
    
    def test_extract_structured_data_languages(self, engine):
        """Test extracting programming languages."""
        user_input = "Python, JavaScript, TypeScript, Go"
        
        data = engine.extract_structured_data(user_input, "languages")
        
        assert 'languages' in data
        assert len(data['languages']) == 4
        assert "Python" in data['languages']
        assert "JavaScript" in data['languages']
    
    def test_priority_detection(self, engine):
        """Test priority detection from text."""
        test_cases = [
            ("This is critical for launch", "high"),
            ("Must have feature", "high"),
            ("Essential functionality", "high"),
            ("Nice to have feature", "low"),
            ("Optional enhancement", "low"),
            ("Regular feature", "medium"),
        ]
        
        for text, expected_priority in test_cases:
            priority = engine._detect_priority(text)
            assert priority == expected_priority
    
    def test_effort_detection(self, engine):
        """Test effort estimation from text."""
        test_cases = [
            ("Simple login form", "small"),
            ("Quick fix", "small"),
            ("Complex integration", "large"),
            ("Difficult implementation", "large"),
            ("Standard feature", "medium"),
        ]
        
        for text, expected_effort in test_cases:
            effort = engine._detect_effort(text)
            assert effort == expected_effort
    
    def test_generate_contextual_response(self, engine, context):
        """Test contextual response generation."""
        # Test help response
        response = engine.generate_contextual_response(IntentType.HELP, context)
        assert "Help:" in response
        
        # Test cancel response
        response = engine.generate_contextual_response(IntentType.CANCEL, context)
        assert "cancel" in response.lower()
        
        # Test validation error response
        response = engine.generate_contextual_response(
            IntentType.PROVIDE_INFO, 
            context, 
            validation_error="Input too short"
        )
        assert "Input too short" in response
        
        # Test retry limit
        context.retry_count = 3
        response = engine.generate_contextual_response(
            IntentType.PROVIDE_INFO,
            context,
            validation_error="Invalid input"
        )
        assert "skip" in response.lower()
    
    def test_handle_stage_transition(self, engine):
        """Test stage transition handling."""
        mock_session = Mock(spec=PlanningSession)
        mock_session.stage = PlanningStage.INITIALIZATION
        
        # Test valid transition
        next_stage = engine.handle_stage_transition(mock_session, 'complete')
        assert next_stage == PlanningStage.GOAL_SETTING
        
        # Test invalid transition
        next_stage = engine.handle_stage_transition(mock_session, 'invalid_action')
        assert next_stage is None
    
    def test_get_stage_progress(self, engine):
        """Test stage progress calculation."""
        mock_session = Mock(spec=PlanningSession)
        mock_session.stage = PlanningStage.FEATURE_DEFINITION
        
        progress = engine.get_stage_progress(mock_session)
        
        assert progress['current_stage'] == 'feature_definition'
        assert progress['current_index'] == 2  # Third stage (0-indexed)
        assert progress['total_stages'] == 8
        assert progress['percentage'] == 25  # 2/8 * 100
        assert len(progress['completed_stages']) == 2
        assert len(progress['remaining_stages']) == 5
    
    def test_generate_stage_summary(self, engine):
        """Test stage summary generation."""
        mock_session = Mock(spec=PlanningSession)
        mock_session.project_plan = Mock()
        mock_session.project_plan.name = "Test Project"
        mock_session.project_plan.description = "A test project"
        mock_session.project_plan.goals = [Mock(description="Goal 1"), Mock(description="Goal 2")]
        mock_session.project_plan.features = [Mock(name="Feature 1")]
        mock_session.project_plan.tech_stack = {"Backend": ["Python"], "Frontend": ["React"]}
        mock_session.project_plan.milestones = []  # Mock empty milestones list
        mock_session.project_plan.timeline = {"total_duration": "6 months"}
        mock_session.project_plan.resources = {"team_size": 5, "budget": "$100k"}
        
        # Test initialization summary
        summary = engine.generate_stage_summary(mock_session, PlanningStage.INITIALIZATION)
        assert "Test Project" in summary
        assert "A test project" in summary
        
        # Test goal setting summary
        summary = engine.generate_stage_summary(mock_session, PlanningStage.GOAL_SETTING)
        assert "Goals defined: 2" in summary
        assert "Goal 1" in summary
        
        # Test technical planning summary
        summary = engine.generate_stage_summary(mock_session, PlanningStage.TECHNICAL_PLANNING)
        assert "Backend: Python" in summary
        assert "Frontend: React" in summary
    
    def test_stage_flow_completeness(self, engine):
        """Test that all stages have defined flows."""
        all_stages = list(PlanningStage)
        
        for stage in all_stages:
            if stage != PlanningStage.FINALIZATION:  # Last stage
                assert stage in engine.stage_flow
                assert 'complete' in engine.stage_flow[stage]
    
    def test_stage_prompts_completeness(self, engine):
        """Test that key stages have prompts defined."""
        key_stages = [
            PlanningStage.INITIALIZATION,
            PlanningStage.GOAL_SETTING,
            PlanningStage.FEATURE_DEFINITION,
            PlanningStage.TECHNICAL_PLANNING
        ]
        
        for stage in key_stages:
            assert stage in engine.stage_prompts
            assert len(engine.stage_prompts[stage]) > 0
            
            # Check prompt structure
            for prompt in engine.stage_prompts[stage]:
                assert 'prompt' in prompt
                assert 'expecting' in prompt
                assert 'help' in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])