#!/usr/bin/env python3
"""
Demo script for the learning from user feedback feature.
This demonstrates how the suggestion system learns and adapts based on user feedback.
"""

from pathlib import Path
import tempfile
import shutil
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from velocitytree.realtime_suggestions import RealTimeSuggestionEngine, SuggestionType
from velocitytree.code_analysis.analyzer import CodeAnalyzer
from velocitytree.documentation.quality import DocQualityChecker
from velocitytree.learning.feedback_collector import FeedbackCollector, LearningEngine

console = Console()


def create_demo_file():
    """Create a demo Python file with various issues."""
    content = '''
def calc(x, y):
    """Calculate something"""
    result = x + y
    return result
    
def PROCESS_DATA(data):
    # Process the data
    for item in data:
        if item > 100:
            print("Large value")
        else:
            if item < 0:
                print("Negative")
            else:
                print("Normal")
                
class dataProcessor:
    def __init__(self):
        self.items = []
        
    def add_item(self, item):
        self.items.append(item)
        
    def unused_method(self):
        pass
        
def complex_function(a, b, c, d, e):
    """This function is too complex"""
    if a > b:
        if c > d:
            if e > 0:
                return a + c + e
            else:
                return a + c - e
        else:
            return a - c
    else:
        if b > c:
            return b
        else:
            if d > e:
                return d
            else:
                return e
'''
    return content


def demo_learning_system():
    """Demonstrate the learning system."""
    console.print("[bold blue]VelocityTree Learning System Demo[/bold blue]\n")
    
    # Create temporary directory and files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        demo_file = temp_dir / "demo.py"
        demo_file.write_text(create_demo_file())
        
        # Initialize components
        feedback_db = temp_dir / "feedback.db"
        feedback_collector = FeedbackCollector(feedback_db)
        learning_engine = LearningEngine(feedback_collector.db)
        
        suggestion_engine = RealTimeSuggestionEngine(
            analyzer=CodeAnalyzer(),
            quality_checker=DocQualityChecker(),
            feedback_collector=feedback_collector,
            learning_engine=learning_engine
        )
        
        console.print("[cyan]Analyzing demo.py for code suggestions...[/cyan]\n")
        
        # Get initial suggestions
        suggestions = suggestion_engine._analyze_sync(
            demo_file,
            demo_file.read_text()
        )
        
        # Display initial suggestions
        console.print(f"[green]Found {len(suggestions)} suggestions:[/green]\n")
        
        suggestion_table = Table(title="Initial Suggestions")
        suggestion_table.add_column("ID", style="cyan")
        suggestion_table.add_column("Type", style="yellow")
        suggestion_table.add_column("Message", style="white")
        suggestion_table.add_column("Priority", style="magenta")
        
        for i, suggestion in enumerate(suggestions[:10]):
            suggestion_table.add_row(
                str(i),
                suggestion.type.value,
                suggestion.message[:50] + "...",
                str(suggestion.priority)
            )
        
        console.print(suggestion_table)
        console.print()
        
        # Collect feedback
        console.print("[bold]Let's provide feedback on some suggestions:[/bold]\n")
        
        feedback_types = {
            "naming": None,
            "documentation": None,
            "complexity": None
        }
        
        for i, suggestion in enumerate(suggestions[:5]):
            console.print(f"\n[yellow]Suggestion {i}:[/yellow]")
            console.print(f"Type: {suggestion.type.value}")
            console.print(f"Message: {suggestion.message}")
            console.print(f"Current Priority: {suggestion.priority}")
            
            if Confirm.ask("Is this suggestion helpful?"):
                rating = Prompt.ask(
                    "Rate this suggestion (1-5)",
                    choices=["1", "2", "3", "4", "5"]
                )
                
                feedback_collector.record_feedback(
                    suggestion_id=f"demo_{i}",
                    feedback_type="accept",
                    value=float(rating) / 5.0,
                    suggestion_type=suggestion.type.value
                )
                
                # Track feedback for summary
                suggestion_key = None
                if "naming" in suggestion.message.lower():
                    suggestion_key = "naming"
                elif "doc" in suggestion.message.lower():
                    suggestion_key = "documentation"
                elif "complex" in suggestion.message.lower():
                    suggestion_key = "complexity"
                
                if suggestion_key:
                    feedback_types[suggestion_key] = True
            else:
                feedback_collector.record_feedback(
                    suggestion_id=f"demo_{i}",
                    feedback_type="reject",
                    value=0.0,
                    suggestion_type=suggestion.type.value
                )
                
                # Track negative feedback
                suggestion_key = None
                if "naming" in suggestion.message.lower():
                    suggestion_key = "naming"
                elif "doc" in suggestion.message.lower():
                    suggestion_key = "documentation"
                elif "complex" in suggestion.message.lower():
                    suggestion_key = "complexity"
                
                if suggestion_key:
                    feedback_types[suggestion_key] = False
        
        # Learn from feedback
        console.print("\n[cyan]Learning from your feedback...[/cyan]\n")
        
        feedbacks = feedback_collector.db.get_feedback()
        patterns = learning_engine.learn_from_feedback(feedbacks)
        learning_engine.update_patterns(patterns)
        
        # Display learning results
        learning_table = Table(title="Learned Patterns")
        learning_table.add_column("Suggestion Type", style="cyan")
        learning_table.add_column("Confidence Adjustment", style="yellow")
        
        for pattern_type, confidence in patterns.items():
            learning_table.add_row(pattern_type, f"{confidence:.2f}")
        
        console.print(learning_table)
        console.print()
        
        # Clear cache and re-analyze with learning
        suggestion_engine.clear_cache()
        
        console.print("[cyan]Re-analyzing with learned preferences...[/cyan]\n")
        
        adapted_suggestions = suggestion_engine._analyze_sync(
            demo_file,
            demo_file.read_text()
        )
        
        # Compare priorities
        comparison_table = Table(title="Priority Comparison")
        comparison_table.add_column("Type", style="cyan")
        comparison_table.add_column("Original Priority", style="yellow")
        comparison_table.add_column("Adapted Priority", style="green")
        comparison_table.add_column("Change", style="magenta")
        
        # Group by type for comparison
        original_by_type = {}
        adapted_by_type = {}
        
        for s in suggestions:
            if s.type.value not in original_by_type:
                original_by_type[s.type.value] = []
            original_by_type[s.type.value].append(s.priority)
        
        for s in adapted_suggestions:
            if s.type.value not in adapted_by_type:
                adapted_by_type[s.type.value] = []
            adapted_by_type[s.type.value].append(s.priority)
        
        for stype in original_by_type:
            if stype in adapted_by_type:
                orig_avg = sum(original_by_type[stype]) / len(original_by_type[stype])
                adapt_avg = sum(adapted_by_type[stype]) / len(adapted_by_type[stype])
                change = adapt_avg - orig_avg
                
                comparison_table.add_row(
                    stype,
                    f"{orig_avg:.1f}",
                    f"{adapt_avg:.1f}",
                    f"{change:+.1f}"
                )
        
        console.print(comparison_table)
        console.print()
        
        # Show feedback summary
        summary = feedback_collector.get_feedback_summary()
        
        console.print("[bold]Feedback Summary:[/bold]")
        console.print(f"Total feedbacks: {summary['total_feedbacks']}")
        console.print(f"Acceptance rate: {summary['acceptance_rate']:.1%}")
        console.print(f"Average rating: {summary['average_rating']:.2f}")
        console.print()
        
        # Demonstrate user preferences
        console.print("[bold]Setting User Preferences:[/bold]\n")
        
        if Confirm.ask("Would you like to filter out low-priority suggestions?"):
            min_priority = Prompt.ask(
                "Minimum priority threshold (0-100)",
                default="50"
            )
            feedback_collector.set_user_preference("min_priority", int(min_priority))
            console.print(f"[green]Set minimum priority to {min_priority}[/green]")
        
        if Confirm.ask("Would you like to filter out specific suggestion types?"):
            filtered_types = []
            for stype in ["style", "documentation", "refactoring"]:
                if Confirm.ask(f"Filter out {stype} suggestions?"):
                    filtered_types.append(stype)
            
            if filtered_types:
                feedback_collector.set_user_preference("filtered_types", filtered_types)
                console.print(f"[green]Filtered out: {', '.join(filtered_types)}[/green]")
        
        # Show filtered suggestions
        console.print("\n[cyan]Applying user preferences...[/cyan]\n")
        
        final_suggestions = suggestion_engine._apply_adaptive_learning(adapted_suggestions)
        
        final_table = Table(title="Final Suggestions (with preferences)")
        final_table.add_column("Type", style="cyan")
        final_table.add_column("Message", style="white")
        final_table.add_column("Priority", style="magenta")
        
        for suggestion in final_suggestions[:10]:
            final_table.add_row(
                suggestion.type.value,
                suggestion.message[:50] + "...",
                str(suggestion.priority)
            )
        
        console.print(final_table)
        console.print()
        
        console.print("[bold green]Demo completed![/bold green]")
        console.print("\nThe learning system has:")
        console.print("1. Collected your feedback on suggestions")
        console.print("2. Learned patterns from your preferences")
        console.print("3. Adjusted suggestion priorities based on feedback")
        console.print("4. Applied user preferences to filter suggestions")
        console.print("\nThis creates a personalized code analysis experience!")


if __name__ == "__main__":
    demo_learning_system()