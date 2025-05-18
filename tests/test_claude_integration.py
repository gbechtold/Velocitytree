"""Tests for Claude integration."""

import pytest
from pathlib import Path
import json
import time
import subprocess
from unittest.mock import Mock, patch, MagicMock

from velocitytree.claude_integration import (
    LocalClaudeProvider,
    ClaudeConfig,
    ContextStreamer,
    StreamConfig,
    PromptManager,
    PromptTemplate,
    ResponseCache,
    SmartCache
)


class TestLocalClaudeProvider:
    """Test local Claude provider."""
    
    @pytest.fixture
    def provider_config(self):
        """Create test configuration."""
        return ClaudeConfig(
            model="claude-3.5-sonnet",
            max_tokens=2048,
            timeout=30,
            use_cache=False
        )
    
    @pytest.fixture
    def mock_claude_cli(self):
        """Mock Claude CLI availability."""
        with patch('shutil.which') as mock_which:
            mock_which.return_value = "/usr/local/bin/claude"
            yield mock_which
    
    def test_find_claude_cli(self, mock_claude_cli):
        """Test finding Claude CLI."""
        provider = LocalClaudeProvider()
        assert provider._cli_path == Path("/usr/local/bin/claude")
    
    def test_no_claude_cli(self):
        """Test handling missing Claude CLI."""
        with patch('shutil.which', return_value=None):
            with pytest.raises(RuntimeError, match="Claude CLI not found"):
                LocalClaudeProvider()
    
    def test_query_success(self, provider_config, mock_claude_cli):
        """Test successful query."""
        provider = LocalClaudeProvider(provider_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Test response",
                stderr=""
            )
            
            response = provider.query("Test prompt")
            assert response == "Test response"
            
            # Check command construction
            call_args = mock_run.call_args[0][0]
            assert "--model" in call_args
            assert "claude-3.5-sonnet" in call_args
            assert "Test prompt" in call_args
    
    def test_query_with_files(self, provider_config, mock_claude_cli, tmp_path):
        """Test query with file context."""
        provider = LocalClaudeProvider(provider_config)
        
        # Create test file
        test_file = tmp_path / "test.py"
        test_file.write_text("def test(): pass")
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Analysis result",
                stderr=""
            )
            
            response = provider.query(
                "Analyze this code",
                files=[test_file]
            )
            
            assert response == "Analysis result"
            
            # Check file was included
            call_args = mock_run.call_args[0][0]
            assert "--file" in call_args
            assert str(test_file) in call_args
    
    def test_query_with_context(self, provider_config, mock_claude_cli):
        """Test query with additional context."""
        provider = LocalClaudeProvider(provider_config)
        
        context = {
            "project": "test_project",
            "language": "python"
        }
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Context response",
                stderr=""
            )
            
            response = provider.query(
                "Generate code",
                context=context
            )
            
            assert response == "Context response"
            
            # Check context was included
            call_args = mock_run.call_args[0][0]
            assert "--system" in call_args
            system_idx = call_args.index("--system") + 1
            assert "Context:" in call_args[system_idx]
            assert "test_project" in call_args[system_idx]
    
    def test_stream_query(self, provider_config, mock_claude_cli):
        """Test streaming query."""
        provider = LocalClaudeProvider(provider_config)
        
        # Mock streaming process
        mock_process = MagicMock()
        mock_process.stdout = [
            '{"chunk": "Part 1"}',
            '{"chunk": "Part 2"}',
            '{"chunk": "Part 3"}'
        ]
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        
        with patch('subprocess.Popen', return_value=mock_process):
            chunks = list(provider.stream_query("Test prompt"))
            
            assert chunks == ["Part 1", "Part 2", "Part 3"]
    
    def test_retry_mechanism(self, provider_config, mock_claude_cli):
        """Test retry mechanism."""
        provider_config.retry_attempts = 3
        provider = LocalClaudeProvider(provider_config)
        
        with patch('subprocess.run') as mock_run:
            # First two attempts fail, third succeeds
            mock_run.side_effect = [
                RuntimeError("Failed"),
                RuntimeError("Failed again"),
                MagicMock(returncode=0, stdout="Success", stderr="")
            ]
            
            response = provider.query("Test prompt")
            assert response == "Success"
            assert mock_run.call_count == 3
    
    def test_fallback_model(self, provider_config, mock_claude_cli):
        """Test fallback model."""
        provider_config.fallback_model = "claude-2"
        provider = LocalClaudeProvider(provider_config)
        
        with patch('subprocess.run') as mock_run:
            # First attempt fails
            mock_run.side_effect = [
                RuntimeError("Primary model failed"),
                MagicMock(returncode=0, stdout="Fallback response", stderr="")
            ]
            
            response = provider.query("Test prompt")
            assert response == "Fallback response"
            
            # Check fallback model was used
            second_call_args = mock_run.call_args_list[1][0][0]
            assert "claude-2" in second_call_args
    
    def test_health_check(self, provider_config, mock_claude_cli):
        """Test health check."""
        provider = LocalClaudeProvider(provider_config)
        
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                # Auth check
                MagicMock(returncode=0, stdout="", stderr=""),
                # Version check
                MagicMock(returncode=0, stdout="Claude CLI v1.0.0", stderr=""),
                # Auth check again
                MagicMock(returncode=0, stdout="", stderr="")
            ]
            
            health = provider.health_check()
            
            assert health["available"]
            assert health["authenticated"]
            assert health["version"] == "Claude CLI v1.0.0"


class TestContextStreamer:
    """Test context streaming."""
    
    @pytest.fixture
    def streamer(self):
        """Create test streamer."""
        config = StreamConfig(
            chunk_size=1024,
            max_chunks=5,
            overlap=128
        )
        return ContextStreamer(config)
    
    def test_stream_file(self, streamer, tmp_path):
        """Test streaming single file."""
        # Create test file
        test_file = tmp_path / "test.py"
        content = "\n".join([f"Line {i}" for i in range(100)])
        test_file.write_text(content)
        
        chunks = list(streamer.stream_file(test_file))
        
        assert len(chunks) > 0
        # Check chunks overlap
        if len(chunks) > 1:
            assert any(
                chunk in chunks[i+1] 
                for i, chunk in enumerate(chunks[:-1])
            )
    
    def test_stream_focused_context(self, streamer, tmp_path):
        """Test streaming with focus line."""
        # Create test file
        test_file = tmp_path / "test.py"
        lines = [f"Line {i}" for i in range(100)]
        test_file.write_text("\n".join(lines))
        
        # Focus on line 50
        chunks = list(streamer.stream_file(
            test_file,
            focus_line=50,
            context_lines=20
        ))
        
        # First chunk should contain immediate context
        assert "Line 49" in chunks[0]
        assert "Line 50" in chunks[0]
    
    def test_stream_multiple_files(self, streamer, tmp_path):
        """Test streaming multiple files."""
        # Create test files
        files = []
        for i in range(3):
            file_path = tmp_path / f"test{i}.py"
            file_path.write_text(f"Content of file {i}\n" * 50)
            files.append(file_path)
        
        chunks = list(streamer.stream_multiple_files(files))
        
        assert len(chunks) > 0
        # Check all files were processed
        all_content = "".join(chunks)
        for i in range(3):
            assert f"Content of file {i}" in all_content
    
    def test_context_optimization(self, streamer, tmp_path):
        """Test context optimization for token limits."""
        # Create test files
        files = []
        for i in range(10):
            file_path = tmp_path / f"test{i}.py"
            file_path.write_text("x" * 1000)  # Large content
            files.append(file_path)
        
        optimized = streamer.optimize_context(
            prompt="Test prompt",
            files=files,
            max_context=4096
        )
        
        assert optimized["prompt"] == "Test prompt"
        assert len(optimized["files"]) > 0
        # Some files might be truncated
        if any(f["truncated"] for f in optimized["files"]):
            assert optimized["truncated"]
    
    def test_file_prioritization(self, streamer, tmp_path):
        """Test file prioritization."""
        # Create test files
        files = []
        for i in range(5):
            file_path = tmp_path / f"test{i}.py"
            file_path.write_text(f"File {i}")
            files.append(file_path)
        
        # Prioritize specific files
        context = {
            "recent_files": [str(files[2]), str(files[4])],
            "priority_patterns": ["test2", "test4"]
        }
        
        chunks = list(streamer.stream_multiple_files(files, context))
        
        # Check prioritized files appear first
        first_chunk = chunks[0] if chunks else ""
        assert "File 2" in first_chunk or "File 4" in first_chunk


class TestPromptManager:
    """Test prompt management."""
    
    @pytest.fixture
    def prompt_manager(self, tmp_path):
        """Create test prompt manager."""
        return PromptManager(template_dir=tmp_path)
    
    def test_builtin_templates(self, prompt_manager):
        """Test built-in templates are loaded."""
        templates = prompt_manager.list_templates()
        
        assert "code_analysis" in templates
        assert "generate_docs" in templates
        assert "bug_fix" in templates
        assert "refactoring" in templates
    
    def test_create_prompt(self, prompt_manager):
        """Test creating prompt from template."""
        prompt = prompt_manager.create_prompt(
            "code_analysis",
            file_path="test.py",
            language="python",
            code="def test(): pass",
            additional_context="Test context"
        )
        
        assert "test.py" in prompt
        assert "python" in prompt
        assert "def test(): pass" in prompt
        assert "Test context" in prompt
    
    def test_missing_variables(self, prompt_manager):
        """Test error on missing variables."""
        with pytest.raises(ValueError, match="Missing required variables"):
            prompt_manager.create_prompt(
                "code_analysis",
                file_path="test.py"
                # Missing other required variables
            )
    
    def test_save_custom_template(self, prompt_manager, tmp_path):
        """Test saving custom template."""
        template = PromptTemplate(
            name="custom_test",
            template="Custom {variable}",
            variables=["variable"],
            tags=["test", "custom"]
        )
        
        prompt_manager.save_template(template)
        
        # Check template was saved
        template_file = tmp_path / "custom_test.json"
        assert template_file.exists()
        
        # Check it can be loaded
        prompt = prompt_manager.create_prompt(
            "custom_test",
            variable="value"
        )
        assert prompt == "Custom value"
    
    def test_filter_by_tags(self, prompt_manager):
        """Test filtering templates by tags."""
        analysis_templates = prompt_manager.list_templates(["analysis"])
        
        assert "code_analysis" in analysis_templates
        assert "progress_analysis" in analysis_templates
    
    def test_contextual_prompt(self, prompt_manager):
        """Test creating contextual prompt."""
        context = {
            "project": "test_project",
            "version": "1.0.0"
        }
        
        prompt = prompt_manager.create_contextual_prompt(
            "code_analysis",
            context=context,
            file_path="test.py",
            language="python",
            code="print('test')",
            additional_context=""  # Will be filled by context
        )
        
        assert "test_project" in prompt
        assert "1.0.0" in prompt
    
    def test_optimize_prompt_for_tokens(self, prompt_manager):
        """Test prompt optimization for token limits."""
        # Create long content
        long_code = "x" * 10000
        
        optimized = prompt_manager.optimize_prompt_for_context(
            "code_analysis",
            available_tokens=1000,
            file_path="test.py",
            language="python",
            code=long_code,
            additional_context="Context"
        )
        
        # Should be truncated
        assert len(optimized) < len(long_code)
        assert "... (truncated)" in optimized


class TestResponseCache:
    """Test response caching."""
    
    @pytest.fixture
    def cache(self, tmp_path):
        """Create test cache."""
        return ResponseCache(
            cache_dir=tmp_path / "cache",
            ttl=10,
            max_size=5
        )
    
    def test_basic_cache_operations(self, cache):
        """Test basic get/set operations."""
        # Set value
        cache.set("key1", "value1")
        
        # Get value
        assert cache.get("key1") == "value1"
        
        # Missing key
        assert cache.get("missing") is None
        
        # Delete key
        assert cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_ttl_expiration(self, cache):
        """Test TTL expiration."""
        cache.ttl = 0.1  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        assert cache.get("key1") is None
    
    def test_size_limit(self, cache):
        """Test cache size limit."""
        cache.max_size = 3
        
        # Fill cache
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        # Only last 3 should remain
        assert cache.get("key0") is None
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("missing")  # Miss
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1
        assert stats["hit_rate"] == 0.5
    
    def test_persistence(self, tmp_path):
        """Test cache persistence."""
        cache_dir = tmp_path / "persistent_cache"
        
        # Create cache and add data
        cache1 = ResponseCache(cache_dir=cache_dir, persist=True)
        cache1.set("key1", "value1")
        cache1.set("key2", "value2")
        
        # Create new cache instance
        cache2 = ResponseCache(cache_dir=cache_dir, persist=True)
        
        # Data should be loaded
        assert cache2.get("key1") == "value1"
        assert cache2.get("key2") == "value2"
    
    def test_smart_cache_priority(self):
        """Test smart cache with priorities."""
        cache = SmartCache(max_size=3, persist=False)
        
        # Set values with priorities
        cache.set_with_priority("low", "value1", priority=1)
        cache.set_with_priority("medium", "value2", priority=5)
        cache.set_with_priority("high", "value3", priority=10)
        
        # Add more to trigger eviction
        cache.set_with_priority("new", "value4", priority=3)
        
        # Low priority should be evicted
        assert cache.get("low") is None
        assert cache.get("high") == "value3"
    
    def test_pattern_rules(self):
        """Test pattern-based caching rules."""
        cache = SmartCache(persist=False)
        
        # Add pattern rule with shorter TTL
        cache.add_pattern_rule("temp_", ttl_override=1)
        
        # Set values
        cache.set("temp_key", "temp_value")
        cache.set("normal_key", "normal_value")
        
        # Wait for pattern TTL
        time.sleep(1.5)
        
        # Pattern key should expire
        assert cache.get("temp_key") is None
        assert cache.get("normal_key") == "normal_value"
    
    def test_cache_analysis(self):
        """Test cache usage analysis."""
        cache = SmartCache(persist=False)
        
        # Add various entries
        cache.set("key1", "short")
        cache.set("key2", "x" * 1000)  # Long value
        
        # Access key1 multiple times
        for _ in range(5):
            cache.get("key1")
        
        analysis = cache.analyze_usage()
        
        # Check most accessed
        assert analysis["most_accessed"][0]["key"] == "key1"
        assert analysis["most_accessed"][0]["hits"] == 5
        
        # Check largest values
        assert analysis["largest_values"][0]["key"] == "key2"