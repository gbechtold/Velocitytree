"""Test security vulnerability scanning."""

import ast
import pytest
from pathlib import Path
from velocitytree.code_analysis.security import (
    SecurityScanner,
    SecurityAnalyzer,
    VulnerabilityType,
    VulnerabilityPattern,
)
from velocitytree.code_analysis.models import (
    SeverityLevel,
    SecurityCategory,
    CodeLocation,
)


@pytest.fixture
def security_scanner():
    """Create a security scanner instance."""
    return SecurityScanner()


@pytest.fixture
def security_analyzer():
    """Create a security analyzer instance."""
    return SecurityAnalyzer()


class TestSecurityScanner:
    """Test the security scanner."""
    
    def test_sql_injection_detection(self, security_scanner):
        """Test detection of SQL injection vulnerabilities."""
        code = '''
import sqlite3

def unsafe_query(user_input):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    cursor.execute(query)
    return cursor.fetchall()
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        assert len(vulnerabilities) > 0
        sql_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.SQL_INJECTION.value]
        assert len(sql_vulns) > 0
        assert sql_vulns[0].severity == SeverityLevel.HIGH
        assert "parameterized queries" in sql_vulns[0].fix_suggestion
    
    def test_command_injection_detection(self, security_scanner):
        """Test detection of command injection vulnerabilities."""
        code = '''
import os
import subprocess

def run_command(user_input):
    # Dangerous: command injection
    os.system("ping " + user_input)
    
    # Also dangerous
    subprocess.call("echo " + user_input, shell=True)
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        cmd_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.COMMAND_INJECTION.value]
        assert len(cmd_vulns) >= 2
        assert all(v.severity == SeverityLevel.CRITICAL for v in cmd_vulns)
    
    def test_hardcoded_credentials_detection(self, security_scanner):
        """Test detection of hardcoded credentials."""
        code = '''
# Hardcoded passwords
password = "super_secret_123"
api_key = "sk-1234567890abcdef"
db_passwd = "admin123"

# This should be fine
password_hash = hashlib.sha256(password.encode()).hexdigest()
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        cred_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.HARDCODED_CREDENTIALS.value]
        assert len(cred_vulns) >= 3
        assert all(v.severity == SeverityLevel.CRITICAL for v in cred_vulns)
        assert all("environment variables" in v.fix_suggestion for v in cred_vulns)
    
    def test_path_traversal_detection(self, security_scanner):
        """Test detection of path traversal vulnerabilities."""
        code = '''
import os

def read_file(filename):
    # Vulnerable to path traversal
    with open("/var/log/" + filename) as f:
        return f.read()
    
def safe_read_file(filename):
    # Safer approach
    safe_path = os.path.join("/var/log", os.path.basename(filename))
    with open(safe_path) as f:
        return f.read()
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        path_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.PATH_TRAVERSAL.value]
        assert len(path_vulns) >= 1
        assert path_vulns[0].severity == SeverityLevel.HIGH
    
    def test_insecure_random_detection(self, security_scanner):
        """Test detection of insecure random number generation."""
        code = '''
import random
import secrets

def generate_token():
    # Insecure for crypto
    return ''.join(random.choice('abcdef0123456789') for _ in range(32))
    
def generate_secure_token():
    # Secure
    return secrets.token_hex(16)
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        random_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.INSECURE_RANDOM.value]
        assert len(random_vulns) >= 1
        assert random_vulns[0].severity == SeverityLevel.MEDIUM
        assert "secrets" in random_vulns[0].fix_suggestion
    
    def test_weak_encryption_detection(self, security_scanner):
        """Test detection of weak encryption algorithms."""
        code = '''
import hashlib
from cryptography.hazmat.primitives import hashes

def weak_hash(data):
    # Weak algorithms
    md5_hash = hashlib.md5(data).hexdigest()
    sha1_hash = hashlib.sha1(data).hexdigest()
    return md5_hash, sha1_hash
    
def strong_hash(data):
    # Strong algorithm
    return hashlib.sha256(data).hexdigest()
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        crypto_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.WEAK_ENCRYPTION.value]
        assert len(crypto_vulns) >= 2
        assert all(v.severity == SeverityLevel.HIGH for v in crypto_vulns)
        assert all("SHA-256" in v.fix_suggestion for v in crypto_vulns)
    
    def test_insecure_deserialization_detection(self, security_scanner):
        """Test detection of insecure deserialization."""
        code = '''
import pickle
import json

def load_data(data):
    # Insecure
    return pickle.loads(data)
    
def safe_load_data(data):
    # Safer
    return json.loads(data)
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        deser_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.INSECURE_DESERIALIZATION.value]
        assert len(deser_vulns) >= 1
        assert deser_vulns[0].severity == SeverityLevel.HIGH
        assert "JSON" in deser_vulns[0].fix_suggestion
    
    def test_eval_exec_detection(self, security_scanner):
        """Test detection of eval/exec usage."""
        code = '''
def execute_code(user_code):
    # Very dangerous
    eval(user_code)
    exec(user_code)
    
def safe_evaluate(expression):
    # Safer for simple literals
    import ast
    return ast.literal_eval(expression)
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        eval_vulns = [v for v in vulnerabilities if 'eval' in v.description.lower() or 'exec' in v.description.lower()]
        assert len(eval_vulns) >= 2
        assert all(v.severity == SeverityLevel.CRITICAL for v in eval_vulns)
    
    def test_dangerous_imports_detection(self, security_scanner):
        """Test detection of dangerous imports."""
        code = '''
import telnetlib
import ftplib
import pickle
import marshal
import imp
import ssl  # This should be fine

def connect():
    telnet = telnetlib.Telnet("example.com")
    ftp = ftplib.FTP("ftp.example.com")
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        import_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.DEPRECATED_API.value]
        assert len(import_vulns) >= 3
        
    def test_assert_in_production_detection(self, security_scanner):
        """Test detection of assert statements."""
        code = '''
def validate_input(value):
    assert value is not None, "Value cannot be None"
    assert isinstance(value, int), "Value must be an integer"
    
    if value < 0:
        raise ValueError("Value must be positive")
'''
        vulnerabilities = security_scanner.scan_code(code, Path("test.py"))
        
        assert_vulns = [v for v in vulnerabilities if v.type == VulnerabilityType.INSUFFICIENT_VALIDATION.value]
        assert len(assert_vulns) >= 2
        assert all(v.severity == SeverityLevel.LOW for v in assert_vulns)


class TestSecurityAnalyzer:
    """Test the security analyzer."""
    
    def test_analyze_file(self, security_analyzer, tmp_path):
        """Test analyzing a single file."""
        test_file = tmp_path / "vulnerable.py"
        test_file.write_text('''
import os
password = "hardcoded_password"
os.system("rm -rf " + user_input)
''')
        
        result = security_analyzer.analyze_file(test_file)
        
        assert 'vulnerabilities' in result
        assert len(result['vulnerabilities']) >= 2
        assert 'summary' in result
        assert result['summary']['total'] >= 2
        assert result['summary']['security_score'] < 100
    
    def test_analyze_directory(self, security_analyzer, tmp_path):
        """Test analyzing a directory."""
        # Create multiple test files
        (tmp_path / "file1.py").write_text('password = "secret123"')
        (tmp_path / "file2.py").write_text('import pickle\npickle.loads(data)')
        (tmp_path / "file3.js").write_text('eval(userInput)')
        
        result = security_analyzer.analyze_directory(tmp_path)
        
        assert 'vulnerabilities' in result
        assert len(result['vulnerabilities']) >= 2
        assert result['files_analyzed'] >= 2
        assert 'summary' in result
    
    def test_security_score_calculation(self, security_analyzer):
        """Test security score calculation."""
        from velocitytree.code_analysis.models import VulnerabilityInfo
        
        # No vulnerabilities = perfect score
        score = security_analyzer._calculate_security_score([])
        assert score == 100.0
        
        # Create test vulnerabilities
        vulnerabilities = [
            VulnerabilityInfo(
                type="test",
                severity=SeverityLevel.CRITICAL,
                category=SecurityCategory.INJECTION,
                description="Test",
                location=CodeLocation("test.py", 1, 1),
                code_snippet="test",
                fix_suggestion="Fix it"
            ),
            VulnerabilityInfo(
                type="test2",
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.INJECTION,
                description="Test2",
                location=CodeLocation("test.py", 2, 2),
                code_snippet="test",
                fix_suggestion="Fix it"
            )
        ]
        
        score = security_analyzer._calculate_security_score(vulnerabilities)
        assert score < 100
        assert score >= 0
    
    def test_vulnerability_patterns_initialization(self, security_scanner):
        """Test that vulnerability patterns are properly initialized."""
        patterns = security_scanner.vulnerability_patterns
        
        assert len(patterns) > 0
        
        # Check that each pattern has required fields
        for pattern in patterns:
            assert isinstance(pattern.type, VulnerabilityType)
            assert isinstance(pattern.severity, SeverityLevel)
            assert isinstance(pattern.category, SecurityCategory)
            assert pattern.description
            assert pattern.pattern
            assert pattern.fix_suggestion
    
    def test_sensitive_data_context_checking(self, security_scanner):
        """Test that sensitive data detection considers context."""
        # Should detect: password in variable assignment
        code1 = 'password = "secret123"'
        vulns1 = security_scanner.scan_code(code1, Path("test.py"))
        sensitive_vulns1 = [v for v in vulns1 if v.type == VulnerabilityType.SENSITIVE_DATA_EXPOSURE.value]
        
        # Should not detect: random string in comment
        code2 = '# This is a comment with abcdef0123456789abcdef0123456789'
        vulns2 = security_scanner.scan_code(code2, Path("test.py"))
        sensitive_vulns2 = [v for v in vulns2 if v.type == VulnerabilityType.SENSITIVE_DATA_EXPOSURE.value]
        
        assert len(sensitive_vulns1) > len(sensitive_vulns2)