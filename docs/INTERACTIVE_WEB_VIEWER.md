# Interactive Web Viewer Documentation

The VelocityTree interactive web viewer provides a dynamic visualization of feature graphs using Flask and Cytoscape.js.

## Features

- **Real-time Graph Visualization**: Interactive graph display using Cytoscape.js
- **Multiple Layout Algorithms**: Hierarchical, Spring, Circular, and Cose-Bilkent layouts
- **Feature Details Sidebar**: Click on any node to see detailed information
- **Project Loading**: Load VelocityTree projects directly from the web interface
- **Feature Status Updates**: Mark features as completed directly from the viewer
- **Responsive Design**: Works on desktop and mobile devices

## Starting the Web Server

### Using the CLI

```bash
# Start with default settings (localhost:5000)
vtree visualize web

# Start with custom host/port
vtree visualize web --host 0.0.0.0 --port 8080

# Load a project automatically
vtree visualize web --project /path/to/project
```

### Using Python Script

```python
from velocitytree.web_server import FeatureGraphWebServer
from velocitytree.core import VelocityTree

# Create server
server = FeatureGraphWebServer(host="127.0.0.1", port=5000)

# Load a project
vt = VelocityTree("/path/to/project")
server.velocity_tree = vt
server.feature_graph = vt.feature_graph

# Run server
server.run()
```

## Web Interface Usage

### Loading a Project

1. Enter the project directory path in the text field
2. Click "Load Project" button
3. The graph will automatically refresh

### Graph Interaction

- **Pan**: Click and drag on empty space
- **Zoom**: Mouse wheel or pinch gesture
- **Select Node**: Click on any node
- **Move Node**: Drag selected node

### Layout Options

- **Hierarchical**: Tree-like structure showing dependencies
- **Spring**: Force-directed layout for complex graphs
- **Circular**: Nodes arranged in circles
- **Cose-Bilkent**: Advanced force-directed layout

### Feature Details

Click on any feature node to see:
- Feature name and ID
- Current status
- Dependencies and dependents
- Whether the feature can start
- Option to mark as completed

## API Endpoints

The web server provides several REST API endpoints:

### GET /api/graph
Returns the current feature graph in Cytoscape.js format.

### POST /api/graph/load
Load a feature graph from a project directory.
```json
{
  "project_dir": "/path/to/project"
}
```

### GET /api/feature/{feature_id}
Get detailed information about a specific feature.

### POST /api/feature/{feature_id}/complete
Mark a feature as completed.

### GET /api/layout/{layout_type}
Get node positions for a specific layout algorithm.

## Architecture

The web viewer consists of:

1. **Flask Backend** (`web_server.py`)
   - REST API endpoints
   - Graph data management
   - Integration with VelocityTree core

2. **Frontend** (HTML/CSS/JavaScript)
   - Cytoscape.js for graph rendering
   - Vanilla JavaScript for UI interaction
   - Responsive CSS design

3. **Templates** (`templates/index.html`)
   - Main HTML structure
   - Controls and sidebar layout

4. **Static Assets**
   - `/static/css/style.css`: Styling
   - `/static/js/app.js`: Client-side logic

## Customization

### Adding New Layouts

Add a new layout option in `app.js`:

```javascript
// In applyLayout() method
if (this.currentLayout === 'custom') {
    const layout = this.cy.layout({
        name: 'your-layout-name',
        // layout options
    });
    layout.run();
}
```

### Styling Nodes

Modify the Cytoscape styles in `getCytoscapeStyles()`:

```javascript
{
    selector: 'node[feature_type="epic"]',
    style: {
        'background-color': '#e74c3c',
        'width': '80px',
        'height': '80px'
    }
}
```

### Adding New API Endpoints

Add endpoints in `web_server.py`:

```python
@self.app.route('/api/custom/<param>')
def custom_endpoint(param):
    # Your logic here
    return jsonify({"result": "data"})
```

## Security Considerations

- The web server binds to localhost by default
- Use authentication if exposing to network
- Validate all input paths
- Consider HTTPS for production use

## Troubleshooting

### Server Won't Start
- Check if port is already in use
- Ensure Flask is installed: `pip install Flask flask-cors`

### Graph Not Loading
- Verify project path is correct
- Check browser console for errors
- Ensure NetworkX is installed

### Layout Issues
- Install required dependencies: `pip install numpy matplotlib`
- Check browser compatibility
- Try different layout algorithms