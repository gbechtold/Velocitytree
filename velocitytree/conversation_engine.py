"""Conversation engine for managing planning session flow."""
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .planning_session import PlanningStage, PlanningSession
from .utils import logger


class IntentType(Enum):
    """Types of user intents in conversation."""
    PROVIDE_INFO = "provide_info"
    ASK_QUESTION = "ask_question"
    REQUEST_CLARIFICATION = "request_clarification"
    CONFIRM = "confirm"
    DENY = "deny"
    MODIFY = "modify"
    SKIP = "skip"
    HELP = "help"
    BACK = "back"
    CANCEL = "cancel"
    COMPLETE = "complete"


@dataclass
class ConversationContext:
    """Context for conversation flow."""
    current_stage: PlanningStage
    last_prompt: str
    expecting_response: str
    validation_rules: Dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3


class ConversationEngine:
    """Manages conversation flow and state transitions."""
    
    def __init__(self):
        """Initialize conversation engine."""
        self.stage_flow = self._define_stage_flow()
        self.stage_prompts = self._define_stage_prompts()
        self.validation_rules = self._define_validation_rules()
        
    def _define_stage_flow(self) -> Dict[PlanningStage, Dict[str, PlanningStage]]:
        """Define stage transitions based on user actions."""
        return {
            PlanningStage.INITIALIZATION: {
                'complete': PlanningStage.GOAL_SETTING,
                'skip': PlanningStage.GOAL_SETTING,
            },
            PlanningStage.GOAL_SETTING: {
                'complete': PlanningStage.FEATURE_DEFINITION,
                'back': PlanningStage.INITIALIZATION,
                'skip': PlanningStage.FEATURE_DEFINITION,
            },
            PlanningStage.FEATURE_DEFINITION: {
                'complete': PlanningStage.TECHNICAL_PLANNING,
                'back': PlanningStage.GOAL_SETTING,
                'skip': PlanningStage.TECHNICAL_PLANNING,
            },
            PlanningStage.TECHNICAL_PLANNING: {
                'complete': PlanningStage.TIMELINE_ESTIMATION,
                'back': PlanningStage.FEATURE_DEFINITION,
                'skip': PlanningStage.TIMELINE_ESTIMATION,
            },
            PlanningStage.TIMELINE_ESTIMATION: {
                'complete': PlanningStage.RESOURCE_PLANNING,
                'back': PlanningStage.TECHNICAL_PLANNING,
                'skip': PlanningStage.RESOURCE_PLANNING,
            },
            PlanningStage.RESOURCE_PLANNING: {
                'complete': PlanningStage.REVIEW,
                'back': PlanningStage.TIMELINE_ESTIMATION,
                'skip': PlanningStage.REVIEW,
            },
            PlanningStage.REVIEW: {
                'complete': PlanningStage.FINALIZATION,
                'back': PlanningStage.RESOURCE_PLANNING,
                'modify': PlanningStage.FEATURE_DEFINITION,  # Can jump back to any stage
            },
            PlanningStage.FINALIZATION: {
                'complete': None,  # End of flow
                'back': PlanningStage.REVIEW,
            }
        }
    
    def _define_stage_prompts(self) -> Dict[PlanningStage, List[Dict[str, str]]]:
        """Define conversation prompts for each stage."""
        return {
            PlanningStage.INITIALIZATION: [
                {
                    'prompt': "What type of project would you like to build?",
                    'expecting': 'project_type',
                    'help': "Examples: web app, mobile app, API, library, tool"
                },
                {
                    'prompt': "Can you describe your project vision in a few sentences?",
                    'expecting': 'project_description',
                    'help': "Tell me what problem it solves and who will use it"
                }
            ],
            PlanningStage.GOAL_SETTING: [
                {
                    'prompt': "What are the main goals for this project?",
                    'expecting': 'project_goals',
                    'help': "Think about what success looks like. List 2-5 key objectives."
                },
                {
                    'prompt': "How will you measure success for these goals?",
                    'expecting': 'success_metrics',
                    'help': "Consider metrics like user count, performance, revenue, etc."
                }
            ],
            PlanningStage.FEATURE_DEFINITION: [
                {
                    'prompt': "What are the must-have features for the MVP?",
                    'expecting': 'core_features',
                    'help': "List the essential features needed for the first version"
                },
                {
                    'prompt': "Are there any nice-to-have features for future versions?",
                    'expecting': 'future_features',
                    'help': "Features that would enhance the product but aren't critical"
                }
            ],
            PlanningStage.TECHNICAL_PLANNING: [
                {
                    'prompt': "What programming languages will you use?",
                    'expecting': 'languages',
                    'help': "E.g., Python, JavaScript, TypeScript, Go, etc."
                },
                {
                    'prompt': "What frameworks and libraries do you plan to use?",
                    'expecting': 'frameworks',
                    'help': "E.g., React, Django, FastAPI, Express, etc."
                },
                {
                    'prompt': "What database and infrastructure will you need?",
                    'expecting': 'infrastructure',
                    'help': "E.g., PostgreSQL, MongoDB, AWS, Docker, etc."
                }
            ],
            PlanningStage.TIMELINE_ESTIMATION: [
                {
                    'prompt': "What's your target completion date?",
                    'expecting': 'deadline',
                    'help': "When do you need the project completed?"
                },
                {
                    'prompt': "How would you like to break this into phases?",
                    'expecting': 'phases',
                    'help': "E.g., MVP in 2 months, v1.0 in 4 months, etc."
                }
            ],
            PlanningStage.RESOURCE_PLANNING: [
                {
                    'prompt': "Who will be working on this project?",
                    'expecting': 'team_members',
                    'help': "List team members and their roles"
                },
                {
                    'prompt': "What's your budget for this project?",
                    'expecting': 'budget',
                    'help': "Include development costs, tools, infrastructure, etc."
                }
            ]
        }
    
    def _define_validation_rules(self) -> Dict[str, Dict[str, Any]]:
        """Define validation rules for user inputs."""
        return {
            'project_type': {
                'min_length': 3,
                'max_length': 50,
                'pattern': r'^[a-zA-Z\s]+$'
            },
            'project_description': {
                'min_length': 20,
                'max_length': 500
            },
            'project_goals': {
                'min_items': 1,
                'max_items': 10,
                'item_min_length': 10
            },
            'core_features': {
                'min_items': 1,
                'max_items': 20,
                'item_min_length': 5
            },
            'languages': {
                'min_items': 1,
                'max_items': 10
            },
            'deadline': {
                'pattern': r'^\d{4}-\d{2}-\d{2}$|^\d+ (days?|weeks?|months?)$'
            }
        }
    
    def detect_intent(self, user_input: str, context: ConversationContext) -> IntentType:
        """Detect user intent from input."""
        user_input_lower = user_input.lower().strip()
        
        # Command detection
        if user_input_lower in ['cancel', 'quit', 'exit']:
            return IntentType.CANCEL
        elif user_input_lower in ['back', 'previous']:
            return IntentType.BACK
        elif user_input_lower in ['help', '?']:
            return IntentType.HELP
        elif user_input_lower in ['skip', 'next']:
            return IntentType.SKIP
        elif user_input_lower in ['done', 'complete', 'finish']:
            return IntentType.COMPLETE
        
        # Response type detection
        if user_input_lower in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay']:
            return IntentType.CONFIRM
        elif user_input_lower in ['no', 'nope', 'nah']:
            return IntentType.DENY
        
        # Question detection
        if '?' in user_input:
            return IntentType.ASK_QUESTION
        
        # Modification detection
        if any(word in user_input_lower for word in ['change', 'modify', 'update', 'edit']):
            return IntentType.MODIFY
        
        # Default to providing information
        return IntentType.PROVIDE_INFO
    
    def validate_input(self, user_input: str, expecting: str) -> Tuple[bool, Optional[str]]:
        """Validate user input based on expected response type."""
        rules = self.validation_rules.get(expecting, {})
        
        # Length validation
        if 'min_length' in rules and len(user_input) < rules['min_length']:
            return False, f"Input too short. Please provide at least {rules['min_length']} characters."
        
        if 'max_length' in rules and len(user_input) > rules['max_length']:
            return False, f"Input too long. Please limit to {rules['max_length']} characters."
        
        # Pattern validation
        if 'pattern' in rules:
            if not re.match(rules['pattern'], user_input):
                return False, "Invalid format. Please check your input."
        
        # List validation (for goals, features, etc.)
        if 'min_items' in rules:
            # Simple check for list items (lines or comma-separated)
            items = [item.strip() for item in re.split(r'[,\n]', user_input) if item.strip()]
            
            if len(items) < rules['min_items']:
                return False, f"Please provide at least {rules['min_items']} items."
            
            if 'max_items' in rules and len(items) > rules['max_items']:
                return False, f"Please limit to {rules['max_items']} items."
            
            if 'item_min_length' in rules:
                short_items = [item for item in items if len(item) < rules['item_min_length']]
                if short_items:
                    return False, f"Some items are too short. Each should be at least {rules['item_min_length']} characters."
        
        return True, None
    
    def extract_structured_data(self, user_input: str, expecting: str) -> Dict[str, Any]:
        """Extract structured data from user input."""
        data = {}
        
        if expecting == 'project_type':
            data['type'] = user_input.strip()
            
        elif expecting == 'project_description':
            data['description'] = user_input.strip()
            
        elif expecting == 'project_goals':
            # Extract goals as list
            goals = []
            for line in user_input.split('\n'):
                line = line.strip()
                if line:
                    # Remove common prefixes
                    line = re.sub(r'^[-*\d+\.]\s*', '', line)
                    if line:
                        goals.append({
                            'description': line,
                            'priority': self._detect_priority(line)
                        })
            data['goals'] = goals
            
        elif expecting == 'core_features':
            # Extract features
            features = []
            for line in user_input.split('\n'):
                line = line.strip()
                if line:
                    line = re.sub(r'^[-*\d+\.]\s*', '', line)
                    if line:
                        features.append({
                            'name': line[:50],
                            'description': line,
                            'priority': self._detect_priority(line),
                            'effort': self._detect_effort(line)
                        })
            data['features'] = features
            
        elif expecting == 'languages':
            # Extract programming languages
            languages = []
            # Split by common delimiters
            parts = re.split(r'[,\n]', user_input)
            for part in parts:
                lang = part.strip()
                if lang:
                    languages.append(lang)
            data['languages'] = languages
            
        elif expecting == 'deadline':
            data['deadline'] = user_input.strip()
            # Attempt to parse relative dates
            if 'month' in user_input.lower():
                match = re.search(r'(\d+)\s*months?', user_input.lower())
                if match:
                    data['deadline_months'] = int(match.group(1))
        
        return data
    
    def _detect_priority(self, text: str) -> str:
        """Detect priority from text."""
        text_lower = text.lower()
        if any(word in text_lower for word in ['critical', 'must', 'essential', 'high']):
            return 'high'
        elif any(word in text_lower for word in ['low', 'nice', 'optional']):
            return 'low'
        return 'medium'
    
    def _detect_effort(self, text: str) -> str:
        """Detect effort estimate from text."""
        text_lower = text.lower()
        if any(word in text_lower for word in ['simple', 'easy', 'quick', 'small']):
            return 'small'
        elif any(word in text_lower for word in ['complex', 'difficult', 'large', 'big']):
            return 'large'
        return 'medium'
    
    def generate_contextual_response(self, 
                                   intent: IntentType, 
                                   context: ConversationContext,
                                   validation_error: Optional[str] = None) -> str:
        """Generate appropriate response based on intent and context."""
        if intent == IntentType.HELP:
            current_prompt = self._get_current_prompt(context.current_stage, context.expecting_response)
            help_text = current_prompt.get('help', 'No additional help available.')
            return f"ℹ️ Help: {help_text}"
        
        elif intent == IntentType.CANCEL:
            return "Are you sure you want to cancel the planning session? (yes/no)"
        
        elif intent == IntentType.BACK:
            return "Going back to the previous stage..."
        
        elif intent == IntentType.SKIP:
            return "Skipping to the next stage..."
        
        elif validation_error:
            context.retry_count += 1
            if context.retry_count >= context.max_retries:
                return f"❌ {validation_error}\n\nLet's skip this for now. Type 'skip' to continue."
            return f"❌ {validation_error}\n\nPlease try again or type 'help' for assistance."
        
        # Generate stage-specific response
        return self._generate_stage_response(context)
    
    def _get_current_prompt(self, stage: PlanningStage, expecting: str) -> Dict[str, str]:
        """Get current prompt details."""
        stage_prompts = self.stage_prompts.get(stage, [])
        for prompt in stage_prompts:
            if prompt['expecting'] == expecting:
                return prompt
        return {}
    
    def _generate_stage_response(self, context: ConversationContext) -> str:
        """Generate response for current stage."""
        prompts = self.stage_prompts.get(context.current_stage, [])
        
        # Find the next prompt in the stage
        for i, prompt in enumerate(prompts):
            if prompt['expecting'] == context.expecting_response:
                # Check if there's a next prompt in this stage
                if i + 1 < len(prompts):
                    next_prompt = prompts[i + 1]
                    return next_prompt['prompt']
                else:
                    # Stage complete, move to next stage
                    return "Great! Let's move to the next stage."
        
        return "Let's continue with the planning."
    
    def handle_stage_transition(self, 
                              session: PlanningSession, 
                              action: str) -> Optional[PlanningStage]:
        """Handle stage transitions based on user actions."""
        current_stage = session.stage
        transitions = self.stage_flow.get(current_stage, {})
        
        next_stage = transitions.get(action)
        if next_stage is not None:
            logger.info(f"Transitioning from {current_stage.value} to {next_stage.value}")
            return next_stage
        
        return None
    
    def get_stage_progress(self, session: PlanningSession) -> Dict[str, Any]:
        """Get progress information for current stage."""
        total_stages = len(PlanningStage)
        current_index = list(PlanningStage).index(session.stage)
        
        return {
            'current_stage': session.stage.value,
            'current_index': current_index,
            'total_stages': total_stages,
            'percentage': int((current_index / total_stages) * 100),
            'completed_stages': [s.value for s in list(PlanningStage)[:current_index]],
            'remaining_stages': [s.value for s in list(PlanningStage)[current_index + 1:]]
        }
    
    def generate_stage_summary(self, session: PlanningSession, stage: PlanningStage) -> str:
        """Generate summary for a completed stage."""
        summaries = {
            PlanningStage.INITIALIZATION: 
                f"Project: {session.project_plan.name}\n" +
                f"Description: {session.project_plan.description}",
                
            PlanningStage.GOAL_SETTING:
                f"Goals defined: {len(session.project_plan.goals)}\n" +
                "\n".join([f"- {g.description}" for g in session.project_plan.goals[:3]]),
                
            PlanningStage.FEATURE_DEFINITION:
                f"Features defined: {len(session.project_plan.features)}\n" +
                "\n".join([f"- {f.name}" for f in session.project_plan.features[:3]]),
                
            PlanningStage.TECHNICAL_PLANNING:
                f"Tech stack defined:\n" +
                "\n".join([f"- {k}: {', '.join(v)}" for k, v in session.project_plan.tech_stack.items()]),
                
            PlanningStage.TIMELINE_ESTIMATION:
                f"Timeline defined:\n" +
                f"- Milestones: {len(session.project_plan.milestones)}\n" +
                f"- Estimated duration: {session.project_plan.timeline.get('total_duration', 'TBD')}",
                
            PlanningStage.RESOURCE_PLANNING:
                f"Resources planned:\n" +
                f"- Team size: {session.project_plan.resources.get('team_size', 'TBD')}\n" +
                f"- Budget: {session.project_plan.resources.get('budget', 'TBD')}"
        }
        
        return summaries.get(stage, f"Completed: {stage.value}")


if __name__ == "__main__":
    # Example usage
    engine = ConversationEngine()
    
    # Create sample context
    context = ConversationContext(
        current_stage=PlanningStage.GOAL_SETTING,
        last_prompt="What are the main goals for this project?",
        expecting_response="project_goals",
        validation_rules=engine.validation_rules
    )
    
    # Test intent detection
    test_inputs = [
        "I want to build a web app",
        "Can you help me?",
        "skip",
        "cancel",
        "yes"
    ]
    
    for input_text in test_inputs:
        intent = engine.detect_intent(input_text, context)
        print(f"Input: '{input_text}' -> Intent: {intent.value}")