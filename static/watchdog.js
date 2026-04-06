/**
 * Browser-watchdog heartbeat script.
 *
 * Pings /api/heartbeat every 10 seconds so the server knows a browser
 * tab is still open.  This script is only included when the Flask server
 * is started with BROWSER_WATCHDOG=true (i.e. via start_app.bat).
 *
 * NOTE: We intentionally do NOT hook beforeunload to call /api/shutdown.
 * That approach fired on every in-app form submission and link click,
 * shutting the server down mid-request.  Instead, the server-side watchdog
 * thread detects genuine tab closure through missed heartbeats: after
 * WATCHDOG_TIMEOUT seconds (default 30) without a ping the server exits
 * cleanly.
 */
(function () {
    'use strict';

    var HEARTBEAT_INTERVAL_MS = 10000;  /* 10 seconds */

    /**
     * Notify the server that this tab is still alive.
     * Uses keepalive:true so the request completes even when the page is
     * in the process of unloading between in-app navigations.
     */
    function ping() {
        fetch('/api/heartbeat', {
            method: 'POST',
            keepalive: true
        }).catch(function () {
            /* Server may already be shutting down — silently ignore. */
        });
    }

    /* Send the first heartbeat immediately, then repeat every 10 s. */
    ping();
    setInterval(ping, HEARTBEAT_INTERVAL_MS);
}());
