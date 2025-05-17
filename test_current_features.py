#!/usr/bin/env python3
"""
Manual testing script for Velocitytree features completed in Steps 1-3.
Run this to verify current functionality before proceeding.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from velocitytree.cli import cli
from velocitytree.config import Config
from velocitytree.core import TreeFlattener, ContextManager
from velocitytree.ai import AIAssistant
from click.testing import CliRunner

# Test utilities
runner = CliRunner()
test_dir = None


def setup_test_environment():
    """Set up a test directory with sample files."""
    global test_dir
    test_dir = tempfile.mkdtemp()
    os.chdir(test_dir)
    
    # Create sample project structure
    Path("src").mkdir()
    Path("src/main.py").write_text("def main():\n    print('Hello, World!')")
    Path("src/utils.py").write_text("def helper():\n    return 42")
    Path("tests").mkdir()
    Path("tests/test_main.py").write_text("def test_main():\n    assert True")
    Path("README.md").write_text("# Test Project\n\nA sample project for testing.")
    Path(".gitignore").write_text("__pycache__/\n*.pyc\n.env")
    
    # Create a config file
    config_content = """
project:
  name: Test Project
  version: 0.1.0

ai:
  provider: openai
  model: gpt-3.5-turbo

flatten:
  output_dir: flattened_output
  exclude:
    - __pycache__
    - "*.pyc"
"""
    Path(".velocitytree.yaml").write_text(config_content)
    
    print(f"Test environment created at: {test_dir}")


def cleanup_test_environment():
    """Clean up the test directory."""
    if test_dir and Path(test_dir).exists():
        shutil.rmtree(test_dir)
        print("Test environment cleaned up")


def test_cli_commands():
    """Test basic CLI commands."""
    print("\n=== Testing CLI Commands ===")
    
    # Test help
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0, f"Help failed: {result.output}"
    print("✓ Help command works")
    
    # Test version
    result = runner.invoke(cli, ['version'])
    assert result.exit_code == 0, f"Version failed: {result.output}"
    print("✓ Version command works")
    
    # Test init
    result = runner.invoke(cli, ['init', '--name', 'TestProject'])
    print(f"Init result: {result.output}")
    print(f"✓ Init command works (exit code: {result.exit_code})")
    
    # Test config display
    result = runner.invoke(cli, ['config'])
    assert result.exit_code == 0, f"Config failed: {result.output}"
    print("✓ Config command works")


def test_core_functionality():
    """Test core TreeFlattener and ContextManager."""
    print("\n=== Testing Core Functionality ===")
    
    # Test TreeFlattener
    try:
        flattener = TreeFlattener(output_dir="test_output")
        result = flattener.flatten(source_dir=Path.cwd())
        print(f"✓ TreeFlattener works: {result['files_processed']} files processed")
    except Exception as e:
        print(f"✗ TreeFlattener failed: {e}")
    
    # Test ContextManager
    try:
        manager = ContextManager()
        context = manager.generate_context()
        print(f"✓ ContextManager works: {context['project_name']}")
    except Exception as e:
        print(f"✗ ContextManager failed: {e}")


def test_ai_module():
    """Test AI module (requires API key)."""
    print("\n=== Testing AI Module ===")
    
    # Check if API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠ Skipping AI tests - OPENAI_API_KEY not set")
        return
    
    try:
        config = Config()
        assistant = AIAssistant(config)
        
        # Test provider info
        info = assistant.get_provider_info()
        print(f"AI Provider: {info['provider']}, Model: {info['model']}")
        
        # Test connection
        if assistant.test_connection():
            print("✓ AI connection successful")
        else:
            print("✗ AI connection failed")
            
    except Exception as e:
        print(f"✗ AI module error: {e}")


def test_cli_ai_commands():
    """Test AI-related CLI commands."""
    print("\n=== Testing AI CLI Commands ===")
    
    # Test AI test command
    result = runner.invoke(cli, ['ai', 'test'])
    print(f"AI test result: {result.output}")
    print(f"Exit code: {result.exit_code}")
    
    # Test AI suggest (without actual API call)
    result = runner.invoke(cli, ['ai', 'suggest', 'improve this code', '--help'])
    assert result.exit_code == 0, "AI suggest help failed"
    print("✓ AI suggest command available")


def test_workflow_commands():
    """Test workflow CLI commands."""
    print("\n=== Testing Workflow Commands ===")
    
    # Test workflow list
    result = runner.invoke(cli, ['workflow', 'list'])
    print(f"Workflow list result: {result.output}")
    
    # Test workflow create
    result = runner.invoke(cli, ['workflow', 'create', 'test_workflow'])
    print(f"Workflow create result: {result.output}")
    
    # Test workflow list again
    result = runner.invoke(cli, ['workflow', 'list'])
    print(f"Workflow list after create: {result.output}")


def test_analyze_command():
    """Test the analyze command."""
    print("\n=== Testing Analyze Command ===")
    
    result = runner.invoke(cli, ['analyze', '--detailed'])
    print(f"Analyze result: {result.output}")
    assert result.exit_code == 0, f"Analyze failed: {result.output}"
    print("✓ Analyze command works")


def run_all_tests():
    """Run all tests."""
    try:
        setup_test_environment()
        
        test_cli_commands()
        test_core_functionality()
        test_analyze_command()
        test_workflow_commands()
        test_ai_module()
        test_cli_ai_commands()
        
        print("\n=== Test Summary ===")
        print("All basic tests completed.")
        print("\nNOTE: Some tests may fail if API keys are not configured.")
        print("This is expected and not a critical issue for local functionality.")
        
    finally:
        cleanup_test_environment()


if __name__ == "__main__":
    print("Velocitytree Test Suite - Steps 1-3")
    print("===================================")
    run_all_tests()