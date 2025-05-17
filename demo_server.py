#!/usr/bin/env python3
"""Simple web server to view demo visualizations."""
import http.server
import socketserver
import webbrowser
from pathlib import Path

PORT = 8000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add headers to allow loading local resources
        self.send_header('Cross-Origin-Embedder-Policy', 'unsafe-none')
        self.send_header('Cross-Origin-Opener-Policy', 'unsafe-none')
        super().end_headers()

def main():
    """Start a simple HTTP server to view visualizations."""
    # Change to the directory containing the HTML files
    Handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Server started at http://localhost:{PORT}")
        print("Available visualizations:")
        
        # List all demo HTML files
        for html_file in Path('.').glob('demo_*.html'):
            print(f"  - http://localhost:{PORT}/{html_file.name}")
        
        print("\nPress Ctrl+C to stop the server")
        
        # Open the hierarchical layout by default
        if Path('demo_hierarchical.html').exists():
            webbrowser.open(f'http://localhost:{PORT}/demo_hierarchical.html')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()