"""Graceful-shutdown helpers for Cocktail Chronicles.

Signal handlers and atexit hooks are ALWAYS installed so that Ctrl-C
and process-termination signals both trigger clean teardown (SQLAlchemy
session removal + connection-pool disposal).

When the environment variable ``BROWSER_WATCHDOG=true`` is set, a daemon
thread also monitors browser heartbeats and automatically shuts the server
down when no heartbeat has been received for ``WATCHDOG_TIMEOUT`` seconds
(default: 30).  This lets the app close itself cleanly when a user closes
the last browser tab — no orphaned Python processes, no memory leaks.

Usage in ``run_app.py``::

    from shutdown_manager import install
    install(app)

The ``app.py`` factory registers ``/api/heartbeat`` and ``/api/shutdown``
endpoints that the base template's JavaScript snippet calls.  These routes
are always registered but are restricted to localhost-only requests for
safety.
"""
from __future__ import annotations

import atexit
import logging
import os
import signal
import sys
import threading
import time

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level watchdog state
# All writes go through _state_lock so the module is thread-safe.
# ---------------------------------------------------------------------------

_state_lock: threading.Lock = threading.Lock()
_last_heartbeat: float = time.monotonic()
_watchdog_timeout: int = int(os.environ.get("WATCHDOG_TIMEOUT", "30"))
_watchdog_enabled: bool = os.environ.get("BROWSER_WATCHDOG", "false").lower() == "true"
_shutdown_requested: bool = False


# ---------------------------------------------------------------------------
# Public helpers (called by Flask route handlers)
# ---------------------------------------------------------------------------

def record_heartbeat() -> None:
    """Reset the browser-idle timer.

    Should be called on every successful POST to ``/api/heartbeat``.
    Safe to call from any thread.
    """
    global _last_heartbeat
    with _state_lock:
        _last_heartbeat = time.monotonic()


def request_shutdown() -> None:
    """Schedule a graceful shutdown of the running server process.

    Safe to call from any thread.  Subsequent calls are no-ops so that
    racing signals or doubly-fired timers cannot cause a double-kill.
    """
    global _shutdown_requested
    with _state_lock:
        if _shutdown_requested:
            return
        _shutdown_requested = True

    logger.info(
        "[Shutdown] Graceful shutdown requested — flushing DB connections and stopping."
    )
    # SIGTERM causes Werkzeug to finish the current request cycle and then
    # exit cleanly, which in turn fires all atexit handlers registered via
    # install().  On Windows SIGTERM behaves like sys.exit(), which is fine.
    os.kill(os.getpid(), signal.SIGTERM)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _watchdog_body() -> None:
    """Long-running daemon thread: fires request_shutdown() after idle timeout.

    An initial grace period (1/3 of the timeout, minimum 10 s) is built in
    so the browser has time to open and send its first heartbeat before the
    watchdog starts counting.
    """
    initial_grace = max(10, _watchdog_timeout // 3)
    logger.info(
        "[Watchdog] Starting; initial grace period = %ds, idle timeout = %ds.",
        initial_grace,
        _watchdog_timeout,
    )
    time.sleep(initial_grace)

    while True:
        time.sleep(5)
        with _state_lock:
            if _shutdown_requested:
                return
            idle_seconds = time.monotonic() - _last_heartbeat

        if idle_seconds > _watchdog_timeout:
            logger.info(
                "[Watchdog] No browser heartbeat for %.0f s (> %d s limit) "
                "— initiating graceful shutdown.",
                idle_seconds,
                _watchdog_timeout,
            )
            request_shutdown()
            return


def _cleanup(app=None) -> None:
    """Dispose the SQLAlchemy connection pool and clear sessions on process exit.

    Registered as an atexit hook by :func:`install`.  The *app* argument
    allows cleanup to run inside a proper application context so that
    ``db.engine.dispose()`` uses the correct engine binding.

    This function is intentionally defensive — any exception is logged and
    swallowed so that a cleanup failure never masks the original exit.
    """
    try:
        if app is not None:
            with app.app_context():
                # Import here (not at module level) to avoid a circular import
                # when shutdown_manager is imported before models is fully loaded.
                from models import db  # noqa: PLC0415

                try:
                    db.session.remove()
                    logger.info("[Shutdown] SQLAlchemy session removed.")
                except Exception as exc:  # pragma: no cover
                    logger.warning("[Shutdown] Session removal error: %s", exc)

                try:
                    db.engine.dispose()
                    logger.info("[Shutdown] Database connection pool disposed.")
                except Exception as exc:  # pragma: no cover
                    logger.warning("[Shutdown] Engine disposal error: %s", exc)
        else:
            logger.warning(
                "[Shutdown] No Flask app context available; skipping DB cleanup."
            )
    except Exception as exc:  # pragma: no cover
        logger.warning("[Shutdown] Unexpected cleanup error: %s", exc)


# ---------------------------------------------------------------------------
# Public installer
# ---------------------------------------------------------------------------

def install(app) -> None:
    """Install signal handlers, atexit DB-cleanup, and (optionally) the watchdog.

    Call once from ``run_app.py`` after the Flask ``app`` object is available
    and **before** ``app.run()`` is called::

        from shutdown_manager import install
        install(app)

    :param app: The Flask application instance (required for atexit DB cleanup).
    """
    # ------------------------------------------------------------------
    # 1. atexit: always ensure DB connections are cleaned up on exit.
    # ------------------------------------------------------------------
    atexit.register(_cleanup, app)
    logger.debug("[Shutdown] atexit cleanup hook registered.")

    # ------------------------------------------------------------------
    # 2. Signal handlers: convert SIGTERM/SIGINT into a clean SystemExit
    #    so that the atexit hooks registered above always run.
    # ------------------------------------------------------------------
    def _handle_sigterm(signum, frame):  # noqa: ANN001
        logger.info("[Shutdown] SIGTERM received — running atexit handlers.")
        sys.exit(0)  # raises SystemExit → triggers atexit

    def _handle_sigint(signum, frame):  # noqa: ANN001
        logger.info("[Shutdown] SIGINT (Ctrl-C) received — running atexit handlers.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigint)
    logger.debug("[Shutdown] Signal handlers installed (SIGTERM, SIGINT).")

    # ------------------------------------------------------------------
    # 3. Browser-watchdog daemon thread (optional).
    # ------------------------------------------------------------------
    if _watchdog_enabled:
        logger.info(
            "[Watchdog] Browser watchdog ENABLED (idle timeout = %ds). "
            "Server will shut down automatically when all browser tabs are closed.",
            _watchdog_timeout,
        )
        t = threading.Thread(
            target=_watchdog_body,
            name="browser-watchdog",
            daemon=True,  # daemon thread exits when the main thread exits
        )
        t.start()
    else:
        logger.info(
            "[Watchdog] Browser watchdog is DISABLED. "
            "Set BROWSER_WATCHDOG=true to enable automatic shutdown on browser close."
        )
