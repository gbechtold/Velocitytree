"""Test visualization generation functionality."""
import unittest
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType
from velocitytree.visualization import FeatureGraphVisualizer


class TestVisualization(unittest.TestCase):
    """Test the visualization generation functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = FeatureGraph("test_project")
        
        # Create test features
        self.features = [
            FeatureNode(
                id="auth",
                name="Authentication", 
                description="User authentication system",
                type="feature",
                status="completed"
            ),
            FeatureNode(
                id="api",
                name="REST API",
                description="API endpoints",
                type="feature", 
                status="in_progress"
            ),
            FeatureNode(
                id="dashboard",
                name="Dashboard",
                description="Main dashboard",
                type="feature",
                status="planned"
            ),
            FeatureNode(
                id="milestone1",
                name="Core Features",
                description="Core functionality",
                type="milestone",
                status="in_progress"
            )
        ]
        
        # Add features to graph
        for feature in self.features:
            self.graph.add_feature(feature)
        
        # Add relationships
        self.graph.add_dependency("api", "auth")
        self.graph.add_dependency("dashboard", "api")
        self.graph.add_relationship("milestone1", "auth", RelationType.INCLUDES)
        self.graph.add_relationship("milestone1", "api", RelationType.INCLUDES)
    
    def test_svg_generation(self):
        """Test SVG output generation."""
        visualizer = FeatureGraphVisualizer(self.graph)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.svg', delete=False) as f:
            svg_content = visualizer.generate_svg(output_path=Path(f.name))
            
            # Verify SVG content
            self.assertTrue(svg_content.startswith('<svg'))
            self.assertTrue('</svg>' in svg_content)
            
            # Parse SVG
            root = ET.fromstring(svg_content)
            self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
            
            # Check for nodes
            nodes = root.findall('.//{http://www.w3.org/2000/svg}g[@class="node"]')
            self.assertEqual(len(nodes), 4)  # 4 features
            
            # Check for relationships
            lines = root.findall('.//{http://www.w3.org/2000/svg}line')
            self.assertGreater(len(lines), 0)
            
            # Verify file was created
            self.assertTrue(Path(f.name).exists())
    
    def test_html_generation(self):
        """Test HTML output generation."""
        visualizer = FeatureGraphVisualizer(self.graph)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            html_content = visualizer.generate_html(
                output_path=Path(f.name),
                title="Test Graph",
                interactive=True
            )
            
            # Verify HTML content
            self.assertTrue('<html' in html_content)
            self.assertTrue('</html>' in html_content)
            self.assertIn('Test Graph', html_content)
            
            # Check for SVG embed
            self.assertIn('<svg', html_content)
            
            # Check for JavaScript
            self.assertIn('<script>', html_content)
            self.assertIn('graphData', html_content)
            
            # Check for controls
            self.assertIn('Show/Hide Info', html_content)
            
            # Verify file was created
            self.assertTrue(Path(f.name).exists())
    
    def test_layout_algorithms(self):
        """Test different layout algorithms."""
        layouts = ['hierarchical', 'spring', 'circular']
        
        for layout in layouts:
            visualizer = FeatureGraphVisualizer(self.graph, layout=layout)
            svg_content = visualizer.generate_svg()
            
            # Should generate valid SVG for all layouts
            self.assertTrue(svg_content.startswith('<svg'))
            
            # Check that nodes have positions
            for node_id in self.graph.features:
                self.assertIn(node_id, visualizer.node_positions)
                pos = visualizer.node_positions[node_id]
                self.assertEqual(len(pos), 2)  # x, y coordinates
    
    def test_status_colors(self):
        """Test that status colors are applied correctly."""
        visualizer = FeatureGraphVisualizer(self.graph)
        svg_content = visualizer.generate_svg()
        
        # Check for status colors in SVG
        self.assertIn(visualizer.STATUS_COLORS['completed'], svg_content)
        self.assertIn(visualizer.STATUS_COLORS['in_progress'], svg_content)
        self.assertIn(visualizer.STATUS_COLORS['planned'], svg_content)
    
    def test_relationship_styles(self):
        """Test that relationships have correct styles."""
        visualizer = FeatureGraphVisualizer(self.graph)
        svg_content = visualizer.generate_svg()
        
        # Check for relationship lines
        root = ET.fromstring(svg_content)
        lines = root.findall('.//{http://www.w3.org/2000/svg}line')
        
        # Verify line attributes
        for line in lines:
            self.assertIsNotNone(line.get('stroke'))
            self.assertIsNotNone(line.get('stroke-width'))
    
    def test_interactive_features(self):
        """Test interactive HTML features."""
        visualizer = FeatureGraphVisualizer(self.graph)
        html_content = visualizer.generate_html(interactive=True)
        
        # Check for interactive JavaScript functions
        self.assertIn('highlightNode', html_content)
        self.assertIn('filterByStatus', html_content)
        self.assertIn('showFeatureDetails', html_content)
        
        # Check that graph data is embedded
        self.assertIn('const graphData =', html_content)
        
        # Verify node data includes dependencies
        import json
        # Extract graph data from JavaScript
        start = html_content.find('const graphData = ') + len('const graphData = ')
        end = html_content.find(';\n', start)
        graph_data_str = html_content[start:end]
        graph_data = json.loads(graph_data_str)
        
        self.assertIn('nodes', graph_data)
        self.assertIn('relationships', graph_data)
        
        # Check that api node has auth as dependency
        api_node = graph_data['nodes']['api']
        self.assertIn('auth', api_node['dependencies'])
    
    def test_empty_graph(self):
        """Test visualization of empty graph."""
        empty_graph = FeatureGraph("empty")
        visualizer = FeatureGraphVisualizer(empty_graph)
        
        # Should still generate valid output
        svg_content = visualizer.generate_svg()
        self.assertTrue(svg_content.startswith('<svg'))
        
        html_content = visualizer.generate_html()
        self.assertIn('<html', html_content)
    
    def test_large_graph_layout(self):
        """Test layout with many nodes."""
        large_graph = FeatureGraph("large")
        
        # Add 20 features
        for i in range(20):
            feature = FeatureNode(
                id=f"feature_{i}",
                name=f"Feature {i}",
                description=f"Description {i}",
                type="feature",
                status="planned"
            )
            large_graph.add_feature(feature)
        
        # Add some dependencies
        for i in range(1, 20):
            if i % 3 == 0:
                large_graph.add_dependency(f"feature_{i}", f"feature_{i-1}")
            if i % 5 == 0 and i > 5:
                large_graph.add_dependency(f"feature_{i}", f"feature_{i-5}")
        
        visualizer = FeatureGraphVisualizer(large_graph)
        svg_content = visualizer.generate_svg()
        
        # Should handle large graphs
        self.assertTrue(svg_content.startswith('<svg'))
        self.assertEqual(len(visualizer.node_positions), 20)
    
    def test_cyclic_graph_handling(self):
        """Test handling of cyclic dependencies."""
        cyclic_graph = FeatureGraph("cyclic")
        
        # Create cycle
        features = ["A", "B", "C"]
        for f in features:
            cyclic_graph.add_feature(FeatureNode(
                id=f, name=f, description=f, type="feature", status="planned"
            ))
        
        # Create cycle: A -> B -> C -> A
        cyclic_graph.add_dependency("A", "B")
        cyclic_graph.add_dependency("B", "C")
        cyclic_graph.add_dependency("C", "A")
        
        visualizer = FeatureGraphVisualizer(cyclic_graph)
        
        # Should fall back to spring layout for cyclic graphs
        svg_content = visualizer.generate_svg()
        self.assertTrue(svg_content.startswith('<svg'))


if __name__ == "__main__":
    unittest.main()