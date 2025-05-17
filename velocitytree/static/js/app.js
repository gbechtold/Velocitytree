// VelocityTree Feature Graph Web Application

class FeatureGraphApp {
    constructor() {
        this.cy = null;
        this.currentLayout = 'hierarchical';
        this.graphData = null;
        
        this.initCytoscape();
        this.bindEvents();
    }
    
    initCytoscape() {
        this.cy = cytoscape({
            container: document.getElementById('cy'),
            style: this.getCytoscapeStyles(),
            elements: [],
            layout: { name: 'preset' }
        });
        
        // Handle node selection
        this.cy.on('tap', 'node', (event) => {
            const node = event.target;
            this.showFeatureDetails(node.id());
        });
    }
    
    getCytoscapeStyles() {
        return [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'width': '60px',
                    'height': '60px',
                    'font-size': '12px',
                    'font-weight': 'bold',
                    'background-color': '#3498db',
                    'color': '#ffffff',
                    'border-width': '2px',
                    'border-color': '#2c3e50',
                    'text-wrap': 'wrap',
                    'text-max-width': '80px'
                }
            },
            {
                selector: 'node[status="pending"]',
                style: {
                    'background-color': '#f39c12'
                }
            },
            {
                selector: 'node[status="in_progress"]',
                style: {
                    'background-color': '#3498db'
                }
            },
            {
                selector: 'node[status="completed"]',
                style: {
                    'background-color': '#27ae60'
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-color': '#e74c3c',
                    'border-width': '4px'
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': '2px',
                    'line-color': '#95a5a6',
                    'target-arrow-color': '#95a5a6',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier'
                }
            },
            {
                selector: 'edge[strength="critical"]',
                style: {
                    'line-color': '#e74c3c',
                    'target-arrow-color': '#e74c3c',
                    'width': '3px'
                }
            },
            {
                selector: 'edge[strength="strong"]',
                style: {
                    'line-color': '#f39c12',
                    'target-arrow-color': '#f39c12',
                    'width': '2.5px'
                }
            },
            {
                selector: 'edge[strength="weak"]',
                style: {
                    'line-color': '#bdc3c7',
                    'target-arrow-color': '#bdc3c7',
                    'line-style': 'dashed'
                }
            }
        ];
    }
    
    bindEvents() {
        document.getElementById('load-project').addEventListener('click', () => {
            this.loadProject();
        });
        
        document.getElementById('project-path').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.loadProject();
            }
        });
        
        document.getElementById('layout-selector').addEventListener('change', (e) => {
            this.currentLayout = e.target.value;
            this.applyLayout();
        });
        
        document.getElementById('refresh-graph').addEventListener('click', () => {
            this.refreshGraph();
        });
    }
    
    async loadProject() {
        const projectPath = document.getElementById('project-path').value;
        if (!projectPath) {
            alert('Please enter a project directory path');
            return;
        }
        
        try {
            const response = await fetch('/api/graph/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ project_dir: projectPath })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess('Project loaded successfully');
                await this.refreshGraph();
            } else {
                this.showError(data.error || 'Failed to load project');
            }
        } catch (error) {
            this.showError('Failed to load project: ' + error.message);
        }
    }
    
    async refreshGraph() {
        try {
            const response = await fetch('/api/graph');
            const data = await response.json();
            
            if (response.ok) {
                this.graphData = data;
                this.updateGraph(data);
                await this.applyLayout();
            } else {
                this.showError(data.error || 'Failed to load graph');
            }
        } catch (error) {
            this.showError('Failed to refresh graph: ' + error.message);
        }
    }
    
    updateGraph(data) {
        // Clear existing elements
        this.cy.elements().remove();
        
        // Add nodes
        const nodes = data.nodes.map(node => ({
            group: 'nodes',
            data: node.data,
            classes: node.data.status
        }));
        
        // Add edges
        const edges = data.edges.map(edge => ({
            group: 'edges',
            data: edge.data,
            classes: edge.data.strength
        }));
        
        this.cy.add(nodes);
        this.cy.add(edges);
    }
    
    async applyLayout() {
        if (!this.graphData || this.graphData.nodes.length === 0) return;
        
        if (this.currentLayout === 'cose-bilkent') {
            // Use Cose-Bilkent layout
            const layout = this.cy.layout({
                name: 'cose-bilkent',
                animate: true,
                animationDuration: 1000,
                idealEdgeLength: 100,
                nodeOverlap: 20,
                refresh: 20,
                fit: true,
                padding: 30,
                randomize: false,
                componentSpacing: 100,
                nodeRepulsion: 400000,
                edgeElasticity: 100,
                nestingFactor: 5,
                gravity: 80,
                numIter: 1000,
                initialTemp: 200,
                coolingFactor: 0.95,
                minTemp: 1.0
            });
            layout.run();
        } else {
            // Use server-provided layouts
            try {
                const response = await fetch(`/api/layout/${this.currentLayout}`);
                const positions = await response.json();
                
                if (response.ok) {
                    // Apply positions
                    this.cy.nodes().forEach(node => {
                        const pos = positions[node.id()];
                        if (pos) {
                            node.position({ x: pos.x * 100, y: pos.y * 100 });
                        }
                    });
                    
                    this.cy.fit(null, 50);
                } else {
                    console.error('Failed to get layout:', positions.error);
                    // Fallback to grid layout
                    this.cy.layout({ name: 'grid', animate: true }).run();
                }
            } catch (error) {
                console.error('Failed to apply layout:', error);
                // Fallback to grid layout
                this.cy.layout({ name: 'grid', animate: true }).run();
            }
        }
    }
    
    async showFeatureDetails(featureId) {
        try {
            const response = await fetch(`/api/feature/${featureId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.displayFeatureDetails(data);
            } else {
                this.showError(data.error || 'Failed to load feature details');
            }
        } catch (error) {
            this.showError('Failed to load feature details: ' + error.message);
        }
    }
    
    displayFeatureDetails(feature) {
        const infoDiv = document.getElementById('feature-info');
        
        const canStartClass = feature.can_start ? 'success' : 'error';
        const canStartText = feature.can_start ? 'Can Start' : 'Cannot Start';
        
        let html = `
            <div class="feature-header">
                <h3>${feature.data.name || feature.id}</h3>
                <span class="feature-status ${feature.data.status}">${feature.data.status}</span>
            </div>
            
            <div class="feature-section">
                <h4>Properties</h4>
                <ul class="feature-list">
                    <li>Type: ${feature.data.feature_type || 'feature'}</li>
                    <li>Can Start: <span class="${canStartClass}">${canStartText}</span></li>
                </ul>
            </div>
            
            <div class="feature-section">
                <h4>Dependencies (${feature.dependencies.length})</h4>
                <ul class="feature-list">
                    ${feature.dependencies.map(dep => `<li>${dep}</li>`).join('')}
                </ul>
            </div>
            
            <div class="feature-section">
                <h4>Dependents (${feature.dependents.length})</h4>
                <ul class="feature-list">
                    ${feature.dependents.map(dep => `<li>${dep}</li>`).join('')}
                </ul>
            </div>
            
            <div class="feature-section">
                <h4>All Dependencies (${feature.all_dependencies.length})</h4>
                <ul class="feature-list">
                    ${feature.all_dependencies.map(dep => `<li>${dep}</li>`).join('')}
                </ul>
            </div>
        `;
        
        if (feature.data.status !== 'completed') {
            html += `
                <div class="feature-actions">
                    <button class="btn btn-success" onclick="app.completeFeature('${feature.id}')">
                        Mark as Completed
                    </button>
                </div>
            `;
        }
        
        infoDiv.innerHTML = html;
    }
    
    async completeFeature(featureId) {
        try {
            const response = await fetch(`/api/feature/${featureId}/complete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showSuccess(data.message);
                await this.refreshGraph();
                this.showFeatureDetails(featureId);
            } else {
                this.showError(data.error || 'Failed to complete feature');
            }
        } catch (error) {
            this.showError('Failed to complete feature: ' + error.message);
        }
    }
    
    showError(message) {
        this.showNotification(message, 'error');
    }
    
    showSuccess(message) {
        this.showNotification(message, 'success');
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = type;
        notification.textContent = message;
        
        const sidebar = document.getElementById('sidebar');
        sidebar.insertBefore(notification, sidebar.firstChild);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

// Initialize the application
const app = new FeatureGraphApp();