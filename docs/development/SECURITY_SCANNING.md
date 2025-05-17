# Security Vulnerability Scanning

VelocityTree includes a comprehensive security vulnerability scanner that helps identify common security issues in your codebase. This feature is integrated into the code analysis system and automatically runs during code analysis operations.

## Features

### Vulnerability Types Detected

The security scanner can detect the following types of vulnerabilities:

1. **SQL Injection**
   - String concatenation in SQL queries
   - String formatting in SQL statements
   - Unsafe query construction

2. **Command Injection**
   - Use of `os.system()` with user input
   - Unsafe `subprocess` calls
   - Shell command concatenation

3. **Path Traversal**
   - Unvalidated file path construction
   - Directory traversal attempts
   - Unsafe file operations

4. **Hardcoded Credentials**
   - Passwords in source code
   - API keys and tokens
   - Secret keys and credentials

5. **Insecure Random Number Generation**
   - Use of `random` module for cryptographic purposes
   - Weak random number generation for security tokens

6. **Weak Encryption**
   - MD5 and SHA1 usage
   - DES, RC4, and other weak algorithms
   - Insecure hashing for passwords

7. **Insecure Deserialization**
   - Unsafe `pickle` usage
   - `marshal` deserialization
   - YAML unsafe loading

8. **Server-Side Request Forgery (SSRF)**
   - Unvalidated URL construction
   - User-controlled request destinations

9. **Cross-Site Scripting (XSS)**
   - Unescaped user input in HTML
   - JavaScript injection points

10. **Sensitive Data Exposure**
    - API keys in code
    - Private keys
    - Personal information (emails, SSNs, phone numbers)

## Usage

### Command Line Integration

The security scanner is automatically integrated into the `vtree analyze` command:

```bash
# Analyze a single file
vtree analyze code my_file.py

# Analyze a directory
vtree analyze code ./src

# Focus on security issues only
vtree analyze code --category security ./src
```

### Programmatic Usage

```python
from velocitytree.code_analysis.security import SecurityAnalyzer

# Create analyzer
analyzer = SecurityAnalyzer()

# Analyze a single file
result = analyzer.analyze_file(Path("vulnerable.py"))
print(f"Found {len(result['vulnerabilities'])} vulnerabilities")
print(f"Security score: {result['summary']['security_score']}")

# Analyze a directory
result = analyzer.analyze_directory(Path("./src"))
for vuln in result['vulnerabilities']:
    print(f"{vuln.severity.value}: {vuln.description} at {vuln.location.file_path}:{vuln.location.line_start}")
```

### Integration with Code Analyzer

The security scanner is automatically integrated with the main code analyzer:

```python
from velocitytree.code_analysis.analyzer import CodeAnalyzer

analyzer = CodeAnalyzer()
module_analysis = analyzer.analyze_file("my_file.py")

# Security issues are included in module.issues
security_issues = [
    issue for issue in module_analysis.issues 
    if issue.category == IssueCategory.SECURITY
]
```

## Vulnerability Details

### Severity Levels

Each vulnerability is assigned a severity level:
- **CRITICAL**: Immediate security risk, must be fixed
- **HIGH**: Serious security concern, should be fixed soon
- **MEDIUM**: Moderate risk, plan to fix
- **LOW**: Minor issue, fix when convenient

### Confidence Scores

Each vulnerability has a confidence score (0.0 to 1.0) indicating the likelihood of it being a true positive:
- **0.9-1.0**: Very high confidence
- **0.7-0.9**: High confidence  
- **0.5-0.7**: Medium confidence
- **Below 0.5**: Low confidence (may be false positive)

### Fix Suggestions

Every vulnerability includes:
- A description of the issue
- A suggested fix
- References to relevant security standards (CWE, OWASP)

## Configuration

The security scanner can be configured through the VelocityTree configuration file:

```yaml
code_analysis:
  security:
    # Enable/disable security scanning
    enabled: true
    
    # Minimum confidence for reporting vulnerabilities
    min_confidence: 0.7
    
    # Severity levels to report
    severity_levels:
      - critical
      - high
      - medium
      - low
    
    # Custom patterns for additional checks
    custom_patterns:
      - pattern: 'eval\s*\('
        type: code_injection
        severity: critical
        description: "Use of eval() function"
```

## Best Practices

### False Positives

Some detections may be false positives. To handle these:

1. **Review each finding**: Check if the vulnerability is actually exploitable
2. **Use confidence scores**: Lower confidence findings need more review
3. **Context matters**: Consider how the code is actually used
4. **Suppress if needed**: Add comments to suppress specific warnings

### Security Standards

The scanner references these security standards:
- **CWE** (Common Weakness Enumeration)
- **OWASP** Top 10
- **SANS** Top 25

### Continuous Integration

Integrate security scanning into your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Security Scan
  run: |
    vtree analyze code --category security ./src
    if [ $? -ne 0 ]; then
      echo "Security vulnerabilities found!"
      exit 1
    fi
```

## Examples

### SQL Injection Detection

```python
# Vulnerable code
query = "SELECT * FROM users WHERE name = '%s'" % user_input
cursor.execute(query)

# Fixed code
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_input,))
```

### Command Injection Prevention

```python
# Vulnerable code
os.system("echo " + user_input)

# Fixed code
subprocess.run(["echo", user_input], check=True)
```

### Secure Random Generation

```python
# Vulnerable code
token = ''.join(random.choice(string.ascii_letters) for _ in range(32))

# Fixed code
import secrets
token = secrets.token_hex(16)
```

## Extending the Scanner

To add custom vulnerability patterns:

```python
from velocitytree.code_analysis.security import VulnerabilityPattern

custom_pattern = VulnerabilityPattern(
    type=VulnerabilityType.CUSTOM,
    severity=SeverityLevel.HIGH,
    category=SecurityCategory.INJECTION,
    description="Custom vulnerability",
    pattern=r'dangerous_function\s*\(',
    fix_suggestion="Use safe_function instead",
    references=["CWE-123"]
)

scanner.vulnerability_patterns.append(custom_pattern)
```

## Performance Considerations

The security scanner is designed to be efficient:
- Pattern matching is optimized with compiled regex
- AST analysis is cached when possible
- Large files are processed in chunks
- Results are cached to avoid redundant scans

For large codebases, consider:
- Running security scans separately from full analysis
- Using file filters to focus on specific areas
- Parallelizing directory scans
- Adjusting confidence thresholds

## Future Enhancements

Planned improvements include:
- Data flow analysis for more accurate detection
- Machine learning for reduced false positives
- Integration with external security databases
- Custom rule definition language
- IDE plugin integration