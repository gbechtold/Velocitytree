"""Planning session management for conversational project planning."""
import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

from .utils import logger
from .ai import AIAssistant
from .config import Config


class SessionState(Enum):
    """States for planning sessions."""
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanningStage(Enum):
    """Stages in the planning process."""
    INITIALIZATION = "initialization"
    GOAL_SETTING = "goal_setting"
    FEATURE_DEFINITION = "feature_definition"
    TECHNICAL_PLANNING = "technical_planning"
    TIMELINE_ESTIMATION = "timeline_estimation"
    RESOURCE_PLANNING = "resource_planning"
    REVIEW = "review"
    FINALIZATION = "finalization"


@dataclass
class PlanningMessage:
    """A message in the planning conversation."""
    role: str  # user, assistant, system
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
        }
        if self.metadata:
            data['metadata'] = self.metadata
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PlanningMessage':
        """Create from dictionary."""
        return cls(
            role=data['role'],
            content=data['content'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            metadata=data.get('metadata')
        )


@dataclass
class ProjectGoal:
    """A project goal defined during planning."""
    description: str
    priority: str  # high, medium, low
    success_criteria: List[str]
    constraints: List[str] = None


@dataclass
class Feature:
    """A feature defined during planning."""
    name: str
    description: str
    priority: str
    requirements: List[str]
    effort_estimate: str  # small, medium, large, x-large
    dependencies: List[str] = None


@dataclass
class Milestone:
    """A project milestone."""
    name: str
    description: str
    deliverables: List[str]
    estimated_duration: str
    dependencies: List[str] = None
    features: List[str] = None


@dataclass
class ProjectPlan:
    """Complete project plan generated from session."""
    name: str
    description: str
    goals: List[ProjectGoal]
    features: List[Feature]
    milestones: List[Milestone]
    tech_stack: Dict[str, List[str]]
    timeline: Dict[str, Any]
    resources: Dict[str, Any]
    risks: List[Dict[str, str]]
    created_at: datetime
    updated_at: datetime


class PlanningSession:
    """Manages a conversational planning session."""
    
    def __init__(self, config: Config, session_id: Optional[str] = None):
        """Initialize planning session."""
        self.config = config
        self.session_id = session_id or str(uuid.uuid4())
        self.state = SessionState.CREATED
        self.stage = PlanningStage.INITIALIZATION
        self.messages: List[PlanningMessage] = []
        self.project_plan: Optional[ProjectPlan] = None
        self.metadata: Dict[str, Any] = {
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'participants': [],
            'template_used': None
        }
        self.ai_assistant = AIAssistant(config)
        
        # Session storage path
        self.session_dir = Path.home() / '.velocitytree' / 'planning_sessions'
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / f"{self.session_id}.json"
        
        logger.info(f"Planning session initialized: {self.session_id}")
    
    def start_session(self, project_name: str, template: Optional[str] = None) -> Dict:
        """Start a new planning session."""
        self.state = SessionState.ACTIVE
        self.metadata['project_name'] = project_name
        self.metadata['template_used'] = template
        self.metadata['started_at'] = datetime.now()
        
        # Initialize project plan
        self.project_plan = ProjectPlan(
            name=project_name,
            description="",
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
        
        # Add system message
        self.add_message(
            role="system",
            content=f"Starting planning session for project: {project_name}",
            metadata={'stage': self.stage.value}
        )
        
        # Get initial greeting
        greeting = self._get_stage_prompt(self.stage)
        self.add_message(
            role="assistant",
            content=greeting,
            metadata={'stage': self.stage.value}
        )
        
        self.save_state()
        
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'stage': self.stage.value,
            'greeting': greeting
        }
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to the conversation."""
        message = PlanningMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.metadata['updated_at'] = datetime.now()
        
        # Process user input
        if role == "user":
            self._process_user_input(content)
    
    def _process_user_input(self, user_input: str) -> str:
        """Process user input and generate response."""
        # Update stage based on conversation progress
        self._update_stage()
        
        # Generate AI response
        context = self._build_context()
        prompt = self._build_prompt(user_input, context)
        
        try:
            # Use suggest method which handles sync context
            context_str = json.dumps(context, default=str)
            full_prompt = f"{prompt}\n\nContext: {context_str}"
            response = self.ai_assistant.suggest(full_prompt, include_context=True)
            
            # Extract structured data from response
            self._extract_planning_data(response, user_input)
            
            # Add assistant response
            self.add_message(
                role="assistant",
                content=response,
                metadata={'stage': self.stage.value}
            )
            
            # Save state after each interaction
            self.save_state()
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            error_msg = "I encountered an error processing your input. Let's try again."
            self.add_message(
                role="assistant",
                content=error_msg,
                metadata={'error': str(e)}
            )
            return error_msg
    
    def _update_stage(self) -> None:
        """Update planning stage based on conversation progress."""
        # Simple stage progression logic
        stage_order = list(PlanningStage)
        current_index = stage_order.index(self.stage)
        
        # Check if current stage is complete
        if self._is_stage_complete():
            if current_index < len(stage_order) - 1:
                self.stage = stage_order[current_index + 1]
                logger.info(f"Progressed to stage: {self.stage.value}")
    
    def _is_stage_complete(self) -> bool:
        """Check if current stage is complete."""
        if self.stage == PlanningStage.INITIALIZATION:
            return bool(self.project_plan.description)
        elif self.stage == PlanningStage.GOAL_SETTING:
            return len(self.project_plan.goals) >= 1
        elif self.stage == PlanningStage.FEATURE_DEFINITION:
            return len(self.project_plan.features) >= 1
        elif self.stage == PlanningStage.TECHNICAL_PLANNING:
            return bool(self.project_plan.tech_stack)
        elif self.stage == PlanningStage.TIMELINE_ESTIMATION:
            return bool(self.project_plan.timeline)
        elif self.stage == PlanningStage.RESOURCE_PLANNING:
            return bool(self.project_plan.resources)
        return False
    
    def _build_context(self) -> Dict:
        """Build context for AI prompt."""
        context = {
            'session_id': self.session_id,
            'project_name': self.project_plan.name,
            'stage': self.stage.value,
            'conversation_history': [msg.to_dict() for msg in self.messages[-10:]],  # Last 10 messages
            'current_plan': {
                'description': self.project_plan.description,
                'goals': [asdict(g) for g in self.project_plan.goals],
                'features': [asdict(f) for f in self.project_plan.features],
                'milestones': [asdict(m) for m in self.project_plan.milestones],
                'tech_stack': self.project_plan.tech_stack,
                'timeline': self.project_plan.timeline,
                'resources': self.project_plan.resources,
                'risks': self.project_plan.risks
            }
        }
        return context
    
    def _build_prompt(self, user_input: str, context: Dict) -> str:
        """Build prompt for AI assistant."""
        stage_prompts = {
            PlanningStage.INITIALIZATION: "Help the user describe their project and understand their vision.",
            PlanningStage.GOAL_SETTING: "Help define clear, measurable project goals.",
            PlanningStage.FEATURE_DEFINITION: "Help identify and prioritize key features.",
            PlanningStage.TECHNICAL_PLANNING: "Help plan the technical architecture and stack.",
            PlanningStage.TIMELINE_ESTIMATION: "Help estimate timelines and milestones.",
            PlanningStage.RESOURCE_PLANNING: "Help plan required resources and team.",
            PlanningStage.REVIEW: "Review the complete plan with the user.",
            PlanningStage.FINALIZATION: "Finalize the plan and prepare outputs."
        }
        
        prompt = f"""You are a project planning assistant helping with stage: {self.stage.value}
        
Project: {context['project_name']}
Current Stage: {self.stage.value}
Stage Goal: {stage_prompts.get(self.stage, "Help the user plan their project.")}

Current Plan Summary:
- Description: {context['current_plan']['description'] or 'Not yet defined'}
- Goals: {len(context['current_plan']['goals'])} defined
- Features: {len(context['current_plan']['features'])} defined
- Tech Stack: {'Defined' if context['current_plan']['tech_stack'] else 'Not yet defined'}

Recent Conversation:
{self._format_conversation_history(context['conversation_history'])}

User Input: {user_input}

Respond helpfully to guide the planning process. Ask clarifying questions when needed.
Format your response to be clear and actionable. When appropriate, summarize what you've understood.
"""
        return prompt
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history for prompt."""
        formatted = []
        for msg in history:
            role = msg['role'].capitalize()
            content = msg['content']
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)
    
    def _get_stage_prompt(self, stage: PlanningStage) -> str:
        """Get initial prompt for a planning stage."""
        prompts = {
            PlanningStage.INITIALIZATION: 
                "Welcome! Let's plan your project. What type of project would you like to build? " +
                "Please describe your vision in a few sentences.",
                
            PlanningStage.GOAL_SETTING:
                "Great! Now let's define your project goals. What are the main objectives you want to achieve? " +
                "Think about what success looks like for this project.",
                
            PlanningStage.FEATURE_DEFINITION:
                "Excellent goals! Now let's identify the key features. What are the must-have features for your project? " +
                "We can prioritize them as high, medium, or low priority.",
                
            PlanningStage.TECHNICAL_PLANNING:
                "Perfect! Now let's plan the technical architecture. What programming languages, frameworks, " +
                "and tools do you plan to use? Consider frontend, backend, database, and infrastructure needs.",
                
            PlanningStage.TIMELINE_ESTIMATION:
                "Great technical choices! Let's estimate the timeline. How much time do you have for this project? " +
                "We'll break it down into milestones and phases.",
                
            PlanningStage.RESOURCE_PLANNING:
                "Now let's plan resources. Who will work on this project? What roles and skills are needed? " +
                "Consider developers, designers, and other team members.",
                
            PlanningStage.REVIEW:
                "Let's review your complete project plan. I'll summarize what we've defined, " +
                "and you can let me know if anything needs adjustment.",
                
            PlanningStage.FINALIZATION:
                "Your project plan is ready! Would you like to export it to a specific format " +
                "(Markdown, JSON, GitHub Issues, JIRA tickets)?"
        }
        return prompts.get(stage, "Let's continue planning your project.")
    
    def _extract_planning_data(self, response: str, user_input: str) -> None:
        """Extract structured planning data from conversation."""
        # This is a simplified version - in production, use more sophisticated NLP
        
        if self.stage == PlanningStage.INITIALIZATION:
            if not self.project_plan.description and len(user_input) > 20:
                self.project_plan.description = user_input
                
        elif self.stage == PlanningStage.GOAL_SETTING:
            # Simple goal extraction (would use NLP in production)
            if "goal" in user_input.lower() or "objective" in user_input.lower():
                goals = user_input.split(',')
                for goal_text in goals:
                    goal = ProjectGoal(
                        description=goal_text.strip(),
                        priority="high",
                        success_criteria=[],
                        constraints=[]
                    )
                    self.project_plan.goals.append(goal)
                    
        elif self.stage == PlanningStage.FEATURE_DEFINITION:
            # Simple feature extraction
            if "feature" in user_input.lower() or any(word in user_input.lower() for word in ["should", "must", "need"]):
                # Extract features from bullet points or numbered lists
                lines = user_input.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                        feature_text = line.lstrip('0123456789.-* ')
                        feature = Feature(
                            name=feature_text[:30],
                            description=feature_text,
                            priority="medium",
                            requirements=[],
                            effort_estimate="medium"
                        )
                        self.project_plan.features.append(feature)
    
    def get_context(self) -> Dict:
        """Get session context for display or processing."""
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'stage': self.stage.value,
            'project_name': self.project_plan.name if self.project_plan else None,
            'messages': [msg.to_dict() for msg in self.messages],
            'metadata': self.metadata,
            'plan_summary': self._get_plan_summary() if self.project_plan else None
        }
    
    def _get_plan_summary(self) -> Dict:
        """Get summary of current plan."""
        return {
            'name': self.project_plan.name,
            'description': self.project_plan.description,
            'goals_count': len(self.project_plan.goals),
            'features_count': len(self.project_plan.features),
            'milestones_count': len(self.project_plan.milestones),
            'has_tech_stack': bool(self.project_plan.tech_stack),
            'has_timeline': bool(self.project_plan.timeline),
            'has_resources': bool(self.project_plan.resources)
        }
    
    def save_state(self) -> None:
        """Save session state to disk."""
        session_data = {
            'session_id': self.session_id,
            'state': self.state.value,
            'stage': self.stage.value,
            'messages': [msg.to_dict() for msg in self.messages],
            'project_plan': self._serialize_project_plan(),
            'metadata': self.metadata
        }
        
        with open(self.session_file, 'w') as f:
            json.dump(session_data, f, indent=2, default=str)
        
        logger.debug(f"Session state saved: {self.session_id}")
    
    def _serialize_project_plan(self) -> Optional[Dict]:
        """Serialize project plan for storage."""
        if not self.project_plan:
            return None
            
        return {
            'name': self.project_plan.name,
            'description': self.project_plan.description,
            'goals': [asdict(g) for g in self.project_plan.goals],
            'features': [asdict(f) for f in self.project_plan.features],
            'milestones': [asdict(m) for m in self.project_plan.milestones],
            'tech_stack': self.project_plan.tech_stack,
            'timeline': self.project_plan.timeline,
            'resources': self.project_plan.resources,
            'risks': self.project_plan.risks,
            'created_at': self.project_plan.created_at.isoformat(),
            'updated_at': self.project_plan.updated_at.isoformat()
        }
    
    @classmethod
    def load_session(cls, config: Config, session_id: str) -> 'PlanningSession':
        """Load session from disk."""
        session_dir = Path.home() / '.velocitytree' / 'planning_sessions'
        session_file = session_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise ValueError(f"Session not found: {session_id}")
        
        with open(session_file, 'r') as f:
            session_data = json.load(f)
        
        # Create session instance
        session = cls(config, session_id)
        
        # Restore state
        session.state = SessionState(session_data['state'])
        session.stage = PlanningStage(session_data['stage'])
        session.messages = [PlanningMessage.from_dict(msg) for msg in session_data['messages']]
        session.metadata = session_data['metadata']
        
        # Restore project plan
        if session_data.get('project_plan'):
            plan_data = session_data['project_plan']
            session.project_plan = ProjectPlan(
                name=plan_data['name'],
                description=plan_data['description'],
                goals=[ProjectGoal(**g) for g in plan_data['goals']],
                features=[Feature(**f) for f in plan_data['features']],
                milestones=[Milestone(**m) for m in plan_data['milestones']],
                tech_stack=plan_data['tech_stack'],
                timeline=plan_data['timeline'],
                resources=plan_data['resources'],
                risks=plan_data['risks'],
                created_at=datetime.fromisoformat(plan_data['created_at']),
                updated_at=datetime.fromisoformat(plan_data['updated_at'])
            )
        
        logger.info(f"Session loaded: {session_id}")
        return session
    
    def pause_session(self) -> None:
        """Pause the current session."""
        self.state = SessionState.PAUSED
        self.metadata['paused_at'] = datetime.now()
        self.save_state()
    
    def resume_session(self) -> Dict:
        """Resume a paused session."""
        if self.state != SessionState.PAUSED:
            raise ValueError("Can only resume paused sessions")
        
        self.state = SessionState.ACTIVE
        self.metadata['resumed_at'] = datetime.now()
        
        # Add resume message
        self.add_message(
            role="system",
            content="Session resumed",
            metadata={'stage': self.stage.value}
        )
        
        # Generate resume greeting
        greeting = f"Welcome back! We were working on {self.stage.value.replace('_', ' ')}. " + \
                  self._get_stage_prompt(self.stage)
        
        self.add_message(
            role="assistant",
            content=greeting,
            metadata={'stage': self.stage.value}
        )
        
        self.save_state()
        
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'stage': self.stage.value,
            'greeting': greeting
        }
    
    def complete_session(self) -> Dict:
        """Complete the planning session."""
        self.state = SessionState.COMPLETED
        self.metadata['completed_at'] = datetime.now()
        
        # Generate completion summary
        summary = self._generate_completion_summary()
        
        self.add_message(
            role="system",
            content="Session completed",
            metadata={'summary': summary}
        )
        
        self.save_state()
        
        return {
            'session_id': self.session_id,
            'state': self.state.value,
            'summary': summary,
            'project_plan': self._serialize_project_plan()
        }
    
    def _generate_completion_summary(self) -> Dict:
        """Generate summary of completed session."""
        duration = None
        if 'started_at' in self.metadata and hasattr(self.metadata['started_at'], 'timestamp'):
            duration = (datetime.now() - self.metadata['started_at']).total_seconds() / 60
        
        return {
            'project_name': self.project_plan.name,
            'duration_minutes': duration,
            'goals_defined': len(self.project_plan.goals),
            'features_defined': len(self.project_plan.features),
            'milestones_defined': len(self.project_plan.milestones),
            'has_tech_stack': bool(self.project_plan.tech_stack),
            'has_timeline': bool(self.project_plan.timeline),
            'has_resources': bool(self.project_plan.resources),
            'total_messages': len(self.messages)
        }
    
    def export_plan(self, format: str = 'markdown') -> str:
        """Export the project plan in specified format."""
        if format == 'markdown':
            return self._export_markdown()
        elif format == 'json':
            return json.dumps(self._serialize_project_plan(), indent=2)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _export_markdown(self) -> str:
        """Export plan as Markdown."""
        md = []
        md.append(f"# {self.project_plan.name}")
        md.append("")
        md.append(f"**Description:** {self.project_plan.description}")
        md.append("")
        
        if self.project_plan.goals:
            md.append("## Goals")
            for i, goal in enumerate(self.project_plan.goals, 1):
                md.append(f"{i}. {goal.description} (Priority: {goal.priority})")
            md.append("")
        
        if self.project_plan.features:
            md.append("## Features")
            for feature in self.project_plan.features:
                md.append(f"### {feature.name}")
                md.append(f"**Description:** {feature.description}")
                md.append(f"**Priority:** {feature.priority}")
                md.append(f"**Effort:** {feature.effort_estimate}")
                if feature.requirements:
                    md.append("**Requirements:**")
                    for req in feature.requirements:
                        md.append(f"- {req}")
                md.append("")
        
        if self.project_plan.tech_stack:
            md.append("## Technical Stack")
            for category, technologies in self.project_plan.tech_stack.items():
                md.append(f"**{category}:** {', '.join(technologies)}")
            md.append("")
        
        if self.project_plan.milestones:
            md.append("## Milestones")
            for milestone in self.project_plan.milestones:
                md.append(f"### {milestone.name}")
                md.append(f"**Description:** {milestone.description}")
                md.append(f"**Duration:** {milestone.estimated_duration}")
                if milestone.deliverables:
                    md.append("**Deliverables:**")
                    for deliverable in milestone.deliverables:
                        md.append(f"- {deliverable}")
                md.append("")
        
        if self.project_plan.timeline:
            md.append("## Timeline")
            md.append("```")
            md.append(json.dumps(self.project_plan.timeline, indent=2))
            md.append("```")
            md.append("")
        
        if self.project_plan.risks:
            md.append("## Risks")
            for risk in self.project_plan.risks:
                md.append(f"- **{risk.get('name', 'Risk')}:** {risk.get('description', '')}")
                md.append(f"  - Probability: {risk.get('probability', 'Unknown')}")
                md.append(f"  - Impact: {risk.get('impact', 'Unknown')}")
                md.append(f"  - Mitigation: {risk.get('mitigation', 'None defined')}")
            md.append("")
        
        md.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(md)


if __name__ == "__main__":
    # Example usage
    from .config import Config
    
    config = Config()
    session = PlanningSession(config)
    
    # Start a new session
    result = session.start_session("My Awesome Project")
    print(f"Started session: {result['session_id']}")
    print(f"Greeting: {result['greeting']}")