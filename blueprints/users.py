"""Users blueprint: homepage, profile, messaging, ban appeals."""
import asyncio
import logging
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, session, flash, request

from models import db, User, Ingredient, UserFavoriteIngredients, AdminMessage, UserAppeal
from forms import PreferenceForm, UserFavoriteIngredientForm, UserMessageForm, AppealForm
from decorators import login_required
from cocktaildb_api import list_ingredients

users_bp = Blueprint('users', __name__)


@users_bp.route("/")
def homepage():
    # Redirect unauthenticated visitors straight to registration.
    if "user_id" in session:
        return render_template("index.html")
    return redirect(url_for('auth.register'))


@users_bp.route('/users/profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def profile(user_id):
    current_user_id = session['user_id']
    # Allow admins to view and edit any profile; regular users may only touch their own.
    if current_user_id != user_id:
        current_user_obj = User.query.get(current_user_id)
        if not current_user_obj or not current_user_obj.is_admin:
            flash('You do not have permission to edit this profile.', 'danger')
            return redirect(url_for('users.homepage'))

    user = User.query.get_or_404(user_id)
    preference_form = PreferenceForm()
    ingredient_form = UserFavoriteIngredientForm()

    ingredients_from_api = asyncio.run(list_ingredients())
    if ingredients_from_api:
        ingredient_form.ingredient.choices = [
            (i['strIngredient1'], i['strIngredient1'])
            for i in ingredients_from_api.get('drinks', [])
        ]
    else:
        logging.error("Failed to retrieve ingredients from API")

    if request.method == 'POST':
        submit_button = request.form.get('submit_button')

        if submit_button == 'Save Preference' and preference_form.validate():
            try:
                # Persist the new drink-type preference directly on the user row.
                user.preference = preference_form.preference.data
                db.session.commit()
                flash('Preference updated successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                logging.error(f"Failed to update preference: {e}")
                flash('Failed to update preference!', 'danger')

        elif submit_button == 'Add Ingredient' and ingredient_form.validate():
            ingredient_name = ingredient_form.ingredient.data
            ingredient = Ingredient.query.filter_by(name=ingredient_name).first()
            if not ingredient:
                # Create the ingredient row and flush so its PK is available
                # before the UserFavoriteIngredients FK row is built.
                ingredient = Ingredient(name=ingredient_name)
                db.session.add(ingredient)
                db.session.flush()

            # Prevent adding the same ingredient twice to the favourites list.
            existing = UserFavoriteIngredients.query.filter_by(
                user_id=user.id, ingredient_id=ingredient.id
            ).first()
            if existing:
                flash('Ingredient already added!', 'warning')
            else:
                try:
                    db.session.add(
                        UserFavoriteIngredients(user_id=user.id, ingredient_id=ingredient.id)
                    )
                    db.session.commit()
                    flash('Ingredient added successfully!', 'success')
                except Exception as e:
                    db.session.rollback()
                    logging.error(f"Failed to add ingredient: {e}")
                    flash('Failed to add ingredient!', 'danger')

    user_favorite_ingredients = [
        (i.ingredient.id, i.ingredient.name) for i in user.user_favorite_ingredients
    ]
    return render_template(
        '/users/profile.html',
        user=user,
        preference_form=preference_form,
        ingredient_form=ingredient_form,
        user_favorite_ingredients=user_favorite_ingredients,
    )


@users_bp.route('/delete-favorite-ingredient/<int:user_id>/<int:ingredient_id>', methods=['POST'])
def delete_favorite_ingredient(user_id, ingredient_id):
    # Restrict deletion to the owning user only (no admin exception needed here).
    if 'user_id' not in session or session.get('user_id') != user_id:
        flash('You do not have permission to delete this ingredient.', 'danger')
        return redirect(url_for('users.profile', user_id=user_id))
    try:
        favorite = UserFavoriteIngredients.query.filter_by(
            user_id=user_id, ingredient_id=ingredient_id
        ).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            flash('Ingredient deleted successfully!', 'success')
        else:
            flash('Ingredient not found.', 'danger')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to delete favorite ingredient: {e}")
        flash('Failed to delete ingredient!', 'danger')

    return redirect(url_for('users.profile', user_id=user_id))


@users_bp.route("/user/messages")
@login_required
def user_messages():
    user_id = session.get("user_id")
    # Retrieve the user's message thread, newest first.
    messages = (
        AdminMessage.query
        .filter_by(user_id=user_id)
        .order_by(AdminMessage.created_at.desc())
        .all()
    )
    return render_template("user_messages.html", messages=messages)


@users_bp.route("/user/send-message", methods=["GET", "POST"])
@login_required
def send_user_message():
    form = UserMessageForm()
    if form.validate_on_submit():
        db.session.add(
            AdminMessage(
                user_id=session["user_id"],
                subject=form.subject.data,
                message=form.message.data,
                message_type=form.message_type.data,
            )
        )
        db.session.commit()
        flash("Your message has been sent to the admin.", "success")
        return redirect(url_for('users.user_messages'))
    return render_template("send_user_message.html", form=form)


@users_bp.route("/appeal/status")
def appeal_status():
    """Stable landing page for banned users after they submit or already have a pending appeal.

    This endpoint is in _BAN_EXEMPT so banned users are not bounced back to
    /appeal in an infinite redirect loop.
    """
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get_or_404(user_id)
    pending_appeal = UserAppeal.query.filter_by(user_id=user_id, status='pending').first()
    return render_template("users/appeal_status.html", user=user, pending_appeal=pending_appeal)


@users_bp.route("/appeal", methods=["GET", "POST"])
def submit_appeal():
    user_id = session.get("user_id")
    if not user_id:
        flash("You must be logged in to submit an appeal.", "warning")
        return redirect(url_for('auth.login'))

    user = User.query.get_or_404(user_id)

    # Only currently-banned users may access the appeal form.
    if not (user.is_permanently_banned or
            (user.ban_until and user.ban_until > datetime.utcnow())):
        flash("Your account is not currently banned.", "info")
        return redirect(url_for('users.homepage'))

    # Block duplicate submissions; one pending appeal per user at a time.
    existing_appeal = UserAppeal.query.filter_by(
        user_id=user_id, status='pending'
    ).first()
    if existing_appeal:
        flash("You already have a pending appeal. Please wait for a response.", "info")
        # Redirect to the ban-exempt status page so banned users do not loop
        # back through enforce_ban() -> submit_appeal() -> here indefinitely.
        return redirect(url_for('users.appeal_status'))

    form = AppealForm()
    if form.validate_on_submit():
        # Store the appeal with a 'pending' status for admin review.
        db.session.add(
            UserAppeal(user_id=user_id, appeal_text=form.appeal_text.data, status='pending')
        )
        db.session.commit()
        flash(
            "Your appeal has been submitted. Our admin team will review it shortly.",
            "success",
        )
        # Redirect to the ban-exempt status page to avoid a redirect loop for
        # still-banned users (enforce_ban would send them straight back here).
        return redirect(url_for('users.appeal_status'))

    return render_template("users/appeal.html", form=form, user=user)
