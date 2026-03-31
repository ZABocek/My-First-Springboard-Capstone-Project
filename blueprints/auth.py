"""Authentication blueprint: register, login, logout, email verification."""
import logging
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, session, flash

from models import db, User
from forms import RegisterForm, LoginForm
from extensions import limiter

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():
    # Skip the registration form for already-authenticated users.
    if "user_id" in session:
        return redirect(url_for('users.homepage'))
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        pwd = form.password.data
        email = form.email.data

        # Enforce unique usernames before persisting anything.
        if User.query.filter_by(username=username).count() > 0:
            flash("Username already taken. Please log in or choose a different name.", "danger")
            return redirect(url_for('auth.login'))

        # Enforce unique email addresses before persisting anything.
        if User.query.filter_by(email=email).count() > 0:
            flash("Email already registered. Please log in or use a different address.", "danger")
            return redirect(url_for('auth.register'))

        # Hash the password and stage the new user record (not yet committed).
        user = User.register(username, email, pwd)
        db.session.add(user)

        try:
            from services.email_service import send_verification_email
            # Generate a signed, time-limited token.  This may raise if
            # SECRET_KEY is missing — catch it before we commit so the
            # session can be cleanly rolled back.
            token = user.generate_email_verification_token()
            # Commit only after the token is successfully generated.
            db.session.commit()
            # Enqueue the verification email as a Celery task.
            # NOTE: actual SMTP delivery is asynchronous — if the Celery
            # worker later fails (e.g. SMTP unreachable), the error is logged
            # but the user row is already committed.  Users can request a
            # resend from the verification-pending page.
            send_verification_email(user, token)
            flash(
                f"Registration successful! A verification email has been sent to {email}. "
                "Please check your inbox.",
                "info",
            )
            # Store the user's ID in the session so that only this browser
            # session can access the verification-pending page and resend.
            session['pending_verification_user_id'] = user.id
            return redirect(url_for('auth.verification_pending', user_id=user.id))
        except Exception as e:
            logging.error(f"Error during registration token generation: {e}")
            # Token generation failed before commit — roll back the staged row
            # so the email address remains free to register again.
            db.session.rollback()
            flash("Error completing registration. Please try again.", "danger")
            return redirect(url_for('auth.register'))

    return render_template("users/register.html", form=form)


@auth_bp.route('/verify-email/<token>')
def verify_email(token):
    try:
        # Decode the signed token; returns None when invalid or past max_age.
        email = User.verify_email_token(token)
        if not email:
            flash("The verification link is invalid or has expired.", "danger")
            return redirect(url_for('auth.login'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash("User not found. Please register again.", "danger")
            return redirect(url_for('auth.register'))

        # Idempotent: clicking the link more than once is harmless.
        if user.is_email_verified:
            flash("Your email is already verified. You can log in.", "info")
            return redirect(url_for('auth.login'))

        # Stamp the verification timestamp and persist.
        user.mark_email_verified()
        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for('auth.login'))

    except Exception as e:
        logging.error(f"Error verifying email: {e}")
        flash("An error occurred while verifying your email. Please try again.", "danger")
        return redirect(url_for('auth.login'))


@auth_bp.route('/verification-pending/<int:user_id>')
def verification_pending(user_id):
    # Only allow the browser that registered (pending session key) or the
    # already-authenticated user to see this page.  Any other visitor would
    # be able to enumerate users and expose their email addresses.
    pending_id = session.get('pending_verification_user_id')
    logged_in_id = session.get('user_id')
    if pending_id != user_id and logged_in_id != user_id:
        flash("You don't have permission to view this page.", "danger")
        return redirect(url_for('auth.login'))
    try:
        user = User.query.get_or_404(user_id)
        return render_template('users/verification_pending.html', user=user)
    except Exception as e:
        logging.error(f"Error loading verification pending page: {e}")
        flash("An error occurred. Please try again.", "danger")
        return redirect(url_for('auth.register'))


@auth_bp.route('/resend-verification/<int:user_id>', methods=['POST'])
@limiter.limit("5 per hour")
def resend_verification(user_id):
    # Only the browser session that registered (or the logged-in owner) may
    # request a resend.  This prevents CSRF-style abuse and enumeration.
    pending_id = session.get('pending_verification_user_id')
    logged_in_id = session.get('user_id')
    if pending_id != user_id and logged_in_id != user_id:
        flash("You don't have permission to do that.", "danger")
        return redirect(url_for('auth.login'))
    try:
        user = User.query.get_or_404(user_id)
        if user.is_email_verified:
            flash("Your email is already verified. You can log in.", "info")
            return redirect(url_for('auth.login'))

        from services.email_service import send_resend_verification_email
        token = user.generate_email_verification_token()
        send_resend_verification_email(user, token)
        flash(f"A new verification email has been sent to {user.email}.", "success")
        return redirect(url_for('auth.verification_pending', user_id=user.id))

    except Exception as e:
        logging.error(f"Error resending verification email: {e}")
        flash("Error sending verification email. Please try again.", "danger")
        return redirect(url_for('auth.verification_pending', user_id=user_id))


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        # Verify credentials via bcrypt check inside User.authenticate.
        user = User.authenticate(form.username.data, form.password.data)
        if user:
            # Block login until the user has confirmed ownership of their email.
            # Redirect to verification_pending (which already shows the resend
            # button) rather than embedding an HTML link in a flash message.
            if not user.is_email_verified:
                flash(
                    "Please verify your email address before logging in.",
                    "warning",
                )
                # Grant this browser session access to verification_pending and
                # resend_verification so the user is not locked out of their own flow.
                session['pending_verification_user_id'] = user.id
                return redirect(url_for('auth.verification_pending', user_id=user.id))

            # Establish the session *before* the ban redirect so the appeals
            # route can read the session and render correctly.
            session["user_id"] = user.id

            # Redirect banned users to the appeal form instead of the homepage.
            if user.is_permanently_banned:
                flash(
                    "Your account has been permanently suspended. "
                    "You may submit an appeal below.",
                    "danger",
                )
                return redirect(url_for('users.submit_appeal'))

            # Temporary bans are also blocked; the expiry date is shown to the user.
            if user.ban_until and user.ban_until > datetime.now(timezone.utc).replace(tzinfo=None):
                flash(
                    f"Your account is suspended until "
                    f"{user.ban_until.strftime('%B %d, %Y')}. "
                    "You may submit an appeal below.",
                    "danger",
                )
                return redirect(url_for('users.submit_appeal'))

            return redirect(url_for('users.homepage'))

        # Keep error messages vague to avoid leaking which field was wrong.
        form.username.errors = ["Bad name/password"]

    return render_template("users/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Remove both identity keys so stale session state cannot authorize access
    # to verification_pending / resend_verification after logout.
    session.pop("user_id", None)
    session.pop("pending_verification_user_id", None)
    return redirect(url_for('auth.login'))
