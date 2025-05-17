"""Visualization generation for feature graphs."""
import json
import math
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import networkx as nx
from datetime import datetime

from .feature_graph import FeatureGraph, RelationType, RelationshipStrength, FeatureNode
from .utils import logger


class FeatureGraphVisualizer:
    """Generate visualizations for feature graphs."""
    
    # Color schemes for different statuses
    STATUS_COLORS = {
        "completed": "#4CAF50",  # Green
        "in_progress": "#2196F3",  # Blue
        "planned": "#9E9E9E",  # Gray
        "blocked": "#F44336",  # Red
        "cancelled": "#757575",  # Dark gray
    }
    
    # Color schemes for node types
    TYPE_COLORS = {
        "milestone": "#9C27B0",  # Purple
        "feature": "#2196F3",  # Blue
        "epic": "#FF9800",  # Orange
        "task": "#00BCD4",  # Cyan
    }
    
    # Relationship line styles
    RELATIONSHIP_STYLES = {
        RelationType.DEPENDS_ON: {"stroke": "#333", "stroke-dasharray": ""},
        RelationType.BLOCKS: {"stroke": "#F44336", "stroke-dasharray": "5,5"},
        RelationType.RELATED_TO: {"stroke": "#2196F3", "stroke-dasharray": "2,2"},
        RelationType.PARENT_CHILD: {"stroke": "#4CAF50", "stroke-dasharray": ""},
        RelationType.INCLUDES: {"stroke": "#9C27B0", "stroke-dasharray": "3,3"},
        RelationType.IMPLEMENTS: {"stroke": "#FF9800", "stroke-dasharray": ""},
        RelationType.PRECEDES: {"stroke": "#795548", "stroke-dasharray": ""},
        RelationType.FOLLOWS: {"stroke": "#607D8B", "stroke-dasharray": ""},
        RelationType.DUPLICATES: {"stroke": "#E91E63", "stroke-dasharray": "5,2"},
    }
    
    # Relationship strength to line width
    STRENGTH_WIDTHS = {
        RelationshipStrength.CRITICAL: 3,
        RelationshipStrength.STRONG: 2.5,
        RelationshipStrength.NORMAL: 2,
        RelationshipStrength.WEAK: 1.5,
    }
    
    def __init__(self, graph: FeatureGraph, layout: str = "hierarchical"):
        """Initialize the visualizer."""
        self.graph = graph
        self.layout = layout
        self.node_positions: Dict[str, Tuple[float, float]] = {}
        self.width = 1200
        self.height = 800
        self.margin = 50
        logger.info(f"Initialized visualizer for graph: {graph.project_id}")
    
    def generate_svg(self, output_path: Optional[Path] = None, 
                    include_labels: bool = True,
                    show_status: bool = True) -> str:
        """Generate SVG visualization of the graph."""
        # Calculate layout
        self._calculate_layout()
        
        # Start SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}">',
            '<defs>',
            self._generate_arrow_markers(),
            self._generate_filters(),
            '</defs>',
            '<g class="graph-container">',
        ]
        
        # Draw relationships (edges)
        svg_parts.append('<g class="relationships">')
        for (source, target), relationship in self.graph.relationships.items():
            svg_parts.append(self._draw_relationship(source, target, relationship))
        svg_parts.append('</g>')
        
        # Draw nodes
        svg_parts.append('<g class="nodes">')
        for node_id, node in self.graph.features.items():
            svg_parts.append(self._draw_node(node_id, node, include_labels, show_status))
        svg_parts.append('</g>')
        
        svg_parts.append('</g>')
        svg_parts.append('</svg>')
        
        svg_content = '\n'.join(svg_parts)
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(svg_content)
            logger.info(f"Saved SVG to {output_path}")
        
        return svg_content
    
    def generate_html(self, output_path: Optional[Path] = None,
                     title: str = "Feature Graph Visualization",
                     interactive: bool = True) -> str:
        """Generate HTML page with embedded SVG and optional interactivity."""
        svg_content = self.generate_svg()
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="en">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>{title}</title>',
            '<style>',
            self._generate_css(),
            '</style>',
            '</head>',
            '<body>',
            f'<h1>{title}</h1>',
            '<div class="controls">',
            self._generate_controls(),
            '</div>',
            '<div class="visualization-container">',
            svg_content,
            '</div>',
            '<div class="info-panel">',
            self._generate_info_panel(),
            '</div>',
        ]
        
        if interactive:
            html_parts.extend([
                '<script>',
                self._generate_javascript(),
                '</script>',
            ])
        
        html_parts.extend([
            '</body>',
            '</html>',
        ])
        
        html_content = '\n'.join(html_parts)
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                f.write(html_content)
            logger.info(f"Saved HTML to {output_path}")
        
        return html_content
    
    def _calculate_layout(self):
        """Calculate node positions based on layout algorithm."""
        nx_graph = self.graph.get_feature_tree()
        
        if self.layout == "hierarchical":
            # Use topological sort for hierarchical layout
            try:
                if nx.is_directed_acyclic_graph(nx_graph):
                    # Create layers based on topological generations
                    layers = list(nx.topological_generations(nx_graph))
                    self._arrange_hierarchical(layers)
                else:
                    # Fall back to spring layout for cyclic graphs
                    self._use_spring_layout(nx_graph)
            except nx.NetworkXError:
                self._use_spring_layout(nx_graph)
        
        elif self.layout == "spring":
            self._use_spring_layout(nx_graph)
        
        elif self.layout == "circular":
            self._use_circular_layout(nx_graph)
        
        else:
            # Default to spring layout
            self._use_spring_layout(nx_graph)
    
    def _arrange_hierarchical(self, layers: List[List[str]]):
        """Arrange nodes in hierarchical layers."""
        y_spacing = (self.height - 2 * self.margin) / max(len(layers) - 1, 1)
        
        for layer_idx, layer in enumerate(layers):
            y = self.margin + layer_idx * y_spacing
            x_spacing = (self.width - 2 * self.margin) / max(len(layer) - 1, 1)
            
            for node_idx, node_id in enumerate(layer):
                x = self.margin + node_idx * x_spacing
                self.node_positions[node_id] = (x, y)
    
    def _use_spring_layout(self, nx_graph: nx.DiGraph):
        """Use spring/force-directed layout."""
        pos = nx.spring_layout(nx_graph, k=2, iterations=50)
        
        # Scale to SVG dimensions
        for node_id, (x, y) in pos.items():
            scaled_x = self.margin + (x + 1) * (self.width - 2 * self.margin) / 2
            scaled_y = self.margin + (y + 1) * (self.height - 2 * self.margin) / 2
            self.node_positions[node_id] = (scaled_x, scaled_y)
    
    def _use_circular_layout(self, nx_graph: nx.DiGraph):
        """Use circular layout."""
        pos = nx.circular_layout(nx_graph)
        
        # Scale to SVG dimensions
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) / 2 - self.margin
        
        for node_id, (x, y) in pos.items():
            scaled_x = center_x + x * radius
            scaled_y = center_y + y * radius
            self.node_positions[node_id] = (scaled_x, scaled_y)
    
    def _draw_node(self, node_id: str, node: FeatureNode, 
                  include_labels: bool, show_status: bool) -> str:
        """Draw a single node."""
        x, y = self.node_positions.get(node_id, (0, 0))
        
        # Determine colors
        fill_color = self.STATUS_COLORS.get(node.status, "#999")
        stroke_color = self.TYPE_COLORS.get(node.type, "#333")
        
        # Node shape based on type
        if node.type == "milestone":
            shape = f'<rect x="{x-40}" y="{y-20}" width="80" height="40" rx="5" ry="5"'
        else:
            shape = f'<circle cx="{x}" cy="{y}" r="30"'
        
        svg_parts = [
            f'<g class="node" data-id="{node_id}" data-status="{node.status}" data-type="{node.type}">',
            f'{shape} fill="{fill_color}" stroke="{stroke_color}" stroke-width="2" filter="url(#dropshadow)"/>',
        ]
        
        if include_labels:
            # Truncate long names
            display_name = node.name[:15] + "..." if len(node.name) > 15 else node.name
            svg_parts.append(
                f'<text x="{x}" y="{y}" text-anchor="middle" dominant-baseline="middle" '
                f'font-size="12" font-weight="bold" fill="white">{display_name}</text>'
            )
        
        if show_status:
            # Status icon
            status_icon = self._get_status_icon(node.status)
            svg_parts.append(
                f'<text x="{x}" y="{y+20}" text-anchor="middle" font-size="16">{status_icon}</text>'
            )
        
        svg_parts.append('</g>')
        return '\n'.join(svg_parts)
    
    def _draw_relationship(self, source: str, target: str, relationship) -> str:
        """Draw a relationship between nodes."""
        if source not in self.node_positions or target not in self.node_positions:
            return ""
        
        x1, y1 = self.node_positions[source]
        x2, y2 = self.node_positions[target]
        
        # Get style based on relationship type
        style = self.RELATIONSHIP_STYLES.get(
            relationship.relation_type,
            {"stroke": "#999", "stroke-dasharray": ""}
        )
        
        # Get width based on strength
        width = self.STRENGTH_WIDTHS.get(relationship.strength, 2)
        
        # Calculate arrow position
        dx = x2 - x1
        dy = y2 - y1
        angle = math.atan2(dy, dx)
        
        # Shorten line to not overlap with node
        node_radius = 30
        x2_adjusted = x2 - node_radius * math.cos(angle)
        y2_adjusted = y2 - node_radius * math.sin(angle)
        
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2_adjusted}" y2="{y2_adjusted}" '
            f'stroke="{style["stroke"]}" stroke-width="{width}" '
            f'stroke-dasharray="{style["stroke-dasharray"]}" '
            f'marker-end="url(#arrowhead)" '
            f'data-source="{source}" data-target="{target}" '
            f'data-type="{relationship.relation_type.value}"/>'
        )
    
    def _generate_arrow_markers(self) -> str:
        """Generate SVG arrow markers."""
        return '''
        <marker id="arrowhead" markerWidth="10" markerHeight="7" 
                refX="9" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#333"/>
        </marker>
        '''
    
    def _generate_filters(self) -> str:
        """Generate SVG filters."""
        return '''
        <filter id="dropshadow" height="130%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
            <feOffset dx="2" dy="2" result="offsetblur"/>
            <feComponentTransfer>
                <feFuncA type="linear" slope="0.3"/>
            </feComponentTransfer>
            <feMerge>
                <feMergeNode/>
                <feMergeNode in="SourceGraphic"/>
            </feMerge>
        </filter>
        '''
    
    def _get_status_icon(self, status: str) -> str:
        """Get icon for status."""
        icons = {
            "completed": "✓",
            "in_progress": "⚡",
            "blocked": "🚫",
            "planned": "○",
            "cancelled": "✗"
        }
        return icons.get(status, "?")
    
    def _generate_css(self) -> str:
        """Generate CSS for HTML visualization."""
        return '''
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        
        h1 {
            color: #333;
            text-align: center;
        }
        
        .visualization-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 20px auto;
            max-width: 1200px;
            overflow: auto;
        }
        
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        
        .controls button {
            margin: 0 5px;
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            background-color: #2196F3;
            color: white;
            cursor: pointer;
            font-size: 14px;
        }
        
        .controls button:hover {
            background-color: #1976D2;
        }
        
        .info-panel {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin: 20px auto;
            max-width: 1200px;
            display: none;
        }
        
        .info-panel.active {
            display: block;
        }
        
        .legend {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin: 20px 0;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            border: 2px solid #333;
        }
        
        .node {
            cursor: pointer;
            transition: opacity 0.3s;
        }
        
        .node:hover {
            opacity: 0.8;
        }
        
        .node.highlighted {
            filter: brightness(1.2);
        }
        
        .node.dimmed {
            opacity: 0.3;
        }
        
        line {
            transition: opacity 0.3s;
        }
        
        line.highlighted {
            stroke-width: 4 !important;
        }
        
        line.dimmed {
            opacity: 0.3;
        }
        '''
    
    def _generate_controls(self) -> str:
        """Generate control buttons."""
        return '''
        <button onclick="toggleInfoPanel()">Show/Hide Info</button>
        <button onclick="resetHighlight()">Reset View</button>
        <button onclick="filterByStatus('completed')">Show Completed</button>
        <button onclick="filterByStatus('in_progress')">Show In Progress</button>
        <button onclick="filterByStatus('blocked')">Show Blocked</button>
        <button onclick="showAll()">Show All</button>
        '''
    
    def _generate_info_panel(self) -> str:
        """Generate information panel."""
        progress = self.graph.calculate_progress()
        
        return f'''
        <h2>Project Overview</h2>
        <div class="stats">
            <p><strong>Total Features:</strong> {progress.total_features}</p>
            <p><strong>Completed:</strong> {progress.completed_features} ({progress.completion_percentage:.1f}%)</p>
            <p><strong>In Progress:</strong> {progress.in_progress_features}</p>
            <p><strong>Blocked:</strong> {progress.blocked_features}</p>
            <p><strong>Planned:</strong> {progress.planned_features}</p>
        </div>
        
        <h3>Legend</h3>
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background-color: #4CAF50;"></div>
                <span>Completed</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #2196F3;"></div>
                <span>In Progress</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #F44336;"></div>
                <span>Blocked</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background-color: #9E9E9E;"></div>
                <span>Planned</span>
            </div>
        </div>
        
        <div id="feature-details" style="display: none;">
            <h3>Feature Details</h3>
            <div id="feature-info"></div>
        </div>
        '''
    
    def _generate_javascript(self) -> str:
        """Generate JavaScript for interactivity."""
        graph_data = {
            'nodes': {
                node_id: {
                    'name': node.name,
                    'description': node.description,
                    'status': node.status,
                    'type': node.type,
                    'dependencies': self.graph.get_dependencies(node_id),
                    'dependents': self.graph.get_dependents(node_id)
                }
                for node_id, node in self.graph.features.items()
            },
            'relationships': [
                {
                    'source': source,
                    'target': target,
                    'type': rel.relation_type.value,
                    'strength': rel.strength.value,
                    'description': rel.description
                }
                for (source, target), rel in self.graph.relationships.items()
            ]
        }
        
        return f'''
        const graphData = {json.dumps(graph_data)};
        
        function toggleInfoPanel() {{
            const panel = document.querySelector('.info-panel');
            panel.classList.toggle('active');
        }}
        
        function highlightNode(nodeId) {{
            // Reset all
            document.querySelectorAll('.node').forEach(n => {{
                n.classList.remove('highlighted', 'dimmed');
            }});
            document.querySelectorAll('line').forEach(l => {{
                l.classList.remove('highlighted', 'dimmed');
            }});
            
            // Highlight selected node
            const selectedNode = document.querySelector(`.node[data-id="${{nodeId}}"]`);
            if (selectedNode) {{
                selectedNode.classList.add('highlighted');
                
                // Highlight connected edges
                document.querySelectorAll(`line[data-source="${{nodeId}}"], line[data-target="${{nodeId}}"]`).forEach(line => {{
                    line.classList.add('highlighted');
                }});
                
                // Dim unrelated nodes
                document.querySelectorAll('.node').forEach(node => {{
                    const id = node.getAttribute('data-id');
                    if (id !== nodeId && !isConnected(id, nodeId)) {{
                        node.classList.add('dimmed');
                    }}
                }});
                
                // Show feature details
                showFeatureDetails(nodeId);
            }}
        }}
        
        function isConnected(nodeId1, nodeId2) {{
            return graphData.relationships.some(rel => 
                (rel.source === nodeId1 && rel.target === nodeId2) ||
                (rel.source === nodeId2 && rel.target === nodeId1)
            );
        }}
        
        function showFeatureDetails(nodeId) {{
            const node = graphData.nodes[nodeId];
            if (!node) return;
            
            const detailsDiv = document.getElementById('feature-details');
            const infoDiv = document.getElementById('feature-info');
            
            infoDiv.innerHTML = `
                <p><strong>Name:</strong> ${{node.name}}</p>
                <p><strong>Description:</strong> ${{node.description}}</p>
                <p><strong>Status:</strong> ${{node.status}}</p>
                <p><strong>Type:</strong> ${{node.type}}</p>
                <p><strong>Dependencies:</strong> ${{node.dependencies.join(', ') || 'None'}}</p>
                <p><strong>Dependents:</strong> ${{node.dependents.join(', ') || 'None'}}</p>
            `;
            
            detailsDiv.style.display = 'block';
        }}
        
        function resetHighlight() {{
            document.querySelectorAll('.node').forEach(n => {{
                n.classList.remove('highlighted', 'dimmed');
            }});
            document.querySelectorAll('line').forEach(l => {{
                l.classList.remove('highlighted', 'dimmed');
            }});
            document.getElementById('feature-details').style.display = 'none';
        }}
        
        function filterByStatus(status) {{
            document.querySelectorAll('.node').forEach(node => {{
                if (node.getAttribute('data-status') === status) {{
                    node.style.display = 'block';
                }} else {{
                    node.style.display = 'none';
                }}
            }});
            
            updateEdgeVisibility();
        }}
        
        function showAll() {{
            document.querySelectorAll('.node').forEach(node => {{
                node.style.display = 'block';
            }});
            document.querySelectorAll('line').forEach(line => {{
                line.style.display = 'block';
            }});
        }}
        
        function updateEdgeVisibility() {{
            document.querySelectorAll('line').forEach(line => {{
                const source = line.getAttribute('data-source');
                const target = line.getAttribute('data-target');
                const sourceNode = document.querySelector(`.node[data-id="${{source}}"]`);
                const targetNode = document.querySelector(`.node[data-id="${{target}}"]`);
                
                if (sourceNode && targetNode && 
                    sourceNode.style.display !== 'none' && 
                    targetNode.style.display !== 'none') {{
                    line.style.display = 'block';
                }} else {{
                    line.style.display = 'none';
                }}
            }});
        }}
        
        // Add click handlers to nodes
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('.node').forEach(node => {{
                node.addEventListener('click', (e) => {{
                    const nodeId = node.getAttribute('data-id');
                    highlightNode(nodeId);
                    e.stopPropagation();
                }});
            }});
            
            // Click on empty space to reset
            document.querySelector('svg').addEventListener('click', () => {{
                resetHighlight();
            }});
        }});
        '''


if __name__ == "__main__":
    # Example usage
    from .feature_graph import FeatureGraph, FeatureNode
    
    # Create a sample graph
    graph = FeatureGraph("example_project")
    
    # Add some features
    features = [
        FeatureNode(id="auth", name="Authentication", description="User auth system",
                   type="feature", status="completed"),
        FeatureNode(id="dashboard", name="Dashboard", description="Main dashboard",
                   type="feature", status="in_progress"),
        FeatureNode(id="api", name="API", description="REST API",
                   type="feature", status="planned"),
        FeatureNode(id="reports", name="Reports", description="Reporting system",
                   type="feature", status="blocked"),
    ]
    
    for feature in features:
        graph.add_feature(feature)
    
    # Add relationships
    graph.add_dependency("dashboard", "auth")
    graph.add_dependency("api", "auth")
    graph.add_dependency("reports", "dashboard")
    
    # Create visualization
    visualizer = FeatureGraphVisualizer(graph)
    
    # Generate HTML
    html_content = visualizer.generate_html(
        output_path=Path("feature_graph.html"),
        title="My Project Features"
    )
    
    print("Visualization saved to feature_graph.html")