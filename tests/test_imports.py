#!/usr/bin/env python3
"""
Quick import test to ensure all modules can be loaded.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("Testing Velocitytree imports...")

try:
    import velocitytree
    print(f"✓ Main package imported, version: {velocitytree.__version__}")
except Exception as e:
    print(f"✗ Failed to import main package: {e}")

try:
    from velocitytree.cli import cli
    print("✓ CLI module imported")
except Exception as e:
    print(f"✗ Failed to import CLI: {e}")

try:
    from velocitytree.core import TreeFlattener, ContextManager
    print("✓ Core module imported")
except Exception as e:
    print(f"✗ Failed to import core: {e}")

try:
    from velocitytree.config import Config
    print("✓ Config module imported")
except Exception as e:
    print(f"✗ Failed to import config: {e}")

try:
    from velocitytree.ai import AIAssistant
    print("✓ AI module imported")
except Exception as e:
    print(f"✗ Failed to import AI: {e}")

try:
    from velocitytree.workflows import WorkflowManager
    print("✓ Workflows module imported")
except Exception as e:
    print(f"✗ Failed to import workflows: {e}")

try:
    from velocitytree.utils import logger
    print("✓ Utils module imported")
except Exception as e:
    print(f"✗ Failed to import utils: {e}")

print("\nImport test completed!")