"""Shared Flask extension singletons.

Import extension objects from here rather than from ``app`` to prevent
circular-import errors (blueprints → app → blueprints).

Usage in blueprints::

    from extensions import limiter, mail, cache
"""

from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache

# Uninitialised singletons — call .init_app(app) inside create_app().
csrf = CSRFProtect()
mail = Mail()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()
