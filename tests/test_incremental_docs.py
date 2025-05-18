"""Test incremental documentation updates."""

import os
import pytest
import tempfile
import time
from pathlib import Path

from velocitytree.documentation import IncrementalDocUpdater, DocConfig, DocFormat
from velocitytree.documentation.incremental import FileChange, DocChange, ChangeSet


class TestIncrementalDocUpdater:
    """Test cases for IncrementalDocUpdater."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
            
    @pytest.fixture
    def updater(self, temp_dir):
        """Create an IncrementalDocUpdater instance with isolated cache."""
        config = DocConfig()
        updater = IncrementalDocUpdater(config)
        # Use isolated cache directory for tests
        updater.cache_dir = temp_dir / ".velocitytree" / "doc_cache"
        updater.cache_dir.mkdir(parents=True, exist_ok=True)
        updater._init_cache()
        return updater
        
    @pytest.fixture
    def sample_python_file(self, temp_dir):
        """Create a sample Python file."""
        file_path = temp_dir / "sample.py"
        content = '''"""Sample module for testing."""

def add(a, b):
    """Add two numbers."""
    return a + b
    
class Calculator:
    """Simple calculator class."""
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
'''
        file_path.write_text(content)
        return file_path
        
    def test_init(self, updater):
        """Test initialization."""
        assert updater.cache_dir.exists()
        assert updater.cache_file.exists()
        assert updater.hash_file.exists()
        
    def test_file_hash_calculation(self, updater, sample_python_file):
        """Test file hash calculation."""
        hash1 = updater._calculate_file_hash(str(sample_python_file))
        assert hash1
        
        # Same content should give same hash
        hash2 = updater._calculate_file_hash(str(sample_python_file))
        assert hash1 == hash2
        
        # Modified content should give different hash
        sample_python_file.write_text("# Modified content")
        hash3 = updater._calculate_file_hash(str(sample_python_file))
        assert hash1 != hash3
        
    def test_detect_changes_new_file(self, updater, sample_python_file):
        """Test detecting changes for a new file."""
        change_set = updater.detect_changes([str(sample_python_file)])
        
        # Find the change for our specific file
        relevant_changes = [c for c in change_set.file_changes if c.path == str(sample_python_file)]
        assert len(relevant_changes) == 1
        change = relevant_changes[0]
        assert change.change_type == 'added'
        assert change.new_content == sample_python_file.read_text()
        assert change.old_content == ""
        
    def test_detect_changes_modified_file(self, updater, sample_python_file):
        """Test detecting changes for a modified file."""
        # First scan
        updater.detect_changes([str(sample_python_file)])
        updater.file_hashes[str(sample_python_file)] = updater._calculate_file_hash(str(sample_python_file))
        
        # Modify file
        original_content = sample_python_file.read_text()
        modified_content = original_content + "\n# Added comment"
        sample_python_file.write_text(modified_content)
        
        # Detect changes
        change_set = updater.detect_changes([str(sample_python_file)])
        
        # Find the change for our specific file
        relevant_changes = [c for c in change_set.file_changes if c.path == str(sample_python_file)]
        assert len(relevant_changes) == 1
        change = relevant_changes[0]
        assert change.change_type == 'modified'
        assert change.old_content == ""  # Cache wasn't populated
        assert change.new_content == modified_content
        
    def test_detect_changes_deleted_file(self, updater, sample_python_file):
        """Test detecting changes for a deleted file."""
        # Add file to tracking
        file_path = str(sample_python_file)
        updater.file_hashes[file_path] = updater._calculate_file_hash(file_path)
        
        # Delete file
        os.remove(file_path)
        
        # Detect changes (with empty file list)
        change_set = updater.detect_changes([])
        
        # Find the change for our specific file
        relevant_changes = [c for c in change_set.file_changes if c.path == file_path]
        assert len(relevant_changes) == 1
        change = relevant_changes[0]
        assert change.change_type == 'deleted'
        
    def test_find_changed_lines(self, updater):
        """Test finding changed lines."""
        old_content = """line 1
line 2
line 3"""
        
        new_content = """line 1
line 2 modified
line 3
line 4"""
        
        changed_lines = updater._find_changed_lines(old_content, new_content)
        assert 2 in changed_lines  # Modified line
        assert 4 in changed_lines  # Added line
        
    def test_analyze_doc_changes(self, updater, temp_dir):
        """Test analyzing documentation changes."""
        # Create initial file
        old_content = '''def old_function():
    """Old function docstring."""
    pass'''
    
        new_content = '''def old_function():
    """Updated function docstring."""
    pass
    
def new_function():
    """New function docstring."""
    pass'''
    
        change = FileChange(
            path=str(temp_dir / "test.py"),
            old_content=old_content,
            new_content=new_content,
            change_type='modified',
            change_lines=[2, 5, 6, 7],
        )
        
        doc_changes = updater._analyze_doc_changes(change)
        
        assert len(doc_changes) == 2
        
        # Check for modified function
        modified = [dc for dc in doc_changes if dc.element == 'old_function'][0]
        assert modified.change_type == 'modified'
        assert modified.old_doc == 'Old function docstring.'
        assert modified.new_doc == 'Updated function docstring.'
        
        # Check for added function
        added = [dc for dc in doc_changes if dc.element == 'new_function'][0]
        assert added.change_type == 'added'
        assert added.old_doc is None
        assert added.new_doc == 'New function docstring.'
        
    def test_extract_elements(self, updater):
        """Test extracting elements from AST."""
        import ast
        
        code = '''"""Module docstring."""

def func1():
    """Function 1 docstring."""
    pass
    
class MyClass:
    """Class docstring."""
    
    def method1(self):
        """Method 1 docstring."""
        pass
'''
        
        tree = ast.parse(code)
        elements = updater._extract_elements(tree)
        
        assert 'func1' in elements
        assert elements['func1']['type'] == 'function'
        assert elements['func1']['docstring'] == 'Function 1 docstring.'
        
        assert 'MyClass' in elements
        assert elements['MyClass']['type'] == 'class'
        assert elements['MyClass']['docstring'] == 'Class docstring.'
        
        assert 'MyClass.method1' in elements
        assert elements['MyClass.method1']['type'] == 'method'
        assert elements['MyClass.method1']['docstring'] == 'Method 1 docstring.'
        
    def test_can_update_incrementally(self, updater):
        """Test checking if changes can be updated incrementally."""
        # Only docstring changes - can update incrementally
        changes = [
            DocChange(
                element='func1',
                element_type='function',
                old_doc='Old doc',
                new_doc='New doc',
                change_type='modified',
                location='file.py:10',
            )
        ]
        assert updater._can_update_incrementally(changes)
        
        # Structural changes - cannot update incrementally
        changes = [
            DocChange(
                element='func2',
                element_type='function',
                old_doc=None,
                new_doc='New function',
                change_type='added',
                location='file.py:20',
            )
        ]
        assert not updater._can_update_incrementally(changes)
        
        # Module-level changes - cannot update incrementally
        changes = [
            DocChange(
                element='module',
                element_type='module',
                old_doc='Old module doc',
                new_doc='New module doc',
                change_type='modified',
                location='file.py:1',
            )
        ]
        assert not updater._can_update_incrementally(changes)
        
    def test_update_documentation(self, updater, sample_python_file):
        """Test updating documentation."""
        # Initial scan
        change_set = updater.detect_changes([str(sample_python_file)])
        results = updater.update_documentation(change_set)
        
        assert str(sample_python_file) in results
        result = results[str(sample_python_file)]
        assert result.content
        assert result.quality_score > 0
        assert result.completeness_score > 0
        
        # Verify cache is updated
        assert str(sample_python_file) in updater.file_hashes
        assert str(sample_python_file) in updater.doc_cache
        
    def test_get_cached_documentation(self, updater, sample_python_file):
        """Test getting cached documentation."""
        # No cache initially
        result = updater.get_cached_documentation(str(sample_python_file))
        assert result is None
        
        # Generate and cache documentation
        change_set = updater.detect_changes([str(sample_python_file)])
        updater.update_documentation(change_set)
        
        # Get from cache
        result = updater.get_cached_documentation(str(sample_python_file))
        assert result is not None
        assert result.generation_time == 0.0  # Cached result
        
    def test_invalidate_cache(self, updater, sample_python_file):
        """Test cache invalidation."""
        # Generate and cache documentation
        change_set = updater.detect_changes([str(sample_python_file)])
        updater.update_documentation(change_set)
        
        # Verify cache exists
        assert str(sample_python_file) in updater.file_hashes
        assert str(sample_python_file) in updater.doc_cache
        
        # Invalidate specific file
        updater.invalidate_cache([str(sample_python_file)])
        assert str(sample_python_file) not in updater.file_hashes
        assert str(sample_python_file) not in updater.doc_cache
        
        # Add back to cache
        change_set = updater.detect_changes([str(sample_python_file)])
        updater.update_documentation(change_set)
        
        # Invalidate all
        updater.invalidate_cache()
        assert len(updater.file_hashes) == 0
        assert len(updater.doc_cache) == 0
        
    def test_watch_files_callback(self, updater, sample_python_file):
        """Test watch files with callback."""
        results_captured = []
        changes_captured = []
        
        def callback(results, change_set):
            results_captured.append(results)
            changes_captured.append(change_set)
            
        # Start watching in a thread (with immediate timeout)
        import threading
        watch_thread = threading.Thread(
            target=updater.watch_files,
            args=([str(sample_python_file)],),
            kwargs={'callback': callback, 'interval': 0.1}
        )
        watch_thread.daemon = True
        watch_thread.start()
        
        # Give it a moment to start
        time.sleep(0.2)
        
        # Modify file
        sample_python_file.write_text(sample_python_file.read_text() + "\n# Modified")
        
        # Give it time to detect
        time.sleep(0.3)
        
        # Should have captured changes
        assert len(results_captured) > 0
        assert len(changes_captured) > 0