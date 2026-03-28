"""Service layer for all outbound email sending.

Emails are dispatched in background daemon threads so the HTTP request
returns immediately without waiting for the SMTP round-trip.
"""
import logging
import threading

from flask import url_for, current_app
from flask_mail import Message


# ---------------------------------------------------------------------------
# Background-send helpers
# ---------------------------------------------------------------------------

def _deliver(app, msg):
    """Send *msg* inside a fresh app context (runs in a daemon thread)."""
    with app.app_context():
        from extensions import mail as _mail
        try:
            _mail.send(msg)
        except Exception as exc:
            logging.error("Background email send failed: %s", exc)


def _dispatch(msg):
    """Dispatch *msg* to a daemon thread; call from within a request context."""
    app = current_app._get_current_object()  # unwrap proxy before crossing thread boundary
    t = threading.Thread(target=_deliver, args=(app, msg), daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Public send functions — no longer accept a ``mail`` argument
# ---------------------------------------------------------------------------

def send_verification_email(user, token):
    """Send an email-verification message to a newly registered user."""
    from helpers import generate_email_verification_email
    link = url_for('auth.verify_email', token=token, _external=True)
    body = generate_email_verification_email(user.username, link)
    _dispatch(Message(
        subject="Verify Your Email - Cocktail Chronicles",
        recipients=[user.email],
        body=body,
    ))


def send_resend_verification_email(user, token):
    """Re-send an email-verification message to an unverified user."""
    from helpers import generate_email_resend_verification_email
    link = url_for('auth.verify_email', token=token, _external=True)
    body = generate_email_resend_verification_email(user.username, link)
    _dispatch(Message(
        subject="Verify Your Email - Cocktail Chronicles (Resend)",
        recipients=[user.email],
        body=body,
    ))


def send_ban_notification_email(user):
    """Notify a user that their account has been suspended and they may appeal."""
    from helpers import generate_ban_appeal_email
    appeal_link = url_for('users.submit_appeal', _external=True)
    body = generate_ban_appeal_email(user.username, appeal_link)
    _dispatch(Message(
        subject='Account Suspension Notice - Appeal Process Available',
        recipients=[user.email],
        body=body,
    ))


def send_ban_lifted_email(user):
    """Notify a user that their suspension has been lifted."""
    from helpers import generate_ban_lifted_email
    body = generate_ban_lifted_email(user.username)
    _dispatch(Message(
        subject='Your Account Suspension Has Been Lifted',
        recipients=[user.email],
        body=body,
    ))


def send_appeal_rejection_email(user):
    """Notify a user that their ban appeal has been rejected."""
    from helpers import generate_appeal_rejection_email
    body = generate_appeal_rejection_email(user.username)
    _dispatch(Message(
        subject='Your Ban Appeal Has Been Reviewed',
        recipients=[user.email],
        body=body,
    ))
