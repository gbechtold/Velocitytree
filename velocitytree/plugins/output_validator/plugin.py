"""Output Validator Plugin for Velocitytree."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from velocitytree.plugin_system import Plugin


class OutputValidatorPlugin(Plugin):
    """Plugin that validates generated output against configurable rules."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self._config = {
            'max_file_size_mb': 10,
            'allowed_extensions': [
                '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h',
                '.md', '.txt', '.json', '.yaml', '.yml', '.toml'
            ],
            'encoding_check': True,
            'validate_syntax': False
        }
        self.validation_errors = []
    
    @property
    def name(self) -> str:
        return "output_validator"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Validates generated code context against configurable rules"
    
    def activate(self):
        """Activate the plugin with configuration."""
        super().activate()
        # Get plugin configuration from config if available
        if self.config and hasattr(self.config, 'config_data'):
            plugin_config = self.config.config_data.get('plugins', {}).get('output_validator', {})
            self._config.update(plugin_config)
        self.logger.info(f"Output validator activated with config: {self._config}")
    
    def validate_file(self, file_path: Path) -> List[str]:
        """Validate a single file."""
        errors = []
        
        # Check file exists
        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
            return errors
        
        # Check file extension
        if self._config['allowed_extensions']:
            if file_path.suffix not in self._config['allowed_extensions']:
                errors.append(f"Unsupported file extension: {file_path.suffix}")
        
        # Check file size
        max_size = self._config['max_file_size_mb'] * 1024 * 1024  # Convert to bytes
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            errors.append(f"File too large: {file_path} ({file_size} bytes)")
        
        # Check encoding
        if self._config['encoding_check']:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError:
                errors.append(f"Invalid UTF-8 encoding: {file_path}")
        
        # Validate syntax if enabled
        if self._config['validate_syntax']:
            if file_path.suffix == '.json':
                try:
                    with open(file_path, 'r') as f:
                        json.load(f)
                except json.JSONDecodeError as e:
                    errors.append(f"Invalid JSON syntax in {file_path}: {e}")
            elif file_path.suffix == '.py':
                try:
                    with open(file_path, 'r') as f:
                        compile(f.read(), file_path, 'exec')
                except SyntaxError as e:
                    errors.append(f"Invalid Python syntax in {file_path}: {e}")
        
        return errors
    
    def register_hooks(self, hook_manager):
        """Register validation hooks."""
        def validate_output(output_path: Path, **kwargs):
            """Validate the generated output."""
            self.validation_errors.clear()
            
            if output_path.is_file():
                errors = self.validate_file(output_path)
                if errors:
                    self.validation_errors.extend(errors)
                    for error in errors:
                        self.logger.error(error)
            elif output_path.is_dir():
                for file_path in output_path.rglob('*'):
                    if file_path.is_file():
                        errors = self.validate_file(file_path)
                        if errors:
                            self.validation_errors.extend(errors)
                            for error in errors:
                                self.logger.error(error)
            
            if self.validation_errors:
                self.logger.error(f"Validation failed with {len(self.validation_errors)} errors")
            else:
                self.logger.info("Output validation passed")
        
        def report_validation_errors(**kwargs):
            """Report validation errors at the end."""
            if self.validation_errors:
                self.logger.error("Validation Summary:")
                for error in self.validation_errors:
                    self.logger.error(f"  - {error}")
        
        # Register hooks
        hook_manager.register_hook('flatten_complete', validate_output)
        hook_manager.register_hook('after_command', report_validation_errors)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status with validation error count."""
        status = super().get_health_status()
        status['validation_errors'] = len(self.validation_errors)
        return status