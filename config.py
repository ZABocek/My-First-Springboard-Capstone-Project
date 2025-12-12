import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Secret key for Flask session management and CSRF protection
# In production, load this from environment variables
# For development, use a fixed key so CSRF tokens work consistently
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-springboard-cocktail-app-2025')

# Admin password key for accessing the admin panel
# This key should be stored in .env file and never committed to GitHub
ADMIN_PASSWORD_KEY = os.environ.get('ADMIN_PASSWORD_KEY', 'default-admin-key')

# Database URL
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///cocktails.db')

# Security settings
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_HTTPONLY = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

# Rate limiting
RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'True').lower() == 'true'
# Email configuration for Flask-Mail
# For development, uses file:// protocol to save emails to files
# For production, configure with actual SMTP server
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 25))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@cocktaildb.com')