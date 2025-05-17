"""
Core functionality for Velocitytree.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Set
import pathspec
from rich.progress import Progress

from .utils import logger, get_file_info
from .constants import (
    DEFAULT_EXCLUDE_PATTERNS,
    DEFAULT_INCLUDE_EXTENSIONS,
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_BINARY_EXTENSIONS
)


class TreeFlattener:
    """Flattens directory structures similar to TreeTamer functionality."""
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
        include_extensions: Optional[List[str]] = None,
        preserve_structure: bool = False,
        follow_symlinks: bool = False
    ):
        self.output_dir = Path(output_dir or "tamed_tree")
        self.exclude_patterns = exclude_patterns or DEFAULT_EXCLUDE_PATTERNS
        self.include_extensions = include_extensions or DEFAULT_INCLUDE_EXTENSIONS
        self.preserve_structure = preserve_structure
        self.follow_symlinks = follow_symlinks
        self.processed_files: Set[str] = set()
        
        # Initialize pathspec for exclusion patterns
        self._init_pathspec()
    
    def _init_pathspec(self):
        """Initialize pathspec patterns for file exclusion."""
        patterns = self.exclude_patterns + DEFAULT_EXCLUDE_PATTERNS
        self.exclude_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
    
    def _should_process_file(self, path: Path) -> bool:
        """Determine if a file should be processed."""
        # Check if file exists
        if not path.exists():
            return False
            
        # Check symlinks
        if path.is_symlink() and not self.follow_symlinks:
            return False
            
        # Check binary files
        if path.suffix.lower() in DEFAULT_BINARY_EXTENSIONS:
            return False
            
        # Check if file matches exclusion patterns
        if self.exclude_spec.match_file(str(path)):
            return False
            
        # Check include extensions
        if self.include_extensions:
            if path.suffix.lower() not in self.include_extensions:
                return False
                
        return True
    
    def _get_flat_filename(self, path: Path, root_dir: Path) -> str:
        """Generate a flattened filename from a path."""
        relative_path = path.relative_to(root_dir)
        
        if self.preserve_structure:
            return str(relative_path)
        
        # Replace path separators with underscores
        flat_name = str(relative_path).replace(os.sep, '_')
        
        # Handle name collisions
        if flat_name in self.processed_files:
            hash_suffix = hashlib.md5(str(path).encode()).hexdigest()[:8]
            name_parts = flat_name.rsplit('.', 1)
            if len(name_parts) == 2:
                flat_name = f"{name_parts[0]}_{hash_suffix}.{name_parts[1]}"
            else:
                flat_name = f"{flat_name}_{hash_suffix}"
        
        return flat_name
    
    def flatten(self, source_dir: Optional[Path] = None) -> Dict[str, any]:
        """Flatten the directory structure."""
        source_dir = Path(source_dir or os.getcwd())
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        stats = {
            'files_processed': 0,
            'files_skipped': 0,
            'total_size': 0,
            'output_dir': str(self.output_dir)
        }
        
        # Process files
        for path in source_dir.rglob('*'):
            if path.is_file() and self._should_process_file(path):
                flat_name = self._get_flat_filename(path, source_dir)
                output_path = self.output_dir / flat_name
                
                try:
                    # Create parent directories if preserving structure
                    if self.preserve_structure:
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(path, output_path)
                    self.processed_files.add(flat_name)
                    
                    stats['files_processed'] += 1
                    stats['total_size'] += path.stat().st_size
                    
                    logger.debug(f"Processed: {path} -> {output_path}")
                    
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
                    stats['files_skipped'] += 1
        
        # Generate structure file if tree command is available
        self._generate_structure_file(source_dir)
        
        return stats
    
    def _generate_structure_file(self, source_dir: Path):
        """Generate a file containing the original directory structure."""
        structure_file = self.output_dir / 'original_structure.txt'
        
        try:
            import subprocess
            result = subprocess.run(
                ['tree', str(source_dir)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                structure_file.write_text(result.stdout)
                logger.info("Generated structure file")
        except Exception as e:
            logger.debug(f"Could not generate structure file: {e}")


class ContextManager:
    """Manages project context for AI integration and documentation."""
    
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = Path(project_root or os.getcwd())
        self.context_data = {}
    
    def generate_context(
        self,
        include_code: bool = True,
        include_structure: bool = True,
        include_docs: bool = True,
        ai_ready: bool = False
    ) -> Dict[str, any]:
        """Generate comprehensive project context."""
        context = {
            'project_name': self.project_root.name,
            'project_path': str(self.project_root),
            'generated_at': os.environ.get('TODAY', 'unknown'),
            'context_version': '1.0'
        }
        
        if include_structure:
            context['structure'] = self._get_project_structure()
        
        if include_code:
            context['code_summary'] = self._get_code_summary()
        
        if include_docs:
            context['documentation'] = self._get_documentation()
        
        if ai_ready:
            context = self._format_for_ai(context)
        
        return context
    
    def _get_project_structure(self) -> Dict[str, any]:
        """Get project directory structure."""
        structure = {
            'directories': [],
            'files': [],
            'total_size': 0
        }
        
        for path in self.project_root.rglob('*'):
            if path.is_dir():
                structure['directories'].append(str(path.relative_to(self.project_root)))
            else:
                file_info = get_file_info(path)
                structure['files'].append({
                    'path': str(path.relative_to(self.project_root)),
                    'size': file_info['size'],
                    'extension': file_info['extension']
                })
                structure['total_size'] += file_info['size']
        
        return structure
    
    def _get_code_summary(self) -> Dict[str, any]:
        """Generate code summary statistics."""
        summary = {
            'languages': {},
            'total_lines': 0,
            'total_files': 0
        }
        
        # Count lines and files by language
        for ext in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs']:
            count = 0
            lines = 0
            
            for path in self.project_root.rglob(f'*{ext}'):
                if path.is_file():
                    count += 1
                    lines += len(path.read_text().splitlines())
            
            if count > 0:
                summary['languages'][ext] = {
                    'files': count,
                    'lines': lines
                }
                summary['total_files'] += count
                summary['total_lines'] += lines
        
        return summary
    
    def _get_documentation(self) -> Dict[str, any]:
        """Extract documentation from the project."""
        docs = {
            'readme': None,
            'license': None,
            'api_docs': [],
            'guides': []
        }
        
        # Find README
        for name in ['README.md', 'README.rst', 'README.txt', 'README']:
            readme_path = self.project_root / name
            if readme_path.exists():
                docs['readme'] = readme_path.read_text()
                break
        
        # Find LICENSE
        for name in ['LICENSE', 'LICENSE.txt', 'LICENSE.md']:
            license_path = self.project_root / name
            if license_path.exists():
                docs['license'] = license_path.read_text()
                break
        
        # Find other documentation
        docs_dir = self.project_root / 'docs'
        if docs_dir.exists():
            for doc_file in docs_dir.rglob('*.md'):
                docs['guides'].append({
                    'name': doc_file.name,
                    'path': str(doc_file.relative_to(self.project_root))
                })
        
        return docs
    
    def _format_for_ai(self, context: Dict[str, any]) -> Dict[str, any]:
        """Format context for AI consumption."""
        ai_context = {
            'system_prompt': self._generate_system_prompt(context),
            'project_summary': self._generate_project_summary(context),
            'key_files': self._identify_key_files(context),
            'context_data': context
        }
        
        return ai_context
    
    def _generate_system_prompt(self, context: Dict[str, any]) -> str:
        """Generate a system prompt for AI assistants."""
        prompt = f"""
You are assisting with the {context['project_name']} project.
Project path: {context['project_path']}

Project structure summary:
- Total directories: {len(context.get('structure', {}).get('directories', []))}
- Total files: {len(context.get('structure', {}).get('files', []))}
- Primary languages: {', '.join(context.get('code_summary', {}).get('languages', {}).keys())}

Please provide assistance based on this project context.
"""
        return prompt
    
    def _generate_project_summary(self, context: Dict[str, any]) -> str:
        """Generate a concise project summary."""
        readme = context.get('documentation', {}).get('readme', '')
        
        if readme:
            # Extract first paragraph or first 200 characters
            lines = readme.split('\n')
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    return line.strip()
        
        return f"A {context['project_name']} project with {context.get('code_summary', {}).get('total_files', 0)} files."
    
    def _identify_key_files(self, context: Dict[str, any]) -> List[str]:
        """Identify key files in the project."""
        key_files = []
        
        # Add main entry points
        for name in ['main.py', 'app.py', 'index.js', 'main.go', 'main.rs']:
            for file_info in context.get('structure', {}).get('files', []):
                if file_info['path'].endswith(name):
                    key_files.append(file_info['path'])
        
        # Add configuration files
        for name in ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod']:
            for file_info in context.get('structure', {}).get('files', []):
                if file_info['path'].endswith(name):
                    key_files.append(file_info['path'])
        
        return key_files
    
    def save_context(self, context: Dict[str, any], output_path: Path, format: str = 'json'):
        """Save context to file in specified format."""
        output_path = Path(output_path)
        
        if format == 'json':
            import json
            output_path.write_text(json.dumps(context, indent=2))
        elif format == 'yaml':
            import yaml
            output_path.write_text(yaml.dump(context, default_flow_style=False))
        elif format == 'markdown':
            md_content = self._context_to_markdown(context)
            output_path.write_text(md_content)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _context_to_markdown(self, context: Dict[str, any]) -> str:
        """Convert context to markdown format."""
        md = f"# {context['project_name']} Context\n\n"
        md += f"Generated at: {context['generated_at']}\n\n"
        
        if 'project_summary' in context:
            md += f"## Summary\n{context['project_summary']}\n\n"
        
        if 'structure' in context:
            md += "## Project Structure\n"
            md += f"- Directories: {len(context['structure']['directories'])}\n"
            md += f"- Files: {len(context['structure']['files'])}\n"
            md += f"- Total size: {context['structure']['total_size']:,} bytes\n\n"
        
        if 'code_summary' in context:
            md += "## Code Summary\n"
            for lang, stats in context['code_summary']['languages'].items():
                md += f"- {lang}: {stats['files']} files, {stats['lines']} lines\n"
            md += "\n"
        
        return md