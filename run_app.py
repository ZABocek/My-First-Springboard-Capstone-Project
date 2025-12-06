#!/usr/bin/env python
"""Run the Flask application."""

from app import app, init_db
import os

if __name__ == '__main__':
    # Initialize the database
    init_db()
    
    # Set debug mode for development
    app.config['DEBUG'] = True
    
    # Determine the host and port
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f"\n{'='*60}")
    print(f"Starting Flask Application")
    print(f"{'='*60}")
    print(f"Server running at: http://{host}:{port}")
    print(f"Press CTRL+C to stop the server")
    print(f"{'='*60}\n")
    
    # Run the app
    app.run(host=host, port=port, debug=True)
