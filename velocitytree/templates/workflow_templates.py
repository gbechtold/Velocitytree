"""
Pre-defined workflow templates for common development tasks.
"""

WORKFLOW_TEMPLATES = {
    "daily-standup": {
        "name": "Daily Standup",
        "description": "Prepare daily standup report with git status and AI summary",
        "steps": [
            {
                "name": "Check git status",
                "type": "command",
                "command": "git status --porcelain",
                "continue_on_error": True
            },
            {
                "name": "Get recent commits",
                "type": "command",
                "command": "git log --oneline -5",
                "continue_on_error": True
            },
            {
                "name": "Analyze project",
                "type": "velocitytree",
                "command": "analyze",
                "args": {
                    "detailed": True
                }
            },
            {
                "name": "Generate summary",
                "type": "velocitytree",
                "command": "ai",
                "args": {
                    "method": "suggest",
                    "task": "Create a daily standup summary based on git status and recent commits"
                },
                "condition": "{{ai.api_key_configured}}"
            }
        ]
    },
    
    "code-review": {
        "name": "Code Review",
        "description": "Prepare code for review with linting, tests, and AI analysis",
        "steps": [
            {
                "name": "Run linters",
                "type": "command",
                "command": "flake8 .",
                "continue_on_error": True
            },
            {
                "name": "Run tests",
                "type": "command",
                "command": "pytest",
                "continue_on_error": True
            },
            {
                "name": "Flatten for review",
                "type": "velocitytree",
                "command": "flatten",
                "args": {
                    "output_dir": "review_{{timestamp}}",
                    "exclude": ["tests", "__pycache__", "*.pyc"]
                }
            },
            {
                "name": "AI code review",
                "type": "velocitytree",
                "command": "ai",
                "args": {
                    "method": "analyze_code",
                    "analysis_type": "general"
                },
                "condition": "{{ai.api_key_configured}}"
            }
        ]
    },
    
    "release-prep": {
        "name": "Release Preparation",
        "description": "Prepare project for release",
        "steps": [
            {
                "name": "Check uncommitted changes",
                "type": "command",
                "command": "git status --porcelain",
                "continue_on_error": False
            },
            {
                "name": "Run all tests",
                "type": "command",
                "command": "pytest --cov",
                "continue_on_error": False
            },
            {
                "name": "Update version",
                "type": "python",
                "command": """
import re
from pathlib import Path

version_file = Path('velocitytree/__init__.py')
content = version_file.read_text()
current_version = re.search(r'__version__ = "(.+)"', content).group(1)
parts = current_version.split('.')
parts[-1] = str(int(parts[-1]) + 1)
new_version = '.'.join(parts)
content = re.sub(r'__version__ = ".+"', f'__version__ = "{new_version}"', content)
version_file.write_text(content)
print(f"Updated version from {current_version} to {new_version}")
output = new_version
"""
            },
            {
                "name": "Generate changelog",
                "type": "command",
                "command": "git log --oneline --since='1 month ago'",
                "continue_on_error": True
            },
            {
                "name": "Build distribution",
                "type": "command",
                "command": "python -m build",
                "continue_on_error": False
            }
        ]
    },
    
    "documentation": {
        "name": "Documentation Update",
        "description": "Update and verify project documentation",
        "steps": [
            {
                "name": "Generate API docs",
                "type": "command",
                "command": "sphinx-apidoc -o docs/api velocitytree",
                "continue_on_error": True
            },
            {
                "name": "Build documentation",
                "type": "command",
                "command": "cd docs && make html",
                "continue_on_error": True
            },
            {
                "name": "Check README",
                "type": "python",
                "command": """
from pathlib import Path
readme = Path('README.md')
if readme.exists():
    content = readme.read_text()
    if '## Installation' not in content:
        print("Warning: README missing Installation section")
    if '## Usage' not in content:
        print("Warning: README missing Usage section")
    print(f"README size: {len(content)} characters")
else:
    print("Error: README.md not found")
"""
            },
            {
                "name": "Generate context docs",
                "type": "velocitytree",
                "command": "context",
                "args": {
                    "format": "markdown",
                    "output": "docs/project_context.md"
                }
            }
        ]
    },
    
    "dependency-check": {
        "name": "Dependency Check",
        "description": "Check and update project dependencies",
        "steps": [
            {
                "name": "Check outdated packages",
                "type": "command",
                "command": "pip list --outdated",
                "continue_on_error": True
            },
            {
                "name": "Security audit",
                "type": "command",
                "command": "pip-audit",
                "continue_on_error": True
            },
            {
                "name": "Generate requirements",
                "type": "command",
                "command": "pip freeze > requirements-current.txt",
                "continue_on_error": True
            },
            {
                "name": "Check imports",
                "type": "python",
                "command": """
import ast
import os
from pathlib import Path

def find_imports(file_path):
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())
    
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

all_imports = set()
for py_file in Path('velocitytree').rglob('*.py'):
    try:
        all_imports.update(find_imports(py_file))
    except:
        pass

print(f"Found {len(all_imports)} unique imports")
print("Top-level imports:", sorted(all_imports))
"""
            }
        ]
    },
    
    "performance-check": {
        "name": "Performance Check",
        "description": "Analyze performance and find bottlenecks",
        "steps": [
            {
                "name": "Profile flattening",
                "type": "python",
                "command": """
import time
from velocitytree.core import TreeFlattener

start = time.time()
flattener = TreeFlattener(output_dir="perf_test")
result = flattener.flatten()
end = time.time()

print(f"Flattening took {end - start:.2f} seconds")
print(f"Processed {result['files_processed']} files")
if result['files_processed'] > 0:
    print(f"Average time per file: {(end - start) / result['files_processed']:.4f} seconds")
"""
            },
            {
                "name": "Memory usage",
                "type": "python",
                "command": """
import psutil
import os

process = psutil.Process(os.getpid())
memory_info = process.memory_info()
print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
print(f"Virtual memory: {memory_info.vms / 1024 / 1024:.2f} MB")
"""
            },
            {
                "name": "Check disk usage",
                "type": "command",
                "command": "du -sh .",
                "continue_on_error": True
            }
        ]
    },
    
    "blog_post": {
        "name": "Blog Post Creator",
        "description": "Create professional blog posts with AI assistance",
        "tags": ["content", "writing", "ai"],
        "steps": [
            {
                "name": "Setup",
                "type": "command",
                "command": "mkdir -p blog_posts",
                "description": "Create output directory"
            },
            {
                "name": "Get Topic",
                "type": "python",
                "command": """
topic = input("\\n📝 Enter your blog post topic: ")
context.set_var('topic', topic)
print(f"\\n✅ Topic set: {topic}")
"""
            },
            {
                "name": "Research",
                "type": "velocitytree",
                "command": "ai",
                "args": {
                    "method": "suggest",
                    "prompt": "Research key points and create an outline for a blog post about: {{vars.topic}}"
                }
            },
            {
                "name": "Generate Draft",
                "type": "velocitytree",
                "command": "ai",
                "args": {
                    "method": "generate",
                    "prompt": "Write a comprehensive blog post based on this outline:\\n\\n{{step_2.output}}\\n\\nTopic: {{vars.topic}}"
                }
            },
            {
                "name": "Save Draft",
                "type": "python",
                "command": """
import re
from datetime import datetime

# Clean topic for filename
filename = re.sub(r'[^a-zA-Z0-9\\s-]', '', context.get_var('topic'))
filename = re.sub(r'\\s+', '-', filename.lower())
filename = f"{datetime.now().strftime('%Y%m%d')}_{filename}.md"

# Save the blog post
with open(f'blog_posts/{filename}', 'w') as f:
    f.write(context.get_step_output('step_3'))

print(f"\\n✅ Blog post saved to: blog_posts/{filename}")
"""
            },
            {
                "name": "Summary",
                "type": "command",
                "command": "echo '\\n🎉 Blog post created successfully!'"
            }
        ]
    }
}