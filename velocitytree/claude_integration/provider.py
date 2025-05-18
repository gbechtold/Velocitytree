"""Local Claude provider for AI processing."""

import subprocess
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import shutil

from ..utils import logger


@dataclass
class ClaudeConfig:
    """Configuration for Claude integration."""
    model: str = "claude-3.5-sonnet"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    fallback_model: Optional[str] = None
    use_cache: bool = True
    cache_ttl: int = 3600  # seconds
    stream_response: bool = False
    env_vars: Dict[str, str] = field(default_factory=dict)


class LocalClaudeProvider:
    """Interface to Claude CLI for local AI processing."""
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        """Initialize Claude provider.
        
        Args:
            config: Claude configuration
        """
        self.config = config or ClaudeConfig()
        self._cli_path = self._find_claude_cli()
        self._validate_setup()
        
        # Initialize cache if enabled
        if self.config.use_cache:
            from .cache import ResponseCache
            self.cache = ResponseCache(ttl=self.config.cache_ttl)
        else:
            self.cache = None
    
    def _find_claude_cli(self) -> Optional[Path]:
        """Find Claude CLI executable."""
        # Check common locations
        locations = [
            "claude",  # In PATH
            "/usr/local/bin/claude",
            "~/.claude/bin/claude",
            "~/claude/claude",
        ]
        
        for location in locations:
            if location.startswith("~"):
                location = Path.home() / location[2:]
            else:
                location = Path(location)
            
            if shutil.which(str(location)):
                return location
        
        # Try to find via shell command
        try:
            result = subprocess.run(
                ["which", "claude"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except Exception:
            pass
        
        return None
    
    def _validate_setup(self):
        """Validate Claude CLI setup."""
        if not self._cli_path:
            raise RuntimeError(
                "Claude CLI not found. Please install Claude CLI or "
                "ensure it's in your PATH"
            )
        
        # Check if CLI is executable
        if not shutil.which(str(self._cli_path)):
            raise RuntimeError(
                f"Claude CLI at {self._cli_path} is not executable"
            )
        
        # Verify authentication
        try:
            result = subprocess.run(
                [str(self._cli_path), "auth", "check"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.warning(
                    "Claude CLI authentication may not be configured. "
                    "Run 'claude auth login' to authenticate."
                )
        except subprocess.TimeoutExpired:
            logger.warning("Claude CLI auth check timed out")
        except Exception as e:
            logger.warning(f"Failed to check Claude auth: {e}")
    
    def query(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[Path]] = None
    ) -> str:
        """Query Claude with prompt and optional context.
        
        Args:
            prompt: The prompt to send to Claude
            context: Additional context data
            files: Files to include in context
            
        Returns:
            Claude's response
        """
        # Check cache first
        cache_key = self._generate_cache_key(prompt, context, files)
        if self.cache:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                logger.debug("Using cached response")
                return cached_response
        
        # Prepare command
        cmd = self._build_command(prompt, context, files)
        
        # Execute with retries
        for attempt in range(self.config.retry_attempts):
            try:
                response = self._execute_command(cmd)
                
                # Cache successful response
                if self.cache:
                    self.cache.set(cache_key, response)
                
                return response
                
            except Exception as e:
                logger.warning(
                    f"Claude query failed (attempt {attempt + 1}): {e}"
                )
                
                if attempt < self.config.retry_attempts - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
                else:
                    # Last attempt failed, try fallback
                    if self.config.fallback_model:
                        return self._fallback_query(prompt, context, files)
                    raise
        
        return ""
    
    def stream_query(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[Path]] = None
    ) -> Any:
        """Stream Claude response for large contexts.
        
        Args:
            prompt: The prompt to send to Claude
            context: Additional context data
            files: Files to include in context
            
        Yields:
            Response chunks
        """
        cmd = self._build_command(prompt, context, files, stream=True)
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._get_env()
            )
            
            # Stream output
            for line in process.stdout:
                if line.strip():
                    try:
                        data = json.loads(line)
                        if "chunk" in data:
                            yield data["chunk"]
                    except json.JSONDecodeError:
                        yield line.strip()
            
            process.wait()
            
            if process.returncode != 0:
                error = process.stderr.read()
                raise RuntimeError(f"Claude command failed: {error}")
                
        except Exception as e:
            logger.error(f"Streaming query failed: {e}")
            raise
    
    def _build_command(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[Path]] = None,
        stream: bool = False
    ) -> List[str]:
        """Build Claude CLI command."""
        cmd = [str(self._cli_path)]
        
        # Add model
        cmd.extend(["--model", self.config.model])
        
        # Add parameters
        cmd.extend(["--max-tokens", str(self.config.max_tokens)])
        cmd.extend(["--temperature", str(self.config.temperature)])
        
        # Add streaming flag
        if stream or self.config.stream_response:
            cmd.append("--stream")
        
        # Add context files
        if files:
            for file_path in files:
                if file_path.exists():
                    cmd.extend(["--file", str(file_path)])
        
        # Add context as system message
        if context:
            context_str = json.dumps(context)
            cmd.extend(["--system", f"Context: {context_str}"])
        
        # Add prompt
        cmd.append(prompt)
        
        return cmd
    
    def _execute_command(self, cmd: List[str]) -> str:
        """Execute Claude command and return response."""
        logger.debug(f"Executing: {' '.join(cmd[:3])}...")  # Log first few args
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.timeout,
            env=self._get_env()
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise RuntimeError(f"Claude command failed: {error_msg}")
        
        return result.stdout.strip()
    
    def _get_env(self) -> Dict[str, str]:
        """Get environment variables for subprocess."""
        import os
        env = os.environ.copy()
        env.update(self.config.env_vars)
        return env
    
    def _generate_cache_key(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[Path]] = None
    ) -> str:
        """Generate cache key for request."""
        import hashlib
        
        key_parts = [prompt]
        
        if context:
            key_parts.append(json.dumps(context, sort_keys=True))
        
        if files:
            for file_path in sorted(files):
                if file_path.exists():
                    # Include file modification time
                    mtime = file_path.stat().st_mtime
                    key_parts.append(f"{file_path}:{mtime}")
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _fallback_query(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        files: Optional[List[Path]] = None
    ) -> str:
        """Fallback query using alternative model or method."""
        logger.info(f"Attempting fallback with {self.config.fallback_model}")
        
        # Try with fallback model
        if self.config.fallback_model:
            original_model = self.config.model
            self.config.model = self.config.fallback_model
            
            try:
                response = self.query(prompt, context, files)
                return response
            finally:
                self.config.model = original_model
        
        # If no fallback, return error message
        return "Unable to process request. Claude service is unavailable."
    
    def validate_response(self, response: str) -> bool:
        """Validate Claude's response."""
        if not response or not response.strip():
            return False
        
        # Check for common error patterns
        error_patterns = [
            "error:",
            "failed to",
            "could not",
            "unable to",
            "invalid",
        ]
        
        response_lower = response.lower()
        for pattern in error_patterns:
            if pattern in response_lower[:100]:  # Check first 100 chars
                return False
        
        return True
    
    def format_context(self, context: Dict[str, Any]) -> str:
        """Format context for Claude."""
        formatted_parts = []
        
        for key, value in context.items():
            if isinstance(value, dict):
                value_str = json.dumps(value, indent=2)
            elif isinstance(value, list):
                value_str = "\n".join(str(item) for item in value)
            else:
                value_str = str(value)
            
            formatted_parts.append(f"{key}:\n{value_str}")
        
        return "\n\n".join(formatted_parts)
    
    def health_check(self) -> Dict[str, Any]:
        """Check Claude provider health."""
        health = {
            "available": False,
            "cli_path": str(self._cli_path) if self._cli_path else None,
            "authenticated": False,
            "model": self.config.model,
            "cache_enabled": self.config.use_cache,
        }
        
        if not self._cli_path:
            health["error"] = "Claude CLI not found"
            return health
        
        # Check CLI availability
        try:
            result = subprocess.run(
                [str(self._cli_path), "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                health["available"] = True
                health["version"] = result.stdout.strip()
        except Exception as e:
            health["error"] = str(e)
        
        # Check authentication
        try:
            result = subprocess.run(
                [str(self._cli_path), "auth", "check"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                health["authenticated"] = True
        except Exception:
            pass
        
        # Check cache
        if self.cache:
            health["cache_size"] = len(self.cache)
        
        return health