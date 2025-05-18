"""Report generation for code analysis results."""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from jinja2 import Template

from .code_analysis.models import (
    ModuleAnalysis,
    AnalysisResult,
    CodeIssue,
    Severity,
    IssueCategory,
)
from .utils import logger


class ReportGenerator:
    """Generate reports from code analysis results."""
    
    def __init__(self):
        """Initialize the report generator."""
        self.markdown_template = self._load_markdown_template()
        self.html_template = self._load_html_template()
    
    def generate_file_report(self, analysis: ModuleAnalysis, format: str) -> str:
        """Generate a report for a single file analysis.
        
        Args:
            analysis: Module analysis result
            format: Report format (json, markdown, html, report)
            
        Returns:
            Generated report content
        """
        if format == 'json':
            return self._generate_json_report(analysis)
        elif format == 'markdown' or format == 'report':
            return self._generate_markdown_report(analysis)
        elif format == 'html':
            return self._generate_html_report(analysis)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_directory_report(self, analysis: AnalysisResult, format: str) -> str:
        """Generate a report for directory analysis.
        
        Args:
            analysis: Directory analysis result
            format: Report format (json, markdown, html, report)
            
        Returns:
            Generated report content
        """
        if format == 'json':
            return self._generate_json_directory_report(analysis)
        elif format == 'markdown' or format == 'report':
            return self._generate_markdown_directory_report(analysis)
        elif format == 'html':
            return self._generate_html_directory_report(analysis)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def generate_batch_report(self, results: List[Dict[str, Any]], format: str) -> str:
        """Generate a report for batch analysis results.
        
        Args:
            results: List of analysis results
            format: Report format (json, markdown, html, report)
            
        Returns:
            Generated report content
        """
        if format == 'json':
            return json.dumps({
                'timestamp': datetime.now().isoformat(),
                'files_analyzed': len(results),
                'results': results
            }, indent=2)
        elif format == 'markdown' or format == 'report':
            return self._generate_markdown_batch_report(results)
        elif format == 'html':
            return self._generate_html_batch_report(results)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_json_report(self, analysis: ModuleAnalysis) -> str:
        """Generate JSON report for a module."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'file': analysis.file_path,
            'summary': {
                'functions': len(analysis.functions),
                'classes': len(analysis.classes),
                'issues': len(analysis.issues),
            }
        }
        
        if analysis.metrics:
            report_data['metrics'] = {
                'lines_of_code': analysis.metrics.lines_of_code,
                'cyclomatic_complexity': analysis.metrics.cyclomatic_complexity,
                'maintainability_index': analysis.metrics.maintainability_index,
                'technical_debt_ratio': analysis.metrics.technical_debt_ratio,
            }
        
        # Issues by severity
        severity_counts = {}
        for issue in analysis.issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
        report_data['issues_by_severity'] = severity_counts
        
        # Issues by category
        category_counts = {}
        for issue in analysis.issues:
            category_counts[issue.category.value] = category_counts.get(issue.category.value, 0) + 1
        report_data['issues_by_category'] = category_counts
        
        # Detailed issues
        report_data['issues'] = [
            {
                'severity': issue.severity.value,
                'category': issue.category.value,
                'message': issue.message,
                'location': {
                    'line': issue.location.line_start,
                    'column': issue.location.column_start,
                },
                'suggestion': issue.suggestion,
                'rule_id': issue.rule_id,
            }
            for issue in analysis.issues
        ]
        
        # Functions
        report_data['functions'] = [
            {
                'name': func.name,
                'parameters': func.parameters,
                'returns': func.returns,
                'has_docstring': bool(func.docstring),
                'lines_of_code': getattr(func, 'lines_of_code', None),
            }
            for func in analysis.functions
        ]
        
        # Classes
        report_data['classes'] = [
            {
                'name': cls.name,
                'parent_classes': cls.parent_classes,
                'methods': len(cls.methods),
                'has_docstring': bool(cls.docstring),
            }
            for cls in analysis.classes
        ]
        
        return json.dumps(report_data, indent=2)
    
    def _generate_markdown_report(self, analysis: ModuleAnalysis) -> str:
        """Generate Markdown report for a module."""
        report = f"""# Code Analysis Report

## File: {analysis.file_path}
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Functions**: {len(analysis.functions)}
- **Classes**: {len(analysis.classes)}
- **Total Issues**: {len(analysis.issues)}

"""
        
        # Metrics
        if analysis.metrics:
            report += f"""## Metrics

| Metric | Value |
|--------|-------|
| Lines of Code | {analysis.metrics.lines_of_code} |
| Cyclomatic Complexity | {analysis.metrics.cyclomatic_complexity:.1f} |
| Maintainability Index | {analysis.metrics.maintainability_index:.1f} |
| Technical Debt Ratio | {analysis.metrics.technical_debt_ratio:.1%} |

"""
        
        # Issues by severity
        severity_counts = {}
        for issue in analysis.issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
        
        if severity_counts:
            report += "## Issues by Severity\n\n"
            report += "| Severity | Count |\n"
            report += "|----------|-------|\n"
            for severity in ['critical', 'error', 'warning', 'info']:
                if severity in severity_counts:
                    report += f"| {severity.capitalize()} | {severity_counts[severity]} |\n"
            report += "\n"
        
        # Detailed issues
        if analysis.issues:
            report += "## Detailed Issues\n\n"
            
            # Group by severity
            by_severity = {}
            for issue in analysis.issues:
                by_severity.setdefault(issue.severity.value, []).append(issue)
            
            for severity in ['critical', 'error', 'warning', 'info']:
                if severity in by_severity:
                    report += f"### {severity.capitalize()}\n\n"
                    for issue in by_severity[severity]:
                        report += f"- **{issue.message}**\n"
                        report += f"  - Location: Line {issue.location.line_start}\n"
                        if issue.suggestion:
                            report += f"  - Suggestion: {issue.suggestion}\n"
                        report += "\n"
        
        # Functions
        if analysis.functions:
            report += "## Functions\n\n"
            report += "| Name | Parameters | Returns | Documented |\n"
            report += "|------|------------|---------|------------|\n"
            for func in analysis.functions:
                doc_status = "✓" if func.docstring else "✗"
                params = ', '.join(func.parameters) or 'None'
                report += f"| {func.name} | {params} | {func.returns or 'None'} | {doc_status} |\n"
            report += "\n"
        
        # Classes
        if analysis.classes:
            report += "## Classes\n\n"
            report += "| Name | Parents | Methods | Documented |\n"
            report += "|------|---------|---------|------------|\n"
            for cls in analysis.classes:
                doc_status = "✓" if cls.docstring else "✗"
                parents = ', '.join(cls.parent_classes) or 'object'
                report += f"| {cls.name} | {parents} | {len(cls.methods)} | {doc_status} |\n"
            report += "\n"
        
        return report
    
    def _generate_html_report(self, analysis: ModuleAnalysis) -> str:
        """Generate HTML report for a module."""
        template = Template(self.html_template)
        
        # Prepare data for template
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'file_path': analysis.file_path,
            'summary': {
                'functions': len(analysis.functions),
                'classes': len(analysis.classes),
                'issues': len(analysis.issues),
            },
            'metrics': None,
            'issues_by_severity': {},
            'issues_by_category': {},
            'issues': [],
            'functions': [],
            'classes': [],
        }
        
        if analysis.metrics:
            data['metrics'] = {
                'lines_of_code': analysis.metrics.lines_of_code,
                'cyclomatic_complexity': analysis.metrics.cyclomatic_complexity,
                'maintainability_index': analysis.metrics.maintainability_index,
                'technical_debt_ratio': analysis.metrics.technical_debt_ratio,
            }
        
        # Process issues
        for issue in analysis.issues:
            data['issues_by_severity'][issue.severity.value] = \
                data['issues_by_severity'].get(issue.severity.value, 0) + 1
            data['issues_by_category'][issue.category.value] = \
                data['issues_by_category'].get(issue.category.value, 0) + 1
            
            data['issues'].append({
                'severity': issue.severity.value,
                'category': issue.category.value,
                'message': issue.message,
                'location': f"Line {issue.location.line_start}",
                'suggestion': issue.suggestion,
            })
        
        # Process functions
        for func in analysis.functions:
            data['functions'].append({
                'name': func.name,
                'parameters': ', '.join(func.parameters) or 'None',
                'returns': func.returns or 'None',
                'documented': bool(func.docstring),
            })
        
        # Process classes
        for cls in analysis.classes:
            data['classes'].append({
                'name': cls.name,
                'parents': ', '.join(cls.parent_classes) or 'object',
                'methods': len(cls.methods),
                'documented': bool(cls.docstring),
            })
        
        return template.render(**data)
    
    def _generate_json_directory_report(self, analysis: AnalysisResult) -> str:
        """Generate JSON report for directory analysis."""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'files_analyzed': analysis.files_analyzed,
            'total_lines': analysis.total_lines,
            'total_issues': len(analysis.all_issues),
            'summary': {},
        }
        
        # Issues by severity
        severity_counts = {}
        for issue in analysis.all_issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
        report_data['issues_by_severity'] = severity_counts
        
        # Issues by file
        by_file = {}
        for issue in analysis.all_issues:
            file_path = issue.location.file_path
            by_file.setdefault(file_path, []).append({
                'severity': issue.severity.value,
                'message': issue.message,
                'line': issue.location.line_start,
            })
        report_data['issues_by_file'] = by_file
        
        # Metrics summary
        if analysis.overall_metrics:
            report_data['overall_metrics'] = {
                'average_complexity': analysis.overall_metrics.get('average_complexity', 0),
                'average_maintainability': analysis.overall_metrics.get('average_maintainability', 0),
                'total_functions': analysis.overall_metrics.get('total_functions', 0),
                'total_classes': analysis.overall_metrics.get('total_classes', 0),
            }
        
        return json.dumps(report_data, indent=2)
    
    def _generate_markdown_directory_report(self, analysis: AnalysisResult) -> str:
        """Generate Markdown report for directory analysis."""
        report = f"""# Directory Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Files Analyzed**: {analysis.files_analyzed}
- **Total Lines**: {analysis.total_lines}
- **Total Issues**: {len(analysis.all_issues)}

"""
        
        # Issues by severity
        severity_counts = {}
        for issue in analysis.all_issues:
            severity_counts[issue.severity.value] = severity_counts.get(issue.severity.value, 0) + 1
        
        if severity_counts:
            report += "## Issues by Severity\n\n"
            report += "| Severity | Count |\n"
            report += "|----------|-------|\n"
            for severity in ['critical', 'error', 'warning', 'info']:
                if severity in severity_counts:
                    report += f"| {severity.capitalize()} | {severity_counts[severity]} |\n"
            report += "\n"
        
        # Files with most issues
        by_file = {}
        for issue in analysis.all_issues:
            file_path = issue.location.file_path
            by_file[file_path] = by_file.get(file_path, 0) + 1
        
        if by_file:
            sorted_files = sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]
            report += "## Files with Most Issues\n\n"
            report += "| File | Issues |\n"
            report += "|------|--------|\n"
            for file_path, count in sorted_files:
                report += f"| {Path(file_path).name} | {count} |\n"
            report += "\n"
        
        # Overall metrics
        if analysis.overall_metrics:
            report += "## Overall Metrics\n\n"
            report += "| Metric | Value |\n"
            report += "|--------|-------|\n"
            metrics = analysis.overall_metrics
            if 'average_complexity' in metrics:
                report += f"| Average Complexity | {metrics['average_complexity']:.1f} |\n"
            if 'average_maintainability' in metrics:
                report += f"| Average Maintainability | {metrics['average_maintainability']:.1f} |\n"
            if 'total_functions' in metrics:
                report += f"| Total Functions | {metrics['total_functions']} |\n"
            if 'total_classes' in metrics:
                report += f"| Total Classes | {metrics['total_classes']} |\n"
            report += "\n"
        
        return report
    
    def _generate_html_directory_report(self, analysis: AnalysisResult) -> str:
        """Generate HTML report for directory analysis."""
        template = Template(self._load_directory_html_template())
        
        # Prepare data
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'files_analyzed': analysis.files_analyzed,
            'total_lines': analysis.total_lines,
            'total_issues': len(analysis.all_issues),
            'issues_by_severity': {},
            'files_with_issues': [],
            'overall_metrics': {},
        }
        
        # Issues by severity
        for issue in analysis.all_issues:
            severity = issue.severity.value
            data['issues_by_severity'][severity] = data['issues_by_severity'].get(severity, 0) + 1
        
        # Files with issues
        by_file = {}
        for issue in analysis.all_issues:
            file_path = issue.location.file_path
            by_file[file_path] = by_file.get(file_path, 0) + 1
        
        sorted_files = sorted(by_file.items(), key=lambda x: x[1], reverse=True)[:10]
        data['files_with_issues'] = [
            {'name': Path(fp).name, 'count': count}
            for fp, count in sorted_files
        ]
        
        # Metrics
        if analysis.overall_metrics:
            data['overall_metrics'] = analysis.overall_metrics
        
        return template.render(**data)
    
    def _generate_markdown_batch_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate Markdown report for batch analysis."""
        report = f"""# Batch Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Files Analyzed**: {len(results)}

## Summary

"""
        
        total_issues = 0
        total_functions = 0
        total_classes = 0
        
        # Process each result
        file_summaries = []
        for result in results:
            path = result['path']
            analysis = result['result']
            
            issues_count = len(analysis.issues)
            functions_count = len(analysis.functions)
            classes_count = len(analysis.classes)
            
            total_issues += issues_count
            total_functions += functions_count
            total_classes += classes_count
            
            file_summaries.append({
                'path': path,
                'issues': issues_count,
                'functions': functions_count,
                'classes': classes_count,
            })
        
        report += f"- **Total Issues**: {total_issues}\n"
        report += f"- **Total Functions**: {total_functions}\n"
        report += f"- **Total Classes**: {total_classes}\n\n"
        
        # File summaries
        report += "## File Summaries\n\n"
        report += "| File | Issues | Functions | Classes |\n"
        report += "|------|--------|-----------|----------|\n"
        
        for summary in file_summaries:
            file_name = Path(summary['path']).name
            report += f"| {file_name} | {summary['issues']} | {summary['functions']} | {summary['classes']} |\n"
        
        return report
    
    def _generate_html_batch_report(self, results: List[Dict[str, Any]]) -> str:
        """Generate HTML report for batch analysis."""
        template = Template(self._load_batch_html_template())
        
        # Prepare data
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'files_analyzed': len(results),
            'total_issues': 0,
            'total_functions': 0,
            'total_classes': 0,
            'file_summaries': [],
        }
        
        # Process results
        for result in results:
            analysis = result['result']
            data['total_issues'] += len(analysis.issues)
            data['total_functions'] += len(analysis.functions)
            data['total_classes'] += len(analysis.classes)
            
            data['file_summaries'].append({
                'name': Path(result['path']).name,
                'path': result['path'],
                'issues': len(analysis.issues),
                'functions': len(analysis.functions),
                'classes': len(analysis.classes),
            })
        
        return template.render(**data)
    
    def _load_markdown_template(self) -> str:
        """Load the markdown template."""
        # Simple template - could be loaded from file
        return ""
    
    def _load_html_template(self) -> str:
        """Load the HTML template for file reports."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Code Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .critical { color: #d32f2f; }
        .error { color: #f57c00; }
        .warning { color: #fbc02d; }
        .info { color: #1976d2; }
        .metric { background-color: #e3f2fd; }
        h1, h2, h3 { color: #333; }
    </style>
</head>
<body>
    <h1>Code Analysis Report</h1>
    
    <div class="metadata">
        <p><strong>File:</strong> {{ file_path }}</p>
        <p><strong>Generated:</strong> {{ timestamp }}</p>
    </div>
    
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Functions</td>
            <td>{{ summary.functions }}</td>
        </tr>
        <tr>
            <td>Classes</td>
            <td>{{ summary.classes }}</td>
        </tr>
        <tr>
            <td>Total Issues</td>
            <td>{{ summary.issues }}</td>
        </tr>
    </table>
    
    {% if metrics %}
    <h2>Code Metrics</h2>
    <table class="metric">
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Lines of Code</td>
            <td>{{ metrics.lines_of_code }}</td>
        </tr>
        <tr>
            <td>Cyclomatic Complexity</td>
            <td>{{ "%.1f"|format(metrics.cyclomatic_complexity) }}</td>
        </tr>
        <tr>
            <td>Maintainability Index</td>
            <td>{{ "%.1f"|format(metrics.maintainability_index) }}</td>
        </tr>
        <tr>
            <td>Technical Debt Ratio</td>
            <td>{{ "%.1f%%" | format(metrics.technical_debt_ratio * 100) }}</td>
        </tr>
    </table>
    {% endif %}
    
    {% if issues %}
    <h2>Issues</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Category</th>
            <th>Message</th>
            <th>Location</th>
            <th>Suggestion</th>
        </tr>
        {% for issue in issues %}
        <tr>
            <td class="{{ issue.severity }}">{{ issue.severity|upper }}</td>
            <td>{{ issue.category }}</td>
            <td>{{ issue.message }}</td>
            <td>{{ issue.location }}</td>
            <td>{{ issue.suggestion or 'N/A' }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    {% if functions %}
    <h2>Functions</h2>
    <table>
        <tr>
            <th>Name</th>
            <th>Parameters</th>
            <th>Returns</th>
            <th>Documented</th>
        </tr>
        {% for func in functions %}
        <tr>
            <td>{{ func.name }}</td>
            <td>{{ func.parameters }}</td>
            <td>{{ func.returns }}</td>
            <td>{{ "✓" if func.documented else "✗" }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    {% if classes %}
    <h2>Classes</h2>
    <table>
        <tr>
            <th>Name</th>
            <th>Parents</th>
            <th>Methods</th>
            <th>Documented</th>
        </tr>
        {% for cls in classes %}
        <tr>
            <td>{{ cls.name }}</td>
            <td>{{ cls.parents }}</td>
            <td>{{ cls.methods }}</td>
            <td>{{ "✓" if cls.documented else "✗" }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
</body>
</html>"""
    
    def _load_directory_html_template(self) -> str:
        """Load the HTML template for directory reports."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Directory Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .critical { color: #d32f2f; }
        .error { color: #f57c00; }
        .warning { color: #fbc02d; }
        .info { color: #1976d2; }
        h1, h2, h3 { color: #333; }
    </style>
</head>
<body>
    <h1>Directory Analysis Report</h1>
    
    <div class="metadata">
        <p><strong>Generated:</strong> {{ timestamp }}</p>
    </div>
    
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Files Analyzed</td>
            <td>{{ files_analyzed }}</td>
        </tr>
        <tr>
            <td>Total Lines</td>
            <td>{{ total_lines }}</td>
        </tr>
        <tr>
            <td>Total Issues</td>
            <td>{{ total_issues }}</td>
        </tr>
    </table>
    
    <h2>Issues by Severity</h2>
    <table>
        <tr>
            <th>Severity</th>
            <th>Count</th>
        </tr>
        {% for severity, count in issues_by_severity.items() %}
        <tr>
            <td class="{{ severity }}">{{ severity|upper }}</td>
            <td>{{ count }}</td>
        </tr>
        {% endfor %}
    </table>
    
    {% if files_with_issues %}
    <h2>Files with Most Issues</h2>
    <table>
        <tr>
            <th>File</th>
            <th>Issues</th>
        </tr>
        {% for file in files_with_issues %}
        <tr>
            <td>{{ file.name }}</td>
            <td>{{ file.count }}</td>
        </tr>
        {% endfor %}
    </table>
    {% endif %}
    
    {% if overall_metrics %}
    <h2>Overall Metrics</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        {% if overall_metrics.average_complexity %}
        <tr>
            <td>Average Complexity</td>
            <td>{{ "%.1f"|format(overall_metrics.average_complexity) }}</td>
        </tr>
        {% endif %}
        {% if overall_metrics.average_maintainability %}
        <tr>
            <td>Average Maintainability</td>
            <td>{{ "%.1f"|format(overall_metrics.average_maintainability) }}</td>
        </tr>
        {% endif %}
        {% if overall_metrics.total_functions %}
        <tr>
            <td>Total Functions</td>
            <td>{{ overall_metrics.total_functions }}</td>
        </tr>
        {% endif %}
        {% if overall_metrics.total_classes %}
        <tr>
            <td>Total Classes</td>
            <td>{{ overall_metrics.total_classes }}</td>
        </tr>
        {% endif %}
    </table>
    {% endif %}
</body>
</html>"""
    
    def _load_batch_html_template(self) -> str:
        """Load the HTML template for batch reports."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Batch Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        h1, h2, h3 { color: #333; }
    </style>
</head>
<body>
    <h1>Batch Analysis Report</h1>
    
    <div class="metadata">
        <p><strong>Generated:</strong> {{ timestamp }}</p>
        <p><strong>Files Analyzed:</strong> {{ files_analyzed }}</p>
    </div>
    
    <h2>Summary</h2>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Total Issues</td>
            <td>{{ total_issues }}</td>
        </tr>
        <tr>
            <td>Total Functions</td>
            <td>{{ total_functions }}</td>
        </tr>
        <tr>
            <td>Total Classes</td>
            <td>{{ total_classes }}</td>
        </tr>
    </table>
    
    <h2>File Summaries</h2>
    <table>
        <tr>
            <th>File</th>
            <th>Path</th>
            <th>Issues</th>
            <th>Functions</th>
            <th>Classes</th>
        </tr>
        {% for file in file_summaries %}
        <tr>
            <td>{{ file.name }}</td>
            <td>{{ file.path }}</td>
            <td>{{ file.issues }}</td>
            <td>{{ file.functions }}</td>
            <td>{{ file.classes }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>"""