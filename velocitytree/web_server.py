"""Web server for interactive feature graph visualization."""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os
import json
from typing import Dict, Any, Optional

from velocitytree.feature_graph import FeatureGraph
from velocitytree.visualization import FeatureGraphVisualizer
from velocitytree.core import VelocityTree
from velocitytree.progress_tracking import ProgressCalculator


class FeatureGraphWebServer:
    """Web server for serving interactive feature graph visualizations."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        """Initialize the web server.
        
        Args:
            host: Host address to bind to
            port: Port to listen on
        """
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                        static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        CORS(self.app)
        self.host = host
        self.port = port
        self.feature_graph = None
        self.velocity_tree = None
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up Flask routes."""
        
        @self.app.route('/')
        def index():
            """Serve the main visualization page."""
            return render_template('index.html')
        
        @self.app.route('/api/graph')
        def get_graph():
            """Get the current feature graph data."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            # Convert graph to Cytoscape.js format
            nodes = []
            edges = []
            
            for node_id in self.feature_graph.graph.nodes():
                node_data = self.feature_graph.graph.nodes[node_id]
                nodes.append({
                    "data": {
                        "id": node_id,
                        "label": node_data.get("name", node_id),
                        "status": node_data.get("status", "pending"),
                        "feature_type": node_data.get("feature_type", "feature")
                    }
                })
            
            for source, target, data in self.feature_graph.graph.edges(data=True):
                edges.append({
                    "data": {
                        "source": source,
                        "target": target,
                        "relationship": data.get("relationship", "depends_on"),
                        "strength": data.get("strength", "normal")
                    }
                })
            
            return jsonify({
                "nodes": nodes,
                "edges": edges
            })
        
        @self.app.route('/api/graph/load', methods=['POST'])
        def load_graph():
            """Load a feature graph from a project directory."""
            data = request.get_json()
            project_dir = data.get("project_dir")
            
            if not project_dir:
                return jsonify({"error": "project_dir is required"}), 400
            
            try:
                # Initialize VelocityTree for the project
                self.velocity_tree = VelocityTree(project_dir)
                self.feature_graph = self.velocity_tree.feature_graph
                
                return jsonify({"success": True, "message": "Graph loaded successfully"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/feature/<feature_id>')
        def get_feature_details(feature_id):
            """Get detailed information about a specific feature."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            if feature_id not in self.feature_graph.graph.nodes():
                return jsonify({"error": "Feature not found"}), 404
            
            feature_data = self.feature_graph.graph.nodes[feature_id]
            
            # Get relationships
            dependencies = list(self.feature_graph.get_dependencies(feature_id))
            dependents = list(self.feature_graph.get_dependents(feature_id))
            all_deps = self.feature_graph.get_all_dependencies(feature_id)
            all_deps_recursive = list(all_deps)
            
            # Check if feature can start
            can_start = self.feature_graph.can_start_feature(feature_id)
            
            # Get suggested next features
            suggested_next = list(self.feature_graph.get_suggested_next_features())
            
            return jsonify({
                "id": feature_id,
                "data": feature_data,
                "dependencies": dependencies,
                "dependents": dependents,
                "all_dependencies": all_deps_recursive,
                "can_start": can_start,
                "suggested_next": suggested_next
            })
        
        @self.app.route('/api/feature/<feature_id>/complete', methods=['POST'])
        def complete_feature(feature_id):
            """Mark a feature as completed."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            if feature_id not in self.feature_graph.graph.nodes():
                return jsonify({"error": "Feature not found"}), 404
            
            self.feature_graph.complete_feature(feature_id)
            
            # Save the updated graph
            if self.velocity_tree:
                self.velocity_tree.save_state()
            
            return jsonify({"success": True, "message": f"Feature {feature_id} marked as completed"})
        
        @self.app.route('/api/layout/<layout_type>')
        def get_layout(layout_type):
            """Get node positions for a specific layout."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            visualizer = FeatureGraphVisualizer(self.feature_graph)
            
            try:
                if layout_type == "hierarchical":
                    positions = visualizer._hierarchical_layout()
                elif layout_type == "spring":
                    positions = visualizer._spring_layout()
                elif layout_type == "circular":
                    positions = visualizer._circular_layout()
                else:
                    return jsonify({"error": "Unknown layout type"}), 400
                
                # Convert positions for JSON
                positions_dict = {
                    node_id: {"x": pos[0], "y": pos[1]}
                    for node_id, pos in positions.items()
                }
                
                return jsonify(positions_dict)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/progress/feature/<feature_id>')
        def get_feature_progress(feature_id):
            """Get progress information for a specific feature."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            try:
                calculator = ProgressCalculator(self.feature_graph)
                progress = calculator.calculate_feature_progress(feature_id)
                
                # Convert to dictionary for JSON
                return jsonify({
                    "feature_id": progress.feature_id,
                    "name": progress.name,
                    "status": progress.status,
                    "completion_percentage": progress.completion_percentage,
                    "dependencies_completed": progress.dependencies_completed,
                    "total_dependencies": progress.total_dependencies,
                    "estimated_completion_date": progress.estimated_completion_date.isoformat() if progress.estimated_completion_date else None,
                    "velocity": progress.velocity,
                    "blockers": progress.blockers,
                    "critical_path": progress.critical_path
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/progress/project')
        def get_project_progress():
            """Get overall project progress."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            try:
                calculator = ProgressCalculator(self.feature_graph)
                progress = calculator.calculate_project_progress()
                
                # Convert burndown data for JSON
                burndown_data = [
                    {"date": date.isoformat(), "completion": percentage}
                    for date, percentage in progress.burndown_data
                ]
                
                return jsonify({
                    "total_completion": progress.total_completion,
                    "features_completed": progress.features_completed,
                    "total_features": progress.total_features,
                    "milestones_completed": progress.milestones_completed,
                    "total_milestones": progress.total_milestones,
                    "estimated_completion_date": progress.estimated_completion_date.isoformat() if progress.estimated_completion_date else None,
                    "current_velocity": progress.current_velocity,
                    "average_velocity": progress.average_velocity,
                    "burndown_data": burndown_data
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/progress/velocity')
        def get_velocity_report():
            """Get velocity metrics and trends."""
            if not self.feature_graph:
                return jsonify({"error": "No feature graph loaded"}), 404
            
            try:
                calculator = ProgressCalculator(self.feature_graph)
                report = calculator.get_velocity_report()
                return jsonify(report)
            except Exception as e:
                return jsonify({"error": str(e)}), 500
    
    def run(self):
        """Run the web server."""
        print(f"Starting VelocityTree web server at http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=True)


def main():
    """Main entry point for the web server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="VelocityTree Feature Graph Web Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    parser.add_argument("--project", help="Project directory to load automatically")
    
    args = parser.parse_args()
    
    server = FeatureGraphWebServer(host=args.host, port=args.port)
    
    if args.project:
        # Load project automatically
        server.velocity_tree = VelocityTree(args.project)
        server.feature_graph = server.velocity_tree.feature_graph
    
    server.run()


if __name__ == "__main__":
    main()