"""Security vulnerability scanning for code analysis."""

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Set, Optional, Any
from pathlib import Path
import importlib.util

from .models import (
    VulnerabilityInfo,
    SeverityLevel,
    SecurityCategory,
    CodeLocation,
)
from .patterns import PatternDetectorRegistry, PatternDetector


class VulnerabilityType(Enum):
    """Types of security vulnerabilities."""
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    XSS = "cross_site_scripting"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    INSECURE_RANDOM = "insecure_random"
    HARDCODED_CREDENTIALS = "hardcoded_credentials"
    WEAK_ENCRYPTION = "weak_encryption"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    XML_EXTERNAL_ENTITY = "xml_external_entity"
    SSRF = "server_side_request_forgery"
    UNRESTRICTED_FILE_UPLOAD = "unrestricted_file_upload"
    INSUFFICIENT_VALIDATION = "insufficient_validation"
    RACE_CONDITION = "race_condition"
    DEPRECATED_API = "deprecated_api"


@dataclass
class VulnerabilityPattern:
    """Pattern for detecting vulnerabilities."""
    type: VulnerabilityType
    severity: SeverityLevel
    category: SecurityCategory
    description: str
    pattern: str
    fix_suggestion: str
    references: List[str] = field(default_factory=list)
    confidence: float = 0.8


class SecurityScanner:
    """Scanner for detecting security vulnerabilities in code."""
    
    def __init__(self):
        self.vulnerability_patterns = self._initialize_patterns()
        self.dangerous_functions = self._get_dangerous_functions()
        self.sensitive_patterns = self._get_sensitive_patterns()
        
    def _initialize_patterns(self) -> List[VulnerabilityPattern]:
        """Initialize vulnerability detection patterns."""
        return [
            # SQL Injection patterns
            VulnerabilityPattern(
                type=VulnerabilityType.SQL_INJECTION,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.INJECTION,
                description="Potential SQL injection vulnerability",
                pattern=r'(execute|cursor\.execute)\s*\(\s*["\'].*?\%[sd].*?["\'].*?\%',
                fix_suggestion="Use parameterized queries instead of string formatting",
                references=["https://owasp.org/www-community/attacks/SQL_Injection"]
            ),
            VulnerabilityPattern(
                type=VulnerabilityType.SQL_INJECTION,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.INJECTION,
                description="SQL query with string concatenation",
                pattern=r'(SELECT|INSERT|UPDATE|DELETE).*?\+.*?(\'|")',
                fix_suggestion="Use parameterized queries instead of string concatenation",
                references=["CWE-89"]
            ),
            
            # Command injection patterns
            VulnerabilityPattern(
                type=VulnerabilityType.COMMAND_INJECTION,
                severity=SeverityLevel.CRITICAL,
                category=SecurityCategory.INJECTION,
                description="Potential command injection vulnerability",
                pattern=r'(os\.system|subprocess\.(call|run|Popen))\s*\([^)]*\+[^)]*\)',
                fix_suggestion="Use subprocess with shell=False and pass arguments as a list",
                references=["CWE-78"]
            ),
            
            # Path traversal patterns
            VulnerabilityPattern(
                type=VulnerabilityType.PATH_TRAVERSAL,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.PATH_TRAVERSAL,
                description="Potential path traversal vulnerability",
                pattern=r'open\s*\([^)]*\+[^)]*\)|Path\s*\([^)]*\+[^)]*\)',
                fix_suggestion="Validate and sanitize file paths before use",
                references=["CWE-22"]
            ),
            
            # Hardcoded credentials
            VulnerabilityPattern(
                type=VulnerabilityType.HARDCODED_CREDENTIALS,
                severity=SeverityLevel.CRITICAL,
                category=SecurityCategory.AUTHENTICATION,
                description="Hardcoded credentials detected",
                pattern=r'(password|passwd|pwd|secret|api_key|token)\s*=\s*["\'][^"\']+["\']',
                fix_suggestion="Use environment variables or secure credential storage",
                references=["CWE-798"]
            ),
            
            # Insecure random
            VulnerabilityPattern(
                type=VulnerabilityType.INSECURE_RANDOM,
                severity=SeverityLevel.MEDIUM,
                category=SecurityCategory.CRYPTOGRAPHY,
                description="Use of insecure random number generator",
                pattern=r'random\.(random|randint|choice)\s*\(',
                fix_suggestion="Use secrets module for cryptographic purposes",
                references=["CWE-330"]
            ),
            
            # Weak encryption
            VulnerabilityPattern(
                type=VulnerabilityType.WEAK_ENCRYPTION,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.CRYPTOGRAPHY,
                description="Use of weak encryption algorithm",
                pattern=r'(MD5|SHA1|DES|RC4)\s*\(',
                fix_suggestion="Use strong encryption algorithms like SHA-256 or AES",
                references=["CWE-327"]
            ),
            
            # Insecure deserialization
            VulnerabilityPattern(
                type=VulnerabilityType.INSECURE_DESERIALIZATION,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.INJECTION,
                description="Potential insecure deserialization",
                pattern=r'pickle\.(load|loads)\s*\(',
                fix_suggestion="Validate input before deserialization or use safer formats like JSON",
                references=["CWE-502"]
            ),
            
            # SSRF patterns
            VulnerabilityPattern(
                type=VulnerabilityType.SSRF,
                severity=SeverityLevel.HIGH,
                category=SecurityCategory.INJECTION,
                description="Potential Server-Side Request Forgery",
                pattern=r'requests\.(get|post|put|delete)\s*\([^)]*\+[^)]*\)',
                fix_suggestion="Validate and whitelist URLs before making requests",
                references=["CWE-918"]
            ),
        ]
        
    def _get_dangerous_functions(self) -> Dict[str, List[str]]:
        """Get list of dangerous functions by category."""
        return {
            'os': ['system', 'popen', 'execl', 'execle', 'execlp', 'execv', 'execve', 'execvp'],
            'subprocess': ['call', 'run', 'Popen'],
            'eval': ['eval', 'exec', 'compile', '__import__'],
            'file': ['open', 'file'],
            'network': ['urlopen', 'urlretrieve'],
            'pickle': ['load', 'loads'],
            'yaml': ['load', 'load_all'],
            'xml': ['parse', 'XMLParse', 'XMLTreeBuilder'],
        }
        
    def _get_sensitive_patterns(self) -> List[re.Pattern]:
        """Get patterns for sensitive data detection."""
        return [
            re.compile(r'[A-Za-z0-9]{32,}'),  # API keys
            re.compile(r'-----BEGIN (RSA |EC )?PRIVATE KEY-----'),  # Private keys
            re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),  # Emails
            re.compile(r'\b(?:\d{3}[-.]?)?\d{3}[-.]?\d{4}\b'),  # Phone numbers
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # SSN pattern
            re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),  # Credit card pattern
        ]
        
    def scan_code(self, code: str, file_path: Optional[Path] = None) -> List[VulnerabilityInfo]:
        """Scan code for security vulnerabilities."""
        vulnerabilities = []
        
        # Check regex patterns
        vulnerabilities.extend(self._scan_patterns(code, file_path))
        
        # AST-based analysis for Python
        if file_path and file_path.suffix == '.py':
            vulnerabilities.extend(self._scan_ast(code, file_path))
            
        # Check for sensitive data exposure
        vulnerabilities.extend(self._scan_sensitive_data(code, file_path))
        
        # Check imported modules
        vulnerabilities.extend(self._scan_imports(code, file_path))
        
        return vulnerabilities
        
    def _scan_patterns(self, code: str, file_path: Optional[Path]) -> List[VulnerabilityInfo]:
        """Scan code using regex patterns."""
        vulnerabilities = []
        
        for pattern in self.vulnerability_patterns:
            matches = re.finditer(pattern.pattern, code, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                vulnerability = VulnerabilityInfo(
                    type=pattern.type.value,
                    severity=pattern.severity,
                    category=pattern.category,
                    description=pattern.description,
                    location=CodeLocation(
                        file_path=str(file_path) if file_path else 'unknown',
                        line_start=line_num,
                        line_end=line_num,
                        column_start=match.start() - code.rfind('\n', 0, match.start()),
                        column_end=match.end() - code.rfind('\n', 0, match.start()),
                    ),
                    code_snippet=code.splitlines()[line_num - 1] if line_num <= len(code.splitlines()) else '',
                    fix_suggestion=pattern.fix_suggestion,
                    references=pattern.references,
                    confidence=pattern.confidence,
                )
                
                vulnerabilities.append(vulnerability)
                
        return vulnerabilities
        
    def _scan_ast(self, code: str, file_path: Path) -> List[VulnerabilityInfo]:
        """Scan Python AST for vulnerabilities."""
        vulnerabilities = []
        
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    vulnerabilities.extend(self._check_dangerous_call(node, code, file_path))
                    
                # Check for eval/exec usage
                if isinstance(node, ast.Name) and node.id in ['eval', 'exec']:
                    vulnerabilities.append(self._create_eval_vulnerability(node, code, file_path))
                    
                # Check for assert statements in production code
                if isinstance(node, ast.Assert):
                    vulnerabilities.append(self._create_assert_vulnerability(node, code, file_path))
                    
        except SyntaxError:
            pass  # Invalid syntax, skip AST analysis
            
        return vulnerabilities
        
    def _check_dangerous_call(self, node: ast.Call, code: str, file_path: Path) -> List[VulnerabilityInfo]:
        """Check for dangerous function calls."""
        vulnerabilities = []
        
        # Get function name
        func_name = self._get_function_name(node)
        
        for category, funcs in self.dangerous_functions.items():
            if func_name in funcs:
                vulnerability = VulnerabilityInfo(
                    type=VulnerabilityType.COMMAND_INJECTION.value if category in ['os', 'subprocess'] else VulnerabilityType.INSECURE_DESERIALIZATION.value,
                    severity=SeverityLevel.HIGH if category in ['os', 'subprocess', 'eval'] else SeverityLevel.MEDIUM,
                    category=SecurityCategory.INJECTION,
                    description=f"Use of dangerous function: {func_name}",
                    location=CodeLocation(
                        file_path=str(file_path),
                        line_start=node.lineno,
                        line_end=node.end_lineno or node.lineno,
                        column_start=node.col_offset,
                        column_end=node.end_col_offset or node.col_offset,
                    ),
                    code_snippet=code.splitlines()[node.lineno - 1] if node.lineno <= len(code.splitlines()) else '',
                    fix_suggestion=self._get_fix_suggestion(func_name),
                    references=self._get_references(func_name),
                    confidence=0.9,
                )
                vulnerabilities.append(vulnerability)
                
        return vulnerabilities
        
    def _get_function_name(self, node: ast.Call) -> str:
        """Extract function name from a call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ''
        
    def _get_fix_suggestion(self, func_name: str) -> str:
        """Get fix suggestion for dangerous function."""
        suggestions = {
            'system': 'Use subprocess.run() with shell=False',
            'exec': 'Avoid using exec, consider alternative approaches',
            'eval': 'Use ast.literal_eval() for safe evaluation',
            'pickle.load': 'Consider using JSON for serialization',
            'yaml.load': 'Use yaml.safe_load() instead',
        }
        return suggestions.get(func_name, 'Consider using a safer alternative')
        
    def _get_references(self, func_name: str) -> List[str]:
        """Get references for dangerous function."""
        references = {
            'system': ['CWE-78'],
            'exec': ['CWE-94'],
            'eval': ['CWE-94', 'CWE-95'],
            'pickle.load': ['CWE-502'],
        }
        return references.get(func_name, ['CWE-676'])
        
    def _scan_sensitive_data(self, code: str, file_path: Optional[Path]) -> List[VulnerabilityInfo]:
        """Scan for exposed sensitive data."""
        vulnerabilities = []
        
        for pattern in self.sensitive_patterns:
            matches = pattern.finditer(code)
            
            for match in matches:
                line_num = code[:match.start()].count('\n') + 1
                
                # Check context to reduce false positives
                context = code[max(0, match.start() - 50):match.end() + 50]
                if self._is_likely_sensitive(match.group(), context):
                    vulnerability = VulnerabilityInfo(
                        type=VulnerabilityType.SENSITIVE_DATA_EXPOSURE.value,
                        severity=SeverityLevel.HIGH,
                        category=SecurityCategory.DATA_EXPOSURE,
                        description="Potential sensitive data exposure",
                        location=CodeLocation(
                            file_path=str(file_path) if file_path else 'unknown',
                            line_start=line_num,
                            line_end=line_num,
                            column_start=match.start() - code.rfind('\n', 0, match.start()),
                            column_end=match.end() - code.rfind('\n', 0, match.start()),
                        ),
                        code_snippet=code.splitlines()[line_num - 1] if line_num <= len(code.splitlines()) else '',
                        fix_suggestion="Remove or encrypt sensitive data",
                        references=["CWE-200", "CWE-312"],
                        confidence=0.7,
                    )
                    vulnerabilities.append(vulnerability)
                    
        return vulnerabilities
        
    def _is_likely_sensitive(self, data: str, context: str) -> bool:
        """Check if data is likely sensitive based on context."""
        # Skip if in a comment
        if '#' in context and context.index('#') < context.index(data):
            return False
            
        # Check for keywords indicating sensitive data
        sensitive_keywords = ['password', 'secret', 'key', 'token', 'credential', 'auth']
        context_lower = context.lower()
        
        return any(keyword in context_lower for keyword in sensitive_keywords)
        
    def _scan_imports(self, code: str, file_path: Optional[Path]) -> List[VulnerabilityInfo]:
        """Scan for dangerous imports."""
        vulnerabilities = []
        
        dangerous_imports = {
            'telnetlib': ('Use of insecure Telnet protocol', 'Use SSH instead of Telnet'),
            'ftplib': ('Use of insecure FTP protocol', 'Use SFTP or FTPS instead'),
            'pickle': ('Use of pickle can lead to arbitrary code execution', 'Consider using JSON for serialization'),
            'marshal': ('Use of marshal can be insecure', 'Consider using JSON for serialization'),
            'imp': ('Deprecated import mechanism', 'Use importlib instead'),
        }
        
        import_pattern = re.compile(r'^\s*(?:from\s+(\w+)|import\s+(\w+))', re.MULTILINE)
        
        for match in import_pattern.finditer(code):
            module = match.group(1) or match.group(2)
            
            if module in dangerous_imports:
                line_num = code[:match.start()].count('\n') + 1
                desc, fix = dangerous_imports[module]
                
                vulnerability = VulnerabilityInfo(
                    type=VulnerabilityType.DEPRECATED_API.value,
                    severity=SeverityLevel.MEDIUM,
                    category=SecurityCategory.CONFIGURATION,
                    description=desc,
                    location=CodeLocation(
                        file_path=str(file_path) if file_path else 'unknown',
                        line_start=line_num,
                        line_end=line_num,
                        column_start=match.start() - code.rfind('\n', 0, match.start()),
                        column_end=match.end() - code.rfind('\n', 0, match.start()),
                    ),
                    code_snippet=code.splitlines()[line_num - 1] if line_num <= len(code.splitlines()) else '',
                    fix_suggestion=fix,
                    references=["CWE-676"],
                    confidence=0.9,
                )
                vulnerabilities.append(vulnerability)
                
        return vulnerabilities
        
    def _create_eval_vulnerability(self, node: ast.Name, code: str, file_path: Path) -> VulnerabilityInfo:
        """Create vulnerability for eval/exec usage."""
        return VulnerabilityInfo(
            type=VulnerabilityType.COMMAND_INJECTION.value,
            severity=SeverityLevel.CRITICAL,
            category=SecurityCategory.INJECTION,
            description=f"Use of {node.id} can lead to arbitrary code execution",
            location=CodeLocation(
                file_path=str(file_path),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                column_start=node.col_offset,
                column_end=node.end_col_offset or node.col_offset,
            ),
            code_snippet=code.splitlines()[node.lineno - 1] if node.lineno <= len(code.splitlines()) else '',
            fix_suggestion=f"Avoid using {node.id}, consider safer alternatives",
            references=["CWE-94", "CWE-95"],
            confidence=1.0,
        )
        
    def _create_assert_vulnerability(self, node: ast.Assert, code: str, file_path: Path) -> VulnerabilityInfo:
        """Create vulnerability for assert usage."""
        return VulnerabilityInfo(
            type=VulnerabilityType.INSUFFICIENT_VALIDATION.value,
            severity=SeverityLevel.LOW,
            category=SecurityCategory.INPUT_VALIDATION,
            description="Assert statements are removed in optimized bytecode",
            location=CodeLocation(
                file_path=str(file_path),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                column_start=node.col_offset,
                column_end=node.end_col_offset or node.col_offset,
            ),
            code_snippet=code.splitlines()[node.lineno - 1] if node.lineno <= len(code.splitlines()) else '',
            fix_suggestion="Use proper error handling instead of assert for validation",
            references=["CWE-617"],
            confidence=0.8,
        )
        

class SecurityAnalyzer:
    """High-level security analyzer integrating various security checks."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.scanner = SecurityScanner()
        self.pattern_registry = PatternDetectorRegistry()
        
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file for security vulnerabilities."""
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
            
        vulnerabilities = self.scanner.scan_code(code, file_path)
        
        # Group by severity
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
        }
        
        for vuln in vulnerabilities:
            severity_counts[vuln.severity.value] += 1
            
        return {
            'file': str(file_path),
            'vulnerabilities': vulnerabilities,
            'summary': {
                'total': len(vulnerabilities),
                'by_severity': severity_counts,
                'security_score': self._calculate_security_score(vulnerabilities),
            }
        }
        
    def analyze_directory(self, directory: Path, patterns: List[str] = None) -> Dict[str, Any]:
        """Analyze all files in a directory for security vulnerabilities."""
        if patterns is None:
            patterns = ['*.py', '*.js', '*.ts', '*.java', '*.rb', '*.php']
            
        all_vulnerabilities = []
        file_results = []
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    try:
                        result = self.analyze_file(file_path)
                        file_results.append(result)
                        all_vulnerabilities.extend(result['vulnerabilities'])
                    except Exception as e:
                        print(f"Error analyzing {file_path}: {e}")
                        
        return {
            'directory': str(directory),
            'files_analyzed': len(file_results),
            'vulnerabilities': all_vulnerabilities,
            'file_results': file_results,
            'summary': self._create_summary(all_vulnerabilities),
        }
        
    def _calculate_security_score(self, vulnerabilities: List[VulnerabilityInfo]) -> float:
        """Calculate a security score based on vulnerabilities."""
        if not vulnerabilities:
            return 100.0
            
        # Weight by severity
        weights = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 5,
            SeverityLevel.LOW: 1,
        }
        
        total_penalty = sum(weights.get(v.severity, 0) for v in vulnerabilities)
        
        # Cap at 0
        score = max(0, 100 - total_penalty)
        
        return score
        
    def _create_summary(self, vulnerabilities: List[VulnerabilityInfo]) -> Dict[str, Any]:
        """Create a summary of vulnerabilities."""
        severity_counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
        }
        
        category_counts = {}
        type_counts = {}
        
        for vuln in vulnerabilities:
            severity_counts[vuln.severity.value] += 1
            
            category = vuln.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
            
            vuln_type = vuln.type
            type_counts[vuln_type] = type_counts.get(vuln_type, 0) + 1
            
        return {
            'total': len(vulnerabilities),
            'by_severity': severity_counts,
            'by_category': category_counts,
            'by_type': type_counts,
            'security_score': self._calculate_security_score(vulnerabilities),
            'most_common': sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        }