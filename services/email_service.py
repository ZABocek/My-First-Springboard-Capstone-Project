"""Service layer for all outbound email sending.

Email messages are serialised as JSON and dispatched to a Celery worker
so the HTTP request returns immediately without waiting for the SMTP
round-trip.  The worker runs under a pushed Flask application context
(configured in ``app._celery_init``), giving it full access to
Flask-Mail and the rest of the app.
"""
import logging

from flask import url_for
from flask_mail import Message

from extensions import celery


# ---------------------------------------------------------------------------
# Celery task — runs in a worker process under the Flask app context
# ---------------------------------------------------------------------------

@celery.task(name='email_service.deliver', ignore_result=True)
def _deliver(subject, recipients, body, html=None):
    """Send a plain-text (and optionally HTML) email via Flask-Mail.

    All arguments are plain JSON-serialisable types so the task is
    compatible with Celery's default JSON serialiser.  When *html* is
    provided the message is sent as multipart/alternative so email
    clients that support HTML will render the anchor tag instead of the
    raw URL, preventing quoted-printable line-wrapping from breaking the
    verification link.
    """
    from extensions import mail
    try:
        mail.send(Message(subject=subject, recipients=recipients, body=body, html=html))
    except Exception as exc:
        logging.error("Celery email delivery failed: %s", exc)
        raise  # propagate so Celery marks the task as FAILURE


# ---------------------------------------------------------------------------
# Public send functions — called from request context; enqueue the task
# ---------------------------------------------------------------------------

def send_verification_email(user, token):
    """Queue an email-verification message for a newly registered user."""
    from helpers import generate_email_verification_email, generate_email_verification_html
    link = url_for('auth.verify_email', token=token, _external=True)
    body = generate_email_verification_email(user.username, link)
    html = generate_email_verification_html(user.username, link)
    _deliver.delay(
        subject="Verify Your Email - Cocktail Chronicles",
        recipients=[user.email],
        body=body,
        html=html,
    )


def send_resend_verification_email(user, token):
    """Queue a re-send of the email-verification message."""
    from helpers import generate_email_resend_verification_email, generate_email_verification_html
    link = url_for('auth.verify_email', token=token, _external=True)
    body = generate_email_resend_verification_email(user.username, link)
    html = generate_email_verification_html(user.username, link)
    _deliver.delay(
        subject="Verify Your Email - Cocktail Chronicles (Resend)",
        recipients=[user.email],
        body=body,
        html=html,
    )


def send_ban_notification_email(user):
    """Queue a suspension notice with an appeal link."""
    from helpers import generate_ban_appeal_email
    appeal_link = url_for('users.submit_appeal', _external=True)
    body = generate_ban_appeal_email(user.username, appeal_link)
    _deliver.delay(
        subject='Account Suspension Notice - Appeal Process Available',
        recipients=[user.email],
        body=body,
    )


def send_ban_lifted_email(user):
    """Queue a notification that the user's suspension has been lifted."""
    from helpers import generate_ban_lifted_email
    body = generate_ban_lifted_email(user.username)
    _deliver.delay(
        subject='Your Account Suspension Has Been Lifted',
        recipients=[user.email],
        body=body,
    )


def send_appeal_rejection_email(user):
    """Queue a notification that the user's ban appeal was rejected."""
    from helpers import generate_appeal_rejection_email
    body = generate_appeal_rejection_email(user.username)
    _deliver.delay(
        subject='Your Ban Appeal Has Been Reviewed',
        recipients=[user.email],
        body=body,
    )
