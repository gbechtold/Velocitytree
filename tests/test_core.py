"""
Tests for core functionality.
"""

import pytest
import tempfile
from pathlib import Path

from velocitytree.core import TreeFlattener, ContextManager


class TestTreeFlattener:
    
    def test_init(self):
        """Test TreeFlattener initialization."""
        flattener = TreeFlattener()
        assert flattener.output_dir == Path("tamed_tree")
        assert not flattener.preserve_structure
        assert not flattener.follow_symlinks
    
    def test_flatten_simple(self, tmp_path):
        """Test flattening a simple directory structure."""
        # Create test structure
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        # Create some files
        (source_dir / "file1.py").write_text("print('hello')")
        (source_dir / "file2.txt").write_text("test content")
        
        # Create a subdirectory
        sub_dir = source_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "file3.py").write_text("def test(): pass")
        
        # Flatten
        output_dir = tmp_path / "output"
        flattener = TreeFlattener(output_dir=str(output_dir))
        result = flattener.flatten(source_dir)
        
        # Check results
        assert result['files_processed'] == 3
        assert output_dir.exists()
        assert (output_dir / "file1.py").exists()
        assert (output_dir / "file2.txt").exists()
        assert (output_dir / "subdir_file3.py").exists()
    
    def test_exclusion_patterns(self, tmp_path):
        """Test file exclusion patterns."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        # Create files that should be excluded
        (source_dir / "file.py").write_text("code")
        (source_dir / "file.pyc").write_text("compiled")
        (source_dir / "__pycache__").mkdir()
        
        # Flatten
        output_dir = tmp_path / "output"
        flattener = TreeFlattener(output_dir=str(output_dir))
        result = flattener.flatten(source_dir)
        
        # Check that excluded files weren't processed
        assert result['files_processed'] == 1
        assert (output_dir / "file.py").exists()
        assert not (output_dir / "file.pyc").exists()
    
    def test_preserve_structure(self, tmp_path):
        """Test preserving directory structure."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        
        # Create nested structure
        (source_dir / "a" / "b" / "c").mkdir(parents=True)
        (source_dir / "a" / "b" / "c" / "file.py").write_text("test")
        
        # Flatten with structure preservation
        output_dir = tmp_path / "output"
        flattener = TreeFlattener(
            output_dir=str(output_dir),
            preserve_structure=True
        )
        result = flattener.flatten(source_dir)
        
        # Check structure is preserved
        assert (output_dir / "a" / "b" / "c" / "file.py").exists()


class TestContextManager:
    
    def test_init(self, tmp_path):
        """Test ContextManager initialization."""
        manager = ContextManager(project_root=tmp_path)
        assert manager.project_root == tmp_path
    
    def test_generate_context(self, tmp_path):
        """Test context generation."""
        # Create test project structure
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "main.py").write_text("def main(): pass")
        (tmp_path / "module.py").write_text("class TestClass: pass")
        
        manager = ContextManager(project_root=tmp_path)
        context = manager.generate_context()
        
        assert context['project_name'] == tmp_path.name
        assert 'structure' in context
        assert 'code_summary' in context
        assert 'documentation' in context
    
    def test_get_project_structure(self, tmp_path):
        """Test project structure analysis."""
        # Create files
        (tmp_path / "file1.py").write_text("test")
        (tmp_path / "dir1").mkdir()
        (tmp_path / "dir1" / "file2.txt").write_text("content")
        
        manager = ContextManager(project_root=tmp_path)
        structure = manager._get_project_structure()
        
        assert len(structure['directories']) == 1
        assert len(structure['files']) == 2
        assert structure['total_size'] > 0
    
    def test_save_context_json(self, tmp_path):
        """Test saving context as JSON."""
        manager = ContextManager(project_root=tmp_path)
        context = {'test': 'data'}
        
        output_file = tmp_path / "context.json"
        manager.save_context(context, output_file, format='json')
        
        assert output_file.exists()
        import json
        loaded = json.loads(output_file.read_text())
        assert loaded == context
    
    def test_save_context_yaml(self, tmp_path):
        """Test saving context as YAML."""
        manager = ContextManager(project_root=tmp_path)
        context = {'test': 'data'}
        
        output_file = tmp_path / "context.yaml"
        manager.save_context(context, output_file, format='yaml')
        
        assert output_file.exists()
        import yaml
        loaded = yaml.safe_load(output_file.read_text())
        assert loaded == context
    
    def test_ai_ready_context(self, tmp_path):
        """Test AI-ready context generation."""
        (tmp_path / "README.md").write_text("# Test Project\nA test project")
        (tmp_path / "main.py").write_text("def main(): pass")
        
        manager = ContextManager(project_root=tmp_path)
        context = manager.generate_context(ai_ready=True)
        
        assert 'system_prompt' in context
        assert 'project_summary' in context
        assert 'key_files' in context
        assert 'context_data' in context