"""
AI integration module for Velocitytree.
"""

import os
import json
import asyncio
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
import aiohttp
import openai
from anthropic import Anthropic
from rich.console import Console
from functools import wraps

from .config import Config
from .constants import AI_PROVIDERS
from .utils import logger, is_url
from .core import ContextManager

console = Console()


def retry_on_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to retry function calls on error with exponential backoff."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            wait_time = delay
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (ValueError, ConnectionError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        wait_time *= backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed.")
            
            raise last_exception
        return wrapper
    return decorator


class AIAssistant:
    """AI assistant for code analysis and generation."""
    
    def __init__(self, config: Config):
        self.config = config
        self.provider = config.config.ai.provider
        self.model = config.config.ai.model
        self.api_key = config.config.ai.api_key
        self.temperature = config.config.ai.temperature
        self.max_tokens = config.config.ai.max_tokens
        
        # Validate configuration
        self._validate_config()
        
        # Initialize provider client
        self._init_client()
    
    def _validate_config(self):
        """Validate AI configuration settings."""
        # Check if provider is supported
        if self.provider not in AI_PROVIDERS:
            raise ValueError(f"Unsupported AI provider: {self.provider}. Supported: {', '.join(AI_PROVIDERS.keys())}")
        
        # Check if model is supported for the provider
        provider_info = AI_PROVIDERS[self.provider]
        supported_models = provider_info.get('models', [])
        
        # For local models, we don't restrict model names
        if self.provider != 'local' and self.model not in supported_models:
            logger.warning(f"Model '{self.model}' may not be supported by {self.provider}. Supported models: {', '.join(supported_models)}")
        
        # Validate temperature
        if not 0 <= self.temperature <= 2:
            raise ValueError(f"Temperature must be between 0 and 2, got {self.temperature}")
        
        # Validate max_tokens
        if self.max_tokens <= 0:
            raise ValueError(f"Max tokens must be positive, got {self.max_tokens}")
        
        # Log configuration for debugging
        logger.debug(f"AI Configuration: provider={self.provider}, model={self.model}, temperature={self.temperature}, max_tokens={self.max_tokens}")
    
    def _init_client(self):
        """Initialize the AI provider client."""
        if self.provider == "openai":
            if not self.api_key:
                raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable or add to config.")
            openai.api_key = self.api_key
            if self.config.config.ai.base_url:
                openai.base_url = self.config.config.ai.base_url
            self.client = openai
        elif self.provider == "anthropic":
            if not self.api_key:
                raise ValueError("Anthropic API key not provided. Set ANTHROPIC_API_KEY environment variable or add to config.")
            self.client = Anthropic(api_key=self.api_key)
        elif self.provider == "local":
            # Local model initialization (e.g., Ollama)
            self.base_url = self.config.config.ai.base_url or "http://localhost:11434"
            self.client = None  # Will use aiohttp for local models
        else:
            raise ValueError(f"Unknown AI provider: {self.provider}. Supported: openai, anthropic, local")
    
    @retry_on_error(max_retries=3, delay=1.0)
    async def _call_openai(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call OpenAI API asynchronously."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Using the synchronous client for now (OpenAI's async support varies)
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
        except openai.error.AuthenticationError:
            raise ValueError("Invalid OpenAI API key. Please check your configuration.")
        except openai.error.RateLimitError:
            raise ValueError("OpenAI API rate limit exceeded. Please wait and try again.")
        except openai.error.InvalidRequestError as e:
            raise ValueError(f"Invalid request to OpenAI API: {str(e)}")
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    async def _call_anthropic(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call Anthropic API asynchronously."""
        try:
            # Prepare the prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\nHuman: {prompt}\n\nAssistant:"
            else:
                full_prompt = f"Human: {prompt}\n\nAssistant:"
            
            # Call Anthropic API
            response = self.client.completions.create(
                model=self.model,
                prompt=full_prompt,
                max_tokens_to_sample=self.max_tokens,
                temperature=self.temperature
            )
            
            return response.completion
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise ValueError(f"Anthropic API error: {str(e)}")
    
    @retry_on_error(max_retries=3, delay=1.0)
    async def _call_local(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Call local AI model (e.g., Ollama)."""
        import aiohttp
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["message"]["content"]
                    else:
                        error_text = await response.text()
                        raise ValueError(f"Local model API error: {error_text}")
        except aiohttp.ClientError as e:
            raise ValueError(f"Failed to connect to local model at {self.base_url}: {str(e)}")
        except Exception as e:
            logger.error(f"Local model API call failed: {e}")
            raise ValueError(f"Local model error: {str(e)}")
    
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text using the configured AI provider."""
        if self.provider == "openai":
            return await self._call_openai(prompt, system_prompt)
        elif self.provider == "anthropic":
            return await self._call_anthropic(prompt, system_prompt)
        elif self.provider == "local":
            return await self._call_local(prompt, system_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    def suggest(self, task: str, include_context: bool = False) -> str:
        """Get AI suggestions for a task."""
        prompt = f"Task: {task}\n"
        
        if include_context:
            context_manager = ContextManager()
            context = context_manager.generate_context(ai_ready=True)
            
            # Add project context intelligently
            project_summary = context.get('project_summary', '')
            key_files = context.get('key_files', [])
            
            prompt += f"\nProject: {context.get('context_data', {}).get('project_name', 'Unknown')}\n"
            prompt += f"Summary: {project_summary}\n"
            
            if key_files:
                prompt += f"Key Files: {', '.join(key_files[:5])}\n"
            
            # Add code structure summary
            code_summary = context.get('context_data', {}).get('code_summary', {})
            if code_summary:
                languages = list(code_summary.get('languages', {}).keys())
                if languages:
                    prompt += f"Primary Languages: {', '.join(languages)}\n"
        
        # Run async function in sync context
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If there's already a running loop, create a task
                task = asyncio.create_task(self.generate(prompt))
                response = asyncio.run_coroutine_threadsafe(task, loop).result()
            else:
                response = loop.run_until_complete(self.generate(prompt))
            
            return response
        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")
            raise
    
    def analyze_code(self, file_path: Path, analysis_type: str = "general") -> Dict[str, Any]:
        """Analyze code file using AI."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        code_content = file_path.read_text()
        file_type = file_path.suffix
        
        prompts = {
            "general": f"Analyze this {file_type} code and provide insights, potential issues, and suggestions for improvement:\n\n{code_content}",
            "security": f"Analyze this {file_type} code for security vulnerabilities and provide recommendations:\n\n{code_content}",
            "performance": f"Analyze this {file_type} code for performance issues and optimization opportunities:\n\n{code_content}",
            "refactor": f"Suggest refactoring improvements for this {file_type} code:\n\n{code_content}",
            "documentation": f"Generate documentation for this {file_type} code:\n\n{code_content}",
        }
        
        prompt = prompts.get(analysis_type, prompts["general"])
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return {
            "file": str(file_path),
            "analysis_type": analysis_type,
            "response": response
        }
    
    def generate_code(self, description: str, language: str = "python", context: Optional[Dict[str, Any]] = None) -> str:
        """Generate code based on description."""
        prompt = f"Generate {language} code for the following requirement:\n{description}\n"
        
        if context:
            prompt += f"\nContext:\n{json.dumps(context, indent=2)}\n"
        
        prompt += f"\nPlease provide clean, well-documented {language} code:"
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def explain_code(self, code: str, language: Optional[str] = None) -> str:
        """Explain code in detail."""
        prompt = "Explain the following code in detail, including what it does, how it works, and any important considerations:\n\n"
        
        if language:
            prompt += f"Language: {language}\n\n"
        
        prompt += code
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def optimize_code(self, code: str, optimization_goal: str = "general") -> str:
        """Optimize code based on specific goals."""
        goals = {
            "general": "Optimize this code for general improvements including readability, efficiency, and best practices",
            "performance": "Optimize this code for maximum performance",
            "memory": "Optimize this code for minimal memory usage",
            "readability": "Refactor this code for maximum readability and maintainability",
            "async": "Convert this code to use async/await patterns where appropriate",
        }
        
        prompt = f"{goals.get(optimization_goal, goals['general'])}:\n\n{code}\n\nProvide the optimized version:"
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def create_tests(self, code: str, test_framework: str = "pytest") -> str:
        """Generate tests for given code."""
        prompt = f"Generate comprehensive unit tests for the following code using {test_framework}:\n\n{code}\n\nInclude edge cases and error handling:"
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def fix_errors(self, code: str, error_message: str) -> str:
        """Fix code based on error message."""
        prompt = f"""Fix the following code that produces this error:

Error: {error_message}

Code:
{code}

Provide the corrected code:"""
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def translate_code(self, code: str, from_language: str, to_language: str) -> str:
        """Translate code from one language to another."""
        prompt = f"Translate the following {from_language} code to {to_language}:\n\n{code}\n\nProvide equivalent {to_language} code:"
        
        loop = asyncio.get_event_loop()
        response = loop.run_until_complete(self.generate(prompt))
        
        return response
    
    def chat(self, message: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Chat with AI assistant about the project."""
        try:
            # Add system prompt
            context_manager = ContextManager()
            context = context_manager.generate_context(ai_ready=True)
            system_prompt = context.get('system_prompt', '')
            
            # For provider-specific handling, prepare appropriate messages
            if self.provider == "openai":
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                
                # Add conversation history
                if conversation_history:
                    messages.extend(conversation_history)
                
                # Add current message
                messages.append({"role": "user", "content": message})
                
                # Get response using synchronous call
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
            else:
                # For other providers, use the generate method
                # Combine conversation history into a single prompt
                full_prompt = ""
                if conversation_history:
                    for msg in conversation_history:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        full_prompt += f"{role.capitalize()}: {content}\n"
                
                full_prompt += f"User: {message}"
                
                # Run async function in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    task = asyncio.create_task(self.generate(full_prompt, system_prompt))
                    response = asyncio.run_coroutine_threadsafe(task, loop).result()
                else:
                    response = loop.run_until_complete(self.generate(full_prompt, system_prompt))
                
                return response
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            raise ValueError(f"Failed to chat with AI: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test the AI connection with a simple prompt."""
        try:
            response = self.generate("Hello, can you hear me?")
            logger.info(f"AI connection test successful. Response: {response[:50]}...")
            return True
        except Exception as e:
            logger.error(f"AI connection test failed: {e}")
            return False
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about the current AI provider configuration."""
        return {
            "provider": self.provider,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key_configured": bool(self.api_key),
            "supported_models": AI_PROVIDERS.get(self.provider, {}).get('models', [])
        }