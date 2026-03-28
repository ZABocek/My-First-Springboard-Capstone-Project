"""Central configuration module for Cocktail Chronicles.

All environment-specific and sensitive values are loaded here via
python-dotenv so that the rest of the application never reads
``os.environ`` directly for configuration.  Import the constants you
need from this module.

DO NOT commit a ``.env`` file to version control.
See ``.env.example`` for the full list of supported variables and their
safe development defaults.
"""
import os
from dotenv import load_dotenv

# Populate os.environ from .env (silently a no-op when the file is absent,
# e.g. in CI/CD environments that inject variables another way).
load_dotenv()

# ── Core Flask ────────────────────────────────────────────────────────────────
# MUST be a long random string in production.
# Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-key-change-me-in-production')

# Set to True only for local development; NEVER True in production.
FLASK_DEBUG: bool = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# ── Database ──────────────────────────────────────────────────────────────────
# SQLite for local development; set a full PostgreSQL URL in production.
# Heroku-style postgres:// URIs are normalised to postgresql:// in app.py.
DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite:///cocktails.db')

# ── Session / security cookies ────────────────────────────────────────────────
# Enable SECURE_SSL_REDIRECT (and SESSION_COOKIE_SECURE) once the app is
# served over HTTPS.
SECURE_SSL_REDIRECT: bool = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE: bool = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_HTTPONLY: bool = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
SESSION_COOKIE_SAMESITE: str = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

# ── Mail (Flask-Mail) ─────────────────────────────────────────────────────────
# For local development the defaults point at localhost with no auth.
# In production, set MAIL_SERVER, MAIL_USERNAME, and MAIL_PASSWORD via .env.
MAIL_SERVER: str = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT: int = int(os.environ.get('MAIL_PORT', '25'))
MAIL_USE_TLS: bool = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
MAIL_USE_SSL: bool = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
MAIL_USERNAME: str = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD: str = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER: str = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cocktaildb.com')

# ── Admin panel ───────────────────────────────────────────────────────────────
# Keep this private; never commit its real value to version control.
ADMIN_PASSWORD_KEY: str = os.environ.get('ADMIN_PASSWORD_KEY', 'default-admin-key')

# ── External API keys ─────────────────────────────────────────────────────────
# CocktailDB API — "1" is the public free-tier key embedded in the base URL.
# Override with a paid key here if the project upgrades to a premium plan.
COCKTAILDB_API_KEY: str = os.environ.get('COCKTAILDB_API_KEY', '1')

# ── Rate limiting (Flask-Limiter) ─────────────────────────────────────────────
# Set to False in test environments to disable rate limiting.
RATELIMIT_ENABLED: bool = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'