"""Test the interactive web server functionality."""

import pytest
import json
from unittest.mock import Mock, patch

from velocitytree.web_server import FeatureGraphWebServer
from velocitytree.feature_graph import FeatureGraph, FeatureNode, RelationType


class TestWebServer:
    """Test the feature graph web server."""
    
    @pytest.fixture
    def feature_graph(self):
        """Create a test feature graph."""
        graph = FeatureGraph("test_project")
        
        # Add test features
        features = [
            FeatureNode(id="f1", name="Feature 1", feature_type="feature", status="completed"),
            FeatureNode(id="f2", name="Feature 2", feature_type="feature", status="in_progress"),
            FeatureNode(id="f3", name="Feature 3", feature_type="feature", status="pending"),
        ]
        
        for feature in features:
            graph.add_feature(feature)
        
        # Add relationships
        graph.add_relationship("f2", "f1", RelationType.DEPENDS_ON)
        graph.add_relationship("f3", "f2", RelationType.DEPENDS_ON)
        
        return graph
    
    @pytest.fixture
    def web_server(self, feature_graph):
        """Create test web server instance."""
        server = FeatureGraphWebServer(host="127.0.0.1", port=5001)
        server.feature_graph = feature_graph
        server.app.config['TESTING'] = True
        return server
    
    def test_server_initialization(self):
        """Test server initialization."""
        server = FeatureGraphWebServer()
        assert server.host == "127.0.0.1"
        assert server.port == 5000
        assert server.feature_graph is None
        assert server.velocity_tree is None
    
    def test_index_route(self, web_server):
        """Test the index route."""
        client = web_server.app.test_client()
        response = client.get('/')
        assert response.status_code == 200
        assert b'VelocityTree Feature Graph' in response.data
    
    def test_get_graph_api(self, web_server):
        """Test getting graph data."""
        client = web_server.app.test_client()
        response = client.get('/api/graph')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'nodes' in data
        assert 'edges' in data
        assert len(data['nodes']) == 3
        assert len(data['edges']) == 2
    
    def test_get_graph_no_data(self, web_server):
        """Test getting graph when no graph is loaded."""
        web_server.feature_graph = None
        client = web_server.app.test_client()
        response = client.get('/api/graph')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_feature_details_api(self, web_server):
        """Test getting feature details."""
        client = web_server.app.test_client()
        response = client.get('/api/feature/f1')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['id'] == 'f1'
        assert 'data' in data
        assert 'dependencies' in data
        assert 'dependents' in data
        assert 'can_start' in data
    
    def test_feature_not_found(self, web_server):
        """Test getting non-existent feature."""
        client = web_server.app.test_client()
        response = client.get('/api/feature/invalid')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_complete_feature_api(self, web_server):
        """Test completing a feature."""
        client = web_server.app.test_client()
        response = client.post('/api/feature/f3/complete')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Check that feature is now completed
        feature = web_server.feature_graph.get_feature('f3')
        assert feature.status == 'completed'
    
    def test_layout_api(self, web_server):
        """Test getting layout positions."""
        client = web_server.app.test_client()
        
        # Test different layouts
        for layout in ['hierarchical', 'spring', 'circular']:
            response = client.get(f'/api/layout/{layout}')
            assert response.status_code == 200
            
            positions = json.loads(response.data)
            assert isinstance(positions, dict)
            assert 'f1' in positions
            assert 'x' in positions['f1']
            assert 'y' in positions['f1']
    
    def test_invalid_layout(self, web_server):
        """Test invalid layout type."""
        client = web_server.app.test_client()
        response = client.get('/api/layout/invalid')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    @patch('velocitytree.web_server.VelocityTree')
    def test_load_graph_api(self, mock_velocity_tree, web_server):
        """Test loading a graph from project directory."""
        mock_vt_instance = Mock()
        mock_vt_instance.feature_graph = Mock()
        mock_velocity_tree.return_value = mock_vt_instance
        
        client = web_server.app.test_client()
        response = client.post('/api/graph/load',
                             json={'project_dir': '/test/path'})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True
        assert web_server.velocity_tree is not None
        assert web_server.feature_graph is not None
    
    def test_load_graph_missing_dir(self, web_server):
        """Test loading graph without directory."""
        client = web_server.app.test_client()
        response = client.post('/api/graph/load', json={})
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_load_graph_error(self, web_server):
        """Test loading graph with error."""
        with patch('velocitytree.web_server.VelocityTree', side_effect=Exception("Test error")):
            client = web_server.app.test_client()
            response = client.post('/api/graph/load',
                                 json={'project_dir': '/test/path'})
            assert response.status_code == 500
            
            data = json.loads(response.data)
            assert 'error' in data
            assert 'Test error' in data['error']