"""Test integration of security analysis with the main code analyzer."""

import pytest
from pathlib import Path
from velocitytree.code_analysis.analyzer import CodeAnalyzer
from velocitytree.code_analysis.models import IssueCategory, Severity


@pytest.fixture
def analyzer():
    """Create a code analyzer with security enabled."""
    return CodeAnalyzer()


def test_security_issues_in_module_analysis(analyzer, tmp_path):
    """Test that security vulnerabilities are included in module analysis."""
    test_file = tmp_path / "vulnerable.py"
    test_file.write_text('''
import os
import pickle

# Hardcoded password
password = "super_secret_password"

def dangerous_function(user_input):
    # Command injection vulnerability
    os.system("echo " + user_input)
    
    # SQL injection vulnerability
    query = "SELECT * FROM users WHERE id = %s" % user_input
    
    # Insecure deserialization
    data = pickle.loads(user_input)
    
    return data
''')
    
    module_analysis = analyzer.analyze_file(test_file)
    
    assert module_analysis is not None
    assert len(module_analysis.issues) > 0
    
    # Check for security issues
    security_issues = [issue for issue in module_analysis.issues 
                      if issue.category == IssueCategory.SECURITY]
    
    assert len(security_issues) >= 3  # At least command injection, SQL injection, hardcoded password
    
    # Check issue details
    issue_types = {issue.rule_id for issue in security_issues}
    assert any('command_injection' in rule for rule in issue_types)
    assert any('hardcoded_credentials' in rule for rule in issue_types)
    
    # Check severity levels
    critical_issues = [issue for issue in security_issues 
                      if issue.severity == Severity.CRITICAL]
    assert len(critical_issues) >= 2  # Command injection and hardcoded credentials should be critical


def test_directory_analysis_with_security(analyzer, tmp_path):
    """Test directory analysis includes security vulnerabilities."""
    # Create multiple files with different vulnerabilities
    (tmp_path / "auth.py").write_text('''
import hashlib

def authenticate(username, password):
    # Weak hashing algorithm
    password_hash = hashlib.md5(password.encode()).hexdigest()
    
    # Hardcoded admin password
    if username == "admin" and password == "admin123":
        return True
    
    return check_database(username, password_hash)
''')
    
    (tmp_path / "data_processor.py").write_text('''
import pickle
import random

def process_data(data):
    # Insecure deserialization
    obj = pickle.loads(data)
    
    # Insecure random for tokens
    token = ''.join(random.choice('0123456789abcdef') for _ in range(32))
    
    return obj, token
''')
    
    (tmp_path / "commands.py").write_text('''
import os
import subprocess

def run_user_command(cmd):
    # Command injection
    result = subprocess.call("ls " + cmd, shell=True)
    
    # Another command injection
    os.system(f"echo {cmd}")
    
    return result
''')
    
    result = analyzer.analyze_directory(tmp_path)
    
    assert result.files_analyzed >= 3
    
    # Collect all security issues
    all_security_issues = []
    for module in result.modules:
        security_issues = [issue for issue in module.issues 
                          if issue.category == IssueCategory.SECURITY]
        all_security_issues.extend(security_issues)
    
    assert len(all_security_issues) >= 5
    
    # Check for various vulnerability types
    issue_messages = {issue.message for issue in all_security_issues}
    assert any('command injection' in msg.lower() for msg in issue_messages)
    assert any('weak encryption' in msg.lower() or 'weak hash' in msg.lower() for msg in issue_messages)
    assert any('hardcoded' in msg.lower() for msg in issue_messages)
    assert any('insecure deserialization' in msg.lower() or 'pickle' in msg.lower() for msg in issue_messages)


def test_caching_with_security_updates(analyzer, tmp_path):
    """Test that cache is properly updated when security vulnerabilities change."""
    test_file = tmp_path / "evolving.py"
    
    # Initial version with one vulnerability
    test_file.write_text('''
password = "hardcoded123"

def process(data):
    return data.upper()
''')
    
    analysis1 = analyzer.analyze_file(test_file)
    security_issues1 = [issue for issue in analysis1.issues 
                       if issue.category == IssueCategory.SECURITY]
    initial_count = len(security_issues1)
    
    # Update file to add more vulnerabilities
    test_file.write_text('''
import os
import pickle

password = "hardcoded123"
api_key = "sk-1234567890"

def process(data):
    # Add command injection
    os.system("echo " + data)
    
    # Add insecure deserialization
    return pickle.loads(data)
''')
    
    analysis2 = analyzer.analyze_file(test_file)
    security_issues2 = [issue for issue in analysis2.issues 
                       if issue.category == IssueCategory.SECURITY]
    updated_count = len(security_issues2)
    
    assert updated_count > initial_count
    assert updated_count >= 3  # Should find all the new vulnerabilities


def test_mixed_issues_and_vulnerabilities(analyzer, tmp_path):
    """Test that both code quality issues and security vulnerabilities are reported."""
    test_file = tmp_path / "mixed_issues.py"
    test_file.write_text('''
import os

# Security issue: hardcoded password
password = "secret123"

def very_long_function_with_multiple_issues(user_input):
    """This function has both security and quality issues."""
    # Security issue: command injection
    os.system("echo " + user_input)
    
    # Code quality issue: very long function (simulate with comments)
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    # Line 32
    # Line 33
    # Line 34
    # Line 35
    # Line 36
    # Line 37
    # Line 38
    # Line 39
    # Line 40
    # Line 41
    # Line 42
    # Line 43
    # Line 44
    # Line 45
    # Line 46
    # Line 47
    # Line 48
    # Line 49
    # Line 50
    # Line 51
    # Line 52
    # Line 53
    # Line 54
    # Line 55
    
    return "Done"
''')
    
    analysis = analyzer.analyze_file(test_file)
    
    # Should have both security and maintainability issues
    security_issues = [issue for issue in analysis.issues 
                      if issue.category == IssueCategory.SECURITY]
    quality_issues = [issue for issue in analysis.issues 
                     if issue.category == IssueCategory.MAINTAINABILITY]
    
    assert len(security_issues) >= 2  # Hardcoded password and command injection
    assert len(quality_issues) >= 1   # Long function
    
    # Total issues should include both types
    assert len(analysis.issues) >= 3


def test_confidence_levels_in_security_issues(analyzer, tmp_path):
    """Test that security issues have appropriate confidence levels."""
    test_file = tmp_path / "confidence_test.py"
    test_file.write_text('''
import os

# High confidence: obvious command injection
os.system("rm -rf " + user_input)

# Medium confidence: potential SQL injection
query = "SELECT * FROM table WHERE id = %s" % some_value

# Lower confidence: might be a false positive
data = "1234567890abcdef1234567890abcdef"  # Might be mistaken for API key
''')
    
    analysis = analyzer.analyze_file(test_file)
    security_issues = [issue for issue in analysis.issues 
                      if issue.category == IssueCategory.SECURITY]
    
    # Check that issues have confidence scores
    assert all(hasattr(issue, 'confidence') for issue in security_issues)
    
    # Command injection should have high confidence
    cmd_injection = next((issue for issue in security_issues 
                         if 'command injection' in issue.message.lower()), None)
    if cmd_injection:
        assert cmd_injection.confidence >= 0.8