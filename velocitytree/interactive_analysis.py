"""Interactive code analysis interface."""

from typing import Optional, List, Dict, Any
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .code_analysis.analyzer import CodeAnalyzer
from .code_analysis.security import SecurityAnalyzer
from .code_analysis.models import (
    ModuleAnalysis,
    FunctionAnalysis,
    ClassAnalysis,
    CodeIssue,
    Severity,
    IssueCategory,
)
from .documentation.quality import DocQualityChecker
from .utils import logger


class InteractiveAnalyzer:
    """Interactive code analysis session."""
    
    def __init__(self, console: Console):
        """Initialize the interactive analyzer.
        
        Args:
            console: Rich console for output
        """
        self.console = console
        self.code_analyzer = CodeAnalyzer()
        self.security_analyzer = SecurityAnalyzer()
        self.quality_checker = DocQualityChecker()
        self.current_analysis = None
        self.history = []
        
    def start_session(self, path: Path):
        """Start an interactive analysis session.
        
        Args:
            path: Path to analyze
        """
        self.console.print(f"[bold blue]Starting interactive analysis for: {path}[/bold blue]")
        
        # Initial analysis
        self._analyze(path)
        
        # Interactive loop
        while True:
            command = self._get_command()
            
            if command == 'quit':
                break
            elif command == 'help':
                self._show_help()
            elif command == 'summary':
                self._show_summary()
            elif command == 'issues':
                self._show_issues()
            elif command == 'metrics':
                self._show_metrics()
            elif command == 'functions':
                self._show_functions()
            elif command == 'classes':
                self._show_classes()
            elif command == 'doc-quality':
                self._check_doc_quality()
            elif command == 'security':
                self._check_security()
            elif command == 'suggest':
                self._suggest_improvements()
            elif command == 'export':
                self._export_results()
            elif command.startswith('analyze '):
                new_path = command.split(' ', 1)[1]
                self._analyze(Path(new_path))
            elif command.startswith('detail '):
                item = command.split(' ', 1)[1]
                self._show_detail(item)
            else:
                self.console.print(f"[red]Unknown command: {command}[/red]")
                self.console.print("Type 'help' for available commands")
    
    def _analyze(self, path: Path):
        """Perform analysis on a path."""
        try:
            self.console.print(f"[blue]Analyzing {path}...[/blue]")
            
            if path.is_file():
                self.current_analysis = self.code_analyzer.analyze_file(path)
                self.history.append(path)
            else:
                self.current_analysis = self.code_analyzer.analyze_directory(path)
                self.history.append(path)
                
            if self.current_analysis:
                self.console.print("[green]Analysis complete![/green]")
                self._show_summary()
            else:
                self.console.print("[red]Analysis failed[/red]")
                
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")
            logger.error(f"Analysis error: {e}", exc_info=True)
    
    def _get_command(self) -> str:
        """Get user command with autocomplete."""
        commands = [
            'help', 'quit', 'summary', 'issues', 'metrics', 
            'functions', 'classes', 'doc-quality', 'security',
            'suggest', 'export', 'analyze', 'detail'
        ]
        completer = WordCompleter(commands)
        
        return prompt(
            "analyze> ",
            completer=completer,
        ).strip()
    
    def _show_help(self):
        """Show help information."""
        help_text = """
[bold]Available Commands:[/bold]

[green]Navigation:[/green]
  help         - Show this help
  quit         - Exit interactive mode
  analyze PATH - Analyze a different file/directory
  
[green]Analysis:[/green]
  summary      - Show analysis summary
  issues       - List all issues
  metrics      - Show code metrics
  functions    - List all functions
  classes      - List all classes
  security     - Security analysis
  doc-quality  - Documentation quality check
  
[green]Details:[/green]
  detail ITEM  - Show details for function/class
  suggest      - Get improvement suggestions
  export       - Export results to file

[green]Examples:[/green]
  detail MyClass
  analyze ./src/main.py
  export --format json
"""
        self.console.print(help_text)
    
    def _show_summary(self):
        """Show analysis summary."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        if isinstance(self.current_analysis, ModuleAnalysis):
            # Single file analysis
            analysis = self.current_analysis
            
            summary = Table(title="Analysis Summary")
            summary.add_column("Metric", style="cyan")
            summary.add_column("Value", style="green")
            
            if analysis.metrics:
                summary.add_row("Lines of Code", str(analysis.metrics.lines_of_code))
                summary.add_row("Cyclomatic Complexity", f"{analysis.metrics.cyclomatic_complexity:.1f}")
                summary.add_row("Maintainability Index", f"{analysis.metrics.maintainability_index:.1f}")
            
            summary.add_row("Functions", str(len(analysis.functions)))
            summary.add_row("Classes", str(len(analysis.classes)))
            summary.add_row("Issues", str(len(analysis.issues)))
            
            self.console.print(summary)
        else:
            # Directory analysis
            analysis = self.current_analysis
            
            summary = Table(title="Analysis Summary")
            summary.add_column("Metric", style="cyan")
            summary.add_column("Value", style="green")
            
            summary.add_row("Files Analyzed", str(analysis.files_analyzed))
            summary.add_row("Total Lines", str(analysis.total_lines))
            summary.add_row("Total Issues", str(len(analysis.all_issues)))
            
            self.console.print(summary)
    
    def _show_issues(self):
        """Show all issues."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        issues = []
        if isinstance(self.current_analysis, ModuleAnalysis):
            issues = self.current_analysis.issues
        else:
            issues = self.current_analysis.all_issues
            
        if not issues:
            self.console.print("[green]No issues found![/green]")
            return
            
        # Group by severity
        by_severity = {}
        for issue in issues:
            by_severity.setdefault(issue.severity.value, []).append(issue)
            
        for severity in ['critical', 'error', 'warning', 'info']:
            if severity in by_severity:
                self.console.print(f"\n[bold]{severity.upper()}:[/bold]")
                for issue in by_severity[severity]:
                    self.console.print(f"  • {issue.message}")
                    self.console.print(f"    Location: {issue.location.file_path}:{issue.location.line_start}")
                    if issue.suggestion:
                        self.console.print(f"    Fix: {issue.suggestion}")
    
    def _show_metrics(self):
        """Show detailed metrics."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        if isinstance(self.current_analysis, ModuleAnalysis):
            metrics = self.current_analysis.metrics
            if not metrics:
                self.console.print("[yellow]No metrics available[/yellow]")
                return
                
            table = Table(title="Code Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Rating", style="yellow")
            
            # Lines of code
            table.add_row(
                "Lines of Code",
                str(metrics.lines_of_code),
                self._rate_loc(metrics.lines_of_code)
            )
            
            # Complexity
            table.add_row(
                "Cyclomatic Complexity",
                f"{metrics.cyclomatic_complexity:.1f}",
                self._rate_complexity(metrics.cyclomatic_complexity)
            )
            
            # Maintainability
            table.add_row(
                "Maintainability Index",
                f"{metrics.maintainability_index:.1f}",
                self._rate_maintainability(metrics.maintainability_index)
            )
            
            # Technical debt
            if metrics.technical_debt_ratio > 0:
                table.add_row(
                    "Technical Debt Ratio",
                    f"{metrics.technical_debt_ratio:.1%}",
                    self._rate_debt(metrics.technical_debt_ratio)
                )
            
            self.console.print(table)
    
    def _show_functions(self):
        """Show all functions."""
        if not self.current_analysis or not isinstance(self.current_analysis, ModuleAnalysis):
            self.console.print("[yellow]No module analysis available[/yellow]")
            return
            
        functions = self.current_analysis.functions
        if not functions:
            self.console.print("[yellow]No functions found[/yellow]")
            return
            
        table = Table(title="Functions")
        table.add_column("Name", style="cyan")
        table.add_column("Lines", style="green")
        table.add_column("Parameters", style="yellow")
        table.add_column("Returns", style="blue")
        table.add_column("Docstring", style="magenta")
        
        for func in functions:
            table.add_row(
                func.name,
                str(func.lines_of_code) if hasattr(func, 'lines_of_code') else "?",
                str(len(func.parameters)),
                func.returns or "None",
                "✓" if func.docstring else "✗"
            )
            
        self.console.print(table)
    
    def _show_classes(self):
        """Show all classes."""
        if not self.current_analysis or not isinstance(self.current_analysis, ModuleAnalysis):
            self.console.print("[yellow]No module analysis available[/yellow]")
            return
            
        classes = self.current_analysis.classes
        if not classes:
            self.console.print("[yellow]No classes found[/yellow]")
            return
            
        table = Table(title="Classes")
        table.add_column("Name", style="cyan")
        table.add_column("Methods", style="green")
        table.add_column("Attributes", style="yellow")
        table.add_column("Parents", style="blue")
        table.add_column("Docstring", style="magenta")
        
        for cls in classes:
            table.add_row(
                cls.name,
                str(len(cls.methods)),
                str(len(cls.instance_attributes)) if hasattr(cls, 'instance_attributes') else "?",
                ", ".join(cls.parent_classes) or "None",
                "✓" if cls.docstring else "✗"
            )
            
        self.console.print(table)
    
    def _check_doc_quality(self):
        """Check documentation quality."""
        if not self.current_analysis or not isinstance(self.current_analysis, ModuleAnalysis):
            self.console.print("[yellow]No module analysis available[/yellow]")
            return
            
        try:
            quality_report = self.quality_checker.check_quality(self.current_analysis)
            
            # Overall score
            self.console.print(f"\n[bold]Documentation Quality Score: {quality_report.overall_score:.1f}/100[/bold]")
            
            # Metric breakdown
            table = Table(title="Quality Metrics")
            table.add_column("Metric", style="cyan")
            table.add_column("Score", style="green")
            
            for metric, score in quality_report.metric_scores.items():
                table.add_row(metric.value, f"{score:.1f}")
                
            self.console.print(table)
            
            # Issues
            if quality_report.issues:
                self.console.print("\n[yellow]Documentation Issues:[/yellow]")
                for issue in quality_report.issues[:10]:  # Show top 10
                    self.console.print(f"  • {issue.message}")
                    
            # Suggestions
            if quality_report.suggestions:
                self.console.print("\n[blue]Suggestions:[/blue]")
                for suggestion in quality_report.suggestions[:5]:  # Show top 5
                    self.console.print(f"  • {suggestion}")
                    
        except Exception as e:
            self.console.print(f"[red]Error checking documentation quality: {e}[/red]")
    
    def _check_security(self):
        """Perform security analysis."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        try:
            path = self.history[-1] if self.history else None
            if not path:
                self.console.print("[yellow]No file path available[/yellow]")
                return
                
            security_result = self.security_analyzer.analyze_file(path)
            vulnerabilities = security_result['vulnerabilities']
            
            if not vulnerabilities:
                self.console.print("[green]No security vulnerabilities found![/green]")
            else:
                self.console.print(f"\n[red]Found {len(vulnerabilities)} security vulnerabilities:[/red]")
                
                # Group by severity
                by_severity = {}
                for vuln in vulnerabilities:
                    by_severity.setdefault(vuln.severity.value, []).append(vuln)
                
                for severity in ['critical', 'high', 'medium', 'low']:
                    if severity in by_severity:
                        self.console.print(f"\n[bold]{severity.upper()}:[/bold]")
                        for vuln in by_severity[severity]:
                            self.console.print(f"  • {vuln.description}")
                            self.console.print(f"    Location: {vuln.location.file_path}:{vuln.location.line_start}")
                            self.console.print(f"    Fix: {vuln.fix_suggestion}")
                            
            # Security score
            self.console.print(f"\n[blue]Security Score: {security_result['summary']['security_score']:.1f}/100[/blue]")
            
        except Exception as e:
            self.console.print(f"[red]Error during security analysis: {e}[/red]")
    
    def _suggest_improvements(self):
        """Get improvement suggestions."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        suggestions = []
        
        # Collect suggestions from various sources
        if isinstance(self.current_analysis, ModuleAnalysis):
            # Complexity suggestions
            if self.current_analysis.metrics:
                if self.current_analysis.metrics.cyclomatic_complexity > 10:
                    suggestions.append("Consider refactoring complex functions to reduce cyclomatic complexity")
                if self.current_analysis.metrics.maintainability_index < 65:
                    suggestions.append("Improve maintainability by breaking down complex code")
                    
            # Documentation suggestions
            undocumented_funcs = [f for f in self.current_analysis.functions if not f.docstring]
            if undocumented_funcs:
                suggestions.append(f"Add docstrings to {len(undocumented_funcs)} undocumented functions")
                
            # Pattern suggestions
            if self.current_analysis.patterns:
                for pattern in self.current_analysis.patterns:
                    if pattern.confidence > 0.8:
                        suggestions.append(f"Consider addressing {pattern.pattern_type.value}: {pattern.name}")
        
        if suggestions:
            self.console.print("\n[blue]Improvement Suggestions:[/blue]")
            for i, suggestion in enumerate(suggestions, 1):
                self.console.print(f"{i}. {suggestion}")
        else:
            self.console.print("[green]No specific suggestions - code looks good![/green]")
    
    def _show_detail(self, item_name: str):
        """Show details for a specific function or class."""
        if not self.current_analysis or not isinstance(self.current_analysis, ModuleAnalysis):
            self.console.print("[yellow]No module analysis available[/yellow]")
            return
            
        # Search in functions
        for func in self.current_analysis.functions:
            if func.name == item_name:
                self._show_function_detail(func)
                return
                
        # Search in classes
        for cls in self.current_analysis.classes:
            if cls.name == item_name:
                self._show_class_detail(cls)
                return
                
        self.console.print(f"[red]Item not found: {item_name}[/red]")
    
    def _show_function_detail(self, func: FunctionAnalysis):
        """Show detailed information about a function."""
        panel_content = f"""[bold]{func.name}[/bold]

[cyan]Parameters:[/cyan] {', '.join(func.parameters) or 'None'}
[cyan]Returns:[/cyan] {func.returns or 'None'}
[cyan]Decorators:[/cyan] {', '.join(func.decorators) or 'None'}

[cyan]Docstring:[/cyan]
{func.docstring or '[dim]No docstring[/dim]'}
"""
        
        if hasattr(func, 'lines_of_code'):
            panel_content += f"\n[cyan]Lines of code:[/cyan] {func.lines_of_code}"
        if hasattr(func, 'complexity'):
            panel_content += f"\n[cyan]Complexity:[/cyan] {func.complexity}"
            
        panel = Panel(panel_content, title=f"Function: {func.name}")
        self.console.print(panel)
    
    def _show_class_detail(self, cls: ClassAnalysis):
        """Show detailed information about a class."""
        panel_content = f"""[bold]{cls.name}[/bold]

[cyan]Parent Classes:[/cyan] {', '.join(cls.parent_classes) or 'object'}
[cyan]Methods:[/cyan] {len(cls.methods)}
[cyan]Instance Attributes:[/cyan] {len(cls.instance_attributes) if hasattr(cls, 'instance_attributes') else '?'}

[cyan]Docstring:[/cyan]
{cls.docstring or '[dim]No docstring[/dim]'}

[cyan]Methods:[/cyan]"""
        
        for method in cls.methods:
            panel_content += f"\n  • {method.name}({', '.join(method.parameters)})"
            
        panel = Panel(panel_content, title=f"Class: {cls.name}")
        self.console.print(panel)
    
    def _export_results(self):
        """Export analysis results."""
        if not self.current_analysis:
            self.console.print("[yellow]No analysis available[/yellow]")
            return
            
        format_choice = Prompt.ask(
            "Export format",
            choices=["json", "markdown", "html"],
            default="markdown"
        )
        
        filename = Prompt.ask("Output filename", default=f"analysis_{format_choice}")
        
        try:
            from .report_generator import ReportGenerator
            report_gen = ReportGenerator()
            
            if isinstance(self.current_analysis, ModuleAnalysis):
                report = report_gen.generate_file_report(self.current_analysis, format_choice)
            else:
                report = report_gen.generate_directory_report(self.current_analysis, format_choice)
                
            with open(filename, 'w') as f:
                f.write(report)
                
            self.console.print(f"[green]Results exported to: {filename}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]Error exporting results: {e}[/red]")
    
    def _rate_loc(self, loc: int) -> str:
        """Rate lines of code."""
        if loc < 50:
            return "[green]Small[/green]"
        elif loc < 200:
            return "[yellow]Medium[/yellow]"
        else:
            return "[red]Large[/red]"
    
    def _rate_complexity(self, complexity: float) -> str:
        """Rate cyclomatic complexity."""
        if complexity < 5:
            return "[green]Simple[/green]"
        elif complexity < 10:
            return "[yellow]Moderate[/yellow]"
        else:
            return "[red]Complex[/red]"
    
    def _rate_maintainability(self, index: float) -> str:
        """Rate maintainability index."""
        if index > 80:
            return "[green]Excellent[/green]"
        elif index > 65:
            return "[yellow]Good[/yellow]"
        else:
            return "[red]Poor[/red]"
    
    def _rate_debt(self, ratio: float) -> str:
        """Rate technical debt ratio."""
        if ratio < 0.05:
            return "[green]Low[/green]"
        elif ratio < 0.1:
            return "[yellow]Medium[/yellow]"
        else:
            return "[red]High[/red]"