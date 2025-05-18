"""Tests for refactoring recommendations."""

import pytest
from pathlib import Path
from typing import List
from unittest.mock import Mock, patch, MagicMock

from velocitytree.refactoring import (
    RefactoringRecommendationEngine,
    RefactoringDetector,
    RefactoringPlanner,
    ImpactAnalyzer,
    RefactoringType,
    RefactoringCandidate,
    RefactoringPlan,
    ImpactAnalysis,
    RefactoringImpact
)
from velocitytree.code_analysis.models import (
    ModuleAnalysis,
    FunctionAnalysis,
    ClassAnalysis,
    CodeLocation,
    CodeMetrics,
    LanguageSupport
)
# Imported separately to avoid issues
from velocitytree.realtime_suggestions import (
    CodeSuggestion,
    SuggestionType,
    Severity
)


@pytest.fixture
def sample_module():
    """Create a sample module for testing."""
    return ModuleAnalysis(
        file_path="test.py",
        language=LanguageSupport.PYTHON,
        imports=["os", "sys"],
        functions=[
            FunctionAnalysis(
                name="complex_function",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=10,
                    line_end=100
                ),
                complexity=25,  # Very high complexity
                parameters=["arg1", "arg2", "arg3"],
                returns="dict",
                docstring=None,
                issues=[]
            ),
            FunctionAnalysis(
                name="simple_function",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=110,
                    line_end=120
                ),
                complexity=3,
                parameters=["x"],
                returns="int",
                docstring="Simple function",
                issues=[]
            ),
            FunctionAnalysis(
                name="duplicate_function_1",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=130,
                    line_end=150
                ),
                complexity=8,
                parameters=["data"],
                returns="str",
                docstring=None,
                issues=[]
            ),
            FunctionAnalysis(
                name="duplicate_function_2",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=160,
                    line_end=180
                ),
                complexity=8,  # Same complexity as duplicate_function_1
                parameters=["data"],
                returns="str",
                docstring=None,
                issues=[]
            ),
            FunctionAnalysis(
                name="_unused_old_function",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=200,
                    line_end=210
                ),
                complexity=5,
                parameters=[],
                returns=None,
                docstring=None,
                issues=[]
            )
        ],
        classes=[
            ClassAnalysis(
                name="GodClass",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=300,
                    line_end=600
                ),
                methods=[
                    FunctionAnalysis(
                        name=f"method_{i}",
                        location=CodeLocation(
                            file_path="test.py",
                            line_start=310 + i*10,
                            line_end=315 + i*10
                        ),
                        complexity=3,
                        parameters=[],
                        returns=None,
                        docstring=None,
                        issues=[]
                    ) for i in range(25)  # 25 methods
                ],
                attributes=[f"attr_{i}" for i in range(20)],  # 20 attributes
                parent_classes=[],
                docstring=None
            ),
            ClassAnalysis(
                name="SimpleClass",
                location=CodeLocation(
                    file_path="test.py",
                    line_start=700,
                    line_end=750
                ),
                methods=[
                    FunctionAnalysis(
                        name="simple_method",
                        location=CodeLocation(
                            file_path="test.py",
                            line_start=710,
                            line_end=720
                        ),
                        complexity=2,
                        parameters=[],
                        returns=None,
                        docstring="Simple method",
                        issues=[]
                    )
                ],
                attributes=["simple_attr"],
                parent_classes=[],
                docstring="Simple class"
            )
        ],
        global_variables=[],
        docstring=None,
        metrics=CodeMetrics(
            lines_of_code=800,
            lines_of_comments=50,
            cyclomatic_complexity=15.0,
            cognitive_complexity=20.0,
            maintainability_index=55.0,
            test_coverage=None,
            duplicate_lines=40,
            technical_debt_ratio=0.15,
            code_to_comment_ratio=0.0625,
            average_function_length=40.0,
            max_function_length=90,
            number_of_functions=5,
            number_of_classes=2
        ),
        issues=[],
        patterns=[]
    )


class TestRefactoringDetector:
    
    @pytest.fixture
    def detector(self):
        return RefactoringDetector()
    
    def test_detect_extract_method(self, detector, sample_module):
        """Test detection of methods that should be extracted."""
        candidates = detector._detect_extract_method(sample_module)
        
        # Should detect complex_function for extraction
        assert len(candidates) >= 1
        
        complex_func_candidate = next(
            c for c in candidates 
            if c.metadata.get("function_name") == "complex_function"
        )
        assert complex_func_candidate.type == RefactoringType.EXTRACT_METHOD
        assert complex_func_candidate.confidence > 0.8
        assert "too complex" in complex_func_candidate.rationale
        assert complex_func_candidate.impact == RefactoringImpact.LOW
    
    def test_detect_extract_class(self, detector, sample_module):
        """Test detection of god classes."""
        candidates = detector._detect_extract_class(sample_module)
        
        # Should detect GodClass for decomposition
        assert len(candidates) >= 1
        
        god_class_candidate = next(
            c for c in candidates 
            if c.metadata.get("class_name") == "GodClass"
        )
        assert god_class_candidate.type == RefactoringType.EXTRACT_CLASS
        assert god_class_candidate.confidence > 0.7
        assert "too many responsibilities" in god_class_candidate.rationale
        assert god_class_candidate.impact == RefactoringImpact.MEDIUM
        assert len(god_class_candidate.metadata.get("suggested_classes", [])) > 0
    
    def test_detect_duplicate_code(self, detector, sample_module):
        """Test detection of duplicate code."""
        candidates = detector._detect_duplicate_code(sample_module)
        
        # Should detect duplicate functions
        assert len(candidates) >= 1
        
        duplicate_candidate = None
        for c in candidates:
            if c.type == RefactoringType.CONSOLIDATE_DUPLICATE:
                func1 = c.metadata.get("function1")
                func2 = c.metadata.get("function2")
                if "duplicate_function" in func1 and "duplicate_function" in func2:
                    duplicate_candidate = c
                    break
        
        assert duplicate_candidate is not None
        assert duplicate_candidate.confidence > 0.5
        assert "similar" in duplicate_candidate.rationale
    
    def test_detect_dead_code(self, detector, sample_module):
        """Test detection of dead code."""
        candidates = detector._detect_dead_code(sample_module)
        
        # Should detect _unused_old_function
        assert len(candidates) >= 1
        
        dead_code_candidate = next(
            c for c in candidates 
            if c.metadata.get("function_name") == "_unused_old_function"
        )
        assert dead_code_candidate.type == RefactoringType.REMOVE_DEAD_CODE
        assert dead_code_candidate.confidence > 0.6
        assert "unused" in dead_code_candidate.rationale
    
    def test_detect_all_opportunities(self, detector, sample_module):
        """Test detection of all refactoring opportunities."""
        candidates = detector.detect_refactoring_opportunities(sample_module)
        
        # Should find multiple types of refactoring opportunities
        types = {c.type for c in candidates}
        assert RefactoringType.EXTRACT_METHOD in types
        assert RefactoringType.EXTRACT_CLASS in types
        assert RefactoringType.REMOVE_DEAD_CODE in types
        
        # Should have reasonable confidence levels
        assert all(0.0 <= c.confidence <= 1.0 for c in candidates)
        
        # Should have impact assessments
        assert all(c.impact in RefactoringImpact for c in candidates)


class TestRefactoringPlanner:
    
    @pytest.fixture
    def planner(self):
        return RefactoringPlanner()
    
    def test_plan_extract_method(self, planner, sample_module):
        """Test planning for method extraction."""
        candidate = RefactoringCandidate(
            type=RefactoringType.EXTRACT_METHOD,
            location=CodeLocation("test.py", 10, 100),
            confidence=0.9,
            rationale="Function is too complex",
            complexity_reduction=0.5,
            readability_improvement=0.7,
            maintainability_improvement=0.8,
            impact=RefactoringImpact.LOW,
            metadata={"function_name": "complex_function"}
        )
        
        plan = planner.create_refactoring_plan(candidate, sample_module)
        
        assert plan.candidate == candidate
        assert len(plan.steps) > 0
        assert "Identify the code block" in plan.steps[0]
        assert len(plan.preview) > 0
        assert Path("test.py") in plan.preview
        assert "extracted_method" in str(plan.preview[Path("test.py")])
        assert plan.estimated_effort == "minutes"
        assert len(plan.risks) > 0
        assert len(plan.benefits) > 0
    
    def test_plan_extract_class(self, planner, sample_module):
        """Test planning for class extraction."""
        candidate = RefactoringCandidate(
            type=RefactoringType.EXTRACT_CLASS,
            location=CodeLocation("test.py", 300, 600),
            confidence=0.8,
            rationale="Class has too many responsibilities",
            complexity_reduction=0.6,
            readability_improvement=0.8,
            maintainability_improvement=0.9,
            impact=RefactoringImpact.MEDIUM,
            metadata={
                "class_name": "GodClass",
                "method_count": 25,
                "suggested_classes": ["GodClassCore", "GodClassUtils"]
            }
        )
        
        plan = planner.create_refactoring_plan(candidate, sample_module)
        
        assert plan.candidate == candidate
        assert "Analyze responsibilities" in plan.steps[0]
        assert "Create new classes" in plan.steps[2]
        assert plan.estimated_effort == "hours"
        assert "API changes" in plan.risks[0]
        assert "Better organization" in plan.benefits[0]
        assert RefactoringType.EXTRACT_INTERFACE in plan.alternatives
    
    def test_plan_remove_dead_code(self, planner, sample_module):
        """Test planning for dead code removal."""
        candidate = RefactoringCandidate(
            type=RefactoringType.REMOVE_DEAD_CODE,
            location=CodeLocation("test.py", 200, 210),
            confidence=0.7,
            rationale="Function appears to be unused",
            complexity_reduction=0.3,
            readability_improvement=0.5,
            maintainability_improvement=0.7,
            impact=RefactoringImpact.LOW,
            metadata={"function_name": "_unused_old_function"}
        )
        
        plan = planner.create_refactoring_plan(candidate, sample_module)
        
        assert plan.candidate == candidate
        assert "Verify" in plan.steps[0]
        assert "Remove function" in plan.steps[3]
        assert plan.estimated_effort == "minutes"
        assert len(plan.risks) > 0
        assert "Cleaner codebase" in plan.benefits[0]


class TestImpactAnalyzer:
    
    @pytest.fixture
    def impact_analyzer(self):
        return ImpactAnalyzer()
    
    def test_analyze_extract_method_impact(self, impact_analyzer):
        """Test impact analysis for method extraction."""
        candidate = RefactoringCandidate(
            type=RefactoringType.EXTRACT_METHOD,
            location=CodeLocation("test.py", 10, 100),
            confidence=0.9,
            rationale="Function is too complex",
            complexity_reduction=0.5,
            readability_improvement=0.7,
            maintainability_improvement=0.8,
            impact=RefactoringImpact.LOW,
            metadata={"function_name": "complex_function"}
        )
        
        plan = RefactoringPlan(
            candidate=candidate,
            steps=["Extract code"],
            preview={},
            rollback_plan=["Inline back"],
            estimated_effort="minutes",
            risks=[],
            benefits=[],
            alternatives=[]
        )
        
        impact = impact_analyzer.analyze_impact(plan, Path("test.py").parent)
        
        assert "will be split" in impact.direct_impacts[0]
        assert "New method will be created" in impact.direct_impacts[1]
        assert len(impact.test_impacts) > 0
        assert impact.performance_impact == "neutral"
        assert impact.risk_score < 0.5  # Low risk
        assert len(impact.breaking_changes) == 0
    
    def test_analyze_extract_class_impact(self, impact_analyzer):
        """Test impact analysis for class extraction."""
        candidate = RefactoringCandidate(
            type=RefactoringType.EXTRACT_CLASS,
            location=CodeLocation("test.py", 300, 600),
            confidence=0.8,
            rationale="Class has too many responsibilities",
            complexity_reduction=0.6,
            readability_improvement=0.8,
            maintainability_improvement=0.9,
            impact=RefactoringImpact.MEDIUM,
            metadata={"class_name": "GodClass"}
        )
        
        plan = RefactoringPlan(
            candidate=candidate,
            steps=["Extract class"],
            preview={},
            rollback_plan=["Merge back"],
            estimated_effort="hours",
            risks=[],
            benefits=[],
            alternatives=[]
        )
        
        impact = impact_analyzer.analyze_impact(plan, Path("test.py").parent)
        
        assert "will be split" in impact.direct_impacts[0]
        assert "New import statements" in impact.direct_impacts[1]
        assert "Subclasses may be affected" in impact.indirect_impacts[0]
        assert len(impact.test_impacts) > 0
        assert impact.risk_score > 0.5  # Higher risk
        assert len(impact.breaking_changes) > 0
    
    def test_analyze_remove_dead_code_impact(self, impact_analyzer):
        """Test impact analysis for dead code removal."""
        candidate = RefactoringCandidate(
            type=RefactoringType.REMOVE_DEAD_CODE,
            location=CodeLocation("test.py", 200, 210),
            confidence=0.7,
            rationale="Function appears to be unused",
            complexity_reduction=0.3,
            readability_improvement=0.5,
            maintainability_improvement=0.7,
            impact=RefactoringImpact.LOW,
            metadata={"function_name": "_unused_old_function"}
        )
        
        plan = RefactoringPlan(
            candidate=candidate,
            steps=["Remove function"],
            preview={},
            rollback_plan=["Restore function"],
            estimated_effort="minutes",
            risks=[],
            benefits=[],
            alternatives=[]
        )
        
        with patch.object(impact_analyzer, '_find_references', return_value=[]):
            impact = impact_analyzer.analyze_impact(plan, Path("test.py").parent)
        
        assert "will be removed" in impact.direct_impacts[0]
        assert "Dynamic calls may break" in impact.indirect_impacts[0]
        assert impact.performance_impact == "positive"
        assert impact.risk_score < 0.3  # Low risk when no references
        assert len(impact.breaking_changes) == 0


class TestRefactoringRecommendationEngine:
    
    @pytest.fixture
    def engine(self):
        analyzer = Mock()
        detector = Mock()
        planner = Mock()
        impact_analyzer = Mock()
        
        return RefactoringRecommendationEngine(
            analyzer=analyzer,
            detector=detector,
            planner=planner,
            impact_analyzer=impact_analyzer
        )
    
    def test_analyze_and_recommend(self, engine, sample_module):
        """Test full recommendation flow."""
        # Mock the analyzer
        engine.analyzer.analyze_file.return_value = sample_module
        
        # Mock detector to return candidates
        candidates = [
            RefactoringCandidate(
                type=RefactoringType.EXTRACT_METHOD,
                location=CodeLocation("test.py", 10, 100),
                confidence=0.9,
                rationale="Function is too complex",
                complexity_reduction=0.5,
                readability_improvement=0.7,
                maintainability_improvement=0.8,
                impact=RefactoringImpact.LOW,
                metadata={"function_name": "complex_function"}
            ),
            RefactoringCandidate(
                type=RefactoringType.EXTRACT_CLASS,
                location=CodeLocation("test.py", 300, 600),
                confidence=0.8,
                rationale="Class has too many responsibilities",
                complexity_reduction=0.6,
                readability_improvement=0.8,
                maintainability_improvement=0.9,
                impact=RefactoringImpact.MEDIUM,
                metadata={"class_name": "GodClass"}
            )
        ]
        engine.detector.detect_refactoring_opportunities.return_value = candidates
        
        # Mock planner and impact analyzer
        plan = Mock(estimated_effort="minutes", benefits=["Better code"], risks=[])
        impact = Mock(risk_score=0.3)
        
        engine.planner.create_refactoring_plan.return_value = plan
        engine.impact_analyzer.analyze_impact.return_value = impact
        
        # Get recommendations
        recommendations = engine.analyze_and_recommend(Path("test.py"))
        
        assert len(recommendations) == 2
        
        # Should be sorted by benefit/risk ratio
        first_rec = recommendations[0]
        assert first_rec[0].maintainability_improvement / (first_rec[2].risk_score + 0.1) >= \
               recommendations[1][0].maintainability_improvement / (recommendations[1][2].risk_score + 0.1)
    
    def test_generate_suggestions(self, engine):
        """Test converting recommendations to suggestions."""
        candidate = RefactoringCandidate(
            type=RefactoringType.EXTRACT_METHOD,
            location=CodeLocation("test.py", 10, 100),
            confidence=0.9,
            rationale="Function is too complex",
            complexity_reduction=0.5,
            readability_improvement=0.7,
            maintainability_improvement=0.8,
            impact=RefactoringImpact.LOW,
            metadata={"function_name": "complex_function"}
        )
        
        plan = RefactoringPlan(
            candidate=candidate,
            steps=["Extract code"],
            preview={Path("test.py"): "def extracted_method():\n    pass"},
            rollback_plan=["Inline back"],
            estimated_effort="minutes",
            risks=["Performance"],
            benefits=["Readability"],
            alternatives=[]
        )
        
        impact = ImpactAnalysis(
            direct_impacts=["Code change"],
            indirect_impacts=[],
            test_impacts=[],
            documentation_impacts=[],
            performance_impact="neutral",
            risk_score=0.2,
            affected_components=["test.py"],
            breaking_changes=[]
        )
        
        recommendations = [(candidate, plan, impact)]
        suggestions = engine.generate_suggestions(recommendations)
        
        assert len(suggestions) == 1
        
        suggestion = suggestions[0]
        assert suggestion.type == SuggestionType.REFACTORING
        assert suggestion.severity == Severity.ERROR  # Low risk = high priority
        assert suggestion.message == "Function is too complex"
        assert len(suggestion.quick_fixes) > 0
        assert suggestion.metadata["refactoring_type"] == "extract_method"
        assert suggestion.metadata["confidence"] == 0.9
        assert suggestion.metadata["effort"] == "minutes"
        assert suggestion.priority == 80  # Based on maintainability improvement


class TestRefactoringIntegration:
    """Integration tests with real code analysis."""
    
    @pytest.fixture
    def test_file(self, tmp_path):
        """Create a test Python file with refactoring opportunities."""
        file_path = tmp_path / "refactor_test.py"
        file_path.write_text("""
class DataProcessor:
    def __init__(self):
        self.data = []
        self.cache = {}
        self.config = {}
        self.logger = None
        self.db_connection = None
        self.api_client = None
        self.temp_storage = []
        self.validators = []
        self.formatters = []
        self.transformers = []
    
    def process_data(self, raw_data):
        # Very long method with multiple responsibilities
        if not raw_data:
            return None
            
        # Validation
        if not isinstance(raw_data, dict):
            raise ValueError("Data must be dict")
        if 'id' not in raw_data:
            raise ValueError("ID required")
        if 'timestamp' not in raw_data:
            raise ValueError("Timestamp required")
            
        # Transformation
        processed = {}
        processed['id'] = str(raw_data['id'])
        processed['timestamp'] = int(raw_data['timestamp'])
        
        # Complex calculation
        if raw_data.get('value', 0) > 100:
            if raw_data.get('category') == 'premium':
                if raw_data.get('region') == 'US':
                    multiplier = 1.5
                else:
                    multiplier = 1.2
            else:
                multiplier = 1.0
        else:
            multiplier = 0.8
            
        processed['calculated_value'] = raw_data.get('value', 0) * multiplier
        
        # More processing...
        # ... 50+ more lines ...
        
        return processed
    
    def validate_input(self, data): pass
    def transform_data(self, data): pass
    def calculate_metrics(self, data): pass
    def format_output(self, data): pass
    def log_processing(self, data): pass
    def cache_result(self, data): pass
    def save_to_db(self, data): pass
    def notify_api(self, data): pass
    def cleanup_temp(self): pass
    def generate_report(self, data): pass
    def send_email(self, data): pass
    def update_dashboard(self, data): pass
    def archive_data(self, data): pass
    def compress_data(self, data): pass
    def encrypt_data(self, data): pass
    def validate_output(self, data): pass
    def handle_errors(self, error): pass
    def retry_operation(self, operation): pass
    def backup_data(self, data): pass
    def restore_data(self, backup_id): pass
    def migrate_data(self, source, target): pass
    def synchronize_data(self, remote): pass
    def audit_trail(self, action): pass
    def performance_metrics(self): pass
    
    def _old_process_method(self, data):
        # Deprecated method
        pass
""")
        return file_path
    
    def test_full_refactoring_analysis(self, test_file):
        """Test full refactoring analysis on a real file."""
        engine = RefactoringRecommendationEngine()
        
        recommendations = engine.analyze_and_recommend(test_file)
        
        # Should find multiple refactoring opportunities
        assert len(recommendations) > 0
        
        # Check for specific refactorings
        types = {rec[0].type for rec in recommendations}
        assert RefactoringType.EXTRACT_CLASS in types  # DataProcessor god class
        
        # Other refactorings may or may not be detected depending on analysis
        # We know at minimum the god class should be detected
        if RefactoringType.REMOVE_DEAD_CODE in types:
            # Check that _old_process_method was detected
            dead_code_recs = [r for r in recommendations if r[0].type == RefactoringType.REMOVE_DEAD_CODE]
            assert any("_old_process_method" in r[0].metadata.get("function_name", "") for r in dead_code_recs)
        
        # Convert to suggestions
        suggestions = engine.generate_suggestions(recommendations)
        assert len(suggestions) > 0
        
        # Check priorities are set
        assert all(s.priority > 0 for s in suggestions)
        
        # Check suggestions are properly ordered
        priorities = [s.priority for s in suggestions]
        assert priorities == sorted(priorities, reverse=True)