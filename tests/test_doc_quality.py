"""Test documentation quality checking and suggestions."""

import pytest
from pathlib import Path
from dataclasses import dataclass, field

from velocitytree.documentation.quality import (
    DocQualityChecker,
    DocSuggestionEngine,
    QualityMetric,
    SuggestionRule,
)
from velocitytree.documentation.models import DocStyle, DocSeverity
from velocitytree.code_analysis.models import (
    ModuleAnalysis,
    ClassAnalysis,
    FunctionAnalysis,
    CodeLocation,
    CodeMetrics,
    Pattern,
    CodeIssue,
    Severity,
    LanguageSupport,
)


class TestDocQualityChecker:
    """Test cases for DocQualityChecker."""
    
    @pytest.fixture
    def checker(self):
        """Create a DocQualityChecker instance."""
        return DocQualityChecker(style=DocStyle.GOOGLE)
        
    @pytest.fixture
    def sample_module(self):
        """Create a sample module analysis."""
        # Create functions
        func1 = FunctionAnalysis(
            name="add",
            location=CodeLocation(
                file_path="test.py",
                line_start=5,
                line_end=7,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["a", "b"],
            returns="int",
            docstring="Add two numbers.",
        )
        
        func2 = FunctionAnalysis(
            name="multiply",
            location=CodeLocation(
                file_path="test.py",
                line_start=10,
                line_end=12,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["x", "y"],
            returns="int",
            docstring=None,  # Missing docstring
        )
        
        # Create class with methods
        method1 = FunctionAnalysis(
            name="calculate",
            location=CodeLocation(
                file_path="test.py",
                line_start=20,
                line_end=25,
                column_start=0,
                column_end=0,
            ),
            complexity=2,
            parameters=["self", "value"],
            returns="float",
            docstring="Calculate result.",
        )
        
        method2 = FunctionAnalysis(
            name="process",
            location=CodeLocation(
                file_path="test.py",
                line_start=27,
                line_end=30,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["self", "data"],
            returns="None",
            docstring=None,  # Missing docstring
        )
        
        calc_class = ClassAnalysis(
            name="Calculator",
            location=CodeLocation(
                file_path="test.py",
                line_start=15,
                line_end=30,
                column_start=0,
                column_end=0,
            ),
            methods=[method1, method2],
            attributes=[],
            parent_classes=[],
            docstring="Calculator class.",
        )
        
        # Create module
        module = ModuleAnalysis(
            file_path="test.py",
            language=LanguageSupport.PYTHON,
            imports=["math"],
            functions=[func1, func2],
            classes=[calc_class],
            global_variables=[],
            docstring="Test module for calculations.",
            metrics=CodeMetrics(
                lines_of_code=50,
                lines_of_comments=10,
                cyclomatic_complexity=5,
                cognitive_complexity=3.0,
                maintainability_index=75.0,
                test_coverage=80.0,
                duplicate_lines=0,
                technical_debt_ratio=0.05,
                code_to_comment_ratio=5.0,
                average_function_length=15.0,
                max_function_length=25,
                number_of_functions=2,
                number_of_classes=1,
            ),
        )
        
        return module
        
    def test_init(self, checker):
        """Test initialization."""
        assert checker.style == DocStyle.GOOGLE
        assert len(checker.rules) > 0
        assert 'completeness' in checker.rules
        assert 'consistency' in checker.rules
        assert 'clarity' in checker.rules
        
    def test_check_quality(self, checker, sample_module):
        """Test quality checking."""
        report = checker.check_quality(sample_module)
        
        assert report.overall_score > 0
        assert len(report.metric_scores) > 0
        assert QualityMetric.COMPLETENESS in report.metric_scores
        assert len(report.issues) > 0  # Should find missing docstrings
        assert len(report.suggestions) > 0
        assert report.statistics['total_elements'] > 0
        
    def test_missing_docstrings(self, checker, sample_module):
        """Test detection of missing docstrings."""
        report = checker.check_quality(sample_module)
        
        # Should find missing docstrings for multiply function and process method
        missing_issues = [i for i in report.issues if 'missing' in i.message.lower()]
        assert len(missing_issues) >= 2
        
        # Check specific missing docstrings - location format might be different
        function_issues = [i for i in missing_issues if 'multiply' in i.location.lower()]
        assert len(function_issues) >= 1
        
        method_issues = [i for i in missing_issues if 'process' in i.location.lower()]
        assert len(method_issues) >= 1
        
    def test_completeness_score(self, checker, sample_module):
        """Test completeness score calculation."""
        report = checker.check_quality(sample_module)
        
        # Module has 5 elements total (1 module + 2 functions + 1 class + 1 public method)
        # 3 are documented (module + add function + Calculator class + calculate method)
        # 2 are undocumented (multiply function + process method)
        expected_completeness = (4 / 6) * 100  # ~66.7%
        
        assert report.metric_scores[QualityMetric.COMPLETENESS] < 100
        assert report.metric_scores[QualityMetric.COMPLETENESS] > 50
        
    def test_style_compliance(self, checker):
        """Test style compliance checking."""
        # Create function with non-compliant docstring
        func = FunctionAnalysis(
            name="test_func",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=5,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["param1", "param2"],
            returns="str",
            docstring="This function does stuff with params and returns something.",
        )
        
        module = ModuleAnalysis(
            file_path="test.py",
            language=LanguageSupport.PYTHON,
            imports=[],
            functions=[func],
            classes=[],
            global_variables=[],
            docstring="Test module.",
            metrics=CodeMetrics(
                lines_of_code=10,
                lines_of_comments=2,
                cyclomatic_complexity=1,
                cognitive_complexity=1.0,
                maintainability_index=90.0,
                test_coverage=100.0,
                duplicate_lines=0,
                technical_debt_ratio=0.0,
                code_to_comment_ratio=5.0,
                average_function_length=5.0,
                max_function_length=5,
                number_of_functions=1,
                number_of_classes=0,
            ),
        )
        
        report = checker.check_quality(module)
        
        # Should find style issues
        style_issues = [i for i in report.issues if hasattr(i, '_category') and i._category == 'structure']
        assert len(style_issues) > 0
        
    def test_suggestions_generation(self, checker, sample_module):
        """Test suggestion generation."""
        report = checker.check_quality(sample_module)
        
        assert len(report.suggestions) > 0
        
        # Should have priority suggestions
        assert any('Priority' in s for s in report.suggestions)
        
        # Should have style guide reference
        assert any('Google style guide' in s for s in report.suggestions)


class TestDocSuggestionEngine:
    """Test cases for DocSuggestionEngine."""
    
    @pytest.fixture
    def engine(self):
        """Create a DocSuggestionEngine instance."""
        return DocSuggestionEngine()
        
    def test_init(self, engine):
        """Test initialization."""
        assert len(engine.templates) > 0
        assert 'function' in engine.templates
        assert 'class' in engine.templates
        assert 'module' in engine.templates
        
    def test_suggest_function_docstring(self, engine):
        """Test function docstring suggestion."""
        func = FunctionAnalysis(
            name="calculate_total",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=5,
                column_start=0,
                column_end=0,
            ),
            complexity=2,
            parameters=["items", "tax_rate"],
            returns="float",
            docstring=None,
        )
        
        suggestion = engine.suggest_docstring(func, 'function')
        
        assert 'Args:' in suggestion
        assert 'items' in suggestion
        assert 'tax_rate' in suggestion
        assert 'Returns:' in suggestion
        
    def test_suggest_class_docstring(self, engine):
        """Test class docstring suggestion."""
        cls = ClassAnalysis(
            name="DataProcessor",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=50,
                column_start=0,
                column_end=0,
            ),
            methods=[],
            attributes=[],
            parent_classes=["BaseProcessor"],
            docstring=None,
        )
        
        suggestion = engine.suggest_docstring(cls, 'class')
        
        assert 'Attributes:' in suggestion
        assert 'DataProcessor' in suggestion or 'class' in suggestion.lower()
        
    def test_suggest_complex_docstring(self, engine):
        """Test complex element docstring suggestion."""
        # Complex function with many parameters
        func = FunctionAnalysis(
            name="process_data",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=100,
                column_start=0,
                column_end=0,
            ),
            complexity=15,
            parameters=["data", "config", "options", "callback", "timeout"],
            returns="Dict[str, Any]",
            docstring=None,
        )
        
        suggestion = engine.suggest_docstring(func, 'function')
        
        # Should use complex template
        assert 'Examples:' in suggestion
        assert 'Raises:' in suggestion
        assert all(param in suggestion for param in func.parameters)
        
    def test_improve_docstring(self, engine):
        """Test docstring improvement."""
        func = FunctionAnalysis(
            name="add",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=3,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["a", "b"],
            returns="int",
            docstring="Add numbers.",
        )
        
        # Create issues
        from velocitytree.documentation.models import DocIssue
        issues = [
            DocIssue(
                severity=DocSeverity.INFO,
                location="Function: add",
                message="Missing Args section for parameters",
                suggestion="Add an Args section to document parameters a and b",
                line_number=1,
            )
        ]
        
        improved = engine.improve_docstring(func.docstring, func, issues)
        
        # Should add missing sections
        assert 'Args:' in improved
        assert 'a:' in improved
        assert 'b:' in improved
        
    def test_template_filling(self, engine):
        """Test template variable filling."""
        func = FunctionAnalysis(
            name="test",
            location=CodeLocation(
                file_path="test.py",
                line_start=1,
                line_end=3,
                column_start=0,
                column_end=0,
            ),
            complexity=1,
            parameters=["x", "y"],
            returns="None",
            docstring=None,
        )
        
        # Add parameter types
        func.parameter_types = {"x": "int", "y": "str"}
        
        suggestion = engine.suggest_docstring(func, 'function')
        
        # Should include parameter types
        assert 'x (int)' in suggestion
        assert 'y (str)' in suggestion


class TestIntegration:
    """Integration tests for quality checking and suggestions."""
    
    def test_quality_and_suggestions_flow(self):
        """Test complete quality checking and suggestion flow."""
        # Create a module with various issues
        module = ModuleAnalysis(
            file_path="example.py",
            language=LanguageSupport.PYTHON,
            imports=["os", "sys"],
            functions=[
                FunctionAnalysis(
                    name="process",
                    location=CodeLocation(
                        file_path="example.py",
                        line_start=10,
                        line_end=20,
                        column_start=0,
                        column_end=0,
                    ),
                    complexity=3,
                    parameters=["data", "options"],
                    returns="bool",
                    docstring="Process data.",  # Incomplete docstring
                ),
                FunctionAnalysis(
                    name="validate",
                    location=CodeLocation(
                        file_path="example.py",
                        line_start=22,
                        line_end=30,
                        column_start=0,
                        column_end=0,
                    ),
                    complexity=2,
                    parameters=["value"],
                    returns="bool",
                    docstring=None,  # Missing docstring
                ),
            ],
            classes=[],
            global_variables=["CONFIG"],
            docstring=None,  # Missing module docstring
            metrics=CodeMetrics(
                lines_of_code=50,
                lines_of_comments=5,
                cyclomatic_complexity=5,
                cognitive_complexity=3.0,
                maintainability_index=70.0,
                test_coverage=60.0,
                duplicate_lines=2,
                technical_debt_ratio=0.08,
                code_to_comment_ratio=10.0,
                average_function_length=20.0,
                max_function_length=30,
                number_of_functions=2,
                number_of_classes=0,
            ),
        )
        
        # Check quality
        checker = DocQualityChecker()
        report = checker.check_quality(module)
        
        # Generate suggestions
        engine = DocSuggestionEngine()
        
        # Should have found issues
        assert len(report.issues) > 0
        assert report.overall_score < 100
        
        # Should be able to generate suggestions for missing docstrings
        module_suggestion = engine.suggest_docstring(module, 'module')
        assert 'example.py' in module_suggestion or 'module' in module_suggestion.lower()
        
        func_suggestion = engine.suggest_docstring(module.functions[1], 'function')
        assert 'validate' in func_suggestion or 'value' in func_suggestion
        
        # Should be able to improve existing docstring
        improved = engine.improve_docstring(
            module.functions[0].docstring,
            module.functions[0],
            [i for i in report.issues if 'process' in i.location]
        )
        assert len(improved) > len(module.functions[0].docstring)