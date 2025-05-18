"""Incremental documentation update system."""

import ast
import difflib
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from ..code_analysis.analyzer import CodeAnalyzer
from ..code_analysis.models import (
    ModuleAnalysis,
    ClassAnalysis,
    FunctionAnalysis,
)
from .generator import DocGenerator
from .models import (
    DocFormat,
    DocType,
    DocStyle,
    DocumentationResult,
    DocConfig,
    DocMetadata,
)
from ..utils import logger


@dataclass
class FileChange:
    """Represents a change in a file."""
    path: str
    old_content: str
    new_content: str
    change_type: str  # 'added', 'modified', 'deleted'
    change_lines: List[int]
    
    
@dataclass
class DocChange:
    """Represents a change in documentation."""
    element: str  # function/class/module name
    element_type: str  # 'function', 'class', 'module'
    old_doc: Optional[str]
    new_doc: Optional[str]
    change_type: str  # 'added', 'modified', 'deleted'
    location: str  # file:line
    
    
@dataclass
class ChangeSet:
    """Collection of file and documentation changes."""
    file_changes: List[FileChange]
    doc_changes: List[DocChange]
    timestamp: float
    

class IncrementalDocUpdater:
    """Handle incremental documentation updates."""
    
    def __init__(self, config: Optional[DocConfig] = None):
        """Initialize the incremental updater.
        
        Args:
            config: Documentation configuration
        """
        self.config = config or DocConfig()
        self.analyzer = CodeAnalyzer()
        self.generator = DocGenerator(config)
        self.cache_dir = Path.home() / ".velocitytree" / "doc_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_cache()
        
    def _init_cache(self):
        """Initialize documentation cache."""
        self.cache_file = self.cache_dir / "doc_cache.json"
        self.hash_file = self.cache_dir / "file_hashes.json"
        
        # Load existing caches
        self.doc_cache = self._load_json(self.cache_file)
        self.file_hashes = self._load_json(self.hash_file)
        
        # Create files if they don't exist
        if not self.cache_file.exists():
            self._save_json({}, self.cache_file)
        if not self.hash_file.exists():
            self._save_json({}, self.hash_file)
        
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file or return empty dict."""
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache file {file_path}: {e}")
        return {}
        
    def _save_json(self, data: Dict, file_path: Path):
        """Save data to JSON file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache file {file_path}: {e}")
            
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""
            
    def detect_changes(self, file_paths: List[str]) -> ChangeSet:
        """Detect changes in files since last update.
        
        Args:
            file_paths: List of file paths to check
            
        Returns:
            Set of detected changes
        """
        file_changes = []
        doc_changes = []
        
        for file_path in file_paths:
            # Skip non-existent files
            if not os.path.exists(file_path):
                continue
                
            # Calculate current hash
            current_hash = self._calculate_file_hash(file_path)
            old_hash = self.file_hashes.get(file_path)
            
            # Check if file changed
            if current_hash != old_hash:
                change_type = 'added' if old_hash is None else 'modified'
                
                # Get old content from cache if available
                old_content = ""
                if file_path in self.doc_cache:
                    old_content = self.doc_cache[file_path].get('content', '')
                    
                # Read current content
                with open(file_path, 'r') as f:
                    new_content = f.read()
                    
                # Find changed lines
                change_lines = self._find_changed_lines(old_content, new_content)
                
                file_change = FileChange(
                    path=file_path,
                    old_content=old_content,
                    new_content=new_content,
                    change_type=change_type,
                    change_lines=change_lines,
                )
                file_changes.append(file_change)
                
                # Detect documentation changes
                doc_changes.extend(self._analyze_doc_changes(file_change))
                
        # Check for deleted files
        for file_path in list(self.file_hashes.keys()):
            if file_path not in file_paths and not os.path.exists(file_path):
                file_change = FileChange(
                    path=file_path,
                    old_content=self.doc_cache.get(file_path, {}).get('content', ''),
                    new_content='',
                    change_type='deleted',
                    change_lines=[],
                )
                file_changes.append(file_change)
                
        return ChangeSet(
            file_changes=file_changes,
            doc_changes=doc_changes,
            timestamp=time.time(),
        )
        
    def _find_changed_lines(self, old_content: str, new_content: str) -> List[int]:
        """Find lines that changed between versions."""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        changed_lines = []
        
        line_num = 0
        for line in differ:
            if line.startswith('@@'):
                # Parse line numbers from diff header
                parts = line.split()
                if len(parts) >= 3:
                    new_range = parts[2]
                    if ',' in new_range:
                        start_line = int(new_range.split(',')[0])
                        line_num = start_line
            elif line.startswith('+') and not line.startswith('+++'):
                changed_lines.append(line_num)
                line_num += 1
            elif not line.startswith('-'):
                line_num += 1
                
        return changed_lines
        
    def _analyze_doc_changes(self, file_change: FileChange) -> List[DocChange]:
        """Analyze what documentation changes are needed."""
        doc_changes = []
        
        # Parse old and new AST
        try:
            old_ast = ast.parse(file_change.old_content) if file_change.old_content else None
            new_ast = ast.parse(file_change.new_content) if file_change.new_content else None
        except SyntaxError:
            return doc_changes
            
        # Find changed functions and classes
        old_elements = self._extract_elements(old_ast) if old_ast else {}
        new_elements = self._extract_elements(new_ast) if new_ast else {}
        
        # Check for added/modified/deleted elements
        all_keys = set(old_elements.keys()) | set(new_elements.keys())
        
        for key in all_keys:
            old_elem = old_elements.get(key)
            new_elem = new_elements.get(key)
            
            if old_elem is None and new_elem is not None:
                # Added
                doc_change = DocChange(
                    element=key,
                    element_type=new_elem['type'],
                    old_doc=None,
                    new_doc=new_elem.get('docstring'),
                    change_type='added',
                    location=f"{file_change.path}:{new_elem.get('line', 0)}",
                )
                doc_changes.append(doc_change)
            elif old_elem is not None and new_elem is None:
                # Deleted
                doc_change = DocChange(
                    element=key,
                    element_type=old_elem['type'],
                    old_doc=old_elem.get('docstring'),
                    new_doc=None,
                    change_type='deleted',
                    location=f"{file_change.path}:{old_elem.get('line', 0)}",
                )
                doc_changes.append(doc_change)
            elif old_elem and new_elem:
                # Check if modified
                if (old_elem.get('docstring') != new_elem.get('docstring') or
                    old_elem.get('signature') != new_elem.get('signature')):
                    doc_change = DocChange(
                        element=key,
                        element_type=new_elem['type'],
                        old_doc=old_elem.get('docstring'),
                        new_doc=new_elem.get('docstring'),
                        change_type='modified',
                        location=f"{file_change.path}:{new_elem.get('line', 0)}",
                    )
                    doc_changes.append(doc_change)
                    
        return doc_changes
        
    def _extract_elements(self, tree: ast.AST) -> Dict[str, Dict]:
        """Extract functions and classes from AST."""
        elements = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                elements[node.name] = {
                    'type': 'function',
                    'docstring': ast.get_docstring(node),
                    'signature': self._get_function_signature(node),
                    'line': node.lineno,
                }
            elif isinstance(node, ast.ClassDef):
                elements[node.name] = {
                    'type': 'class',
                    'docstring': ast.get_docstring(node),
                    'line': node.lineno,
                }
                # Add methods
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        method_key = f"{node.name}.{child.name}"
                        elements[method_key] = {
                            'type': 'method',
                            'docstring': ast.get_docstring(child),
                            'signature': self._get_function_signature(child),
                            'line': child.lineno,
                        }
                        
        return elements
        
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature from AST node."""
        args = []
        for arg in node.args.args:
            args.append(arg.arg)
        return f"{node.name}({', '.join(args)})"
        
    def update_documentation(
        self,
        change_set: ChangeSet,
        doc_format: Optional[DocFormat] = None,
        style: Optional[DocStyle] = None,
    ) -> Dict[str, DocumentationResult]:
        """Update documentation based on detected changes.
        
        Args:
            change_set: Set of changes to process
            doc_format: Documentation format
            style: Documentation style
            
        Returns:
            Dictionary of updated documentation results by file
        """
        results = {}
        
        # Group changes by file
        changes_by_file = {}
        for change in change_set.file_changes:
            changes_by_file[change.path] = change
            
        for file_path, file_change in changes_by_file.items():
            if file_change.change_type == 'deleted':
                # Remove from cache
                self.file_hashes.pop(file_path, None)
                self.doc_cache.pop(file_path, None)
                continue
                
            # Check if only specific elements changed
            relevant_doc_changes = [
                dc for dc in change_set.doc_changes 
                if dc.location.startswith(file_path)
            ]
            
            if relevant_doc_changes and self._can_update_incrementally(relevant_doc_changes):
                # Update only changed elements
                result = self._update_elements(
                    file_path,
                    relevant_doc_changes,
                    doc_format,
                    style,
                )
            else:
                # Regenerate full documentation
                result = self.generator.generate_documentation(
                    file_path,
                    format=doc_format,
                    style=style,
                )
                
            results[file_path] = result
            
            # Update cache
            self.file_hashes[file_path] = self._calculate_file_hash(file_path)
            self.doc_cache[file_path] = {
                'content': file_change.new_content,
                'documentation': result.content,
                'timestamp': time.time(),
            }
            
        # Save caches
        self._save_json(self.file_hashes, self.hash_file)
        self._save_json(self.doc_cache, self.cache_file)
        
        return results
        
    def _can_update_incrementally(self, doc_changes: List[DocChange]) -> bool:
        """Check if changes can be updated incrementally."""
        # Can update incrementally if:
        # 1. Only functions/methods changed (not module-level changes)
        # 2. No structural changes (only docstring/signature changes)
        
        for change in doc_changes:
            if change.element_type == 'module':
                return False
            if change.change_type in ['added', 'deleted']:
                # Structural changes require full regeneration
                return False
                
        return True
        
    def _update_elements(
        self,
        file_path: str,
        doc_changes: List[DocChange],
        doc_format: Optional[DocFormat],
        style: Optional[DocStyle],
    ) -> DocumentationResult:
        """Update specific elements in documentation."""
        # Get current analysis
        analysis = self.analyzer.analyze_file(file_path)
        if not analysis:
            raise ValueError(f"Could not analyze file: {file_path}")
            
        # Get cached documentation or generate new
        cached_doc = self.doc_cache.get(file_path, {}).get('documentation')
        if not cached_doc:
            return self.generator.generate_documentation(
                file_path,
                format=doc_format,
                style=style,
            )
            
        # Apply incremental updates
        updated_content = cached_doc
        
        for change in doc_changes:
            if change.change_type == 'modified':
                # Find and update the specific element in the documentation
                updated_content = self._replace_element_documentation(
                    updated_content,
                    change.element,
                    change.new_doc,
                    analysis,
                    style,
                )
                
        # Create updated result
        return DocumentationResult(
            content=updated_content,
            format=doc_format or self.config.format,
            metadata=self.generator._get_metadata(analysis, DocType.MODULE),
            sections=[],  # Would need to parse sections from content
            issues=[],    # Would need to re-check quality
            quality_score=90.0,  # Placeholder
            completeness_score=95.0,  # Placeholder
            generation_time=0.1,  # Incremental update is fast
        )
        
    def _replace_element_documentation(
        self,
        content: str,
        element_name: str,
        new_docstring: Optional[str],
        analysis: ModuleAnalysis,
        style: Optional[DocStyle],
    ) -> str:
        """Replace documentation for a specific element."""
        # This is a simplified implementation
        # In practice, would need to parse the documentation format
        # and update the specific section
        
        lines = content.split('\n')
        updated_lines = []
        in_element = False
        element_pattern = f"### `{element_name}"  # Markdown format
        
        for i, line in enumerate(lines):
            if element_pattern in line:
                in_element = True
                updated_lines.append(line)
                # Skip to description
                while i < len(lines) - 1 and lines[i + 1].strip():
                    i += 1
                    if not lines[i].startswith('#'):
                        break
                # Replace description
                if new_docstring:
                    updated_lines.append(new_docstring.split('\n')[0])
                else:
                    updated_lines.append("No description available.")
            elif in_element and line.startswith('###'):
                in_element = False
                updated_lines.append(line)
            elif not in_element:
                updated_lines.append(line)
                
        return '\n'.join(updated_lines)
        
    def watch_files(
        self,
        file_patterns: List[str],
        callback: Optional[callable] = None,
        interval: float = 1.0,
    ):
        """Watch files for changes and update documentation.
        
        Args:
            file_patterns: List of file patterns to watch
            callback: Optional callback for updates
            interval: Check interval in seconds
        """
        import glob
        
        logger.info(f"Watching files matching patterns: {file_patterns}")
        
        try:
            while True:
                # Expand patterns to file paths
                file_paths = []
                for pattern in file_patterns:
                    file_paths.extend(glob.glob(pattern, recursive=True))
                    
                # Detect changes
                change_set = self.detect_changes(file_paths)
                
                if change_set.file_changes or change_set.doc_changes:
                    logger.info(f"Detected {len(change_set.file_changes)} file changes")
                    
                    # Update documentation
                    results = self.update_documentation(change_set)
                    
                    # Call callback if provided
                    if callback:
                        callback(results, change_set)
                    else:
                        for file_path, result in results.items():
                            logger.info(f"Updated documentation for {file_path}")
                            
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped watching files")
            
    def get_cached_documentation(
        self,
        file_path: str,
    ) -> Optional[DocumentationResult]:
        """Get cached documentation for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Cached documentation result or None
        """
        cached = self.doc_cache.get(file_path)
        if cached and 'documentation' in cached:
            # Check if file hasn't changed
            current_hash = self._calculate_file_hash(file_path)
            cached_hash = self.file_hashes.get(file_path)
            
            if current_hash == cached_hash:
                # Return cached documentation
                return DocumentationResult(
                    content=cached['documentation'],
                    format=self.config.format,
                    metadata=DocMetadata(
                        title=Path(file_path).stem,
                        description="Cached documentation",
                    ),
                    sections=[],
                    issues=[],
                    quality_score=100.0,
                    completeness_score=100.0,
                    generation_time=0.0,
                )
                
        return None
        
    def invalidate_cache(self, file_paths: Optional[List[str]] = None):
        """Invalidate documentation cache.
        
        Args:
            file_paths: Specific files to invalidate (None for all)
        """
        if file_paths is None:
            # Clear all caches
            self.file_hashes.clear()
            self.doc_cache.clear()
        else:
            # Clear specific files
            for file_path in file_paths:
                self.file_hashes.pop(file_path, None)
                self.doc_cache.pop(file_path, None)
                
        # Save updated caches
        self._save_json(self.file_hashes, self.hash_file)
        self._save_json(self.doc_cache, self.cache_file)