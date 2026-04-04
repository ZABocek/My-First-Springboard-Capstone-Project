#!/usr/bin/env python
"""Run the Flask application with graceful shutdown support.

Normal usage::

    python run_app.py

Browser-watchdog mode (started automatically by start_app.bat)::

    set BROWSER_WATCHDOG=true
    python run_app.py

When BROWSER_WATCHDOG=true the server monitors browser heartbeats sent
by the base-template JavaScript and shuts itself down cleanly when all
browser tabs are closed.  Signal handlers and atexit hooks ensure the
SQLAlchemy connection pool is always disposed on exit, preventing
resource leaks regardless of how the process is stopped.
"""
import os
import sys

from app import app
import shutdown_manager


def main() -> None:
    """Entry point — configure, install shutdown hooks, then serve."""
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', '5000'))

    watchdog_on = os.environ.get('BROWSER_WATCHDOG', 'false').lower() == 'true'

    border = '=' * 62
    print(f"\n{border}")
    print(f"  Cocktail Chronicles — Development Server")
    print(f"{border}")
    print(f"  URL     : http://{host}:{port}")
    if watchdog_on:
        print(f"  Stop    : Close the browser tab — server exits automatically.")
        print(f"  Watchdog: ON  (idle timeout = "
              f"{os.environ.get('WATCHDOG_TIMEOUT', '30')} s)")
    else:
        print(f"  Stop    : Press Ctrl-C in this window.")
        print(f"  Watchdog: OFF (set BROWSER_WATCHDOG=true to enable)")
    print(f"{border}\n")

    # Install signal handlers (SIGTERM, SIGINT), atexit DB-cleanup, and
    # (when BROWSER_WATCHDOG=true) the browser-idle watchdog thread.
    # This must be called BEFORE app.run() so every exit path is covered.
    shutdown_manager.install(app)

    try:
        # debug and schema management are driven by config / env variables.
        # Run 'flask db upgrade' to apply Alembic migrations before starting.
        app.run(host=host, port=port)
    except SystemExit:
        # Raised by our signal handlers — atexit hooks fire automatically.
        sys.exit(0)
    except KeyboardInterrupt:
        # Safety net: if SIGINT somehow bypasses our handler.
        print("\n[INFO] Keyboard interrupt — shutting down.")
        sys.exit(0)


if __name__ == '__main__':
    main()
