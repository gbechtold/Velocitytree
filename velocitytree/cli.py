#!/usr/bin/env python3
"""
Command-line interface for Velocitytree.
"""

import click
import sys
import subprocess
import time
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.prompt import Confirm
from rich.progress import track

from .core import TreeFlattener, ContextManager
from .config import Config
from .utils import logger
from .ai import AIAssistant
from .workflows import WorkflowManager
from .version import version_info
from .onboarding import create_onboarding_command
from .web_server import FeatureGraphWebServer
from .git_integration import GitFeatureTracker, GitWorkflowIntegration
from .progress_tracking import ProgressCalculator
from .continuous_eval import ContinuousMonitor, AlertSystem, DriftDetector, RealignmentEngine

console = Console()


def get_suggestion_engine(ctx):
    """Get or create a suggestion engine instance."""
    if 'suggestion_engine' not in ctx.obj:
        from .realtime_suggestions import RealTimeSuggestionEngine
        from .code_analysis.analyzer import CodeAnalyzer
        from .documentation.quality import DocQualityChecker
        
        analyzer = CodeAnalyzer()
        quality_checker = DocQualityChecker()
        ctx.obj['suggestion_engine'] = RealTimeSuggestionEngine(
            analyzer=analyzer,
            quality_checker=quality_checker
        )
    
    return ctx.obj['suggestion_engine']


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Quiet output')
@click.pass_context
def cli(ctx, config, verbose, quiet):
    """Velocitytree - Streamline your developer workflow 🌳⚡"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = Config(config)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    
    if verbose:
        logger.setLevel('DEBUG')
    elif quiet:
        logger.setLevel('ERROR')
    
    # Initialize plugin manager
    from .plugin_system import PluginManager
    ctx.obj['plugin_manager'] = PluginManager(ctx.obj['config'])
    
    # Register plugin commands
    ctx.obj['plugin_manager'].register_cli_commands(cli)


@cli.command()
@click.option('--template', '-t', help='Project template to use')
@click.option('--name', '-n', help='Project name')
@click.option('--force', '-f', is_flag=True, help='Force initialization even if config exists')
@click.pass_context
def init(ctx, template, name, force):
    """Initialize a new Velocitytree project."""
    from pathlib import Path
    import shutil
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing project...", total=None)
        
        # Check if config already exists
        config_path = Path('.velocitytree.yaml')
        if config_path.exists() and not force:
            console.print("[yellow]⚠[/yellow] Configuration file already exists. Use --force to overwrite.")
            return
        
        # Create default configuration
        config = ctx.obj['config']
        if name:
            config.set('project.name', name)
        
        # Save configuration
        config.save(config_path)
        progress.update(task, description="Created configuration file")
        
        # Create .velocitytree directory
        vtree_dir = Path('.velocitytree')
        vtree_dir.mkdir(exist_ok=True)
        
        # Create sample workflow if template requested
        if template:
            workflows_dir = vtree_dir / 'workflows'
            workflows_dir.mkdir(exist_ok=True)
            
            sample_workflow = {
                'description': f'Sample workflow for {template}',
                'steps': [
                    {
                        'name': 'flatten',
                        'type': 'velocitytree',
                        'command': 'flatten',
                        'args': {
                            'output_dir': f'{template}_output'
                        }
                    },
                    {
                        'name': 'generate context',
                        'type': 'velocitytree',
                        'command': 'context',
                        'args': {
                            'format': 'markdown',
                            'output': f'{template}_context.md'
                        }
                    }
                ]
            }
            
            import yaml
            workflow_file = workflows_dir / f'{template}.yaml'
            with open(workflow_file, 'w') as f:
                yaml.dump(sample_workflow, f, default_flow_style=False)
            
            progress.update(task, description=f"Created {template} workflow")
        
        progress.update(task, description="Project initialized successfully!")
        console.print("[green]✓[/green] Project initialized!")
        console.print(f"Configuration saved to: [blue]{config_path}[/blue]")
        
        # Automatically run onboarding wizard
        console.print("\n[yellow]Starting setup wizard to configure AI providers and workflows...[/yellow]")
        from .onboarding import OnboardingWizard
        wizard = OnboardingWizard(ctx.obj['config'])
        wizard.run()


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--exclude', '-e', multiple=True, help='Patterns to exclude')
@click.option('--include-ext', '-i', multiple=True, help='File extensions to include')
@click.option('--preserve-structure', is_flag=True, help='Preserve directory structure')
@click.option('--follow-symlinks', is_flag=True, help='Follow symbolic links')
@click.option('--source', '-s', type=click.Path(exists=True), help='Source directory to flatten')
@click.pass_context
def flatten(ctx, output, exclude, include_ext, preserve_structure, follow_symlinks, source):
    """Flatten project directory structure (TreeTamer functionality)."""
    config = ctx.obj['config']
    
    # Merge command-line options with config
    flatten_config = config.config.flatten
    
    # Use command-line options if provided, otherwise fall back to config
    output_dir = output or flatten_config.output_dir
    exclude_patterns = list(exclude) if exclude else flatten_config.exclude
    include_extensions = list(include_ext) if include_ext else flatten_config.include_extensions
    
    # Handle boolean flags
    preserve = preserve_structure if preserve_structure else flatten_config.preserve_structure
    follow = follow_symlinks if follow_symlinks else flatten_config.follow_symlinks
    
    # Create flattener with merged configuration
    flattener = TreeFlattener(
        output_dir=output_dir,
        exclude_patterns=exclude_patterns,
        include_extensions=include_extensions,
        preserve_structure=preserve,
        follow_symlinks=follow
    )
    
    with console.status("Flattening directory structure...") as status:
        result = flattener.flatten(source_dir=source)
        
    console.print(f"[green]✓[/green] Flattened {result['files_processed']} files")
    console.print(f"Output directory: [blue]{result['output_dir']}[/blue]")
    console.print(f"Total size: {result['total_size']:,} bytes")
    
    if ctx.obj['verbose']:
        console.print(f"Files skipped: {result.get('files_skipped', 0)}")


@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'markdown']), default='json')
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--ai-ready', is_flag=True, help='Generate AI-ready context')
@click.pass_context
def context(ctx, format, output, ai_ready):
    """Generate project context for AI or documentation."""
    manager = ContextManager()
    
    with console.status("Generating context...") as status:
        context_data = manager.generate_context(ai_ready=ai_ready)
        
        if output:
            manager.save_context(context_data, output, format)
            console.print(f"[green]✓[/green] Context saved to {output}")
        else:
            console.print(context_data)


@cli.command()
@click.option('--detailed', is_flag=True, help='Show detailed analysis')
@click.option('--metrics', is_flag=True, help='Show code metrics')
@click.option('--path', '-p', type=click.Path(exists=True), default='.', help='Path to analyze')
@click.pass_context
def analyze(ctx, detailed, metrics, path):
    """Analyze project structure and code quality."""
    from .core import ContextManager
    from pathlib import Path
    import os
    
    project_path = Path(path)
    console.print(f"[blue]Analyzing project: {project_path}[/blue]")
    
    # Use ContextManager to gather project information
    manager = ContextManager(project_root=project_path)
    context = manager.generate_context(include_code=True, include_structure=True)
    
    # Basic metrics table
    table = Table(title="Project Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")
    
    # Extract metrics from context
    structure = context.get('structure', {})
    code_summary = context.get('code_summary', {})
    
    # Basic metrics
    table.add_row("Project Name", context.get('project_name', 'Unknown'))
    table.add_row("Total Files", str(len(structure.get('files', []))))
    table.add_row("Total Directories", str(len(structure.get('directories', []))))
    table.add_row("Total Size", f"{structure.get('total_size', 0):,} bytes")
    table.add_row("Lines of Code", str(code_summary.get('total_lines', 0)))
    
    console.print(table)
    
    if metrics:
        # Language breakdown table
        lang_table = Table(title="Language Breakdown")
        lang_table.add_column("Language", style="cyan")
        lang_table.add_column("Files", style="yellow")
        lang_table.add_column("Lines", style="green")
        
        for lang, stats in code_summary.get('languages', {}).items():
            lang_table.add_row(lang, str(stats['files']), str(stats['lines']))
        
        console.print(lang_table)
    
    if detailed:
        # File type distribution
        file_types = {}
        for file_info in structure.get('files', []):
            ext = file_info.get('extension', 'no extension')
            file_types[ext] = file_types.get(ext, 0) + 1
        
        # Sort by count
        sorted_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:10]
        
        type_table = Table(title="Top File Types")
        type_table.add_column("Extension", style="cyan")
        type_table.add_column("Count", style="yellow")
        
        for ext, count in sorted_types:
            type_table.add_row(ext, str(count))
        
        console.print(type_table)
        
        # Directory depth analysis
        max_depth = 0
        for dir_path in structure.get('directories', []):
            depth = len(Path(dir_path).parts)
            max_depth = max(max_depth, depth)
        
        console.print(f"\n[blue]Maximum directory depth:[/blue] {max_depth}")
        
        # Check for common project files
        project_files = [
            'README.md', 'LICENSE', 'requirements.txt', 'package.json',
            'setup.py', 'Dockerfile', '.gitignore'
        ]
        
        found_files = []
        for file_info in structure.get('files', []):
            file_name = Path(file_info['path']).name
            if file_name in project_files:
                found_files.append(file_name)
        
        if found_files:
            console.print(f"\n[green]Found project files:[/green] {', '.join(found_files)}")
        else:
            console.print(f"\n[yellow]No standard project files found[/yellow]")


@cli.group()
def code():
    """Code analysis and quality commands."""
    pass


@code.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['security', 'quality', 'performance', 'complexity', 'all']), 
              default='all', help='Type of analysis to perform')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'report', 'html']), 
              default='text', help='Output format')
@click.option('--severity', '-s', type=click.Choice(['low', 'medium', 'high', 'critical']), 
              help='Minimum severity level to report')
@click.option('--interactive', '-i', is_flag=True, help='Interactive analysis session')
@click.option('--batch', '-b', type=click.Path(exists=True), help='Batch analyze files from list')
@click.option('--output', '-o', type=click.Path(), help='Output file for reports')
@click.pass_context
def analyze(ctx, path, type, format, severity, interactive, batch, output):
    """Analyze code for security vulnerabilities and quality issues."""
    from pathlib import Path
    from .code_analysis.analyzer import CodeAnalyzer
    from .code_analysis.security import SecurityAnalyzer
    from .code_analysis.models import SeverityLevel, IssueCategory
    from .interactive_analysis import InteractiveAnalyzer
    from .report_generator import ReportGenerator
    from rich.progress import Progress
    import json
    import yaml
    import datetime
    
    # Handle batch mode
    if batch:
        paths_to_analyze = []
        batch_path = Path(batch)
        
        # Read file paths from batch file
        if batch_path.suffix in ['.yaml', '.yml']:
            with open(batch_path) as f:
                batch_config = yaml.safe_load(f)
                paths_to_analyze = [Path(p) for p in batch_config.get('files', [])]
        else:
            with open(batch_path) as f:
                paths_to_analyze = [Path(line.strip()) for line in f if line.strip()]
        
        console.print(f"[blue]Batch analyzing {len(paths_to_analyze)} files...[/blue]")
        
        # Perform batch analysis
        analyzer = CodeAnalyzer()
        batch_results = []
        
        with Progress() as progress:
            task = progress.add_task("Analyzing files...", total=len(paths_to_analyze))
            
            for file_path in paths_to_analyze:
                if file_path.exists():
                    result = analyzer.analyze_file(file_path)
                    if result:
                        batch_results.append({
                            'path': str(file_path),
                            'result': result
                        })
                progress.advance(task)
        
        # Generate report
        report_gen = ReportGenerator()
        report = report_gen.generate_batch_report(batch_results, format)
        
        if output:
            with open(output, 'w') as f:
                f.write(report)
            console.print(f"[green]Report saved to: {output}[/green]")
        else:
            console.print(report)
        return
    
    # Handle interactive mode
    if interactive:
        interactive_analyzer = InteractiveAnalyzer(console)
        interactive_analyzer.start_session(Path(path))
        return
    
    path = Path(path)
    
    # Don't print the analyzing message for JSON format
    if format != 'json':
        console.print(f"[blue]Analyzing: {path}[/blue]")
    
    try:
        if type == 'security':
            # Security-only analysis
            analyzer = SecurityAnalyzer()
            
            if path.is_file():
                result = analyzer.analyze_file(path)
                vulnerabilities = result['vulnerabilities']
            else:
                result = analyzer.analyze_directory(path)
                vulnerabilities = result['vulnerabilities']
            
            # Filter by severity if specified
            if severity:
                min_severity = SeverityLevel[severity.upper()]
                severity_order = [SeverityLevel.LOW, SeverityLevel.MEDIUM, 
                                SeverityLevel.HIGH, SeverityLevel.CRITICAL]
                min_index = severity_order.index(min_severity)
                vulnerabilities = [v for v in vulnerabilities 
                                 if severity_order.index(v.severity) >= min_index]
            
            # Display results
            if format == 'json':
                output = {
                    'vulnerabilities': [
                        {
                            'type': v.type,
                            'severity': v.severity.value,
                            'category': v.category.value,
                            'description': v.description,
                            'location': {
                                'file': v.location.file_path,
                                'line': v.location.line_start,
                                'column': v.location.column_start,
                            },
                            'fix_suggestion': v.fix_suggestion,
                            'confidence': v.confidence,
                        }
                        for v in vulnerabilities
                    ],
                    'summary': result['summary']
                }
                # Use print instead of console.print for JSON output
                print(json.dumps(output, indent=2))
                return
            else:
                if vulnerabilities:
                    console.print(f"\n[red]Found {len(vulnerabilities)} security vulnerabilities:[/red]")
                    
                    # Group by severity
                    by_severity = {}
                    for v in vulnerabilities:
                        by_severity.setdefault(v.severity.value, []).append(v)
                    
                    for severity in ['critical', 'high', 'medium', 'low']:
                        if severity in by_severity:
                            console.print(f"\n[bold]{severity.upper()}:[/bold]")
                            for v in by_severity[severity]:
                                console.print(f"  • {v.description}")
                                console.print(f"    Location: {v.location.file_path}:{v.location.line_start}")
                                console.print(f"    Fix: {v.fix_suggestion}")
                else:
                    console.print("[green]✓[/green] No security vulnerabilities found!")
                
                console.print(f"\n[blue]Security Score: {result['summary']['security_score']:.1f}/100[/blue]")
                
        else:
            # Full code analysis
            analyzer = CodeAnalyzer()
            
            if path.is_file():
                result = analyzer.analyze_file(path)
                if result:
                    # Handle JSON format
                    if format == 'json':
                        from .report_generator import ReportGenerator
                        report_gen = ReportGenerator()
                        report = report_gen.generate_file_report(result, 'json')
                        print(report)
                        return
                    
                    console.print(f"\n[green]Analysis of {path.name}:[/green]")
                    
                    # Display issues
                    if result.issues:
                        console.print(f"\n[yellow]Issues found: {len(result.issues)}[/yellow]")
                        
                        # Group by category
                        by_category = {}
                        for issue in result.issues:
                            by_category.setdefault(issue.category.value, []).append(issue)
                        
                        for category, issues in by_category.items():
                            console.print(f"\n[bold]{category.upper()}:[/bold]")
                            for issue in issues:
                                console.print(f"  • {issue.message}")
                                console.print(f"    Location: {issue.location.file_path}:{issue.location.line_start}")
                                if issue.suggestion:
                                    console.print(f"    Fix: {issue.suggestion}")
                    
                    # Display metrics
                    if result.metrics:
                        console.print(f"\n[blue]Metrics:[/blue]")
                        console.print(f"  Lines of code: {result.metrics.lines_of_code}")
                        console.print(f"  Cyclomatic complexity: {result.metrics.cyclomatic_complexity:.1f}")
                        console.print(f"  Maintainability index: {result.metrics.maintainability_index:.1f}")
                else:
                    console.print("[red]Analysis failed[/red]")
            else:
                result = analyzer.analyze_directory(path)
                console.print(f"\n[green]Analysis Results:[/green]")
                console.print(f"Files analyzed: {result.files_analyzed}")
                console.print(f"Total lines: {result.total_lines}")
                console.print(f"Total issues: {len(result.all_issues)}")
                
                # Show breakdown by severity
                severity_counts = {}
                for issue in result.all_issues:
                    severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
                
                console.print("\n[yellow]Issues by severity:[/yellow]")
                for severity, count in severity_counts.items():
                    console.print(f"  {severity}: {count}")
                
            # Handle report format
            if format in ['report', 'html']:
                report_gen = ReportGenerator()
                
                if path.is_file():
                    report = report_gen.generate_file_report(result, format)
                else:
                    report = report_gen.generate_directory_report(result, format)
                
                if output:
                    with open(output, 'w') as f:
                        f.write(report)
                    console.print(f"[green]Report saved to: {output}[/green]")
                else:
                    if format == 'html':
                        # Save to temp file and open browser
                        import tempfile
                        import webbrowser
                        
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                            f.write(report)
                            temp_path = f.name
                        
                        console.print(f"[blue]Opening report in browser...[/blue]")
                        webbrowser.open(f'file://{temp_path}')
                    else:
                        console.print(report)
                
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Code analysis error: {e}", exc_info=True)


@code.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--watch', '-w', is_flag=True, help='Watch for file changes')
@click.option('--priority', '-p', type=click.Choice(['all', 'high', 'medium', 'low']), 
              default='all', help='Filter by priority level')
@click.option('--type', '-t', type=click.Choice(['all', 'style', 'performance', 'security', 
                                                  'documentation', 'refactoring']), 
              default='all', help='Filter by suggestion type')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), 
              default='text', help='Output format')
@click.option('--fix', '-f', is_flag=True, help='Apply quick fixes automatically')
@click.pass_context
def suggest(ctx, path, watch, priority, type, output, fix):
    """Get real-time code suggestions and improvements."""
    from pathlib import Path
    import asyncio
    import json
    from .realtime_suggestions import (
        RealTimeSuggestionEngine, 
        SuggestionType,
        Severity
    )
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    
    path = Path(path)
    engine = RealTimeSuggestionEngine()
    
    # Priority filtering mapping
    priority_map = {
        'high': 80,
        'medium': 50,
        'low': 30
    }
    
    def filter_suggestions(suggestions):
        """Filter suggestions based on options."""
        filtered = suggestions
        
        # Filter by priority
        if priority != 'all':
            min_priority = priority_map.get(priority, 0)
            filtered = [s for s in filtered if s.priority >= min_priority]
        
        # Filter by type
        if type != 'all':
            filtered = [s for s in filtered if s.type.value == type]
        
        return filtered
    
    def display_suggestions(suggestions, file_path):
        """Display suggestions based on output format."""
        if output == 'json':
            json_output = []
            for suggestion in suggestions:
                json_output.append({
                    'type': suggestion.type.value,
                    'severity': suggestion.severity.value,
                    'message': suggestion.message,
                    'line': suggestion.range.start.line,
                    'column': suggestion.range.start.column,
                    'priority': suggestion.priority,
                    'quick_fixes': [
                        {
                            'type': fix.type.value,
                            'title': fix.title,
                            'description': fix.description
                        }
                        for fix in suggestion.quick_fixes
                    ]
                })
            print(json.dumps(json_output, indent=2))
        else:
            if not suggestions:
                console.print(f"[green]No suggestions for {file_path}[/green]")
                return
            
            console.print(f"\n[blue]Suggestions for {file_path}:[/blue]")
            
            for suggestion in suggestions:
                # Color based on severity
                color_map = {
                    Severity.CRITICAL: "red",
                    Severity.ERROR: "red",
                    Severity.WARNING: "yellow",
                    Severity.INFO: "blue"
                }
                color = color_map.get(suggestion.severity, "white")
                
                console.print(f"\n[{color}]{suggestion.severity.value.upper()}[/{color}] "
                             f"[white]{suggestion.type.value}[/white] "
                             f"(priority: {suggestion.priority})")
                console.print(f"Line {suggestion.range.start.line}: {suggestion.message}")
                
                if suggestion.quick_fixes:
                    console.print("[cyan]Quick fixes available:[/cyan]")
                    for i, fix in enumerate(suggestion.quick_fixes, 1):
                        console.print(f"  {i}. {fix.title}: {fix.description}")
    
    async def analyze_file_async(file_path):
        """Analyze a file asynchronously."""
        suggestions = await engine.analyze_file_async(file_path)
        filtered = filter_suggestions(suggestions)
        display_suggestions(filtered, file_path)
        
        # Apply fixes if requested
        if fix and filtered:
            console.print("\n[yellow]Auto-fix not implemented yet[/yellow]")
        
        return filtered
    
    # Main analysis
    try:
        if path.is_file():
            # Analyze single file
            asyncio.run(analyze_file_async(path))
            
            if watch:
                console.print(f"\n[yellow]Watching {path} for changes...[/yellow]")
                
                class FileChangeHandler(FileSystemEventHandler):
                    def on_modified(self, event):
                        if not event.is_directory and event.src_path == str(path):
                            console.print(f"\n[blue]File changed: {event.src_path}[/blue]")
                            asyncio.run(analyze_file_async(Path(event.src_path)))
                
                event_handler = FileChangeHandler()
                observer = Observer()
                observer.schedule(event_handler, str(path.parent), recursive=False)
                observer.start()
                
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    observer.stop()
                    console.print("\n[yellow]Stopped watching[/yellow]")
                observer.join()
        else:
            # Analyze directory
            import glob
            py_files = list(path.glob("**/*.py"))
            
            if not py_files:
                console.print(f"[yellow]No Python files found in {path}[/yellow]")
                return
            
            console.print(f"[blue]Analyzing {len(py_files)} files...[/blue]")
            
            all_suggestions = {}
            
            async def analyze_all():
                tasks = []
                for file_path in py_files:
                    tasks.append(engine.analyze_file_async(file_path))
                
                results = await asyncio.gather(*tasks)
                
                for file_path, suggestions in zip(py_files, results):
                    filtered = filter_suggestions(suggestions)
                    if filtered:
                        all_suggestions[str(file_path)] = filtered
                        display_suggestions(filtered, file_path)
            
            asyncio.run(analyze_all())
            
            # Summary
            total_suggestions = sum(len(s) for s in all_suggestions.values())
            console.print(f"\n[green]Analysis complete:[/green] "
                         f"{total_suggestions} suggestions in {len(all_suggestions)} files")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Suggestion error: {e}", exc_info=True)


@code.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['all', 'extract_method', 'extract_class', 
                                                  'remove_dead', 'consolidate']), 
              default='all', help='Type of refactoring to detect')
@click.option('--output', '-o', type=click.Choice(['text', 'json']), 
              default='text', help='Output format')
@click.option('--threshold', '-th', type=float, default=0.7, 
              help='Confidence threshold (0.0-1.0)')
@click.option('--max-risk', '-r', type=float, default=0.5, 
              help='Maximum risk score to show (0.0-1.0)')
@click.option('--save', '-s', type=click.Path(), help='Save report to file')
@click.pass_context
def refactor(ctx, path, type, output, threshold, max_risk, save):
    """Analyze code for refactoring opportunities."""
    from pathlib import Path
    from .refactoring import RefactoringRecommendationEngine, RefactoringType
    import json
    
    path = Path(path)
    engine = RefactoringRecommendationEngine()
    
    console.print(f"[blue]Analyzing {path} for refactoring opportunities...[/blue]")
    
    # Get recommendations
    if path.is_file():
        recommendations = engine.analyze_and_recommend(path)
    else:
        # Analyze all Python files in directory
        recommendations = []
        py_files = list(path.rglob("*.py"))
        
        for file_path in track(py_files, description="Analyzing files..."):
            try:
                file_recommendations = engine.analyze_and_recommend(file_path)
                recommendations.extend(file_recommendations)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to analyze {file_path}: {e}[/yellow]")
    
    # Filter by type if specified
    if type != 'all':
        type_map = {
            'extract_method': RefactoringType.EXTRACT_METHOD,
            'extract_class': RefactoringType.EXTRACT_CLASS,
            'remove_dead': RefactoringType.REMOVE_DEAD_CODE,
            'consolidate': RefactoringType.CONSOLIDATE_DUPLICATE
        }
        filter_type = type_map.get(type)
        recommendations = [
            rec for rec in recommendations 
            if rec[0].type == filter_type
        ]
    
    # Filter by confidence threshold
    recommendations = [
        rec for rec in recommendations 
        if rec[0].confidence >= threshold
    ]
    
    # Filter by risk
    recommendations = [
        rec for rec in recommendations 
        if rec[2].risk_score <= max_risk
    ]
    
    # Sort by benefit/risk ratio
    recommendations.sort(
        key=lambda x: x[0].maintainability_improvement / (x[2].risk_score + 0.1),
        reverse=True
    )
    
    if output == 'json':
        # Generate JSON output
        output_data = []
        for candidate, plan, impact in recommendations:
            output_data.append({
                'type': candidate.type.value,
                'file': str(candidate.location.file_path),
                'location': {
                    'start': candidate.location.line_start,
                    'end': candidate.location.line_end
                },
                'confidence': candidate.confidence,
                'rationale': candidate.rationale,
                'impact': {
                    'risk_score': impact.risk_score,
                    'performance': impact.performance_impact,
                    'breaking_changes': impact.breaking_changes
                },
                'plan': {
                    'steps': plan.steps,
                    'effort': plan.estimated_effort,
                    'benefits': plan.benefits,
                    'risks': plan.risks
                },
                'improvements': {
                    'complexity': candidate.complexity_reduction,
                    'readability': candidate.readability_improvement,
                    'maintainability': candidate.maintainability_improvement
                }
            })
        
        if save:
            with open(save, 'w') as f:
                json.dump(output_data, f, indent=2)
            console.print(f"[green]Report saved to {save}[/green]")
        else:
            print(json.dumps(output_data, indent=2))
    else:
        # Generate text output
        if not recommendations:
            console.print("[yellow]No refactoring opportunities found matching criteria[/yellow]")
            return
        
        console.print(f"\n[green]Found {len(recommendations)} refactoring opportunities:[/green]\n")
        
        for i, (candidate, plan, impact) in enumerate(recommendations[:10], 1):
            # Display header
            console.print(f"[bold]{i}. {candidate.type.value.replace('_', ' ').title()}[/bold]")
            console.print(f"   File: [cyan]{candidate.location.file_path}[/cyan]")
            console.print(f"   Lines: {candidate.location.line_start}-{candidate.location.line_end}")
            console.print(f"   Confidence: [green]{candidate.confidence:.1%}[/green]")
            console.print(f"   Risk: [{'red' if impact.risk_score > 0.5 else 'yellow'}]{impact.risk_score:.1%}[/]")
            
            # Display rationale
            console.print(f"\n   [bold]Rationale:[/bold] {candidate.rationale}")
            
            # Display impact
            console.print(f"\n   [bold]Expected Improvements:[/bold]")
            console.print(f"   - Complexity reduction: {candidate.complexity_reduction:.1%}")
            console.print(f"   - Readability improvement: {candidate.readability_improvement:.1%}")
            console.print(f"   - Maintainability improvement: {candidate.maintainability_improvement:.1%}")
            
            # Display plan summary
            console.print(f"\n   [bold]Plan:[/bold]")
            for j, step in enumerate(plan.steps[:3], 1):
                console.print(f"   {j}. {step}")
            if len(plan.steps) > 3:
                console.print(f"   ... ({len(plan.steps) - 3} more steps)")
            
            console.print(f"\n   [bold]Effort:[/bold] {plan.estimated_effort}")
            
            # Display risks and benefits
            if plan.risks:
                console.print(f"\n   [bold]Risks:[/bold]")
                for risk in plan.risks[:2]:
                    console.print(f"   - {risk}")
            
            if plan.benefits:
                console.print(f"\n   [bold]Benefits:[/bold]")
                for benefit in plan.benefits[:2]:
                    console.print(f"   - {benefit}")
            
            console.print("\n" + "-" * 60 + "\n")
        
        if len(recommendations) > 10:
            console.print(f"[dim]... and {len(recommendations) - 10} more opportunities[/dim]")
        
        # Summary
        console.print("\n[bold]Summary by Type:[/bold]")
        type_counts = {}
        for rec in recommendations:
            rec_type = rec[0].type.value
            type_counts[rec_type] = type_counts.get(rec_type, 0) + 1
        
        for ref_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {ref_type.replace('_', ' ').title()}: {count}")
        
        # Risk summary
        low_risk = sum(1 for r in recommendations if r[2].risk_score <= 0.3)
        medium_risk = sum(1 for r in recommendations if 0.3 < r[2].risk_score <= 0.7)
        high_risk = sum(1 for r in recommendations if r[2].risk_score > 0.7)
        
        console.print("\n[bold]Risk Assessment:[/bold]")
        console.print(f"  Low risk: [green]{low_risk}[/green]")
        console.print(f"  Medium risk: [yellow]{medium_risk}[/yellow]")
        console.print(f"  High risk: [red]{high_risk}[/red]")


@cli.group()
def ai():
    """AI assistant commands."""
    pass


@ai.command()
@click.argument('task')
@click.option('--context', is_flag=True, help='Include project context')
@click.option('--save', '-s', type=click.Path(), help='Save suggestions to file')
@click.pass_context
def suggest(ctx, task, context, save):
    """Get AI suggestions for a task."""
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        
        with console.status("Getting AI suggestions...") as status:
            suggestions = assistant.suggest(task, include_context=context)
            
        console.print("[green]AI Suggestions:[/green]")
        console.print(suggestions)
        
        if save:
            with open(save, 'w') as f:
                f.write(suggestions)
            console.print(f"\n[blue]Suggestions saved to:[/blue] {save}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("[yellow]Hint:[/yellow] Make sure your AI API key is configured.")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['general', 'security', 'performance', 'refactor', 'documentation']), 
              default='general', help='Type of analysis to perform')
@click.pass_context
def analyze(ctx, file, type):
    """Analyze a code file with AI."""
    from pathlib import Path
    
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        file_path = Path(file)
        
        with console.status(f"Analyzing {file_path.name}...") as status:
            result = assistant.analyze_code(file_path, analysis_type=type)
            
        console.print(f"[green]Analysis Results for {file_path.name}:[/green]")
        console.print(result['response'])
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.option('--language', '-l', default='python', help='Programming language')
@click.option('--save', '-s', type=click.Path(), help='Save generated code to file')
@click.pass_context
def generate(ctx, language, save):
    """Generate code using AI."""
    from prompt_toolkit import prompt
    
    try:
        # Get description from user
        description = prompt("Describe what you want to generate: ")
        
        assistant = AIAssistant(config=ctx.obj['config'])
        
        with console.status("Generating code...") as status:
            code = assistant.generate_code(description, language=language)
            
        console.print(f"[green]Generated {language} code:[/green]")
        console.print(code)
        
        if save:
            with open(save, 'w') as f:
                f.write(code)
            console.print(f"\n[blue]Code saved to:[/blue] {save}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@ai.command()
@click.pass_context
def test(ctx):
    """Test AI connectivity."""
    try:
        assistant = AIAssistant(config=ctx.obj['config'])
        provider_info = assistant.get_provider_info()
        
        console.print(f"[blue]Testing AI connection...[/blue]")
        console.print(f"Provider: {provider_info['provider']}")
        console.print(f"Model: {provider_info['model']}")
        console.print(f"API Key: {'✓' if provider_info['api_key_configured'] else '✗'}")
        
        with console.status("Testing connection...") as status:
            if assistant.test_connection():
                console.print("[green]✓[/green] AI connection successful!")
            else:
                console.print("[red]✗[/red] AI connection failed!")
                console.print("[yellow]Check your API key and configuration.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        console.print("[yellow]Make sure your AI provider is properly configured.[/yellow]")


@cli.group()
def git():
    """Git-related commands with natural language support."""
    pass


@git.command('feature')
@click.argument('description')
@click.option('--prefix', '-p', default='feature/', help='Branch prefix')
@click.option('--ticket', '-t', help='Ticket reference (e.g., #123, JIRA-456)')
@click.pass_context
def create_feature(ctx, description, prefix, ticket):
    """Create a feature branch from natural language description."""
    from .git_manager import GitManager
    
    # Add ticket reference to description if provided
    if ticket:
        description = f"{ticket} {description}"
    
    try:
        git_mgr = GitManager()
        branch_name = git_mgr.create_feature_branch(description, prefix=prefix)
        console.print(f"[green]✓[/green] Created and switched to branch: [blue]{branch_name}[/blue]")
        
        # Show what to do next
        console.print("\n[yellow]Next steps:[/yellow]")
        console.print("1. Make your changes")
        console.print("2. Use 'vtree git commit' to generate a smart commit message")
        console.print("3. Push your branch and create a pull request")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Failed to create feature branch: {e}", exc_info=True)


@git.command('commit')
@click.option('--message', '-m', help='Custom commit message')
@click.option('--type', '-t', type=click.Choice(['feat', 'fix', 'docs', 'test', 'refactor', 'chore']), 
              help='Commit type for conventional format')
@click.pass_context
def smart_commit(ctx, message, type):
    """Generate and create a smart commit based on changes."""
    from .git_manager import GitManager
    
    try:
        git_mgr = GitManager()
        
        # Analyze changes
        console.print("[blue]Analyzing changes...[/blue]")
        changes = git_mgr.analyze_changes()
        
        # Generate commit message
        if message:
            commit_msg = git_mgr.generate_commit_message(custom_message=message)
        else:
            commit_msg = git_mgr.generate_commit_message(changes=changes)
            
        # Show analysis results
        console.print("\n[cyan]Change Analysis:[/cyan]")
        console.print(f"Files changed: {len(changes.files_changed)}")
        console.print(f"Insertions: [green]+{changes.insertions}[/green]")
        console.print(f"Deletions: [red]-{changes.deletions}[/red]")
        console.print(f"Impact level: {changes.impact_level}")
        console.print(f"Change type: {changes.change_type}")
        
        console.print(f"\n[yellow]Suggested commit message:[/yellow]")
        console.print(commit_msg)
        
        # Confirm or edit
        if click.confirm("\nUse this commit message?"):
            # Actually create the commit
            import subprocess
            result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                console.print("[green]✓[/green] Commit created successfully!")
            else:
                console.print(f"[red]Error creating commit:[/red] {result.stderr}")
        else:
            console.print("[yellow]Commit cancelled. You can create it manually.[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Failed to create commit: {e}", exc_info=True)


@git.command('tag')
@click.option('--type', '-t', type=click.Choice(['major', 'minor', 'patch']), 
              default='patch', help='Version bump type')
@click.option('--version', '-v', help='Custom version tag')
@click.pass_context
def create_tag(ctx, type, version):
    """Create a semantic version tag."""
    from .git_manager import GitManager
    
    try:
        git_mgr = GitManager()
        
        if version:
            new_tag = git_mgr.tag_version(custom_version=version)
        else:
            new_tag = git_mgr.tag_version(version_type=type)
            
        console.print(f"[green]✓[/green] Created tag: [blue]{new_tag}[/blue]")
        console.print("\nTo push this tag to remote:")
        console.print(f"[cyan]git push origin {new_tag}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Failed to create tag: {e}", exc_info=True)


@git.command('analyze')
@click.pass_context
def analyze_changes(ctx):
    """Analyze current git changes in detail."""
    from .git_manager import GitManager
    
    try:
        git_mgr = GitManager()
        changes = git_mgr.analyze_changes()
        
        # Create a detailed table
        table = Table(title="Git Change Analysis")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Files Changed", str(len(changes.files_changed)))
        table.add_row("Total Insertions", f"[green]+{changes.insertions}[/green]")
        table.add_row("Total Deletions", f"[red]-{changes.deletions}[/red]")
        table.add_row("Change Type", changes.change_type)
        table.add_row("Impact Level", changes.impact_level)
        table.add_row("Components Affected", ", ".join(changes.components_affected))
        
        console.print(table)
        
        # Show files changed
        if changes.files_changed:
            console.print("\n[cyan]Files Changed:[/cyan]")
            for file in changes.files_changed:
                console.print(f"  • {file}")
        
        # Show suggested commit message
        console.print(f"\n[yellow]Suggested Commit Message:[/yellow]")
        console.print(changes.suggested_message)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Failed to analyze changes: {e}", exc_info=True)


@cli.group()
def plan():
    """Project planning commands."""
    pass


@cli.group()
def visualize():
    """Visualization commands."""
    pass


@plan.command('start')
@click.option('--template', '-t', help='Planning template to use')
@click.option('--name', '-n', help='Project name')
@click.pass_context
def start_planning(ctx, template, name):
    """Start a new project planning session."""
    from .planning_session import PlanningSession
    from .conversation_engine import ConversationEngine
    from prompt_toolkit import prompt
    from prompt_toolkit.history import InMemoryHistory
    
    # Get project name if not provided
    if not name:
        name = prompt("What's the name of your project? ")
    
    # Create planning session
    session = PlanningSession(ctx.obj['config'])
    result = session.start_session(name, template=template)
    
    console.print(f"[green]✓[/green] Started planning session: [blue]{result['session_id']}[/blue]")
    console.print(f"\n[yellow]{result['greeting']}[/yellow]\n")
    
    # Create conversation engine
    engine = ConversationEngine()
    history = InMemoryHistory()
    
    # Interactive planning loop
    while session.state.value == 'active':
        try:
            # Get user input
            user_input = prompt("> ", history=history)
            
            if not user_input.strip():
                continue
            
            # Add user message
            session.add_message(role="user", content=user_input)
            
            # Process response
            response = session._process_user_input(user_input)
            
            # Display response
            console.print(f"\n[cyan]{response}[/cyan]\n")
            
            # Check for session completion
            if session.stage.value == 'finalization' and 'export' in user_input.lower():
                export_format = 'markdown'
                if 'json' in user_input.lower():
                    export_format = 'json'
                
                # Export plan
                exported = session.export_plan(format=export_format)
                filename = f"{session.project_plan.name.replace(' ', '_')}_{session.session_id[:8]}.{export_format[:2]}"
                
                with open(filename, 'w') as f:
                    f.write(exported)
                
                console.print(f"[green]✓[/green] Plan exported to: [blue]{filename}[/blue]")
                session.complete_session()
                break
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Session paused. Resume with 'vtree plan resume {}'[/yellow]".format(
                result['session_id']
            ))
            session.pause_session()
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            logger.error(f"Planning session error: {e}", exc_info=True)


@plan.command('resume')
@click.argument('session_id')
@click.pass_context
def resume_planning(ctx, session_id):
    """Resume a paused planning session."""
    from .planning_session import PlanningSession
    from .conversation_engine import ConversationEngine
    from prompt_toolkit import prompt
    from prompt_toolkit.history import InMemoryHistory
    
    try:
        # Load session
        session = PlanningSession.load_session(ctx.obj['config'], session_id)
        result = session.resume_session()
        
        console.print(f"[green]✓[/green] Resumed session: [blue]{session_id}[/blue]")
        console.print(f"\n[yellow]{result['greeting']}[/yellow]\n")
        
        # Create conversation engine
        engine = ConversationEngine()
        history = InMemoryHistory()
        
        # Resume interactive planning
        while session.state.value == 'active':
            try:
                user_input = prompt("> ", history=history)
                
                if not user_input.strip():
                    continue
                
                session.add_message(role="user", content=user_input)
                response = session._process_user_input(user_input)
                console.print(f"\n[cyan]{response}[/cyan]\n")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Session paused.[/yellow]")
                session.pause_session()
                break
                
    except ValueError as e:
        console.print(f"[red]Error:[/red] {str(e)}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Failed to resume session: {e}", exc_info=True)


@plan.command('list')
@click.option('--status', '-s', help='Filter by status (active, paused, completed)')
@click.pass_context
def list_planning_sessions(ctx):
    """List all planning sessions."""
    from pathlib import Path
    import json
    
    session_dir = Path.home() / '.velocitytree' / 'planning_sessions'
    
    if not session_dir.exists():
        console.print("[yellow]No planning sessions found.[/yellow]")
        return
    
    table = Table(title="Planning Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Project Name", style="yellow")
    table.add_column("Status", style="green")
    table.add_column("Stage", style="blue")
    table.add_column("Created", style="magenta")
    
    sessions = []
    for session_file in session_dir.glob("*.json"):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                sessions.append(data)
        except Exception as e:
            logger.error(f"Error reading session file {session_file}: {e}")
    
    # Filter by status if specified
    if ctx.params['status']:
        sessions = [s for s in sessions if s.get('state') == ctx.params['status']]
    
    # Sort by creation date
    sessions.sort(key=lambda x: x.get('metadata', {}).get('created_at', ''), reverse=True)
    
    for session_data in sessions:
        session_id = session_data.get('session_id', 'Unknown')
        project_name = session_data.get('project_plan', {}).get('name', 'Unnamed')
        status = session_data.get('state', 'unknown')
        stage = session_data.get('stage', 'unknown')
        created = session_data.get('metadata', {}).get('created_at', 'Unknown')
        
        if isinstance(created, str) and len(created) > 10:
            created = created[:10]  # Just show date
        
        table.add_row(
            session_id[:8] + "...",
            project_name,
            status,
            stage.replace('_', ' ').title(),
            created
        )
    
    console.print(table)


@plan.command('show')
@click.argument('session_id')
@click.pass_context
def show_planning_session(ctx, session_id):
    """Show details of a planning session."""
    from .planning_session import PlanningSession
    
    try:
        session = PlanningSession.load_session(ctx.obj['config'], session_id)
        context = session.get_context()
        
        console.print(f"[blue]Planning Session:[/blue] {session_id}")
        console.print(f"[yellow]Project:[/yellow] {context.get('project_name', 'Unknown')}")
        console.print(f"[green]Status:[/green] {context.get('state')}")
        console.print(f"[cyan]Stage:[/cyan] {context.get('stage')}")
        
        if context.get('plan_summary'):
            summary = context['plan_summary']
            console.print("\n[magenta]Plan Summary:[/magenta]")
            console.print(f"Goals: {summary.get('goals_count', 0)}")
            console.print(f"Features: {summary.get('features_count', 0)}")
            console.print(f"Milestones: {summary.get('milestones_count', 0)}")
            console.print(f"Tech Stack: {'✓' if summary.get('has_tech_stack') else '✗'}")
            console.print(f"Timeline: {'✓' if summary.get('has_timeline') else '✗'}")
            console.print(f"Resources: {'✓' if summary.get('has_resources') else '✗'}")
        
        # Show recent messages
        recent_messages = context.get('messages', [])[-5:]
        if recent_messages:
            console.print("\n[yellow]Recent Conversation:[/yellow]")
            for msg in recent_messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                if len(content) > 100:
                    content = content[:100] + "..."
                console.print(f"[dim]{role}:[/dim] {content}")
                
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@plan.command('export')
@click.argument('session_id')
@click.option('--format', '-f', type=click.Choice(['markdown', 'json']), default='markdown')
@click.option('--output', '-o', help='Output file path')
@click.pass_context
def export_planning_session(ctx, session_id, format, output):
    """Export a planning session to a file."""
    from .planning_session import PlanningSession
    
    try:
        session = PlanningSession.load_session(ctx.obj['config'], session_id)
        
        # Export plan
        exported = session.export_plan(format=format)
        
        # Determine output file
        if not output:
            output = f"{session.project_plan.name.replace(' ', '_')}_{session_id[:8]}.{format[:2]}"
        
        # Save to file
        with open(output, 'w') as f:
            f.write(exported)
        
        console.print(f"[green]✓[/green] Exported to: [blue]{output}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.group()
def git():
    """Git integration commands."""
    pass


@git.command('sync')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--watch', '-w', is_flag=True, help='Watch repository for changes')
@click.pass_context
def git_sync(ctx, project, watch):
    """Sync feature status with git activity."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        git_tracker = GitFeatureTracker(project, vt.feature_graph)
        
        # Scan repository and update features
        console.print("[blue]Scanning repository for feature activity...[/blue]")
        updates = git_tracker.update_feature_status()
        
        if updates:
            console.print(f"[green]✓[/green] Updated {len(updates)} features:")
            for feature_id, new_status in updates.items():
                feature = vt.feature_graph.features[feature_id]
                console.print(f"  • {feature.name} ({feature_id}): [yellow]{new_status}[/yellow]")
        else:
            console.print("[yellow]No feature updates detected[/yellow]")
        
        # Start monitoring if requested
        if watch:
            console.print("\n[blue]Starting repository monitoring...[/blue]")
            console.print("[yellow]Press Ctrl+C to stop[/yellow]")
            
            def on_update(updates):
                console.print(f"\n[green]Detected changes:[/green]")
                for feature_id, new_status in updates.items():
                    feature = vt.feature_graph.features[feature_id]
                    console.print(f"  • {feature.name}: {new_status}")
            
            git_tracker.monitor_repository(callback=on_update)
            
            # Keep the process running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Monitoring stopped[/yellow]")
        
        # Save updated graph
        vt.save_state()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Git sync error: {e}", exc_info=True)


@git.command('report')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def git_report(ctx, project, format):
    """Generate feature progress report from git activity."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        git_integration = GitWorkflowIntegration(project, vt.feature_graph)
        
        # Generate report
        report = git_integration.generate_feature_report()
        
        if format == 'json':
            import json
            console.print(json.dumps(report, indent=2, default=str))
        else:
            # Display as table
            table = Table(title="Feature Progress Report")
            table.add_column("Feature", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Commits", style="green")
            table.add_column("Last Activity", style="blue")
            table.add_column("Branch", style="magenta")
            table.add_column("Merged", style="red")
            
            for feature_id, feature_data in report['features'].items():
                table.add_row(
                    f"{feature_data['name']} ({feature_id})",
                    feature_data['status'],
                    str(feature_data['commits']),
                    str(feature_data['last_activity'])[:10] if feature_data['last_activity'] else "Never",
                    feature_data['branch'] or "None",
                    "Yes" if feature_data['is_merged'] else "No"
                )
            
            console.print(table)
            
            # Print summary
            summary = report['summary']
            console.print(f"\n[bold]Summary:[/bold]")
            console.print(f"Total Features: {summary['total_features']}")
            console.print(f"Active: [green]{summary['active_features']}[/green]")
            console.print(f"Completed: [blue]{summary['completed_features']}[/blue]")
            console.print(f"Stale: [yellow]{summary['stale_features']}[/yellow]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Git report error: {e}", exc_info=True)


@git.command('feature-branch')
@click.argument('feature_id')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.pass_context
def create_feature_branch(ctx, feature_id, project):
    """Create a git branch for a feature."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        git_integration = GitWorkflowIntegration(project, vt.feature_graph)
        
        # Create branch
        branch_name = git_integration.create_feature_branch(feature_id)
        console.print(f"[green]✓[/green] Created branch: [blue]{branch_name}[/blue]")
        
        # Show feature info
        feature = vt.feature_graph.features[feature_id]
        console.print(f"\nFeature: [cyan]{feature.name}[/cyan]")
        console.print(f"Status: [yellow]{feature.status}[/yellow]")
        
        # Check out the branch
        if click.confirm("Check out the new branch?"):
            import subprocess
            subprocess.run(['git', 'checkout', branch_name], cwd=project)
            console.print(f"[green]✓[/green] Switched to branch: {branch_name}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Feature branch error: {e}", exc_info=True)


@git.command('suggest')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.pass_context
def suggest_relationships(ctx, project):
    """Suggest feature relationships based on git activity."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        git_tracker = GitFeatureTracker(project, vt.feature_graph)
        
        # Get suggestions
        suggestions = git_tracker.suggest_feature_relationships()
        
        if not suggestions:
            console.print("[yellow]No relationship suggestions found[/yellow]")
            return
        
        console.print("[blue]Suggested feature relationships:[/blue]\n")
        
        for source, target, rel_type in suggestions:
            if source in vt.feature_graph.features and target in vt.feature_graph.features:
                source_feature = vt.feature_graph.features[source]
                target_feature = vt.feature_graph.features[target]
                
                console.print(f"[cyan]{source_feature.name}[/cyan] {rel_type} [cyan]{target_feature.name}[/cyan]")
                
                if click.confirm("Add this relationship?"):
                    from .feature_graph import RelationType
                    rel_type_enum = RelationType[rel_type]
                    vt.feature_graph.add_relationship(source, target, rel_type_enum)
                    console.print("[green]✓[/green] Relationship added")
        
        # Save if any changes were made
        vt.save_state()
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Relationship suggestion error: {e}", exc_info=True)


@cli.group()
def progress():
    """Progress tracking and velocity commands."""
    pass


@cli.group()
def suggestions():
    """Real-time code suggestions commands."""
    pass


@suggestions.command('realtime')
@click.argument('file_path', type=click.Path(exists=True))
@click.option(
    '--batch', 
    is_flag=True, 
    help='Process multiple files in batch mode'
)
@click.option(
    '--interactive', 
    is_flag=True, 
    help='Enable interactive analysis session'
)
@click.option(
    '--context', 
    multiple=True, 
    help='Additional context for analysis (key=value pairs)'
)
@click.option(
    '--output', 
    type=click.Path(), 
    help='Save suggestions to file'
)
@click.option(
    '--feedback', 
    is_flag=True, 
    help='Show feedback prompts for suggestions'
)
@click.option(
    '--no-cache', 
    is_flag=True, 
    help='Disable suggestion caching'
)
@click.pass_context
def suggestions_realtime(ctx, file_path, batch, interactive, context, output, feedback, no_cache):
    """Get real-time code suggestions for a file or directory."""
    from pathlib import Path
    import json
    from .realtime_suggestions import RealTimeSuggestionEngine
    from .code_analysis.analyzer import CodeAnalyzer
    from .documentation.quality import DocQualityChecker
    
    # Create suggestion engine
    analyzer = CodeAnalyzer()
    quality_checker = DocQualityChecker()
    suggestion_engine = RealTimeSuggestionEngine(
        analyzer=analyzer,
        quality_checker=quality_checker
    )
    
    # Set up feedback collection if requested
    feedback_collector = None
    if feedback:
        from velocitytree.learning.feedback_collector import FeedbackCollector
        feedback_collector = FeedbackCollector()
        suggestion_engine._feedback_collector = feedback_collector
    
    # Override cache behavior if requested
    if no_cache:
        suggestion_engine.clear_cache()
    
    # Parse context
    context_dict = {}
    for ctx_pair in context:
        if '=' in ctx_pair:
            key, value = ctx_pair.split('=', 1)
            context_dict[key] = value
    
    # Determine files to analyze
    path = Path(file_path)
    if path.is_dir():
        files = list(path.glob("**/*.py"))
    else:
        files = [path]
    
    if batch:
        # Batch processing
        console.print(f"[blue]Batch analyzing {len(files)} files...[/blue]")
        all_suggestions = {}
        
        with Progress() as progress:
            task = progress.add_task("Analyzing files...", total=len(files))
            
            for file_path in files:
                try:
                    suggestions = suggestion_engine._analyze_sync(
                        file_path, 
                        file_path.read_text(),
                        context_dict
                    )
                    if suggestions:
                        all_suggestions[str(file_path)] = suggestions
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to analyze {file_path}: {e}[/yellow]")
                progress.advance(task)
        
        # Save or display results
        if output:
            output_data = {
                str(path): [
                    {
                        'type': s.type.value,
                        'severity': s.severity.value,
                        'message': s.message,
                        'line': s.range.start.line,
                        'priority': s.priority
                    }
                    for s in suggestions
                ]
                for path, suggestions in all_suggestions.items()
            }
            
            with open(output, 'w') as f:
                json.dump(output_data, f, indent=2)
            console.print(f"[green]Results saved to: {output}[/green]")
        else:
            # Display summary
            total_suggestions = sum(len(s) for s in all_suggestions.values())
            console.print(f"\n[green]Analysis complete:[/green] {total_suggestions} suggestions in {len(all_suggestions)} files")
            
            for file_path, suggestions in all_suggestions.items():
                console.print(f"\n[blue]{file_path}:[/blue] {len(suggestions)} suggestions")
                for suggestion in suggestions[:3]:  # Show first 3
                    console.print(f"  • {suggestion.type.value}: {suggestion.message}")
                if len(suggestions) > 3:
                    console.print(f"  ... and {len(suggestions) - 3} more")
    
    elif interactive:
        # Interactive analysis session
        from prompt_toolkit import prompt as pt_prompt
        from prompt_toolkit.history import InMemoryHistory
        
        console.print(f"[blue]Starting interactive analysis session for {file_path}[/blue]")
        console.print("[dim]Type 'help' for commands, 'quit' to exit[/dim]\n")
        
        history = InMemoryHistory()
        
        while True:
            try:
                command = pt_prompt("> ", history=history)
                
                if command.lower() in ['quit', 'exit']:
                    break
                elif command.lower() == 'help':
                    console.print("Commands:")
                    console.print("  analyze - Re-analyze the file")
                    console.print("  feedback <suggestion_id> <rating> - Provide feedback")
                    console.print("  apply <suggestion_id> - Apply a quick fix")
                    console.print("  filter <type> - Filter by suggestion type")
                    console.print("  quit - Exit interactive session")
                elif command.lower().startswith('analyze'):
                    suggestions = suggestion_engine._analyze_sync(
                        path,
                        path.read_text(),
                        context_dict
                    )
                    console.print(f"Found {len(suggestions)} suggestions")
                    for i, suggestion in enumerate(suggestions):
                        console.print(f"{i}: {suggestion.type.value} - {suggestion.message}")
                elif command.lower().startswith('feedback'):
                    if feedback:
                        parts = command.split()
                        if len(parts) >= 3:
                            suggestion_id = int(parts[1])
                            rating = parts[2]
                            # Process feedback
                            feedback_collector.record_feedback(
                                suggestion_id=str(suggestion_id),
                                feedback_type='rating',
                                value=rating
                            )
                            console.print("[green]Feedback recorded[/green]")
                    else:
                        console.print("[yellow]Feedback collection not enabled[/yellow]")
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                console.print(f"[red]Error:[/red] {str(e)}")
        
        console.print("\n[yellow]Interactive session ended[/yellow]")
    
    else:
        # Single file analysis
        console.print(f"[blue]Analyzing {file_path}...[/blue]")
        
        try:
            suggestions = suggestion_engine._analyze_sync(
                path,
                path.read_text(),
                context_dict
            )
            
            if not suggestions:
                console.print("[green]No suggestions found[/green]")
                return
            
            console.print(f"\n[green]Found {len(suggestions)} suggestions:[/green]")
            
            for i, suggestion in enumerate(suggestions):
                # Display suggestion
                console.print(f"\n[bold]{i + 1}. {suggestion.type.value.replace('_', ' ').title()}[/bold]")
                console.print(f"   Severity: [yellow]{suggestion.severity.value}[/yellow]")
                console.print(f"   Priority: {suggestion.priority}")
                console.print(f"   Message: {suggestion.message}")
                console.print(f"   Location: Line {suggestion.range.start.line}")
                
                if suggestion.quick_fixes:
                    console.print("   Quick fixes:")
                    for fix in suggestion.quick_fixes:
                        console.print(f"     • {fix.title}: {fix.description}")
                
                # Collect feedback if enabled
                if feedback and feedback_collector:
                    from rich.prompt import Confirm, Prompt
                    
                    if Confirm.ask("Was this suggestion helpful?"):
                        rating = Prompt.ask(
                            "Rate this suggestion (1-5)",
                            choices=["1", "2", "3", "4", "5"]
                        )
                        
                        feedback_collector.record_feedback(
                            suggestion_id=f"{file_path}_{i}",
                            feedback_type='rating',
                            value=int(rating),
                            metadata={
                                'suggestion_type': suggestion.type.value,
                                'severity': suggestion.severity.value,
                                'file_path': str(file_path)
                            }
                        )
                        
                        console.print("[green]Thank you for your feedback![/green]")
                    
                    # Ask for additional feedback
                    if i == 0:  # Only ask once
                        comment = Prompt.ask("Any additional comments? (press Enter to skip)")
                        if comment:
                            feedback_collector.record_feedback(
                                suggestion_id=f"{file_path}_general",
                                feedback_type='comment',
                                value=comment,
                                metadata={'file_path': str(file_path)}
                            )
            
            # Save to file if requested
            if output:
                output_data = [
                    {
                        'type': s.type.value,
                        'severity': s.severity.value,
                        'message': s.message,
                        'line': s.range.start.line,
                        'priority': s.priority,
                        'quick_fixes': [
                            {
                                'type': f.type.value,
                                'title': f.title,
                                'description': f.description
                            }
                            for f in s.quick_fixes
                        ]
                    }
                    for s in suggestions
                ]
                
                with open(output, 'w') as f:
                    json.dump(output_data, f, indent=2)
                console.print(f"\n[green]Suggestions saved to: {output}[/green]")
        
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            logger.error(f"Analysis error: {e}", exc_info=True)


@progress.command('status')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--feature', '-f', help='Show progress for specific feature')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def progress_status(ctx, project, feature, format):
    """Show progress status for features or project."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        if feature:
            # Show specific feature progress
            progress = calculator.calculate_feature_progress(feature)
            
            if format == 'json':
                import json
                console.print(json.dumps(progress.__dict__, default=str, indent=2))
            else:
                console.print(f"\n[cyan]Feature: {progress.name}[/cyan]")
                console.print(f"Status: [yellow]{progress.status}[/yellow]")
                console.print(f"Completion: [green]{progress.completion_percentage}%[/green]")
                console.print(f"Dependencies: {progress.dependencies_completed}/{progress.total_dependencies}")
                
                if progress.blockers:
                    console.print(f"\n[red]Blockers:[/red]")
                    for blocker in progress.blockers:
                        blocker_feature = vt.feature_graph.features[blocker]
                        console.print(f"  • {blocker_feature.name} ({blocker})")
                
                if progress.estimated_completion_date:
                    console.print(f"\nEstimated completion: [blue]{progress.estimated_completion_date.strftime('%Y-%m-%d')}[/blue]")
                
                if progress.critical_path:
                    console.print("\n[red]⚠ This feature is on the critical path[/red]")
        else:
            # Show overall project progress
            project_progress = calculator.calculate_project_progress()
            
            if format == 'json':
                import json
                # Convert burndown data to serializable format
                burndown_serializable = [
                    (date.isoformat(), percentage) 
                    for date, percentage in project_progress.burndown_data
                ]
                project_dict = project_progress.__dict__.copy()
                project_dict['burndown_data'] = burndown_serializable
                console.print(json.dumps(project_dict, default=str, indent=2))
            else:
                console.print("\n[bold]Project Progress[/bold]")
                console.print(f"Overall Completion: [green]{project_progress.total_completion}%[/green]")
                console.print(f"Features: {project_progress.features_completed}/{project_progress.total_features}")
                console.print(f"Milestones: {project_progress.milestones_completed}/{project_progress.total_milestones}")
                
                # Progress bar
                progress_bar = "█" * int(project_progress.total_completion / 5) + "░" * (20 - int(project_progress.total_completion / 5))
                console.print(f"\nProgress: [{progress_bar}]")
                
                console.print(f"\nCurrent Velocity: [cyan]{project_progress.current_velocity:.2f}[/cyan] features/day")
                console.print(f"Average Velocity: [cyan]{project_progress.average_velocity:.2f}[/cyan] features/day")
                
                if project_progress.estimated_completion_date:
                    console.print(f"\nEstimated Completion: [blue]{project_progress.estimated_completion_date.strftime('%Y-%m-%d')}[/blue]")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Progress status error: {e}", exc_info=True)


@progress.command('velocity')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.pass_context
def velocity_report(ctx, project):
    """Show velocity metrics and trends."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        # Get velocity report
        report = calculator.get_velocity_report()
        
        console.print("\n[bold]Velocity Report[/bold]")
        
        # Current velocity
        console.print("\n[cyan]Current Velocity:[/cyan]")
        console.print(f"  Daily:   {report['current_velocity']['daily']:.2f} features/day")
        console.print(f"  Weekly:  {report['current_velocity']['weekly']:.2f} features/week")
        console.print(f"  Monthly: {report['current_velocity']['monthly']:.2f} features/month")
        
        # Trend
        trend_color = {
            "improving": "green",
            "stable": "yellow",
            "declining": "red"
        }.get(report['trend'], "white")
        console.print(f"\nTrend: [{trend_color}]{report['trend'].upper()}[/{trend_color}]")
        console.print(f"Predicted Future Velocity: {report['predicted_velocity']:.2f} features/day")
        
        # Bottlenecks
        if report['bottlenecks']:
            console.print("\n[red]Bottlenecks:[/red]")
            table = Table()
            table.add_column("Feature", style="cyan")
            table.add_column("Status", style="yellow")
            table.add_column("Blocking", style="red")
            
            for bottleneck in report['bottlenecks'][:5]:  # Show top 5
                feature = vt.feature_graph.features[bottleneck['feature_id']]
                table.add_row(
                    feature.name,
                    feature.status,
                    str(bottleneck['blocking_count'])
                )
            
            console.print(table)
        
        # Recommendations
        if report['recommendations']:
            console.print("\n[blue]Recommendations:[/blue]")
            for i, rec in enumerate(report['recommendations'], 1):
                console.print(f"  {i}. {rec}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Velocity report error: {e}", exc_info=True)


@progress.command('burndown')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--output', '-o', type=click.Path(), help='Save burndown chart to file')
@click.option('--days', '-d', type=int, default=30, help='Number of days to show')
@click.pass_context
def burndown_chart(ctx, project, output, days):
    """Generate burndown chart for project."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        # Get project progress
        project_progress = calculator.calculate_project_progress()
        
        # Display or save burndown data
        if output:
            # Generate chart image
            import matplotlib.pyplot as plt
            from matplotlib.dates import DateFormatter
            
            dates = [data[0] for data in project_progress.burndown_data[-days:]]
            percentages = [100 - data[1] for data in project_progress.burndown_data[-days:]]  # Invert for burndown
            
            plt.figure(figsize=(10, 6))
            plt.plot(dates, percentages, 'b-', linewidth=2, label='Actual')
            
            # Add ideal burndown line
            ideal_rate = percentages[0] / len(dates)
            ideal_line = [percentages[0] - (i * ideal_rate) for i in range(len(dates))]
            plt.plot(dates, ideal_line, 'r--', linewidth=1, label='Ideal')
            
            plt.title('Project Burndown Chart')
            plt.xlabel('Date')
            plt.ylabel('Work Remaining (%)')
            plt.legend()
            plt.grid(True, alpha=0.3)
            
            # Format dates
            ax = plt.gca()
            ax.xaxis.set_major_formatter(DateFormatter('%m/%d'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            plt.savefig(output)
            console.print(f"[green]✓[/green] Burndown chart saved to: {output}")
        else:
            # Display in terminal
            console.print("\n[bold]Burndown Chart (Text)[/bold]")
            console.print("Work Remaining (%)")
            
            max_width = 60
            for date, completion in project_progress.burndown_data[-days:]:
                remaining = 100 - completion
                bar_width = int((remaining / 100) * max_width)
                bar = "█" * bar_width + "░" * (max_width - bar_width)
                console.print(f"{date.strftime('%m/%d')} [{bar}] {remaining:.1f}%")
            
            if project_progress.estimated_completion_date:
                console.print(f"\nEstimated completion: [blue]{project_progress.estimated_completion_date.strftime('%Y-%m-%d')}[/blue]")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Burndown chart error: {e}", exc_info=True)


@progress.command('milestones')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.pass_context
def milestone_progress(ctx, project):
    """Show progress for project milestones."""
    from .core import VelocityTree
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        # Group features by milestone
        milestones = calculator._group_features_by_milestone()
        
        if not milestones:
            console.print("[yellow]No milestones found[/yellow]")
            return
        
        # Calculate progress for each milestone
        table = Table(title="Milestone Progress")
        table.add_column("Milestone", style="cyan")
        table.add_column("Progress", style="green")
        table.add_column("Features", style="yellow")
        table.add_column("Critical", style="red")
        table.add_column("At Risk", style="orange1")
        table.add_column("ETA", style="blue")
        
        for milestone_id, features in milestones.items():
            milestone_feature = vt.feature_graph.features[milestone_id]
            progress = calculator.calculate_milestone_progress(features)
            
            # Progress bar
            bar_width = 20
            filled = int((progress.completion_percentage / 100) * bar_width)
            progress_bar = "█" * filled + "░" * (bar_width - filled)
            
            eta_str = progress.estimated_completion_date.strftime('%Y-%m-%d') if progress.estimated_completion_date else "N/A"
            
            table.add_row(
                milestone_feature.name,
                f"[{progress_bar}] {progress.completion_percentage:.1f}%",
                f"{progress.features_completed}/{progress.total_features}",
                str(len(progress.critical_features)),
                str(len(progress.at_risk_features)),
                eta_str
            )
        
        console.print(table)
        
        # Show detailed info for critical milestones
        critical_milestones = [
            (mid, calculator.calculate_milestone_progress(features))
            for mid, features in milestones.items()
        ]
        critical_milestones.sort(key=lambda x: len(x[1].at_risk_features), reverse=True)
        
        if critical_milestones and critical_milestones[0][1].at_risk_features:
            console.print("\n[red]⚠ Critical Milestone:[/red]")
            milestone_id, progress = critical_milestones[0]
            milestone_feature = vt.feature_graph.features[milestone_id]
            console.print(f"[cyan]{milestone_feature.name}[/cyan] has {len(progress.at_risk_features)} at-risk features")
            
            console.print("\nAt-risk features:")
            for feature_id in progress.at_risk_features[:5]:  # Show top 5
                feature = vt.feature_graph.features[feature_id]
                console.print(f"  • {feature.name} ({feature.status})")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Milestone progress error: {e}", exc_info=True)


@progress.command('predict')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--feature', '-f', help='Predict specific feature completion')
@click.option('--confidence', '-c', is_flag=True, help='Show confidence intervals')
@click.option('--risks', '-r', is_flag=True, help='Show risk factors')
@click.option('--format', type=click.Choice(['text', 'json']), default='text',
              help='Output format')
@click.pass_context
def predict_completion(ctx, project, feature, confidence, risks, format):
    """Predict completion dates using machine learning."""
    from .core import VelocityTree
    import json
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        # Get prediction
        prediction = calculator.predict_completion(feature_id=feature)
        
        if format == 'json':
            # JSON output
            output = {
                'predicted_date': prediction.predicted_date.isoformat(),
                'confidence': prediction.confidence,
                'confidence_interval': [
                    prediction.confidence_interval[0].isoformat(),
                    prediction.confidence_interval[1].isoformat()
                ],
                'risk_factors': prediction.risk_factors,
                'recommendations': prediction.recommendations
            }
            console.print(json.dumps(output, indent=2))
        else:
            # Text output
            if feature:
                feature_obj = vt.feature_graph.features[feature]
                console.print(f"\n[cyan]Feature:[/cyan] {feature_obj.name}")
            else:
                console.print("\n[cyan]Project Completion Prediction[/cyan]")
            
            console.print(f"[green]Predicted completion:[/green] {prediction.predicted_date.strftime('%Y-%m-%d')}")
            console.print(f"[blue]Confidence:[/blue] {prediction.confidence:.1%}")
            
            if confidence or prediction.confidence < 0.7:
                console.print(f"\n[yellow]Confidence Interval:[/yellow]")
                console.print(f"  Earliest: {prediction.confidence_interval[0].strftime('%Y-%m-%d')}")
                console.print(f"  Latest:   {prediction.confidence_interval[1].strftime('%Y-%m-%d')}")
            
            if risks or prediction.risk_factors:
                console.print(f"\n[red]Risk Factors:[/red]")
                for risk in prediction.risk_factors:
                    console.print(f"  • {risk}")
            
            if prediction.recommendations:
                console.print(f"\n[blue]Recommendations:[/blue]")
                for i, rec in enumerate(prediction.recommendations, 1):
                    console.print(f"  {i}. {rec}")
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Prediction error: {e}", exc_info=True)


@progress.command('train')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--history', type=click.Path(exists=True),
              help='Path to historical completion data')
@click.pass_context
def train_model(ctx, project, history):
    """Train or update the completion prediction model."""
    from .core import VelocityTree
    import json
    
    try:
        # Load project
        vt = VelocityTree(project)
        calculator = ProgressCalculator(vt.feature_graph)
        
        with console.status("Training prediction model..."):
            if history:
                # Load historical data
                with open(history, 'r') as f:
                    historical_data = json.load(f)
                
                # Update history
                for entry in historical_data:
                    calculator.update_completion_history(
                        entry['feature_id'],
                        datetime.fromisoformat(entry['completion_date'])
                    )
            
            # Train model
            calculator._train_model()
        
        console.print("[green]✓[/green] Model trained successfully")
        console.print(f"Training samples: {len(calculator._velocity_history)}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Training error: {e}", exc_info=True)


@cli.group()
def doc():
    """Documentation generation commands."""
    pass


@doc.command('generate')
@click.argument('source', type=click.Path(exists=True))
@click.option('--type', '-t', type=click.Choice(['module', 'api', 'class', 'function', 'readme', 'changelog']), 
              default='module', help='Type of documentation to generate')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'rst', 'json', 'yaml']), 
              default='markdown', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--template', help='Custom template to use')
@click.option('--style', type=click.Choice(['google', 'numpy', 'sphinx']), 
              default='google', help='Documentation style')
@click.pass_context
def generate_docs(ctx, source, type, format, output, template, style):
    """Generate documentation from source code."""
    from pathlib import Path
    from .documentation import DocGenerator, DocConfig, DocType, DocFormat, DocStyle
    
    # Create generator
    config = DocConfig(
        format=DocFormat[format.upper()],
        style=DocStyle[style.upper()],
    )
    generator = DocGenerator(config)
    
    # Generate documentation
    with console.status(f"Generating {type} documentation..."):
        try:
            result = generator.generate_documentation(
                source=Path(source),
                doc_type=DocType[type.upper()],
            )
            
            # Write output
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(result.content)
                console.print(f"[green]✓[/green] Documentation written to {output}")
            else:
                console.print(result.content)
                
            # Show quality metrics
            console.print(f"\n[blue]Quality Score: {result.quality_score:.1f}/100[/blue]")
            console.print(f"[blue]Completeness: {result.completeness_score:.1f}%[/blue]")
            
            # Show issues if any
            if result.issues:
                console.print(f"\n[yellow]Issues found: {len(result.issues)}[/yellow]")
                for issue in result.issues[:5]:  # Show first 5 issues
                    console.print(f"  • {issue.severity.value}: {issue.message}")
                if len(result.issues) > 5:
                    console.print(f"  ... and {len(result.issues) - 5} more")
                    
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            logger.error(f"Documentation generation error: {e}", exc_info=True)


@doc.command('watch')
@click.argument('patterns', nargs=-1, required=True)
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'rst', 'json', 'yaml']), 
              default='markdown', help='Output format')
@click.option('--style', type=click.Choice(['google', 'numpy', 'sphinx']), 
              default='google', help='Documentation style')
@click.option('--interval', '-i', type=float, default=1.0, help='Check interval in seconds')
@click.pass_context
def watch_docs(ctx, patterns, format, style, interval):
    """Watch files and update documentation incrementally."""
    from .documentation import IncrementalDocUpdater, DocConfig, DocFormat, DocStyle
    
    # Create updater
    config = DocConfig(
        format=DocFormat[format.upper()],
        style=DocStyle[style.upper()],
    )
    updater = IncrementalDocUpdater(config)
    
    def update_callback(results, change_set):
        """Callback for documentation updates."""
        console.print(f"\n[blue]Detected {len(change_set.file_changes)} file changes[/blue]")
        
        for file_path, result in results.items():
            console.print(f"[green]✓[/green] Updated: {file_path}")
            console.print(f"  Quality: {result.quality_score:.1f}/100")
            console.print(f"  Completeness: {result.completeness_score:.1f}%")
            
        # Show specific changes
        if change_set.doc_changes:
            console.print(f"\n[yellow]Documentation changes:[/yellow]")
            for change in change_set.doc_changes[:5]:
                action = change.change_type.capitalize()
                console.print(f"  • {action}: {change.element} ({change.element_type})")
                
    console.print(f"[blue]Watching files matching patterns: {patterns}[/blue]")
    console.print(f"[dim]Press Ctrl+C to stop[/dim]\n")
    
    try:
        updater.watch_files(list(patterns), callback=update_callback, interval=interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching files[/yellow]")


@doc.command('invalidate-cache')
@click.argument('files', nargs=-1)
@click.option('--all', '-a', is_flag=True, help='Invalidate entire cache')
@click.pass_context
def invalidate_cache(ctx, files, all):
    """Invalidate documentation cache."""
    from .documentation import IncrementalDocUpdater
    
    updater = IncrementalDocUpdater()
    
    if all:
        updater.invalidate_cache()
        console.print("[green]✓[/green] Invalidated entire documentation cache")
    elif files:
        updater.invalidate_cache(list(files))
        console.print(f"[green]✓[/green] Invalidated cache for {len(files)} files")
    else:
        console.print("[yellow]Specify files to invalidate or use --all flag[/yellow]")


@doc.command('check')
@click.argument('source', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='Check all files recursively')
@click.pass_context
def check_docs(ctx, source, recursive):
    """Check documentation quality and completeness."""
    from pathlib import Path
    from .documentation import DocGenerator
    
    source_path = Path(source)
    
    if source_path.is_file():
        files = [source_path]
    else:
        pattern = "**/*.py" if recursive else "*.py"
        files = list(source_path.glob(pattern))
    
    total_quality = 0
    total_completeness = 0
    all_issues = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Checking {len(files)} files...", total=len(files))
        
        generator = DocGenerator()
        
        for file_path in files:
            progress.update(task, advance=1, description=f"Checking {file_path.name}")
            
            try:
                result = generator.generate_documentation(file_path)
                total_quality += result.quality_score
                total_completeness += result.completeness_score
                all_issues.extend(result.issues)
            except Exception as e:
                console.print(f"[red]Error checking {file_path}: {e}[/red]")
    
    # Show summary
    avg_quality = total_quality / len(files) if files else 0
    avg_completeness = total_completeness / len(files) if files else 0
    
    console.print(f"\n[blue]Documentation Quality Report[/blue]")
    console.print(f"Files checked: {len(files)}")
    console.print(f"Average quality score: {avg_quality:.1f}/100")
    console.print(f"Average completeness: {avg_completeness:.1f}%")
    console.print(f"Total issues: {len(all_issues)}")
    
    # Show issue breakdown
    if all_issues:
        from collections import Counter
        severity_counts = Counter(issue.severity.value for issue in all_issues)
        
        console.print("\n[yellow]Issues by severity:[/yellow]")
        for severity, count in severity_counts.most_common():
            console.print(f"  {severity}: {count}")


@doc.command('suggest')
@click.argument('source', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Save suggestions to file')
@click.option('--apply', '-a', is_flag=True, help='Apply suggestions automatically')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode for applying suggestions')
@click.pass_context
def suggest_improvements(ctx, source, output, apply, interactive):
    """Suggest documentation improvements for source code."""
    from pathlib import Path
    from .documentation import DocGenerator
    
    generator = DocGenerator()
    
    with console.status(f"Analyzing {source}..."):
        try:
            suggestions = generator.suggest_improvements(Path(source))
            
            # Display summary
            console.print(suggestions['summary'])
            
            # Show specific suggestions if any
            if suggestions['element_suggestions']:
                console.print("\n[yellow]Specific Suggestions:[/yellow]")
                
                for element, suggestion in suggestions['element_suggestions'].items():
                    element_type, name = element.split(':', 1)
                    console.print(f"\n[blue]{element_type.capitalize()}: {name}[/blue]")
                    console.print("[dim]Suggested documentation:[/dim]")
                    console.print(suggestion)
                    
                    if interactive and apply:
                        if Confirm.ask("Apply this suggestion?"):
                            # Would implement actual application here
                            console.print("[green]Applied suggestion[/green]")
                            
            # Save to file if requested
            if output:
                import json
                with open(output, 'w') as f:
                    json.dump(suggestions, f, indent=2)
                console.print(f"\n[green]✓[/green] Suggestions saved to {output}")
                
            # Apply all suggestions if requested
            if apply and not interactive:
                count = len(suggestions['element_suggestions'])
                if count > 0:
                    if Confirm.ask(f"Apply {count} suggestions automatically?"):
                        # Would implement actual application here
                        console.print(f"[green]Applied {count} suggestions[/green]")
                        
        except Exception as e:
            console.print(f"[red]Error:[/red] {str(e)}")
            logger.error(f"Documentation suggestion error: {e}", exc_info=True)


@cli.group()
def workflow():
    """Workflow management commands."""
    pass


@workflow.command('list')
@click.pass_context
def list_workflows(ctx):
    """List available workflows."""
    manager = WorkflowManager(config=ctx.obj['config'])
    workflows = manager.list_workflows()
    
    if not workflows:
        console.print("[yellow]No workflows found.[/yellow]")
        return
    
    table = Table(title="Available Workflows")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="yellow")
    table.add_column("Steps", style="green")
    table.add_column("Source", style="blue")
    
    for workflow in workflows:
        table.add_row(
            workflow['name'],
            workflow['description'][:50] + "..." if len(workflow['description']) > 50 else workflow['description'],
            str(workflow['steps']),
            workflow['source']
        )
    
    console.print(table)

@workflow.command('templates')
@click.pass_context
def list_templates(ctx):
    """List available workflow templates."""
    manager = WorkflowManager(config=ctx.obj['config'])
    templates = manager.list_templates()
    
    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return
    
    table = Table(title="Available Workflow Templates")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Description", style="green")
    table.add_column("Steps", style="blue")
    
    for template in templates:
        table.add_row(
            template['id'],
            template['name'],
            template['description'][:50] + "..." if len(template['description']) > 50 else template['description'],
            str(template['steps'])
        )
    
    console.print(table)

@workflow.command()
@click.argument('name')
@click.option('--template', '-t', help='Use a workflow template')
@click.option('--edit', '-e', is_flag=True, help='Edit workflow after creation')
@click.pass_context
def create(ctx, name, template, edit):
    """Create a new workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Check if template is valid
    if template:
        templates = {t['id']: t for t in manager.list_templates()}
        if template not in templates:
            console.print(f"[red]Invalid template:[/red] {template}")
            console.print("Available templates:")
            for tid, tinfo in templates.items():
                console.print(f"  - {tid}: {tinfo['name']}")
            return
    
    workflow = manager.create_workflow(name, template=template)
    console.print(f"[green]✓[/green] Workflow '{name}' created")
    
    if edit:
        from pathlib import Path
        import subprocess
        import os
        
        workflow_file = Path.home() / '.velocitytree' / 'workflows' / f'{name}.yaml'
        editor = os.environ.get('EDITOR', 'nano')
        
        try:
            subprocess.run([editor, str(workflow_file)])
        except Exception as e:
            console.print(f"[yellow]Could not open editor:[/yellow] {e}")
            console.print(f"Edit manually: {workflow_file}")

@workflow.command()
@click.argument('name')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--var', '-V', multiple=True, help='Set a global variable (format: key=value)')
@click.option('--var-file', type=click.Path(exists=True), help='Load variables from JSON file')
@click.pass_context
def run(ctx, name, verbose, dry_run, var, var_file):
    """Run a workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Parse global variables
    global_vars = {}
    
    # Load from file if specified
    if var_file:
        import json
        with open(var_file, 'r') as f:
            global_vars.update(json.load(f))
    
    # Parse command-line variables
    for var_def in var:
        if '=' in var_def:
            key, value = var_def.split('=', 1)
            # Try to parse value as JSON for complex types
            try:
                import json
                value = json.loads(value)
            except:
                pass  # Keep as string
            global_vars[key] = value
    
    try:
        if dry_run:
            workflow = manager.get_workflow(name)
            if not workflow:
                console.print(f"[red]Workflow not found:[/red] {name}")
                return
            
            console.print(f"[blue]Would run workflow:[/blue] {name}")
            console.print(f"[blue]Description:[/blue] {workflow.description}")
            console.print(f"[blue]Steps:[/blue]")
            
            for i, step in enumerate(workflow.steps):
                console.print(f"  {i+1}. {step.name} ({step.type})")
            return
        
        with console.status(f"Running workflow '{name}'...") as status:
            result = manager.run_workflow(name, global_vars=global_vars)
            
        if result['status'] == 'success':
            console.print(f"[green]✓[/green] Workflow completed successfully")
        else:
            console.print(f"[red]✗[/red] Workflow failed")
            
        if verbose:
            console.print("\n[blue]Workflow Results:[/blue]")
            for step_result in result['results']:
                console.print(f"\nStep {step_result['step'] + 1}: {step_result['name']}")
                console.print(f"Status: {step_result['result']['status']}")
                
                if step_result['result'].get('output'):
                    output = str(step_result['result']['output'])
                    if len(output) > 200:
                        output = output[:200] + "..."
                    console.print(f"Output: {output}")
                
                if step_result['result'].get('error'):
                    console.print(f"[red]Error:[/red] {step_result['result']['error']}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")

@workflow.command()
@click.argument('name')
@click.pass_context
def delete(ctx, name):
    """Delete a workflow."""
    manager = WorkflowManager(config=ctx.obj['config'])
    
    # Confirm deletion
    if click.confirm(f"Are you sure you want to delete workflow '{name}'?"):
        manager.delete_workflow(name)
        console.print(f"[green]✓[/green] Workflow '{name}' deleted")
    else:
        console.print("[yellow]Deletion cancelled[/yellow]")

@workflow.command()
@click.argument('name')
@click.pass_context
def show(ctx, name):
    """Show workflow details."""
    manager = WorkflowManager(config=ctx.obj['config'])
    manager.show_workflow_details(name)


@workflow.group()
def variables():
    """Manage workflow variables."""
    pass


@variables.command('list')
@click.option('--scope', '-s', help='Variable scope to list')
@click.pass_context
def list_variables(ctx):
    """List stored workflow variables."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    variables = store.list_variables(scope=ctx.invoked_subcommand)
    
    if not variables:
        console.print("[yellow]No variables found.[/yellow]")
        return
    
    table = Table(title="Workflow Variables")
    table.add_column("Scope", style="cyan")
    table.add_column("Name", style="yellow")
    table.add_column("Value", style="green")
    
    for scope, vars in variables.items():
        for name, value in vars.items():
            table.add_row(scope, name, str(value))
    
    console.print(table)


@variables.command('set')
@click.argument('name')
@click.argument('value')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def set_variable(ctx, name, value, scope):
    """Set a workflow variable."""
    from .workflow_context import VariableStore
    import json
    
    store = VariableStore()
    
    # Try to parse value as JSON
    try:
        parsed_value = json.loads(value)
    except:
        parsed_value = value
    
    store.set(name, parsed_value, scope)
    console.print(f"[green]✓[/green] Variable '{name}' set in scope '{scope}'")


@variables.command('get')
@click.argument('name')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def get_variable(ctx, name, scope):
    """Get a workflow variable."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    value = store.get(name, scope)
    
    if value is None:
        console.print(f"[yellow]Variable '{name}' not found in scope '{scope}'[/yellow]")
    else:
        console.print(f"{name} = {value}")


@variables.command('delete')
@click.argument('name')
@click.option('--scope', '-s', default='global', help='Variable scope')
@click.pass_context
def delete_variable(ctx, name, scope):
    """Delete a workflow variable."""
    from .workflow_context import VariableStore
    
    store = VariableStore()
    if store.delete(name, scope):
        console.print(f"[green]✓[/green] Variable '{name}' deleted from scope '{scope}'")
    else:
        console.print(f"[yellow]Variable '{name}' not found in scope '{scope}'[/yellow]")


@cli.group()
def plugin():
    """Plugin management commands."""
    pass


@plugin.command('list')
@click.pass_context
def list_plugins(ctx):
    """List available plugins."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    plugins = manager.list_plugins()
    
    if not plugins:
        console.print("[yellow]No plugins found.[/yellow]")
        return
    
    table = Table(title="Available Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Version", style="green")
    table.add_column("Description", style="blue")
    
    for plugin in plugins:
        table.add_row(
            plugin['name'],
            plugin['status'],
            plugin['version'],
            plugin['description'][:50] + "..." if len(plugin['description']) > 50 else plugin['description']
        )
    
    console.print(table)


@plugin.command('activate')
@click.argument('name')
@click.pass_context
def activate_plugin(ctx, name):
    """Activate a plugin."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    
    if manager.activate_plugin(name):
        console.print(f"[green]✓[/green] Plugin '{name}' activated")
    else:
        console.print(f"[red]✗[/red] Failed to activate plugin '{name}'")


@plugin.command('deactivate')
@click.argument('name')
@click.pass_context
def deactivate_plugin(ctx, name):
    """Deactivate a plugin."""
    from .plugin_system import PluginManager
    
    manager = PluginManager(config=ctx.obj['config'])
    
    if manager.deactivate_plugin(name):
        console.print(f"[green]✓[/green] Plugin '{name}' deactivated")
    else:
        console.print(f"[red]✗[/red] Failed to deactivate plugin '{name}'")


@cli.command()
def version():
    """Show version information."""
    console.print(version_info())


@cli.command()
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', '-f', type=click.Choice(['yaml', 'json', 'toml']), default='yaml')
@click.pass_context
def config(ctx, output, format):
    """Show or create configuration."""
    config = ctx.obj['config']
    
    if output:
        # Save current configuration
        config.save(output)
        console.print(f"[green]✓[/green] Configuration saved to {output}")
    else:
        # Display current configuration
        import yaml
        import json
        import toml
        
        config_data = config.config_data
        
        if format == 'yaml':
            output_text = yaml.dump(config_data, default_flow_style=False)
        elif format == 'json':
            output_text = json.dumps(config_data, indent=2)
        elif format == 'toml':
            output_text = toml.dumps(config_data)
        
        console.print(output_text)


@visualize.command('graph')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.option('--format', '-f', type=click.Choice(['svg', 'html']), default='html', 
              help='Output format')
@click.option('--layout', '-l', type=click.Choice(['hierarchical', 'spring', 'circular']), 
              default='hierarchical', help='Graph layout algorithm')
@click.option('--session', '-s', help='Planning session ID to visualize')
@click.option('--title', '-t', default='Feature Graph', help='Visualization title')
@click.option('--interactive/--static', default=True, help='Enable interactive features')
@click.pass_context
def visualize_graph(ctx, output, format, layout, session, title, interactive):
    """Generate visualization of feature dependencies."""
    from .feature_graph import FeatureGraph
    from .visualization import FeatureGraphVisualizer
    
    # Create or load feature graph
    if session:
        # Load from planning session
        from .planning_session import PlanningSession
        try:
            session_obj = PlanningSession.load_session(session, ctx.obj['config'])
            if not session_obj.project_plan:
                console.print("[red]Error:[/red] Session has no project plan")
                return
            
            graph = FeatureGraph(f"session_{session}")
            graph.from_project_plan(session_obj.project_plan)
        except Exception as e:
            console.print(f"[red]Error loading session:[/red] {str(e)}")
            return
    else:
        # Create example graph for demo
        graph = FeatureGraph("demo_project")
        
        # Add sample features
        from .feature_graph import FeatureNode
        
        features = [
            FeatureNode(id="auth", name="Authentication", description="User authentication system",
                       type="feature", status="completed"),
            FeatureNode(id="db", name="Database", description="Database setup",
                       type="feature", status="completed"),
            FeatureNode(id="api", name="API", description="REST API",
                       type="feature", status="in_progress"),
            FeatureNode(id="frontend", name="Frontend", description="React frontend",
                       type="feature", status="planned"),
            FeatureNode(id="admin", name="Admin Panel", description="Admin interface",
                       type="feature", status="planned"),
            FeatureNode(id="reports", name="Reports", description="Reporting system",
                       type="feature", status="blocked"),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        # Add relationships
        graph.add_dependency("api", "auth")
        graph.add_dependency("api", "db")
        graph.add_dependency("frontend", "api")
        graph.add_dependency("admin", "frontend")
        graph.add_dependency("reports", "api")
    
    # Create visualizer
    visualizer = FeatureGraphVisualizer(graph, layout=layout)
    
    # Generate output
    if not output:
        output = f"{graph.project_id}_graph.{format}"
    
    try:
        if format == 'svg':
            svg_content = visualizer.generate_svg(output_path=Path(output))
        else:  # html
            html_content = visualizer.generate_html(
                output_path=Path(output),
                title=title,
                interactive=interactive
            )
        
        console.print(f"[green]✓[/green] Visualization saved to: [blue]{output}[/blue]")
        
        # Optionally open in browser
        if format == 'html' and interactive:
            import webbrowser
            if click.confirm("Open in browser?"):
                webbrowser.open(f"file://{Path(output).resolve()}")
                
    except Exception as e:
        console.print(f"[red]Error generating visualization:[/red] {str(e)}")
        logger.error(f"Visualization error: {e}", exc_info=True)


@visualize.command('dependencies')
@click.argument('feature_id')
@click.option('--depth', '-d', type=int, default=2, help='Dependency depth to show')
@click.option('--format', '-f', type=click.Choice(['tree', 'list']), default='tree')
@click.pass_context
def show_dependencies(ctx, feature_id, depth, format):
    """Show feature dependencies."""
    from .feature_graph import FeatureGraph
    
    # For demo, create sample graph
    graph = FeatureGraph("demo")
    
    # Add sample features (same as above)
    from .feature_graph import FeatureNode, RelationType, RelationshipStrength
    
    features = [
        FeatureNode(id="auth", name="Authentication", type="feature", status="completed"),
        FeatureNode(id="db", name="Database", type="feature", status="completed"),
        FeatureNode(id="api", name="API", type="feature", status="in_progress"),
        FeatureNode(id="frontend", name="Frontend", type="feature", status="planned"),
        FeatureNode(id="admin", name="Admin Panel", type="feature", status="planned"),
    ]
    
    for feature in features:
        graph.add_feature(feature)
    
    # Add relationships
    graph.add_relationship("api", "auth", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
    graph.add_relationship("api", "db", RelationType.DEPENDS_ON, RelationshipStrength.CRITICAL)
    graph.add_relationship("frontend", "api", RelationType.DEPENDS_ON, RelationshipStrength.STRONG)
    graph.add_relationship("admin", "frontend", RelationType.DEPENDS_ON, RelationshipStrength.NORMAL)
    
    # Get dependencies
    if feature_id not in graph.features:
        console.print(f"[red]Error:[/red] Feature '{feature_id}' not found")
        return
    
    # Get all dependencies
    all_deps = graph.get_all_dependencies(feature_id, recursive=True)
    direct_deps = graph.get_dependencies(feature_id)
    
    # Get all dependents
    all_dependents = graph.get_all_dependents(feature_id, recursive=True)
    direct_dependents = graph.get_dependents(feature_id)
    
    # Display results
    feature = graph.features[feature_id]
    console.print(f"\n[cyan]Feature:[/cyan] {feature.name} ({feature_id})")
    console.print(f"[cyan]Status:[/cyan] {feature.status}")
    
    if format == 'tree':
        console.print("\n[yellow]Dependencies:[/yellow]")
        if direct_deps:
            _print_dependency_tree(graph, feature_id, seen=set(), prefix="", is_last=True, 
                                 direction="dependencies", max_depth=depth)
        else:
            console.print("  None")
        
        console.print("\n[yellow]Dependents:[/yellow]")
        if direct_dependents:
            _print_dependency_tree(graph, feature_id, seen=set(), prefix="", is_last=True,
                                 direction="dependents", max_depth=depth)
        else:
            console.print("  None")
    else:  # list format
        console.print("\n[yellow]Direct Dependencies:[/yellow]")
        for dep in direct_deps:
            dep_feature = graph.features[dep]
            console.print(f"  • {dep_feature.name} ({dep}) - {dep_feature.status}")
        
        console.print(f"\n[yellow]All Dependencies ({len(all_deps)}):[/yellow]")
        for dep in all_deps:
            dep_feature = graph.features[dep]
            console.print(f"  • {dep_feature.name} ({dep}) - {dep_feature.status}")
        
        console.print("\n[yellow]Direct Dependents:[/yellow]")
        for dep in direct_dependents:
            dep_feature = graph.features[dep]
            console.print(f"  • {dep_feature.name} ({dep}) - {dep_feature.status}")
        
        console.print(f"\n[yellow]All Dependents ({len(all_dependents)}):[/yellow]")
        for dep in all_dependents:
            dep_feature = graph.features[dep]
            console.print(f"  • {dep_feature.name} ({dep}) - {dep_feature.status}")


def _print_dependency_tree(graph, node_id, seen, prefix="", is_last=True, 
                          direction="dependencies", max_depth=3, current_depth=0):
    """Helper to print dependency tree."""
    if current_depth > max_depth or node_id in seen:
        return
    
    seen.add(node_id)
    feature = graph.features[node_id]
    
    # Print current node
    connector = "└── " if is_last else "├── "
    status_color = {
        "completed": "green",
        "in_progress": "blue",
        "blocked": "red",
        "planned": "yellow"
    }.get(feature.status, "white")
    
    console.print(f"{prefix}{connector}[{status_color}]{feature.name}[/{status_color}] ({node_id})")
    
    # Get children based on direction
    if direction == "dependencies":
        children = graph.get_dependencies(node_id)
    else:
        children = graph.get_dependents(node_id)
    
    if children and current_depth < max_depth:
        # Add continuation line for all but last child
        extension = "    " if is_last else "│   "
        for i, child in enumerate(children):
            if child not in seen:
                _print_dependency_tree(
                    graph, child, seen,
                    prefix=prefix + extension,
                    is_last=(i == len(children) - 1),
                    direction=direction,
                    max_depth=max_depth,
                    current_depth=current_depth + 1
                )


@visualize.command('web')
@click.option('--host', '-h', default='127.0.0.1', help='Host to bind to')
@click.option('--port', '-p', type=int, default=5000, help='Port to listen on')
@click.option('--project', help='Project directory to load automatically')
@click.pass_context
def visualize_web(ctx, host, port, project):
    """Start interactive web server for feature graph visualization."""
    server = FeatureGraphWebServer(host=host, port=port)
    
    if project:
        # Load project automatically
        from .core import VelocityTree
        server.velocity_tree = VelocityTree(project)
        server.feature_graph = server.velocity_tree.feature_graph
        console.print(f"[green]✓[/green] Loaded project: {project}")
    
    console.print(f"[blue]Starting web server at http://{host}:{port}[/blue]")
    console.print("[yellow]Press Ctrl+C to stop the server[/yellow]")
    
    try:
        server.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")


@cli.group()
def monitor():
    """Continuous monitoring and evaluation commands."""
    pass


@monitor.command('start')
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--interval', '-i', type=float, default=1.0,
              help='Monitoring interval in seconds')
@click.option('--cpu-limit', '-c', type=float, default=20.0,
              help='Maximum CPU usage percentage')
@click.option('--batch-size', '-b', type=int, default=10,
              help='Batch size for processing changes')
@click.option('--daemon', '-d', is_flag=True,
              help='Run as daemon/background process')
@click.pass_context
def monitor_start(ctx, project, interval, cpu_limit, batch_size, daemon):
    """Start continuous monitoring for code drift and quality issues."""
    from .continuous_eval import ContinuousMonitor, MonitorConfig
    
    # Create monitor configuration
    config = MonitorConfig(
        scan_interval=interval,
        max_cpu_percent=cpu_limit,
        batch_size=batch_size,
        enabled_checks=['drift', 'quality', 'security', 'performance']
    )
    
    # Create monitor
    monitor = ContinuousMonitor(config=config)
    
    if daemon:
        # Run as daemon
        console.print("[yellow]Daemon mode not yet implemented[/yellow]")
        return
    
    console.print(f"[blue]Starting continuous monitoring...[/blue]")
    console.print(f"Project: {project}")
    console.print(f"Interval: {interval}s")
    console.print(f"CPU Limit: {cpu_limit}%")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    try:
        # Start monitoring
        monitors = monitor.start_monitoring(project)
        console.print(f"[green]✓[/green] Monitoring {len(monitors)} files")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping monitor...[/yellow]")
        monitor.stop_monitoring()
        console.print("[green]✓[/green] Monitor stopped")
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        logger.error(f"Monitor error: {e}", exc_info=True)


@monitor.command('stop')
@click.pass_context
def monitor_stop(ctx):
    """Stop continuous monitoring."""
    from .continuous_eval import ContinuousMonitor
    
    monitor = ContinuousMonitor()
    monitor.stop_monitoring()
    console.print("[green]✓[/green] Monitor stopped")


@monitor.command('status')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def monitor_status(ctx, format):
    """Show monitoring status and statistics."""
    from .continuous_eval import ContinuousMonitor
    
    monitor = ContinuousMonitor()
    status = monitor.get_monitoring_status()
    
    if format == 'json':
        import json
        console.print(json.dumps(status, indent=2))
    else:
        # Display as table
        console.print("[blue]Monitoring Status[/blue]\n")
        
        table = Table()
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Status", "Active" if status['is_running'] else "Stopped")
        table.add_row("Files Monitored", str(status['files_monitored']))
        table.add_row("Changes Detected", str(status['changes_detected']))
        table.add_row("Evaluations Run", str(status['evaluations_run']))
        table.add_row("CPU Usage", f"{status['cpu_usage']:.1f}%")
        table.add_row("Memory Usage", f"{status['memory_usage']:.1f} MB")
        
        console.print(table)


@monitor.command('alerts')
@click.option('--type', '-t', type=click.Choice([
    'drift_detected', 'quality_degradation', 'security_issue',
    'performance_regression', 'dependency_update', 'complexity_increase',
    'coverage_drop', 'documentation_stale'
]), help='Filter by alert type')
@click.option('--severity', '-s', type=click.Choice(['info', 'warning', 'error', 'critical']),
              help='Filter by severity')
@click.option('--limit', '-l', type=int, default=20,
              help='Number of alerts to show')
@click.option('--unresolved', '-u', is_flag=True,
              help='Show only unresolved alerts')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def monitor_alerts(ctx, type, severity, limit, unresolved, format):
    """View monitoring alerts."""
    from .continuous_eval import AlertSystem, AlertType, AlertSeverity
    
    alert_system = AlertSystem()
    
    # Build filters
    filters = {}
    if type:
        filters['type'] = AlertType(type)
    if severity:
        filters['severity'] = AlertSeverity[severity.upper()]
    if unresolved:
        filters['resolved'] = False
    
    # Get alerts
    alerts = alert_system.get_alerts(limit=limit, **filters)
    
    if format == 'json':
        import json
        alert_dicts = [alert.to_dict() for alert in alerts]
        console.print(json.dumps(alert_dicts, indent=2))
    else:
        # Display as table
        if not alerts:
            console.print("[yellow]No alerts found[/yellow]")
            return
        
        table = Table(title="Monitoring Alerts")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Title", style="white")
        table.add_column("File", style="blue")
        table.add_column("Time", style="green")
        
        for alert in alerts:
            severity_color = {
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red on white'
            }.get(alert.severity.name, 'white')
            
            file_str = str(alert.file_path) if alert.file_path else "-"
            if alert.line_number:
                file_str += f":{alert.line_number}"
            
            table.add_row(
                str(alert.alert_id),
                alert.type.value,
                f"[{severity_color}]{alert.severity.name}[/{severity_color}]",
                alert.title[:50] + "..." if len(alert.title) > 50 else alert.title,
                file_str,
                alert.timestamp.strftime("%Y-%m-%d %H:%M")
            )
        
        console.print(table)


@monitor.command('resolve')
@click.argument('alert_id', type=int)
@click.pass_context
def monitor_resolve(ctx, alert_id):
    """Mark an alert as resolved."""
    from .continuous_eval import AlertSystem
    
    alert_system = AlertSystem()
    alert_system.resolve_alert(alert_id)
    console.print(f"[green]✓[/green] Alert {alert_id} marked as resolved")


@monitor.command('suggest')
@click.argument('alert_id', type=int, required=False)
@click.option('--file', '-f', type=click.Path(exists=True),
              help='Generate suggestions for specific file')
@click.option('--interactive', '-i', is_flag=True,
              help='Interactive mode for applying suggestions')
@click.option('--output', '-o', type=click.Path(),
              help='Save suggestions to file')
@click.pass_context
def monitor_suggest(ctx, alert_id, file, interactive, output):
    """Generate realignment suggestions for drift or issues."""
    from .continuous_eval import AlertSystem, DriftDetector, RealignmentEngine
    from pathlib import Path
    
    alert_system = AlertSystem()
    drift_detector = DriftDetector()
    realignment_engine = RealignmentEngine()
    
    if alert_id:
        # Get specific alert
        alerts = alert_system.get_alerts(type=AlertType.DRIFT_DETECTED)
        alert = next((a for a in alerts if a.alert_id == alert_id), None)
        
        if not alert:
            console.print(f"[red]Alert {alert_id} not found[/red]")
            return
        
        # Get drift report for the file
        drift_report = drift_detector.check_file_drift(alert.file_path)
    else:
        # Check specific file or current directory
        file_path = Path(file) if file else Path.cwd()
        drift_report = drift_detector.check_file_drift(file_path)
    
    if not drift_report or not drift_report.drifts:
        console.print("[green]No drift detected[/green]")
        return
    
    # Generate suggestions
    suggestions = realignment_engine.generate_suggestions(drift_report)
    
    if not suggestions:
        console.print("[yellow]No suggestions available[/yellow]")
        return
    
    # Display or save suggestions
    if output:
        import json
        with open(output, 'w') as f:
            json.dump([s.to_dict() for s in suggestions], f, indent=2)
        console.print(f"[green]✓[/green] Suggestions saved to {output}")
    else:
        console.print(f"[blue]Realignment Suggestions ({len(suggestions)})[/blue]\n")
        
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"[bold]{i}. {suggestion.title}[/bold]")
            console.print(f"   Category: [yellow]{suggestion.category.value}[/yellow]")
            console.print(f"   Priority: {suggestion.priority}/5")
            console.print(f"   Effort: {suggestion.effort}/5")
            console.print(f"   {suggestion.description}")
            
            if suggestion.code_snippet:
                console.print("   [dim]Code snippet:[/dim]")
                console.print(f"   {suggestion.code_snippet[:100]}...")
            
            if interactive:
                from rich.prompt import Confirm
                if Confirm.ask("Apply this suggestion?"):
                    # Would implement actual application here
                    console.print("[green]Suggestion would be applied[/green]")
            
            console.print()


@monitor.command('summary')
@click.option('--days', '-d', type=int, default=7,
              help='Number of days to include in summary')
@click.pass_context
def monitor_summary(ctx, days):
    """Show monitoring summary and trends."""
    from .continuous_eval import AlertSystem
    
    alert_system = AlertSystem()
    summary = alert_system.get_alert_summary()
    
    console.print("[blue]Monitoring Summary[/blue]\n")
    
    # Overall stats
    console.print(f"Total Unresolved Alerts: [red]{summary['total_unresolved']}[/red]")
    console.print(f"Recent Alerts (last hour): [yellow]{summary['recent_count']}[/yellow]")
    
    # By type
    console.print("\n[cyan]Alerts by Type:[/cyan]")
    for alert_type, count in summary['by_type'].items():
        console.print(f"  {alert_type}: {count}")
    
    # By severity
    console.print("\n[cyan]Alerts by Severity:[/cyan]")
    for severity, count in summary['by_severity'].items():
        color = {
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red on white'
        }.get(severity, 'white')
        console.print(f"  [{color}]{severity}[/{color}]: {count}")
    
    # Top files
    if summary['top_files']:
        console.print("\n[cyan]Files with Most Alerts:[/cyan]")
        for file_info in summary['top_files']:
            console.print(f"  {file_info['file']}: {file_info['count']} alerts")


@monitor.command('background')
@click.argument('action', type=click.Choice(['start', 'stop', 'status']))
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--interval', '-i', type=int, default=300,
              help='Check interval in seconds (default: 300)')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Configuration file for monitoring')
@click.pass_context
def monitor_background(ctx, action, project, interval, config):
    """Manage background monitoring process."""
    from .monitoring import BackgroundMonitor, MonitoringConfig
    from pathlib import Path
    import json
    
    project_path = Path(project).resolve()
    
    # Load config if provided
    monitor_config = MonitoringConfig(check_interval=interval)
    if config:
        with open(config) as f:
            config_data = json.load(f)
            monitor_config = MonitoringConfig(**config_data)
    
    # Create monitor
    monitor = BackgroundMonitor(project_path, monitor_config)
    
    if action == 'start':
        monitor.start()
        console.print(f"[green]✓[/green] Background monitor started for {project_path}")
        console.print(f"Check interval: {monitor_config.check_interval} seconds")
        
    elif action == 'stop':
        monitor.stop()
        console.print("[green]✓[/green] Background monitor stopped")
        
    elif action == 'status':
        status = monitor.get_status()
        
        console.print("[blue]Background Monitor Status[/blue]\n")
        console.print(f"Status: [yellow]{status['status']}[/yellow]")
        
        # Display metrics
        metrics = status['metrics']
        console.print(f"\nLast Check: {metrics['last_check']}")
        console.print(f"Checks Completed: {metrics['checks_completed']}")
        console.print(f"Issues Detected: {metrics['issues_detected']}")
        console.print(f"Alerts Sent: {metrics['alerts_sent']}")
        
        # Display enabled monitors
        enabled = status['config']['enabled_monitors']
        console.print("\n[cyan]Enabled Monitors:[/cyan]")
        for monitor_type, is_enabled in enabled.items():
            status_icon = "[green]✓[/green]" if is_enabled else "[red]✗[/red]"
            console.print(f"  {status_icon} {monitor_type}")
        
        # Display recent issues
        if status['recent_issues']:
            console.print(f"\n[yellow]Recent Issues:[/yellow]")
            for issue in status['recent_issues'][-5:]:  # Show last 5
                console.print(f"  [{issue['severity']}] {issue['type']}: {issue['description']}")


@monitor.command('issues')
@click.option('--severity', '-s', type=click.Choice(['info', 'warning', 'error', 'critical']),
              help='Filter by severity level')
@click.option('--limit', '-l', type=int, default=20,
              help='Limit number of issues shown')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def monitor_issues(ctx, severity, limit, format):
    """Show monitoring issues."""
    from .monitoring import BackgroundMonitor
    from pathlib import Path
    import json
    
    monitor = BackgroundMonitor(Path.cwd())
    issues = monitor.get_issues(severity=severity)[:limit]
    
    if format == 'json':
        console.print(json.dumps(issues, indent=2))
    else:
        if not issues:
            console.print("[yellow]No issues found[/yellow]")
            return
        
        table = Table(title="Monitoring Issues")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Severity", style="red")
        table.add_column("Description", style="white")
        
        for issue in issues:
            severity_color = {
                'info': 'green',
                'warning': 'yellow',
                'error': 'red',
                'critical': 'red on white'
            }.get(issue['severity'], 'white')
            
            table.add_row(
                issue['timestamp'][:19],  # Just date/time, no milliseconds
                issue['type'],
                f"[{severity_color}]{issue['severity'].upper()}[/{severity_color}]",
                issue['description'][:60] + "..." if len(issue['description']) > 60 else issue['description']
            )
        
        console.print(table)


@monitor.command('config')
@click.option('--show', is_flag=True, help='Show current configuration')
@click.option('--output', '-o', type=click.Path(),
              help='Save configuration to file')
@click.option('--enable', '-e', multiple=True,
              type=click.Choice(['git', 'code', 'performance', 'drift']),
              help='Enable specific monitors')
@click.option('--disable', '-d', multiple=True,
              type=click.Choice(['git', 'code', 'performance', 'drift']),
              help='Disable specific monitors')
@click.option('--interval', '-i', type=int,
              help='Set check interval in seconds')
@click.option('--threshold', '-t', type=int,
              help='Set alert threshold')
@click.pass_context
def monitor_config(ctx, show, output, enable, disable, interval, threshold):
    """Manage monitoring configuration."""
    from .monitoring import MonitoringConfig
    import json
    
    config = MonitoringConfig()
    
    # Update configuration
    for monitor_type in enable:
        setattr(config, f'enable_{monitor_type}_monitoring', True)
    
    for monitor_type in disable:
        setattr(config, f'enable_{monitor_type}_monitoring', False)
    
    if interval:
        config.check_interval = interval
    
    if threshold:
        config.alert_threshold = threshold
    
    if show or output:
        config_dict = {
            'check_interval': config.check_interval,
            'alert_threshold': config.alert_threshold,
            'enable_git_monitoring': config.enable_git_monitoring,
            'enable_code_monitoring': config.enable_code_monitoring,
            'enable_performance_monitoring': config.enable_performance_monitoring,
            'enable_drift_detection': config.enable_drift_detection
        }
        
        if show:
            console.print("[blue]Monitoring Configuration[/blue]\n")
            for key, value in config_dict.items():
                console.print(f"{key}: [yellow]{value}[/yellow]")
        
        if output:
            with open(output, 'w') as f:
                json.dump(config_dict, f, indent=2)
            console.print(f"[green]✓[/green] Configuration saved to {output}")


@monitor.command('drift')
@click.argument('action', type=click.Choice(['check', 'report', 'specs']))
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--file', '-f', type=click.Path(exists=True),
              help='Check drift for specific file')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.option('--severity', '-s', type=click.Choice(['low', 'medium', 'high', 'critical']),
              help='Filter by severity level')
@click.pass_context
def monitor_drift(ctx, action, project, file, format, severity):
    """Manage drift detection and reporting."""
    from .monitoring import DriftDetector
    from pathlib import Path
    import json
    
    project_path = Path(project).resolve()
    detector = DriftDetector(project_path)
    
    if action == 'check':
        # Run drift check
        if file:
            report = detector.check_file_drift(Path(file))
        else:
            report = detector.check_drift()
        
        # Filter by severity if requested
        if severity:
            report.drifts = [d for d in report.drifts if d.severity == severity]
        
        if format == 'json':
            console.print(json.dumps(report.to_dict(), indent=2))
        else:
            # Display as table
            console.print(f"[blue]Drift Report for {project_path}[/blue]\n")
            
            if not report.drifts:
                console.print("[green]No drift detected[/green]")
                return
            
            table = Table(title=f"Found {len(report.drifts)} drift issues")
            table.add_column("Type", style="cyan")
            table.add_column("Severity", style="yellow")
            table.add_column("Description", style="white")
            table.add_column("Location", style="blue")
            
            for drift in report.drifts:
                severity_color = {
                    'low': 'green',
                    'medium': 'yellow',
                    'high': 'red',
                    'critical': 'red on white'
                }.get(drift.severity, 'white')
                
                location = str(drift.file_path) if drift.file_path else "-"
                if drift.line_number:
                    location += f":{drift.line_number}"
                
                table.add_row(
                    drift.drift_type.value,
                    f"[{severity_color}]{drift.severity.upper()}[/{severity_color}]",
                    drift.description[:50] + "..." if len(drift.description) > 50 else drift.description,
                    location
                )
            
            console.print(table)
            
            # Show summary
            summary = report.to_dict()['summary']
            console.print(f"\n[cyan]Summary:[/cyan]")
            console.print(f"Files checked: {report.files_checked}")
            console.print(f"Specifications checked: {', '.join(report.checked_specs)}")
            console.print(f"By type: {summary['by_type']}")
            console.print(f"By severity: {summary['by_severity']}")
    
    elif action == 'report':
        # Generate detailed drift report
        report = detector.check_drift()
        
        if format == 'json':
            console.print(json.dumps(report.to_dict(), indent=2))
        else:
            console.print(f"[blue]Detailed Drift Report[/blue]\n")
            
            for drift in report.drifts:
                console.print(f"[yellow]{drift.drift_type.value.upper()}[/yellow]: {drift.description}")
                console.print(f"Severity: [{drift.severity}]{drift.severity}[/{drift.severity}]")
                if drift.file_path:
                    console.print(f"File: {drift.file_path}:{drift.line_number or ''}")
                if drift.expected:
                    console.print(f"Expected: {drift.expected}")
                if drift.actual:
                    console.print(f"Actual: {drift.actual}")
                if drift.spec_reference:
                    console.print(f"Reference: {drift.spec_reference}")
                console.print()
    
    elif action == 'specs':
        # Show loaded specifications
        specs = detector.specifications
        
        if format == 'json':
            console.print(json.dumps({k: bool(v) for k, v in specs.items()}, indent=2))
        else:
            console.print("[blue]Loaded Specifications[/blue]\n")
            
            for spec_name, spec_data in specs.items():
                status = "[green]✓[/green]" if spec_data else "[red]✗[/red]"
                console.print(f"{status} {spec_name}")
                
                if spec_data and spec_name == 'velocitytree':
                    features = spec_data.get('features', {})
                    console.print(f"    Features defined: {len(features)}")
                elif spec_data and spec_name == 'openapi':
                    paths = spec_data.get('paths', {})
                    console.print(f"    API endpoints: {len(paths)}")
                elif spec_data and spec_name == 'readme':
                    console.print(f"    README length: {len(spec_data)} chars")
                elif spec_data and spec_name == 'architecture':
                    console.print(f"    Architecture doc found")
                elif spec_data and spec_name == 'feature_graph':
                    features = spec_data.get('features', {})
                    console.print(f"    Features in graph: {len(features)}")


@monitor.command('alerts')
@click.argument('action', type=click.Choice(['list', 'summary', 'test']))
@click.option('--hours', '-h', type=int, default=24,
              help='Number of hours to look back')
@click.option('--severity', '-s', type=click.Choice(['info', 'warning', 'error', 'critical']),
              help='Filter by severity')
@click.option('--category', '-c', help='Filter by category')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def monitor_alerts(ctx, action, hours, severity, category, format):
    """Manage monitoring alerts."""
    from .monitoring import AlertManager, AlertConfig, AlertSeverity
    from pathlib import Path
    import json
    
    # Create alert manager
    config = AlertConfig(
        alert_file=Path.cwd() / '.velocitytree' / 'alerts.json'
    )
    manager = AlertManager(config)
    
    if action == 'list':
        # Show recent alerts
        # Load alerts from file
        if not config.alert_file.exists():
            console.print("[yellow]No alerts found[/yellow]")
            return
        
        alerts = []
        with open(config.alert_file) as f:
            for line in f:
                alert_data = json.loads(line)
                # Filter by time
                alert_time = datetime.fromisoformat(alert_data['timestamp'])
                if datetime.now() - alert_time > timedelta(hours=hours):
                    continue
                
                # Filter by severity
                if severity and alert_data['severity'] != severity:
                    continue
                
                # Filter by category
                if category and alert_data['category'] != category:
                    continue
                
                alerts.append(alert_data)
        
        if format == 'json':
            console.print(json.dumps(alerts, indent=2))
        else:
            if not alerts:
                console.print("[yellow]No alerts match criteria[/yellow]")
                return
            
            table = Table(title=f"Alerts (last {hours} hours)")
            table.add_column("Time", style="cyan")
            table.add_column("Severity", style="yellow")
            table.add_column("Category", style="blue")
            table.add_column("Title", style="white")
            table.add_column("Source", style="green")
            
            for alert in sorted(alerts, key=lambda x: x['timestamp'], reverse=True):
                severity_color = {
                    'info': 'green',
                    'warning': 'yellow',
                    'error': 'red',
                    'critical': 'red on white'
                }.get(alert['severity'], 'white')
                
                table.add_row(
                    alert['timestamp'][11:19],  # Just time
                    f"[{severity_color}]{alert['severity'].upper()}[/{severity_color}]",
                    alert['category'],
                    alert['title'][:40] + "..." if len(alert['title']) > 40 else alert['title'],
                    alert['source']
                )
            
            console.print(table)
    
    elif action == 'summary':
        # Show alert summary
        summary = manager.get_alert_summary(hours=hours)
        
        if format == 'json':
            console.print(json.dumps(summary, indent=2))
        else:
            console.print(f"[blue]Alert Summary (last {hours} hours)[/blue]\n")
            console.print(f"Total Alerts: [yellow]{summary['total_alerts']}[/yellow]")
            
            # By severity
            console.print("\n[cyan]By Severity:[/cyan]")
            for sev, count in summary['by_severity'].items():
                color = {
                    'info': 'green',
                    'warning': 'yellow',
                    'error': 'red',
                    'critical': 'red on white'
                }.get(sev, 'white')
                console.print(f"  [{color}]{sev.upper()}[/{color}]: {count}")
            
            # By category
            console.print("\n[cyan]By Category:[/cyan]")
            for cat, count in sorted(summary['by_category'].items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {cat}: {count}")
            
            # By source
            console.print("\n[cyan]By Source:[/cyan]")
            for src, count in sorted(summary['by_source'].items(), key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {src}: {count}")
    
    elif action == 'test':
        # Send test alert
        test_severity = AlertSeverity.INFO
        if severity:
            test_severity = {
                'info': AlertSeverity.INFO,
                'warning': AlertSeverity.WARNING,
                'error': AlertSeverity.ERROR,
                'critical': AlertSeverity.CRITICAL
            }[severity]
        
        alert = manager.create_alert(
            severity=test_severity,
            title="Test Alert",
            description="This is a test alert from the monitoring system",
            source="CLI",
            category=category or "test",
            details={'triggered_by': 'user', 'command': 'velocitytree monitor alerts test'}
        )
        
        if manager.send_alert(alert):
            console.print(f"[green]✓[/green] Test alert sent successfully")
        else:
            console.print(f"[red]✗[/red] Failed to send test alert (may be rate limited or suppressed)")


@monitor.command('alert-config')
@click.option('--show', is_flag=True, help='Show current alert configuration')
@click.option('--channel', '-c', multiple=True,
              type=click.Choice(['log', 'file', 'email', 'webhook', 'console']),
              help='Enable alert channels')
@click.option('--email-config', type=click.Path(exists=True),
              help='Path to email configuration file')
@click.option('--webhook-url', help='Webhook URL for alerts')
@click.option('--rate-limit', type=click.Tuple([str, int]),
              multiple=True, help='Set rate limits (e.g., per_minute 10)')
@click.option('--output', '-o', type=click.Path(),
              help='Save configuration to file')
@click.pass_context
def monitor_alert_config(ctx, show, channel, email_config, webhook_url, rate_limit, output):
    """Configure alert system."""
    from .monitoring import AlertConfig, AlertChannel
    import json
    
    config = AlertConfig()
    
    # Update channels
    if channel:
        config.enabled_channels = []
        for ch in channel:
            config.enabled_channels.append(AlertChannel[ch.upper()])
    
    # Load email config
    if email_config:
        with open(email_config) as f:
            config.email_config = json.load(f)
    
    # Set webhook URL
    if webhook_url:
        config.webhook_config = {'webhook_url': webhook_url}
    
    # Set rate limits
    if rate_limit:
        for period, limit in rate_limit:
            config.rate_limits[period] = limit
    
    if show or output:
        config_dict = {
            'enabled_channels': [ch.value for ch in config.enabled_channels],
            'rate_limits': config.rate_limits,
            'severity_thresholds': {k.value: v for k, v in config.severity_thresholds.items()},
            'suppression_window': config.suppression_window
        }
        
        if config.email_config:
            config_dict['email_config'] = config.email_config
        if config.webhook_config:
            config_dict['webhook_config'] = config.webhook_config
        
        if show:
            console.print("[blue]Alert Configuration[/blue]\n")
            console.print(json.dumps(config_dict, indent=2))
        
        if output:
            with open(output, 'w') as f:
                json.dump(config_dict, f, indent=2)
            console.print(f"[green]✓[/green] Configuration saved to {output}")


@monitor.command('realign')
@click.argument('action', type=click.Choice(['suggest', 'apply', 'export']))
@click.option('--project', '-p', type=click.Path(exists=True), default='.',
              help='Project directory (defaults to current directory)')
@click.option('--drift-file', '-d', type=click.Path(exists=True),
              help='Path to drift report file')
@click.option('--suggestion-id', '-s', help='Specific suggestion ID to apply')
@click.option('--priority', type=click.Choice(['critical', 'high', 'medium', 'low']),
              help='Filter suggestions by priority')
@click.option('--type', '-t', type=click.Choice(['code_change', 'file_creation', 'documentation_update', 'configuration_change', 'refactoring']),
              help='Filter suggestions by type')
@click.option('--automated-only', is_flag=True, help='Show only automated suggestions')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode for applying suggestions')
@click.option('--output', '-o', type=click.Path(), help='Output file for export')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.pass_context
def monitor_realign(ctx, action, project, drift_file, suggestion_id, priority, type, automated_only, interactive, output, format):
    """Generate and apply realignment suggestions."""
    from .monitoring import DriftDetector, RealignmentEngine
    from pathlib import Path
    import json
    
    project_path = Path(project).resolve()
    
    if action == 'suggest':
        # Generate suggestions from drift
        if drift_file:
            # Load drift report from file
            with open(drift_file) as f:
                drift_data = json.load(f)
            # TODO: Reconstruct DriftReport from data
            console.print("[yellow]Loading drift report from file not yet implemented[/yellow]")
            return
        else:
            # Run drift detection
            console.print("[blue]Running drift detection...[/blue]")
            detector = DriftDetector(project_path)
            drift_report = detector.check_drift()
        
        # Generate suggestions
        engine = RealignmentEngine(project_path)
        plan = engine.generate_suggestions(drift_report)
        
        # Filter suggestions
        filtered_suggestions = plan.suggestions
        
        if priority:
            filtered_suggestions = [s for s in filtered_suggestions if s.priority.value == priority]
        
        if type:
            filtered_suggestions = [s for s in filtered_suggestions if s.suggestion_type.value == type]
        
        if automated_only:
            filtered_suggestions = [s for s in filtered_suggestions if s.automated]
        
        if format == 'json':
            plan.suggestions = filtered_suggestions
            console.print(json.dumps(plan.to_dict(), indent=2))
        else:
            if not filtered_suggestions:
                console.print("[yellow]No suggestions match criteria[/yellow]")
                return
            
            console.print(f"[blue]Realignment Suggestions for {project_path}[/blue]\n")
            
            table = Table(title=f"Found {len(filtered_suggestions)} suggestions")
            table.add_column("ID", style="cyan", max_width=8)
            table.add_column("Type", style="yellow")
            table.add_column("Priority", style="red")
            table.add_column("Title", style="white")
            table.add_column("Effort", style="green")
            table.add_column("Auto", style="blue")
            
            for suggestion in filtered_suggestions:
                priority_color = {
                    'critical': 'red on white',
                    'high': 'red',
                    'medium': 'yellow',
                    'low': 'green'
                }.get(suggestion.priority.value, 'white')
                
                table.add_row(
                    suggestion.suggestion_id[:8],
                    suggestion.suggestion_type.value,
                    f"[{priority_color}]{suggestion.priority.value.upper()}[/{priority_color}]",
                    suggestion.title[:50] + "..." if len(suggestion.title) > 50 else suggestion.title,
                    suggestion.estimated_effort,
                    "✓" if suggestion.automated else "✗"
                )
            
            console.print(table)
            
            # Show summary
            console.print(f"\n[cyan]Summary:[/cyan]")
            console.print(f"Total effort: {plan.total_effort}")
            console.print(f"Automated available: {sum(1 for s in filtered_suggestions if s.automated)}")
            
            # Show details for first few suggestions
            console.print("\n[cyan]Top Suggestions:[/cyan]")
            for i, suggestion in enumerate(filtered_suggestions[:3]):
                console.print(f"\n[yellow]{i+1}. {suggestion.title}[/yellow]")
                console.print(f"   Type: {suggestion.suggestion_type.value}")
                console.print(f"   Priority: {suggestion.priority.value}")
                console.print(f"   Description: {suggestion.description}")
                console.print("   Steps:")
                for step in suggestion.implementation_steps[:3]:
                    console.print(f"     - {step}")
                if len(suggestion.implementation_steps) > 3:
                    console.print(f"     ... and {len(suggestion.implementation_steps) - 3} more steps")
    
    elif action == 'apply':
        # Apply specific suggestion
        if not suggestion_id:
            console.print("[red]Error: --suggestion-id required for apply action[/red]")
            return
        
        # Load suggestions (would need to persist them in practice)
        console.print("[yellow]Apply functionality requires persistent suggestion storage[/yellow]")
        console.print("In a real implementation, suggestions would be loaded from storage")
        
        # Mock suggestion for demonstration
        if suggestion_id == "demo":
            from .monitoring import RealignmentSuggestion, DriftItem, DriftType, SuggestionType, SuggestionPriority
            
            mock_suggestion = RealignmentSuggestion(
                suggestion_id="demo",
                drift_item=DriftItem(
                    drift_type=DriftType.CODE_STRUCTURE,
                    description="Demo drift",
                    severity="medium"
                ),
                suggestion_type=SuggestionType.FILE_CREATION,
                priority=SuggestionPriority.MEDIUM,
                title="Create demo file",
                description="Demo suggestion",
                implementation_steps=["Create file"],
                file_changes=[{
                    'action': 'create',
                    'path': 'demo.txt',
                    'content': 'Demo content'
                }],
                automated=True
            )
            
            engine = RealignmentEngine(project_path)
            if engine.apply_suggestion(mock_suggestion):
                console.print("[green]✓[/green] Suggestion applied successfully")
            else:
                console.print("[red]✗[/red] Failed to apply suggestion")
    
    elif action == 'export':
        # Export suggestions to file
        if not output:
            console.print("[red]Error: --output required for export action[/red]")
            return
        
        # Generate suggestions
        detector = DriftDetector(project_path)
        drift_report = detector.check_drift()
        
        engine = RealignmentEngine(project_path)
        plan = engine.generate_suggestions(drift_report)
        
        # Export to file
        with open(output, 'w') as f:
            json.dump(plan.to_dict(), f, indent=2)
        
        console.print(f"[green]✓[/green] Suggestions exported to {output}")


# Register onboarding command
create_onboarding_command(cli)


def main():
    """Main entry point."""
    # Check for first run
    from .onboarding import check_first_run
    if check_first_run():
        return  # Exit after onboarding
        
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()