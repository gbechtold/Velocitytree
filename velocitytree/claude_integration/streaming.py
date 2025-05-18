"""Context streaming for efficient Claude interactions."""

from pathlib import Path
from typing import Dict, Any, List, Optional, Iterator
from dataclasses import dataclass
import json

from ..utils import logger


@dataclass
class StreamConfig:
    """Configuration for context streaming."""
    chunk_size: int = 2048  # tokens per chunk
    max_chunks: int = 10
    overlap: int = 256  # token overlap between chunks
    prioritize_recent: bool = True
    include_dependencies: bool = True
    context_window: int = 8192  # Claude's context window


class ContextStreamer:
    """Handles efficient context streaming for large files."""
    
    def __init__(self, config: Optional[StreamConfig] = None):
        """Initialize context streamer.
        
        Args:
            config: Streaming configuration
        """
        self.config = config or StreamConfig()
    
    def stream_file(
        self,
        file_path: Path,
        focus_line: Optional[int] = None,
        context_lines: int = 50
    ) -> Iterator[str]:
        """Stream file content in chunks.
        
        Args:
            file_path: Path to file
            focus_line: Line number to focus on
            context_lines: Lines of context around focus
            
        Yields:
            Content chunks
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = file_path.read_text()
        lines = content.splitlines()
        
        if focus_line:
            # Stream focused context first
            yield from self._stream_focused_context(
                lines, focus_line, context_lines
            )
        else:
            # Stream entire file in chunks
            yield from self._stream_chunks(content)
    
    def stream_multiple_files(
        self,
        files: List[Path],
        context: Optional[Dict[str, Any]] = None
    ) -> Iterator[str]:
        """Stream multiple files with priority ordering.
        
        Args:
            files: List of file paths
            context: Additional context for prioritization
            
        Yields:
            Content chunks
        """
        # Prioritize files based on context
        prioritized_files = self._prioritize_files(files, context)
        
        total_chunks = 0
        for file_path in prioritized_files:
            if total_chunks >= self.config.max_chunks:
                logger.info(f"Reached chunk limit ({self.config.max_chunks})")
                break
            
            try:
                for chunk in self.stream_file(file_path):
                    yield chunk
                    total_chunks += 1
                    
                    if total_chunks >= self.config.max_chunks:
                        break
            except Exception as e:
                logger.warning(f"Failed to stream {file_path}: {e}")
                continue
    
    def create_context_summary(
        self,
        files: List[Path],
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """Create a summary of file contexts.
        
        Args:
            files: List of file paths
            focus_areas: Specific areas to focus on
            
        Returns:
            Context summary
        """
        summary_parts = []
        
        for file_path in files[:5]:  # Limit to first 5 files
            try:
                content = file_path.read_text()
                file_summary = self._summarize_file(
                    file_path, content, focus_areas
                )
                summary_parts.append(file_summary)
            except Exception as e:
                logger.warning(f"Failed to summarize {file_path}: {e}")
        
        return "\n\n".join(summary_parts)
    
    def optimize_context(
        self,
        prompt: str,
        files: List[Path],
        max_context: int = None
    ) -> Dict[str, Any]:
        """Optimize context for Claude's context window.
        
        Args:
            prompt: The prompt being sent
            files: List of file paths
            max_context: Maximum context size
            
        Returns:
            Optimized context dictionary
        """
        max_context = max_context or self.config.context_window
        
        # Estimate prompt size
        prompt_tokens = self._estimate_tokens(prompt)
        available_context = max_context - prompt_tokens - 1000  # Reserve space
        
        optimized_context = {
            "prompt": prompt,
            "files": [],
            "truncated": False
        }
        
        current_size = 0
        for file_path in files:
            try:
                content = file_path.read_text()
                content_tokens = self._estimate_tokens(content)
                
                if current_size + content_tokens > available_context:
                    # Truncate or skip
                    if current_size < available_context * 0.8:
                        # Truncate this file
                        truncated_content = self._truncate_content(
                            content,
                            available_context - current_size
                        )
                        optimized_context["files"].append({
                            "path": str(file_path),
                            "content": truncated_content,
                            "truncated": True
                        })
                        optimized_context["truncated"] = True
                    break
                else:
                    optimized_context["files"].append({
                        "path": str(file_path),
                        "content": content,
                        "truncated": False
                    })
                    current_size += content_tokens
                    
            except Exception as e:
                logger.warning(f"Failed to process {file_path}: {e}")
        
        return optimized_context
    
    def _stream_chunks(self, content: str) -> Iterator[str]:
        """Stream content in overlapping chunks."""
        lines = content.splitlines()
        chunk_lines = self.config.chunk_size // 50  # Approximate lines per chunk
        overlap_lines = self.config.overlap // 50
        
        start = 0
        while start < len(lines):
            end = min(start + chunk_lines, len(lines))
            chunk = "\n".join(lines[start:end])
            
            yield chunk
            
            # Move forward with overlap
            start = end - overlap_lines
            if start >= len(lines) - overlap_lines:
                break
    
    def _stream_focused_context(
        self,
        lines: List[str],
        focus_line: int,
        context_lines: int
    ) -> Iterator[str]:
        """Stream context around a focus line."""
        # Adjust for 0-based indexing
        focus_idx = focus_line - 1
        
        # Calculate context window
        start = max(0, focus_idx - context_lines)
        end = min(len(lines), focus_idx + context_lines + 1)
        
        # First chunk: immediate context
        immediate_start = max(0, focus_idx - 10)
        immediate_end = min(len(lines), focus_idx + 11)
        
        yield "\n".join(lines[immediate_start:immediate_end])
        
        # Subsequent chunks: expanding context
        if start < immediate_start:
            yield "\n".join(lines[start:immediate_start])
        
        if immediate_end < end:
            yield "\n".join(lines[immediate_end:end])
    
    def _prioritize_files(
        self,
        files: List[Path],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Path]:
        """Prioritize files based on context."""
        if not context:
            return files
        
        # Simple prioritization based on file types and names
        priority_patterns = context.get("priority_patterns", [])
        recent_files = context.get("recent_files", [])
        
        def get_priority(file_path: Path) -> int:
            priority = 0
            
            # Recent files get higher priority
            if str(file_path) in recent_files:
                priority += 10
            
            # Pattern matching
            for i, pattern in enumerate(priority_patterns):
                if pattern in str(file_path):
                    priority += len(priority_patterns) - i
            
            # File type priorities
            if file_path.suffix == ".py":
                priority += 5
            elif file_path.suffix in [".md", ".rst", ".txt"]:
                priority += 3
            
            return priority
        
        return sorted(files, key=get_priority, reverse=True)
    
    def _summarize_file(
        self,
        file_path: Path,
        content: str,
        focus_areas: Optional[List[str]] = None
    ) -> str:
        """Create a summary of a file."""
        lines = content.splitlines()
        
        summary_parts = [f"File: {file_path}"]
        
        # Add basic stats
        summary_parts.append(f"Lines: {len(lines)}")
        summary_parts.append(f"Size: {len(content)} characters")
        
        # Add key sections
        if file_path.suffix == ".py":
            # Python file summary
            imports = [line for line in lines if line.strip().startswith(("import ", "from "))]
            classes = [line for line in lines if line.strip().startswith("class ")]
            functions = [line for line in lines if line.strip().startswith("def ")]
            
            if imports:
                summary_parts.append(f"Imports: {len(imports)}")
            if classes:
                summary_parts.append(f"Classes: {len(classes)}")
                summary_parts.extend(classes[:3])  # Show first 3
            if functions:
                summary_parts.append(f"Functions: {len(functions)}")
                summary_parts.extend(functions[:3])  # Show first 3
        
        # Add focus area matches
        if focus_areas:
            matches = []
            for i, line in enumerate(lines):
                for focus in focus_areas:
                    if focus.lower() in line.lower():
                        matches.append(f"Line {i+1}: {line.strip()}")
                        break
            
            if matches:
                summary_parts.append("\nFocus area matches:")
                summary_parts.extend(matches[:5])  # Show first 5
        
        return "\n".join(summary_parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4
    
    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit token limit."""
        estimated_chars = max_tokens * 4
        
        if len(content) <= estimated_chars:
            return content
        
        # Truncate with ellipsis
        truncated = content[:estimated_chars - 100]
        
        # Try to truncate at a natural boundary
        last_newline = truncated.rfind('\n')
        if last_newline > estimated_chars * 0.8:
            truncated = truncated[:last_newline]
        
        return truncated + "\n... (content truncated)"