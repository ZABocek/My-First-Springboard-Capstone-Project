"""Application factory for Cocktail Chronicles.

All route logic has been moved into blueprints under ``blueprints/``.
This module sets up the Flask app, registers extensions, and wires
blueprints together so that ``app`` remains importable for
gunicorn / wsgi callsites and for blueprint modules that need ``mail``.
"""
import os
from datetime import datetime, timezone

from flask import Flask, session, redirect, url_for, flash, request
from models import db, connect_db, User
from config import (
    SECRET_KEY,
    FLASK_DEBUG,
    DATABASE_URL,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SECURE_SSL_REDIRECT,
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USE_SSL,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_DEFAULT_SENDER,
    RATELIMIT_ENABLED,
    REDIS_URL,
    ADMIN_USERNAME,
    ADMIN_EMAIL,
)
from extensions import csrf, mail, migrate, limiter, cache, celery


def _celery_init(app):
    """Wire the global Celery singleton to Flask's app context.

    Tasks decorated with ``@celery.task`` will automatically run inside
    a pushed application context, giving them access to ``current_app``,
    Flask-Mail, SQLAlchemy, etc.
    """
    class _FlaskTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = _FlaskTask
    celery.config_from_object({
        'broker_url': app.config['REDIS_URL'],
        'result_backend': app.config['REDIS_URL'],
        'task_serializer': 'json',
        'result_serializer': 'json',
        'accept_content': ['json'],
    })


def create_app(config_overrides=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # Core configuration
    # ------------------------------------------------------------------ #
    app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['DEBUG'] = FLASK_DEBUG
    # Issue #5: cap upload size to prevent storage abuse / DoS.
    app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 MB

    # Normalise Heroku-style postgres:// URIs.
    db_uri = DATABASE_URL
    if db_uri.startswith('postgres://'):
        db_uri = db_uri.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Only echo SQL in debug mode - avoid log noise in production.
    app.config['SQLALCHEMY_ECHO'] = app.config['DEBUG']

    # ------------------------------------------------------------------ #
    # Session / security
    # ------------------------------------------------------------------ #
    # SESSION_COOKIE_SECURE: send the cookie over HTTPS only (set True in prod).
    # SESSION_COOKIE_HTTPONLY prevents JS access to the session cookie.
    app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY
    app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

    # ------------------------------------------------------------------ #
    # Mail
    # ------------------------------------------------------------------ #
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = MAIL_PORT
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
    app.config['RATELIMIT_ENABLED'] = RATELIMIT_ENABLED
    app.config['REDIS_URL'] = REDIS_URL

    # Allow tests / scripts to override any config key.
    if config_overrides:
        app.config.update(config_overrides)

    # ------------------------------------------------------------------ #
    # Extensions
    # ------------------------------------------------------------------ #
    connect_db(app)
    csrf.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    # RedisCache is shared across all worker processes (unlike SimpleCache).
    cache.init_app(app, config={
        'CACHE_TYPE': 'RedisCache',
        'CACHE_DEFAULT_TIMEOUT': 600,
        'CACHE_REDIS_URL': app.config['REDIS_URL'],
    })
    _celery_init(app)

    if app.config['DEBUG']:
        from flask_debugtoolbar import DebugToolbarExtension
        DebugToolbarExtension(app)

    # ------------------------------------------------------------------ #
    # Blueprints
    # ------------------------------------------------------------------ #
    from blueprints.auth import auth_bp
    from blueprints.cocktails import cocktails_bp
    from blueprints.admin import admin_bp
    from blueprints.users import users_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(cocktails_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_bp)

    # ------------------------------------------------------------------ #
    # Issue #3: Ban enforcement — block banned users on every request,
    # not only at login time.
    # ------------------------------------------------------------------ #
    # Endpoints that banned users must still be able to reach.
    _BAN_EXEMPT = {
        'auth.login', 'auth.logout', 'auth.register',
        'auth.verify_email', 'auth.verification_pending',
        'auth.resend_verification', 'users.submit_appeal',
        'users.appeal_status',
        'static',
    }

    @app.before_request
    def redirect_to_https():
        """Redirect HTTP to HTTPS when SECURE_SSL_REDIRECT is enabled in config."""
        if SECURE_SSL_REDIRECT and not request.is_secure:
            url = request.url.replace('http://', 'https://', 1)
            return redirect(url, code=301)

    @app.before_request
    def enforce_ban():
        endpoint = request.endpoint
        if endpoint is None or endpoint in _BAN_EXEMPT:
            return
        user_id = session.get('user_id')
        if not user_id:
            return
        user = db.session.get(User, user_id)
        if not user:
            return
        if user.is_permanently_banned:
            flash(
                "Your account has been permanently suspended. "
                "You may submit an appeal below.",
                "danger",
            )
            return redirect(url_for('users.submit_appeal'))
        if user.ban_until and user.ban_until > datetime.now(timezone.utc).replace(tzinfo=None):
            flash(
                f"Your account is suspended until "
                f"{user.ban_until.strftime('%B %d, %Y')}. "
                "You may submit an appeal below.",
                "danger",
            )
            return redirect(url_for('users.submit_appeal'))

    # ------------------------------------------------------------------ #
    # Security response headers
    # ------------------------------------------------------------------ #
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        # Content-Security-Policy: restrict resource origins to trusted CDNs only.
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://code.jquery.com https://cdn.jsdelivr.net "
            "https://stackpath.bootstrapcdn.com; "
            "style-src 'self' https://cdn.jsdelivr.net https://stackpath.bootstrapcdn.com "
            "https://cdnjs.cloudflare.com 'unsafe-inline'; "
            "font-src 'self' https://cdnjs.cloudflare.com "
            "https://stackpath.bootstrapcdn.com; "
            "img-src 'self' data: https://www.thecocktaildb.com;"
        )
        response.headers['Content-Security-Policy'] = csp
        return response

    # ------------------------------------------------------------------ #
    # Browser watchdog API endpoints
    #
    # These two endpoints support graceful local-development shutdown:
    #   POST /api/heartbeat  — browser pings every ~10 s to signal life.
    #   POST /api/shutdown   — browser sends a beacon on tab close.
    #
    # Both endpoints are:
    #   • Always registered (so tests can reach them unconditionally).
    #   • Restricted to localhost (127.0.0.1 / ::1) for safety.
    #   • Exempt from CSRF — neither endpoint modifies application state
    #     or returns sensitive data; they only update an in-process timer
    #     or schedule a clean process exit.
    # ------------------------------------------------------------------ #
    from flask import abort as _abort  # noqa: PLC0415 (local import to avoid shadow)

    @app.route('/api/heartbeat', methods=['POST'])
    def _heartbeat():
        """Browser pings this every 10 s to signal the tab is still open.

        Restricted to localhost. CSRF-exempt (timer reset only; no DB writes).
        """
        if request.remote_addr not in ('127.0.0.1', '::1'):
            _abort(403)
        import shutdown_manager  # noqa: PLC0415
        shutdown_manager.record_heartbeat()
        return '', 204

    @app.route('/api/shutdown', methods=['POST'])
    def _shutdown():
        """Browser sends a beacon here on beforeunload (tab/window close).

        Restricted to localhost. Triggers a graceful server shutdown only when
        BROWSER_WATCHDOG=true is set in the environment (i.e. when launched via
        start_app.bat). In all other modes it returns 204 as a safe no-op so
        that the base template's JS snippet does not cause unexpected shutdowns
        during normal development with ``flask run``.
        """
        if request.remote_addr not in ('127.0.0.1', '::1'):
            _abort(403)
        if os.environ.get('BROWSER_WATCHDOG', 'false').lower() == 'true':
            import threading  # noqa: PLC0415
            import shutdown_manager  # noqa: PLC0415
            # Defer to let the HTTP response be delivered before the process exits.
            timer = threading.Timer(0.5, shutdown_manager.request_shutdown)
            timer.daemon = True
            timer.start()
        return '', 204

    # Exempt both internal system endpoints from CSRF protection.
    csrf.exempt(_heartbeat)
    csrf.exempt(_shutdown)

    # ------------------------------------------------------------------ #
    # Template context: inject browser_watchdog flag so base.html can
    # conditionally include the heartbeat JavaScript snippet.
    # ------------------------------------------------------------------ #
    @app.context_processor
    def _inject_watchdog_flag():
        return {
            'browser_watchdog': (
                os.environ.get('BROWSER_WATCHDOG', 'false').lower() == 'true'
            )
        }

    return app


# Module-level ``app`` so existing gunicorn / run_app.py callsites work
# without modification.
app = create_app()
