"""Celery worker entry point for Cocktail Chronicles.

Creates the Flask app (which configures the Celery broker, result backend,
and FlaskTask base class) and then imports all task modules so the worker
discovers every task before it begins consuming queue messages.

Start a worker:
    celery -A celery_worker worker --loglevel=info

Run scheduled/periodic tasks (optional):
    celery -A celery_worker beat --loglevel=info
"""
from app import create_app

# Spin up the Flask app; this call runs _celery_init(), which:
#   • Sets the broker/result-backend URLs on the global Celery instance.
#   • Replaces celery.Task with _FlaskTask so every task body executes
#     inside a pushed application context automatically.
flask_app = create_app()

# Import task modules *after* create_app() so the _FlaskTask base class
# is already in place when @celery.task decorators are evaluated.
import services.email_service  # noqa: F401 — registers email tasks

# Re-export the configured Celery instance so that
# ``celery -A celery_worker`` can locate it.
from extensions import celery  # noqa: F401
