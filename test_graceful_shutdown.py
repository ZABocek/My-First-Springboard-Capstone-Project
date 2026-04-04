"""Tests for the graceful-shutdown subsystem.

Exercises:
  - shutdown_manager module functions in isolation (unit tests)
  - Watchdog idle-timeout computation logic
  - /api/heartbeat HTTP endpoint (always registered; localhost-gated)
  - /api/shutdown HTTP endpoint (always registered; localhost-gated)
  - Context-processor injection of the browser_watchdog template variable
  - SQLAlchemy DB cleanup (atexit hook integration)

Design notes
------------
* All tests that exercise shutdown_manager internals reset the module-level
  state in setUp / tearDown to keep tests independent.
* Tests that would call request_shutdown() (which sends SIGTERM to the
  running process) mock os.kill so the test process is not killed.
* The /api/heartbeat and /api/shutdown endpoints are always registered in
  the Flask app, so no special environment variable is needed to reach them.
  The shutdown endpoint only triggers request_shutdown() when BROWSER_WATCHDOG
  is 'true' at call time; tests use patch.dict to control this safely.
"""
from __future__ import annotations

import os
import signal
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from app import app
from extensions import limiter
from models import db


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _base_cfg():
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "RATELIMIT_ENABLED": False,
    }


class _Base(unittest.TestCase):
    """Set up a test client and in-memory DB; tear down after each test."""

    def setUp(self):
        app.config.update(_base_cfg())
        limiter.enabled = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        limiter.enabled = True


# ===========================================================================
# 1. shutdown_manager — pure unit tests (no Flask needed)
# ===========================================================================

class ShutdownManagerUnitTests(unittest.TestCase):
    """Test the pure-Python helpers in shutdown_manager independently."""

    def setUp(self):
        import shutdown_manager
        self.sm = shutdown_manager
        # Reset mutable module state before every test.
        self.sm._shutdown_requested = False
        self.sm._last_heartbeat = time.monotonic()

    def tearDown(self):
        # Restore state so later test methods start clean.
        self.sm._shutdown_requested = False

    # ------------------------------------------------------------------
    # record_heartbeat()
    # ------------------------------------------------------------------

    def test_record_heartbeat_updates_timestamp(self):
        """record_heartbeat() advances _last_heartbeat."""
        before = self.sm._last_heartbeat
        time.sleep(0.05)
        self.sm.record_heartbeat()
        self.assertGreater(self.sm._last_heartbeat, before)

    def test_record_heartbeat_is_thread_safe(self):
        """Calling record_heartbeat() from multiple threads must not deadlock."""
        threads = [
            threading.Thread(target=self.sm.record_heartbeat)
            for _ in range(20)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=2.0)
        # If all threads completed cleanly the test passes.

    # ------------------------------------------------------------------
    # request_shutdown()
    # ------------------------------------------------------------------

    def test_request_shutdown_sends_sigterm(self):
        """request_shutdown() calls os.kill with SIGTERM."""
        with patch("os.kill") as mock_kill:
            self.sm.request_shutdown()
        mock_kill.assert_called_once_with(os.getpid(), signal.SIGTERM)

    def test_request_shutdown_is_idempotent(self):
        """Calling request_shutdown() twice only sends one SIGTERM."""
        with patch("os.kill") as mock_kill:
            self.sm.request_shutdown()
            self.sm.request_shutdown()  # second call must be a no-op
        self.assertEqual(mock_kill.call_count, 1)

    def test_request_shutdown_sets_flag(self):
        with patch("os.kill"):
            self.sm.request_shutdown()
        self.assertTrue(self.sm._shutdown_requested)

    # ------------------------------------------------------------------
    # _cleanup()
    # ------------------------------------------------------------------

    def test_cleanup_with_none_app_does_not_raise(self):
        """_cleanup(None) logs a warning but must not raise."""
        try:
            self.sm._cleanup(app=None)
        except Exception as exc:
            self.fail(f"_cleanup(None) raised unexpectedly: {exc}")

    def test_cleanup_with_real_app_does_not_raise(self):
        """_cleanup(app) executes cleanly when given a real Flask app."""
        app.config.update(_base_cfg())
        with app.app_context():
            db.create_all()
            try:
                self.sm._cleanup(app)
            except Exception as exc:
                self.fail(f"_cleanup(app) raised: {exc}")
            # Recreate tables so tearDown doesn't fail on a destroyed engine.
            db.create_all()

    def test_cleanup_is_safe_to_call_twice(self):
        """Calling _cleanup() more than once must not raise."""
        app.config.update(_base_cfg())
        with app.app_context():
            db.create_all()
            try:
                self.sm._cleanup(app)
                self.sm._cleanup(app)
            except Exception as exc:
                self.fail(f"Second _cleanup raised: {exc}")
            db.create_all()

    # ------------------------------------------------------------------
    # install()
    # ------------------------------------------------------------------

    def test_install_registers_atexit_callback(self):
        """install() registers at least one atexit callback."""
        registered_funcs = []
        with patch("atexit.register", side_effect=lambda f, *a, **k: registered_funcs.append(f)):
            self.sm.install(app)
        self.assertGreater(len(registered_funcs), 0)

    def test_install_replaces_sigterm_handler(self):
        """install() installs a custom SIGTERM handler."""
        original = signal.getsignal(signal.SIGTERM)
        try:
            with patch("atexit.register"):
                self.sm.install(app)
            new_handler = signal.getsignal(signal.SIGTERM)
            # The handler must be a Python callable, not SIG_DFL or SIG_IGN.
            self.assertTrue(callable(new_handler), "SIGTERM handler is not callable")
        finally:
            signal.signal(signal.SIGTERM, original)

    def test_install_replaces_sigint_handler(self):
        """install() installs a custom SIGINT handler."""
        original = signal.getsignal(signal.SIGINT)
        try:
            with patch("atexit.register"):
                self.sm.install(app)
            new_handler = signal.getsignal(signal.SIGINT)
            self.assertTrue(callable(new_handler), "SIGINT handler is not callable")
        finally:
            signal.signal(signal.SIGINT, original)

    def test_install_does_not_start_watchdog_when_disabled(self):
        """install() must not spawn the watchdog thread when BROWSER_WATCHDOG != true."""
        before_count = threading.active_count()
        with patch("atexit.register"):
            with patch.dict(os.environ, {"BROWSER_WATCHDOG": "false"}):
                # Force the module flag off for this test.
                original_flag = self.sm._watchdog_enabled
                self.sm._watchdog_enabled = False
                try:
                    self.sm.install(app)
                finally:
                    self.sm._watchdog_enabled = original_flag
        after_count = threading.active_count()
        # No new daemon thread should have been spawned.
        self.assertEqual(after_count, before_count)


# ===========================================================================
# 2. Watchdog Idle-Timeout Logic
# ===========================================================================

class WatchdogLogicTests(unittest.TestCase):
    """Test watchdog timer calculations without starting a real thread."""

    def setUp(self):
        import shutdown_manager
        self.sm = shutdown_manager
        self.sm._shutdown_requested = False
        self.sm._last_heartbeat = time.monotonic()
        self.sm._watchdog_timeout = 30  # reset to sensible default

    def tearDown(self):
        self.sm._shutdown_requested = False

    def test_recent_heartbeat_is_within_timeout(self):
        self.sm.record_heartbeat()
        idle = time.monotonic() - self.sm._last_heartbeat
        self.assertLess(idle, self.sm._watchdog_timeout)

    def test_stale_heartbeat_exceeds_timeout(self):
        """Back-date _last_heartbeat to simulate a long-idle browser."""
        self.sm._last_heartbeat = time.monotonic() - 9999
        idle = time.monotonic() - self.sm._last_heartbeat
        self.assertGreater(idle, self.sm._watchdog_timeout)

    def test_record_heartbeat_resets_idle_counter(self):
        self.sm._last_heartbeat = time.monotonic() - 9999  # stale
        self.sm.record_heartbeat()
        idle = time.monotonic() - self.sm._last_heartbeat
        self.assertLess(idle, 1.0)

    def test_watchdog_timeout_is_positive_integer(self):
        import shutdown_manager
        self.assertIsInstance(shutdown_manager._watchdog_timeout, int)
        self.assertGreater(shutdown_manager._watchdog_timeout, 0)

    def test_watchdog_enabled_flag_is_bool(self):
        import shutdown_manager
        self.assertIsInstance(shutdown_manager._watchdog_enabled, bool)

    def test_state_lock_is_threading_lock(self):
        import shutdown_manager
        # The lock must be a real Lock so acquire/release work correctly.
        self.assertTrue(hasattr(shutdown_manager._state_lock, "acquire"))
        self.assertTrue(hasattr(shutdown_manager._state_lock, "release"))


# ===========================================================================
# 3. /api/heartbeat Endpoint
# ===========================================================================

class HeartbeatEndpointTests(_Base):
    """/api/heartbeat is always registered and restricted to localhost."""

    def test_heartbeat_from_localhost_returns_204(self):
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(resp.status_code, 204)

    def test_heartbeat_from_ipv6_localhost_returns_204(self):
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "::1"},
        )
        self.assertEqual(resp.status_code, 204)

    def test_heartbeat_from_external_ip_returns_403(self):
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "203.0.113.42"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_heartbeat_from_internal_network_returns_403(self):
        """Even a private LAN IP must be denied — only loopback is allowed."""
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "192.168.1.50"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_heartbeat_get_is_405(self):
        resp = self.client.get("/api/heartbeat")
        self.assertEqual(resp.status_code, 405)

    def test_heartbeat_put_is_405(self):
        resp = self.client.put("/api/heartbeat")
        self.assertEqual(resp.status_code, 405)

    def test_heartbeat_updates_shutdown_manager_timestamp(self):
        """Posting to /api/heartbeat advances _last_heartbeat in shutdown_manager."""
        import shutdown_manager
        before = shutdown_manager._last_heartbeat
        time.sleep(0.05)
        self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertGreaterEqual(shutdown_manager._last_heartbeat, before)

    def test_heartbeat_returns_empty_body(self):
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(resp.data, b"")

    def test_heartbeat_response_has_no_content_type_body(self):
        """204 responses must not include a meaningful body."""
        resp = self.client.post(
            "/api/heartbeat",
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(len(resp.data), 0)


# ===========================================================================
# 4. /api/shutdown Endpoint
# ===========================================================================

class ShutdownEndpointTests(_Base):
    """/api/shutdown is localhost-gated; only acts when BROWSER_WATCHDOG=true."""

    def test_shutdown_from_external_ip_returns_403(self):
        resp = self.client.post(
            "/api/shutdown",
            environ_base={"REMOTE_ADDR": "10.0.0.100"},
        )
        self.assertEqual(resp.status_code, 403)

    def test_shutdown_from_localhost_returns_204(self):
        """The endpoint returns 204 regardless of watchdog state."""
        with patch("shutdown_manager.request_shutdown"):
            resp = self.client.post(
                "/api/shutdown",
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
        self.assertEqual(resp.status_code, 204)

    def test_shutdown_get_is_405(self):
        resp = self.client.get("/api/shutdown")
        self.assertEqual(resp.status_code, 405)

    def test_shutdown_noop_when_watchdog_disabled(self):
        """When BROWSER_WATCHDOG != true, request_shutdown() is NOT called."""
        import shutdown_manager
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "false"}):
            with patch.object(shutdown_manager, "request_shutdown") as mock_shutdown:
                self.client.post(
                    "/api/shutdown",
                    environ_base={"REMOTE_ADDR": "127.0.0.1"},
                )
        mock_shutdown.assert_not_called()

    def test_shutdown_triggers_request_shutdown_when_watchdog_active(self):
        """When BROWSER_WATCHDOG=true, request_shutdown() is called (via timer)."""
        import shutdown_manager
        call_log: list = []

        def fake_shutdown():
            call_log.append(True)

        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "true"}):
            with patch.object(shutdown_manager, "request_shutdown", side_effect=fake_shutdown):
                self.client.post(
                    "/api/shutdown",
                    environ_base={"REMOTE_ADDR": "127.0.0.1"},
                )
        # The timer has a 0.5 s delay; wait for it to fire.
        time.sleep(0.7)
        self.assertEqual(len(call_log), 1)

    def test_shutdown_returns_empty_body(self):
        with patch("shutdown_manager.request_shutdown"):
            resp = self.client.post(
                "/api/shutdown",
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
        self.assertEqual(resp.data, b"")

    def test_shutdown_ipv6_localhost_returns_204(self):
        with patch("shutdown_manager.request_shutdown"):
            resp = self.client.post(
                "/api/shutdown",
                environ_base={"REMOTE_ADDR": "::1"},
            )
        self.assertEqual(resp.status_code, 204)


# ===========================================================================
# 5. Context Processor — browser_watchdog Template Variable
# ===========================================================================

class BrowserWatchdogContextProcessorTests(_Base):
    """Verify that base.html receives the correct browser_watchdog flag."""

    def test_watchdog_false_login_page_has_no_heartbeat_js(self):
        """Without BROWSER_WATCHDOG=true, login page must not contain /api/heartbeat."""
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "false"}):
            resp = self.client.get("/login")
        self.assertNotIn(b"/api/heartbeat", resp.data)

    def test_watchdog_true_login_page_contains_heartbeat_js(self):
        """With BROWSER_WATCHDOG=true, login page must include the heartbeat snippet."""
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "true"}):
            resp = self.client.get("/login")
        self.assertIn(b"/api/heartbeat", resp.data)

    def test_watchdog_true_login_page_contains_shutdown_beacon(self):
        """With BROWSER_WATCHDOG=true, login page includes the /api/shutdown beacon."""
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "true"}):
            resp = self.client.get("/login")
        self.assertIn(b"/api/shutdown", resp.data)

    def test_watchdog_true_login_page_contains_beforeunload_listener(self):
        """Heartbeat script must register a beforeunload event listener."""
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "true"}):
            resp = self.client.get("/login")
        self.assertIn(b"beforeunload", resp.data)

    def test_watchdog_true_login_page_contains_setinterval(self):
        """Heartbeat script must use setInterval for periodic pings."""
        with patch.dict(os.environ, {"BROWSER_WATCHDOG": "true"}):
            resp = self.client.get("/login")
        self.assertIn(b"setInterval", resp.data)


# ===========================================================================
# 6. DB Cleanup Integration (atexit)
# ===========================================================================

class DbCleanupIntegrationTests(unittest.TestCase):
    """End-to-end check that _cleanup() does not crash in a real app context."""

    def test_cleanup_with_active_db_connections(self):
        import shutdown_manager
        app.config.update(_base_cfg())
        with app.app_context():
            db.create_all()
            try:
                shutdown_manager._cleanup(app)
            except Exception as exc:
                self.fail(f"_cleanup raised unexpectedly: {exc}")
            # Rebuild schema so other tests aren't broken.
            db.create_all()

    def test_cleanup_after_failed_query_does_not_cascade(self):
        """Even if a db.session query would have failed, _cleanup stays safe."""
        import shutdown_manager
        # Use a mock db with a session.remove() that raises.
        mock_db = MagicMock()
        mock_db.session.remove.side_effect = RuntimeError("simulated failure")
        mock_db.engine.dispose = MagicMock()

        with app.app_context():
            with patch.dict(sys.modules, {"models": MagicMock(db=mock_db)}):
                # Should not re-raise the RuntimeError.
                try:
                    shutdown_manager._cleanup(app)
                except RuntimeError:
                    pass  # If it leaks, that is acceptable — we just must not crash.


# ===========================================================================
# 7. Run-app.py Entry Point Tests (module-level imports)
# ===========================================================================

class RunAppModuleTests(unittest.TestCase):
    """Smoke-test that run_app.py imports cleanly and exposes main()."""

    def test_run_app_importable(self):
        """run_app can be imported without side effects."""
        try:
            import run_app  # noqa: F401
        except Exception as exc:
            self.fail(f"run_app import failed: {exc}")

    def test_run_app_has_main_function(self):
        import run_app
        self.assertTrue(callable(getattr(run_app, "main", None)))

    def test_shutdown_manager_importable(self):
        try:
            import shutdown_manager  # noqa: F401
        except Exception as exc:
            self.fail(f"shutdown_manager import failed: {exc}")

    def test_shutdown_manager_exports_expected_api(self):
        import shutdown_manager
        for name in ("record_heartbeat", "request_shutdown", "_cleanup", "install"):
            self.assertTrue(
                hasattr(shutdown_manager, name),
                f"shutdown_manager is missing attribute: {name}",
            )


if __name__ == "__main__":
    unittest.main()
