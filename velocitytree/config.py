"""
Configuration management for Velocitytree.
"""

import os
import yaml
import toml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from .constants import CONFIG_FILES, DEFAULT_CONFIG
from .utils import logger, merge_dicts


class ProjectConfig(BaseModel):
    """Project configuration model."""
    name: str = Field(default="My Project")
    version: str = Field(default="0.1.0")
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None


class FlattenConfig(BaseModel):
    """Flatten operation configuration."""
    output_dir: str = Field(default="tamed_tree")
    exclude: list = Field(default_factory=list)
    include_extensions: list = Field(default_factory=list)
    preserve_structure: bool = Field(default=False)
    follow_symlinks: bool = Field(default=False)


class AIConfig(BaseModel):
    """AI integration configuration."""
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4")
    api_key: Optional[str] = None
    temperature: float = Field(default=0.7)
    max_tokens: int = Field(default=2000)
    base_url: Optional[str] = None


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: Optional[str] = None


class VelocitytreeConfig(BaseModel):
    """Main configuration model."""
    project: ProjectConfig = Field(default_factory=ProjectConfig)
    flatten: FlattenConfig = Field(default_factory=FlattenConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    workflows: Dict[str, Any] = Field(default_factory=dict)
    plugins: list = Field(default_factory=list)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)


class Config:
    """Configuration manager for Velocitytree."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config_data = self._load_config()
        self.config = VelocitytreeConfig(**self.config_data)
        self._apply_environment_overrides()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find configuration file in current directory or parent directories."""
        current_dir = Path.cwd()
        
        # Check current directory and parents
        for parent in [current_dir] + list(current_dir.parents):
            for config_name in CONFIG_FILES:
                config_path = parent / config_name
                if config_path.exists():
                    logger.debug(f"Found config file: {config_path}")
                    return config_path
        
        return None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        # Start with default configuration
        config = DEFAULT_CONFIG.copy()
        
        # Find config file
        if self.config_file:
            config_path = Path(self.config_file)
        else:
            config_path = self._find_config_file()
        
        if not config_path or not config_path.exists():
            logger.debug("No config file found, using defaults")
            return config
        
        # Load config based on file extension
        try:
            if config_path.suffix in ['.yaml', '.yml']:
                with open(config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}
            elif config_path.suffix == '.toml':
                with open(config_path, 'r') as f:
                    file_config = toml.load(f)
            elif config_path.suffix == '.json':
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
            else:
                logger.warning(f"Unknown config file format: {config_path}")
                return config
            
            # Merge with defaults
            config = merge_dicts(config, file_config)
            logger.info(f"Loaded config from: {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
        
        return config
    
    def _apply_environment_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Override AI API key from environment
        if not self.config.ai.api_key:
            env_key = f"{self.config.ai.provider.upper()}_API_KEY"
            api_key = os.getenv(env_key)
            if api_key:
                self.config.ai.api_key = api_key
        
        # Override project name from environment
        project_name = os.getenv('VELOCITYTREE_PROJECT_NAME')
        if project_name:
            self.config.project.name = project_name
        
        # Override log level from environment
        log_level = os.getenv('VELOCITYTREE_LOG_LEVEL')
        if log_level:
            self.config.logging.level = log_level
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot-notation key."""
        keys = key.split('.')
        config_dict = self.config_data
        
        for k in keys[:-1]:
            if k not in config_dict:
                config_dict[k] = {}
            config_dict = config_dict[k]
        
        config_dict[keys[-1]] = value
        
        # Recreate config object
        self.config = VelocitytreeConfig(**self.config_data)
    
    def save(self, path: Optional[str] = None):
        """Save configuration to file."""
        if path:
            save_path = Path(path)
        else:
            save_path = self.config_file or Path('.velocitytree.yaml')
        
        # Determine format from extension
        if save_path.suffix in ['.yaml', '.yml']:
            with open(save_path, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
        elif save_path.suffix == '.toml':
            with open(save_path, 'w') as f:
                toml.dump(self.config_data, f)
        elif save_path.suffix == '.json':
            with open(save_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        else:
            # Default to YAML
            save_path = save_path.with_suffix('.yaml')
            with open(save_path, 'w') as f:
                yaml.dump(self.config_data, f, default_flow_style=False)
        
        logger.info(f"Configuration saved to: {save_path}")
    
    def validate(self) -> bool:
        """Validate configuration."""
        try:
            # Pydantic automatically validates on instantiation
            VelocitytreeConfig(**self.config_data)
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    @classmethod
    def create_default(cls, path: str = '.velocitytree.yaml'):
        """Create a default configuration file."""
        config = cls()
        config.save(path)
        return config
    
    def merge_cli_options(self, cli_options: Dict[str, Any]) -> 'Config':
        """Merge command-line options with configuration.
        
        Args:
            cli_options: Dictionary of CLI options to merge
            
        Returns:
            Updated Config instance
        """
        # Deep merge CLI options with existing config
        for key, value in cli_options.items():
            if value is not None:  # Only override if value is provided
                self.set(key, value)
        
        return self
    
    def get_flatten_config(self, **cli_overrides) -> FlattenConfig:
        """Get flatten configuration with CLI overrides.
        
        Args:
            **cli_overrides: Command-line overrides for flatten config
            
        Returns:
            FlattenConfig instance with applied overrides
        """
        config = self.config.flatten.dict()
        
        # Apply CLI overrides
        for key, value in cli_overrides.items():
            if value is not None:
                config[key] = value
        
        return FlattenConfig(**config)