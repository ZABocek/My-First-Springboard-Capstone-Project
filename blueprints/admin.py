"""Admin blueprint: panel, user management, messaging, ban appeals."""
import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, session, flash, request

from models import db, User, Cocktail, AdminMessage, UserAppeal, AdminAuditLog
from forms import AdminForm, AdminMessageForm
from decorators import admin_required
from extensions import limiter

admin_bp = Blueprint('admin', __name__)


# ---------------------------------------------------------------------------
# Issue #9: Centralised audit-log helper.
# ---------------------------------------------------------------------------
def _log_admin_action(action: str, target_user_id: int = None, details: str = None) -> None:
    """Append an audit-log entry for the currently-acting admin.

    Called *before* ``db.session.commit()`` so the log entry is written
    atomically with the action it records.
    """
    admin_id = session.get("user_id")
    if not admin_id:
        return
    try:
        db.session.add(AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            details=details,
        ))
    except Exception as exc:
        logging.error(f"Failed to queue audit log entry: {exc}")


def _guard_self_action(user_id: int, verb: str) -> bool:
    """Flash a warning and return True when the admin tries to act on themselves."""
    # Prevent admins from locking themselves out or accidentally modifying their own account.
    if user_id == session.get("user_id"):
        flash(f"You cannot {verb} yourself.", "warning")
        return True
    return False


# ---------------------------------------------------------------------------
# Issue #7: Rate-limit the unlock endpoint to deter brute-force key guessing.
# Issue #8: Require login before the page is shown (not just after POST).
# ---------------------------------------------------------------------------
@admin_bp.route("/admin/unlock", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def admin_unlock():
    # Issue #8: Consistent protection — require login for both GET and POST.
    if "user_id" not in session:
        flash("You must be logged in to access the admin panel.", "warning")
        return redirect(url_for('auth.login'))

    # Redirect already-authenticated admins straight to the panel.
    user = User.query.get(session["user_id"])
    if user and user.is_admin:
        return redirect(url_for('admin.admin_panel'))

    form = AdminForm()
    if form.validate_on_submit():
        from config import ADMIN_PASSWORD_KEY
        if form.admin_key.data == ADMIN_PASSWORD_KEY:
            if user:
                user.is_admin = True
                _log_admin_action("self_promote_admin", target_user_id=user.id,
                                  details="Admin unlock key accepted")
                db.session.commit()
                flash("Admin access granted!", "success")
                return redirect(url_for('admin.admin_panel'))
            flash("You must be logged in to access the admin panel.", "danger")
        else:
            _log_admin_action("failed_admin_unlock_attempt", target_user_id=None,
                              details="Invalid admin key submitted")
            db.session.commit()
            flash("Invalid admin password key.", "danger")

    return render_template("admin/unlock.html", form=form)


@admin_bp.route("/admin/panel")
@admin_required
def admin_panel():
    # Gather high-level counts for the dashboard summary cards.
    stats = {
        'total_users': User.query.count(),
        'total_cocktails': Cocktail.query.count(),
        'total_api_cocktails': Cocktail.query.filter_by(is_api_cocktail=True).count(),
        'total_user_cocktails': Cocktail.query.filter_by(is_api_cocktail=False).count(),
    }
    users = User.query.all()
    # Surface only unresolved appeals so the admin can action them promptly.
    appeals = UserAppeal.query.filter_by(status='pending').all()
    return render_template(
        "admin/panel.html",
        stats=stats,
        users=users,
        appeals=appeals,
        now=datetime.utcnow(),
    )


@admin_bp.route("/admin/user/<int:user_id>/promote", methods=["POST"])
@admin_required
def promote_user(user_id):
    if _guard_self_action(user_id, "promote"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    user.is_admin = True
    _log_admin_action("promote_user", target_user_id=user_id,
                      details=f"Promoted {user.username} to admin")
    db.session.commit()
    flash(f"User {user.username} promoted to admin.", "success")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/user/<int:user_id>/demote", methods=["POST"])
@admin_required
def demote_user(user_id):
    if _guard_self_action(user_id, "demote"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    user.is_admin = False
    _log_admin_action("demote_user", target_user_id=user_id,
                      details=f"Demoted {user.username} from admin")
    db.session.commit()
    flash(f"User {user.username} demoted from admin.", "success")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/user/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    if _guard_self_action(user_id, "ban"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    # Set a rolling 365-day expiry from the moment the ban is applied.
    user.ban_until = datetime.utcnow() + timedelta(days=365)
    _log_admin_action("ban_user_1yr", target_user_id=user_id,
                      details=f"Banned {user.username} for one year")
    db.session.commit()
    try:
        from services.email_service import send_ban_notification_email
        # Notify the user and include the appeal link in the email body.
        send_ban_notification_email(user)
    except Exception as e:
        logging.error(f"Error sending ban notification email: {e}")
    flash(f"User {user.username} has been banned for one year.", "warning")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/user/<int:user_id>/ban-permanent", methods=["POST"])
@admin_required
def ban_user_permanently(user_id):
    if _guard_self_action(user_id, "permanently ban"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    # Flag takes precedence over ban_until; checked independently at login.
    user.is_permanently_banned = True
    _log_admin_action("ban_user_permanent", target_user_id=user_id,
                      details=f"Permanently banned {user.username}")
    db.session.commit()
    try:
        from services.email_service import send_ban_notification_email
        send_ban_notification_email(user)
    except Exception as e:
        logging.error(f"Error sending permanent ban notification email: {e}")
    flash(f"User {user.username} has been permanently banned.", "danger")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    if _guard_self_action(user_id, "delete"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    username = user.username
    _log_admin_action("delete_user", target_user_id=user_id,
                      details=f"Deleted user {username}")
    # Cascade delete removes messages, appeals, and cocktail links tied to this user.
    db.session.delete(user)
    db.session.commit()
    flash(f"User {username} has been deleted from the system.", "success")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/messages")
@admin_required
def admin_messages():
    messages = AdminMessage.query.order_by(AdminMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)


@admin_bp.route("/admin/message/<int:message_id>/respond", methods=["GET", "POST"])
@admin_required
def respond_to_message(message_id):
    message = AdminMessage.query.get_or_404(message_id)
    form = AdminMessageForm()
    if form.validate_on_submit():
        # Attach the admin's reply and timestamp it.
        message.admin_response = form.message.data
        message.admin_response_date = datetime.utcnow()
        message.is_read = True
        db.session.commit()
        flash("Response saved.", "success")
        return redirect(url_for('admin.admin_messages'))
    # Mark the message as read as soon as an admin opens it.
    message.is_read = True
    db.session.commit()
    return render_template("admin/respond_message.html", message=message, form=form)


@admin_bp.route("/admin/appeal/<int:appeal_id>/approve", methods=["POST"])
@admin_required
def approve_appeal(appeal_id):
    appeal = UserAppeal.query.get_or_404(appeal_id)
    if appeal.status != 'pending':
        flash("This appeal has already been decided.", "warning")
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(appeal.user_id)
    # Clear both ban fields so the user can log in normally again.
    user.ban_until = None
    user.is_permanently_banned = False
    appeal.status = 'approved'
    appeal.admin_response = request.form.get('admin_response', '').strip() or None
    appeal.admin_response_date = datetime.utcnow()
    _log_admin_action("approve_appeal", target_user_id=user.id,
                      details=f"Approved appeal #{appeal_id} for {user.username}")
    db.session.commit()
    try:
        from services.email_service import send_ban_lifted_email
        # Let the user know their appeal was successful.
        send_ban_lifted_email(user)
    except Exception as e:
        logging.error(f"Error sending ban lifted email: {e}")
    flash(f"Appeal approved. Ban lifted for user {user.username}.", "success")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/appeal/<int:appeal_id>/reject", methods=["POST"])
@admin_required
def reject_appeal(appeal_id):
    appeal = UserAppeal.query.get_or_404(appeal_id)
    if appeal.status != 'pending':
        flash("This appeal has already been decided.", "warning")
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(appeal.user_id)
    appeal.status = 'rejected'
    appeal.admin_response = request.form.get('admin_response', '').strip() or None
    appeal.admin_response_date = datetime.utcnow()
    _log_admin_action("reject_appeal", target_user_id=appeal.user_id,
                      details=f"Rejected appeal #{appeal_id}")
    db.session.commit()
    try:
        from services.email_service import send_appeal_rejection_email
        send_appeal_rejection_email(user)
    except Exception as e:
        logging.error(f"Error sending appeal rejection email: {e}")
    flash("Appeal rejected.", "warning")
    return redirect(url_for('admin.admin_panel'))


@admin_bp.route("/admin/user/<int:user_id>/remove-ban", methods=["POST"])
@admin_required
def remove_user_ban(user_id):
    if _guard_self_action(user_id, "remove ban from"):
        return redirect(url_for('admin.admin_panel'))
    user = User.query.get_or_404(user_id)
    # Clear both the expiry date and the permanent flag in a single operation.
    user.ban_until = None
    user.is_permanently_banned = False
    _log_admin_action("remove_ban", target_user_id=user_id,
                      details=f"Lifted ban for {user.username}")
    db.session.commit()
    try:
        from services.email_service import send_ban_lifted_email
        send_ban_lifted_email(user)
    except Exception as e:
        logging.error(f"Error sending ban lifted email: {e}")
    flash(f"Ban lifted for user {user.username}.", "success")
    return redirect(url_for('admin.admin_panel'))
