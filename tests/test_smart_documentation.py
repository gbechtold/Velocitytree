"""Test smart documentation generation with template selection."""

import pytest
import tempfile
from pathlib import Path

from velocitytree.documentation import DocGenerator, DocConfig, DocFormat, DocType


@pytest.fixture
def doc_generator():
    """Create a documentation generator with default config."""
    config = DocConfig(format=DocFormat.MARKDOWN)
    return DocGenerator(config)


class TestSmartDocumentation:
    """Test smart documentation generation."""
    
    def test_automatic_template_selection(self, doc_generator):
        """Test automatic template selection based on code."""
        # Create a CLI tool
        code = '''
"""Command-line tool for file processing."""

import click
import os

@click.command()
@click.argument('filename', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file')
def process_file(filename, output):
    """Process a file and generate output.
    
    Args:
        filename: Input file path
        output: Output file path (optional)
    """
    click.echo(f"Processing {filename}")
    
    with open(filename, 'r') as f:
        content = f.read()
        
    # Process content
    processed = content.upper()
    
    if output:
        with open(output, 'w') as f:
            f.write(processed)
        click.echo(f"Written to {output}")
    else:
        click.echo(processed)
        
if __name__ == '__main__':
    process_file()
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate documentation with smart selection
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=True,
            )
            
            assert result is not None
            assert result.content
            assert "Command-line tool" in result.content
            
            # Check if template was selected intelligently
            assert hasattr(result, 'metadata')
            
        finally:
            temp_path.unlink()
            
    def test_api_module_detection(self, doc_generator):
        """Test API module detection and template selection."""
        # Create an API module
        code = '''
"""RESTful API for user management."""

from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# In-memory user storage
users = {}

@app.route('/api/users', methods=['GET'])
def get_users():
    """Get all users.
    
    Returns:
        JSON list of users
    """
    return jsonify(list(users.values()))
    
@app.route('/api/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user.
    
    Args:
        user_id: User ID
        
    Returns:
        User data or 404
    """
    user = users.get(user_id)
    if user:
        return jsonify(user)
    return jsonify({"error": "User not found"}), 404
    
@app.route('/api/users', methods=['POST'])
def create_user():
    """Create a new user.
    
    Request body should contain:
        - username: str
        - email: str
        - password: str
        
    Returns:
        Created user data
    """
    data = request.get_json()
    user_id = str(len(users) + 1)
    
    user = {
        'id': user_id,
        'username': data['username'],
        'email': data['email'],
        'password_hash': generate_password_hash(data['password'])
    }
    
    users[user_id] = user
    return jsonify(user), 201
    
if __name__ == '__main__':
    app.run(debug=True)
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate documentation
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=True,
            )
            
            assert result is not None
            assert "API" in result.content or "api" in result.content
            assert "users" in result.content
            
        finally:
            temp_path.unlink()
            
    def test_library_module_detection(self, doc_generator):
        """Test library module detection."""
        # Create a library-style module
        code = '''
"""Utility library for string manipulation.

This module provides various string manipulation functions
for common text processing tasks.
"""

import re
from typing import List, Optional

__version__ = "1.0.0"
__author__ = "VelocityTree Team"


def camel_to_snake(text: str) -> str:
    """Convert camelCase to snake_case.
    
    Args:
        text: Input string in camelCase
        
    Returns:
        String converted to snake_case
        
    Examples:
        >>> camel_to_snake("CamelCase")
        'camel_case'
        >>> camel_to_snake("HTTPResponse")
        'http_response'
    """
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', text)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    
def snake_to_camel(text: str, pascal_case: bool = False) -> str:
    """Convert snake_case to camelCase or PascalCase.
    
    Args:
        text: Input string in snake_case
        pascal_case: If True, return PascalCase instead of camelCase
        
    Returns:
        String converted to camelCase or PascalCase
    """
    components = text.split('_')
    
    if pascal_case:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])
        
        
def pluralize(word: str) -> str:
    """Simple pluralization of English words.
    
    Args:
        word: Singular word
        
    Returns:
        Pluralized word
        
    Note:
        This is a simple implementation and doesn't handle all edge cases.
    """
    if word.endswith('y'):
        return word[:-1] + 'ies'
    elif word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return word + 'es'
    else:
        return word + 's'
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate documentation
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=True,
            )
            
            assert result is not None
            assert "__version__" in result.content or "1.0.0" in result.content
            assert "string manipulation" in result.content.lower()
            
        finally:
            temp_path.unlink()
            
    def test_style_detection_influence(self, doc_generator):
        """Test that detected docstring style influences template selection."""
        # Create module with NumPy style docstrings
        code = '''
"""Module with NumPy style documentation."""

import numpy as np


def calculate_mean(data):
    """
    Calculate the mean of a dataset.
    
    Parameters
    ----------
    data : array_like
        Input data
        
    Returns
    -------
    float
        The mean value
        
    Examples
    --------
    >>> calculate_mean([1, 2, 3, 4, 5])
    3.0
    """
    return np.mean(data)
    
    
class Statistics:
    """
    Statistical calculations class.
    
    Attributes
    ----------
    data : array_like
        The dataset to analyze
    """
    
    def __init__(self, data):
        """
        Initialize with data.
        
        Parameters
        ----------
        data : array_like
            Input dataset
        """
        self.data = np.array(data)
        
    def std(self):
        """
        Calculate standard deviation.
        
        Returns
        -------
        float
            Standard deviation of the data
        """
        return np.std(self.data)
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate documentation
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=True,
            )
            
            assert result is not None
            # Should maintain NumPy style formatting
            assert "Parameters" in result.content or "parameters" in result.content.lower()
            
        finally:
            temp_path.unlink()
            
    def test_disable_smart_selection(self, doc_generator):
        """Test disabling smart template selection."""
        code = '''
"""Simple module."""

def hello():
    """Say hello."""
    print("Hello!")
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate without smart selection
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=False,
            )
            
            assert result is not None
            assert result.content
            
        finally:
            temp_path.unlink()
            
    def test_context_based_selection(self, doc_generator):
        """Test template selection with additional context."""
        code = '''
"""Data model for user management."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User data model.
    
    Attributes:
        id: Unique user ID
        username: User's username
        email: User's email address
        is_active: Whether the user is active
    """
    id: int
    username: str
    email: str
    is_active: bool = True
    
    def deactivate(self):
        """Deactivate the user."""
        self.is_active = False
        
    def activate(self):
        """Activate the user."""
        self.is_active = True
        
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active
        }
'''
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = Path(f.name)
            
        try:
            # Generate with context hints
            result = doc_generator.generate_documentation(
                source=temp_path,
                doc_type=DocType.MODULE,
                smart_selection=True,
            )
            
            assert result is not None
            assert "@dataclass" in result.content or "dataclass" in result.content.lower()
            assert "User" in result.content
            
        finally:
            temp_path.unlink()