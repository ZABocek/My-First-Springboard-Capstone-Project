#!/usr/bin/env python
"""Run the Flask application."""

from app import app
import os

if __name__ == '__main__':
    # Determine the host and port
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))

    print(f"\n{'='*60}")
    print(f"Starting Flask Application")
    print(f"{'='*60}")
    print(f"Server running at: http://{host}:{port}")
    print(f"Press CTRL+C to stop the server")
    print(f"{'='*60}\n")

    # debug mode and schema management are driven by config/env variables.
    # Use 'flask db upgrade' to apply Alembic migrations before starting.
    app.run(host=host, port=port)
