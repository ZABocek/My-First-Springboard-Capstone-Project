"""Cocktail blueprint: browse, add, edit, delete cocktails."""
import asyncio
import logging
import os

from flask import (
    Blueprint, render_template, redirect, url_for,
    session, flash, request, send_from_directory, current_app,
)

from models import db, User, Cocktail, Cocktails_Users, Cocktails_Ingredients, Ingredient
from forms import OriginalCocktailForm, EditCocktailForm, ListCocktailsForm, IngredientForm
from services.cocktail_service import (
    process_and_store_new_cocktail,
    save_uploaded_image,
    delete_uploaded_image,
    get_cocktail_image_url,
    store_or_get_ingredient,
)
from cocktaildb_api import get_cocktail_detail, get_combined_cocktails_list
from decorators import login_required
from extensions import cache

cocktails_bp = Blueprint('cocktails', __name__)


@cache.cached(timeout=600, key_prefix='all_cocktails')
def _cached_cocktail_list():
    """Fetch the full API catalogue once; cache for 10 minutes (RedisCache)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(get_combined_cocktails_list())
    finally:
        loop.close()


@cocktails_bp.route('/cocktails', methods=['GET', 'POST'])
def list_cocktails():
    form = ListCocktailsForm()
    try:
        cocktails = _cached_cocktail_list()

        if not cocktails:
            flash('No cocktails found!', 'warning')
        else:
            # Populate the select widget with (id, name) pairs from the API.
            form.cocktail.choices = [(c[0], c[1]) for c in cocktails]

        if form.validate_on_submit():
            return redirect(
                url_for('cocktails.cocktail_details', cocktail_id=form.cocktail.data)
            )
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve cocktails: {e}")
        flash('Failed to retrieve cocktails list. Please try again later.', 'danger')
        cocktails = []

    return render_template('list_cocktails.html', form=form, cocktails=cocktails)


@cocktails_bp.route('/cocktail/<int:cocktail_id>')
def cocktail_details(cocktail_id):
    try:
        cocktail = get_cocktail_detail(cocktail_id)
        if not cocktail:
            flash('Cocktail details not found!', 'warning')
            return redirect(url_for('cocktails.list_cocktails'))
    except Exception as e:
        current_app.logger.error(f"Failed to retrieve cocktail details: {e}")
        flash('Failed to retrieve cocktail details. Please try again later.', 'danger')
        return redirect(url_for('cocktails.list_cocktails'))

    return render_template(
        'cocktail_details.html', cocktail=cocktail, user_id=session.get("user_id")
    )


@cocktails_bp.route('/add_api_cocktails', methods=['GET', 'POST'])
@login_required
def add_api_cocktails():
    form = ListCocktailsForm()
    user_id = session['user_id']

    try:
        cocktails = _cached_cocktail_list()
    except Exception as e:
        current_app.logger.error(f"Error fetching cocktails: {e}")
        cocktails = None

    if cocktails:
        form.cocktail.choices = [(c[0], c[1]) for c in cocktails]
    else:
        flash('Failed to retrieve cocktails. Please try again.', 'danger')
        return render_template('add_api_cocktails.html', form=form)

    if form.validate_on_submit():
        # Fetch full detail (ingredients, instructions) for the chosen cocktail.
        cocktail_detail = get_cocktail_detail(form.cocktail.data)
        if cocktail_detail:
            try:
                # Delegate storage to the service layer, which handles deduplication
                # (shared API rows) and emits a single commit.
                newly_added = process_and_store_new_cocktail(cocktail_detail, user_id)
                if newly_added:
                    flash(f"Added {cocktail_detail['strDrink']} to your cocktails!", 'success')
                else:
                    flash(f"{cocktail_detail['strDrink']} is already in your profile.", 'info')
            except Exception as e:
                current_app.logger.error(f"Failed to store cocktail: {e}")
                flash('Failed to save the selected cocktail. Please try again.', 'danger')
            return redirect(url_for('cocktails.my_cocktails'))
        flash('Failed to retrieve the selected cocktail.', 'danger')

    return render_template('add_api_cocktails.html', form=form)


@cocktails_bp.route('/my-cocktails')
@login_required
def my_cocktails():
    user_id = session.get('user_id')

    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))

    cocktail_details = []
    for relation in user.cocktails_relation:
        cocktail = relation.cocktails
        ingredients = [
            {'ingredient': ci.ingredient.name, 'measure': ci.quantity}
            for ci in cocktail.ingredients_relation
        ]
        cocktail_details.append({
            'id': cocktail.id,
            'name': cocktail.name,
            'instructions': cocktail.instructions,
            'ingredients': ingredients,
            # Resolve image URL once via the service helper (prefers image_url,
            # falls back to strDrinkThumb, returns None when neither is set).
            'image_url': get_cocktail_image_url(cocktail),
        })

    cocktail_details.sort(key=lambda x: x['name'])
    return render_template('my_cocktails.html', cocktails=cocktail_details)


@cocktails_bp.route('/delete-cocktail/<int:cocktail_id>', methods=['POST'])
@login_required
def delete_cocktail(cocktail_id):
    user_id = session.get('user_id')

    user = db.session.get(User, user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.login'))

    cocktail = db.session.get(Cocktail, cocktail_id)
    if not cocktail:
        flash('Cocktail not found.', 'danger')
        return redirect(url_for('cocktails.my_cocktails'))

    # Confirm the requesting user actually owns this cocktail before deleting.
    user_cocktail_ids = {r.cocktail_id for r in user.cocktails_relation}
    if cocktail_id not in user_cocktail_ids:
        flash('You do not have permission to delete this cocktail.', 'danger')
        return redirect(url_for('cocktails.my_cocktails'))

    try:
        rel = Cocktails_Users.query.filter_by(
            user_id=user_id, cocktail_id=cocktail_id
        ).first()
        if rel:
            # Capture image filename before any deletions so we can clean up the
            # file from disk after the row is gone.
            old_image = cocktail.image_url if not cocktail.is_api_cocktail else None

            db.session.delete(rel)
            # Flush so the count below reflects the deletion already staged.
            db.session.flush()
            # Remove the cocktail row itself when no other user references it
            # (orphan cleanup).  This applies to both user-created and API
            # cocktails — the latter can also become unreferenced over time.
            remaining = Cocktails_Users.query.filter_by(cocktail_id=cocktail_id).count()
            if remaining == 0:
                db.session.delete(cocktail)
            db.session.commit()
            # Delete the uploaded image file from disk only after the DB commit
            # succeeds, and only for user-created cocktails (API records do not
            # store a local file).
            if old_image:
                delete_uploaded_image(old_image)
            flash('Cocktail deleted successfully!', 'success')
        else:
            flash('Cocktail not found in your collection.', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting cocktail: {e}")
        flash('Failed to delete cocktail. Please try again.', 'danger')

    return redirect(url_for('cocktails.my_cocktails'))


@cocktails_bp.route('/add-original-cocktails', methods=['GET', 'POST'])
@login_required
def add_original_cocktails():

    form = OriginalCocktailForm()
    if form.validate_on_submit():
        # Reject partial rows (ingredient without measure, or vice versa).
        partial_errors = [
            i + 1
            for i, (ing, meas) in enumerate(zip(form.ingredients.data, form.measures.data))
            if bool((ing or '').strip()) != bool((meas or '').strip())
        ]
        if partial_errors:
            for row_num in partial_errors:
                flash(
                    f'Row {row_num}: both the ingredient and its measure must be '
                    f'filled in together, or both left empty.',
                    'danger',
                )
            return render_template('add_original_cocktails.html', form=form)

        # Discard fully-blank rows; keep only pairs where both fields are filled.
        filtered = [
            (i.strip(), m.strip())
            for i, m in zip(form.ingredients.data, form.measures.data)
            if (i or '').strip() and (m or '').strip()
        ]

        if not filtered:
            flash('Please add at least one ingredient with a measurement.', 'danger')
            return render_template('add_original_cocktails.html', form=form)

        # owner_id ties this cocktail to the creating user for ownership queries.
        new_cocktail = Cocktail(
            name=form.name.data,
            instructions=form.instructions.data,
            is_api_cocktail=False,
            owner_id=session['user_id'],
        )
        db.session.add(new_cocktail)
        # Flush to obtain new_cocktail.id before building FK rows.
        db.session.flush()

        # Link the new cocktail to the current user in the join table.
        db.session.add(
            Cocktails_Users(user_id=session['user_id'], cocktail_id=new_cocktail.id)
        )

        for ingredient_name, measure in filtered:
            ingredient = store_or_get_ingredient(ingredient_name)
            # Flush each ingredient so its PK is ready for the association row.
            db.session.flush()
            db.session.add(
                Cocktails_Ingredients(
                    cocktail_id=new_cocktail.id,
                    ingredient_id=ingredient.id,
                    quantity=measure,
                )
            )

        # Track saved upload path so we can clean it up if the DB commit fails.
        filename = None
        try:
            # Validate extension and magic bytes before saving to disk.
            filename = save_uploaded_image(form.image.data)
            if filename:
                new_cocktail.image_url = filename
        except ValueError as e:
            # Invalid image: roll back everything staged in this request and
            # return the form with the error message (do NOT save the cocktail).
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('add_original_cocktails.html', form=form)

        # Single commit covers all the rows prepared above.
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Remove the just-saved upload to avoid orphaning it on disk.
            if filename:
                delete_uploaded_image(filename)
            current_app.logger.error(f"DB commit failed during cocktail creation: {e}")
            flash('Failed to save your cocktail. Please try again.', 'danger')
            return render_template('add_original_cocktails.html', form=form)
        flash('Successfully added your original cocktail!', 'success')
        return redirect(url_for('cocktails.my_cocktails'))

    elif request.method == 'POST':
        current_app.logger.debug(f"Form validation failed: {form.errors}")

    return render_template('add_original_cocktails.html', form=form)


@cocktails_bp.route('/static/uploads/<filename>')
def uploaded_file(filename):
    # Serve user-uploaded images from the configured uploads directory.
    upload_dir = os.path.join(
        current_app.root_path,
        current_app.config['UPLOADED_PHOTOS_DEST'],
    )
    return send_from_directory(upload_dir, filename)


@cocktails_bp.route('/edit-cocktail/<int:cocktail_id>', methods=['GET', 'POST'])
@login_required
def edit_cocktail(cocktail_id):
    user_id = session['user_id']
    original_cocktail = Cocktail.query.get_or_404(cocktail_id)

    ownership = Cocktails_Users.query.filter_by(
        user_id=user_id, cocktail_id=cocktail_id
    ).first()
    if not ownership:
        flash('You do not have permission to edit this cocktail.', 'danger')
        return redirect(url_for('cocktails.my_cocktails'))

    if original_cocktail.is_api_cocktail:
        # Use a JOIN query to find *this user's own* editable copy rather than
        # any user's copy sharing the same name — prevents cross-user leakage.
        user_copy = (
            Cocktail.query
            .join(Cocktails_Users, Cocktails_Users.cocktail_id == Cocktail.id)
            .filter(
                Cocktails_Users.user_id == user_id,
                Cocktail.name == original_cocktail.name,
                Cocktail.is_api_cocktail == False,
            )
            .first()
        )

        if not user_copy:
            # First edit: create a personal copy that the user can freely change
            # without affecting the shared API record that other users reference.
            user_copy = Cocktail(
                name=original_cocktail.name,
                instructions=original_cocktail.instructions,
                strDrinkThumb=original_cocktail.strDrinkThumb,
                image_url=original_cocktail.image_url,
                is_api_cocktail=False,
                owner_id=user_id,
            )
            db.session.add(user_copy)
            # Flush to obtain user_copy.id before creating FK rows below.
            db.session.flush()

            # Copy all ingredient associations from the shared record.
            for ci in original_cocktail.ingredients_relation:
                db.session.add(
                    Cocktails_Ingredients(
                        cocktail_id=user_copy.id,
                        ingredient_id=ci.ingredient_id,
                        quantity=ci.quantity,
                    )
                )

        # Swap the user's join-table row: remove the link to the shared API
        # record and replace it with a link to the personal copy.
        api_rel = Cocktails_Users.query.filter_by(
            user_id=user_id, cocktail_id=original_cocktail.id
        ).first()
        if api_rel:
            db.session.delete(api_rel)
            # Flush so the count below reflects the deletion already staged.
            db.session.flush()
            # If no other user still references the shared API record, remove
            # it entirely to prevent orphaned rows inflating admin stats.
            # The cascade on Cocktail.ct_users2 and .ingredients_relation
            # handles child-row cleanup automatically.
            if Cocktails_Users.query.filter_by(cocktail_id=original_cocktail.id).count() == 0:
                db.session.delete(original_cocktail)

        copy_rel = Cocktails_Users.query.filter_by(
            user_id=user_id, cocktail_id=user_copy.id
        ).first()
        if not copy_rel:
            db.session.add(Cocktails_Users(user_id=user_id, cocktail_id=user_copy.id))

        db.session.commit()
        # Redirect to the copy's own URL so the edit form POSTs to the
        # correct endpoint.  Without this the form still targets the API
        # cocktail's ID, whose Cocktails_Users link was just removed, causing
        # the ownership check on POST to fire the permission error.
        return redirect(url_for('cocktails.edit_cocktail', cocktail_id=user_copy.id))
    else:
        # Already a user-created (non-API) cocktail — edit in place.
        cocktail = original_cocktail

    form = EditCocktailForm(obj=cocktail)

    if request.method == 'POST' and 'add-ingredient' in request.form:
        form.ingredients.append_entry()

    elif form.validate_on_submit():
        cocktail.name = form.name.data
        cocktail.instructions = form.instructions.data

        # Track the new upload path for orphan cleanup if the DB commit fails.
        new_filename = None
        old_image = None
        try:
            # save_uploaded_image validates both extension and magic bytes.
            new_filename = save_uploaded_image(form.image.data)
            if new_filename:
                old_image = cocktail.image_url  # remember for cleanup after commit
                # Consolidate to image_url for user uploads; clear legacy field.
                cocktail.image_url = new_filename
                cocktail.strDrinkThumb = None
        except ValueError as e:
            db.session.rollback()
            flash(str(e), 'danger')
            return render_template('edit_my_cocktails.html', form=form, cocktail=cocktail,
                                   resolved_image=get_cocktail_image_url(cocktail))

        # Sync ingredients: remove rows no longer in the form, add/update the rest.
        new_names = {ing['ingredient'] for ing in form.ingredients.data}
        for ci in list(cocktail.ingredients_relation):
            if ci.ingredient.name not in new_names:
                cocktail.ingredients_relation.remove(ci)
                db.session.delete(ci)

        for ingredient_data in form.ingredients.data:
            assoc = next(
                (
                    ci for ci in cocktail.ingredients_relation
                    if ci.ingredient.name == ingredient_data['ingredient']
                ),
                None,
            )
            if assoc:
                # Update quantity in place rather than deleting and re-adding.
                assoc.quantity = ingredient_data['measure']
            else:
                ingredient_obj = store_or_get_ingredient(ingredient_data['ingredient'])
                db.session.add(
                    Cocktails_Ingredients(
                        cocktail=cocktail,
                        ingredient=ingredient_obj,
                        quantity=ingredient_data['measure'],
                    )
                )

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Remove the new upload to prevent it becoming an orphan on disk.
            if new_filename:
                delete_uploaded_image(new_filename)
            current_app.logger.error(f"DB commit failed during cocktail edit: {e}")
            flash('Failed to save changes. Please try again.', 'danger')
            return render_template('edit_my_cocktails.html', form=form, cocktail=cocktail,
                                   resolved_image=get_cocktail_image_url(cocktail))
        # Delete the old local upload only after a successful commit.
        delete_uploaded_image(old_image)
        flash('Your cocktail has been updated!', 'success')
        return redirect(url_for('cocktails.my_cocktails'))

    else:
        # GET: populate ingredient sub-forms from the DB relationship.
        all_ingredients = Ingredient.query.all()
        IngredientForm.ingredient.choices = [(ing.name, ing.name) for ing in all_ingredients]
        form.ingredients.entries.clear()
        for assoc in cocktail.ingredients_relation:
            entry = IngredientForm()
            entry.ingredient.data = assoc.ingredient.name
            entry.measure.data = assoc.quantity
            form.ingredients.append_entry(entry.data)

    return render_template('edit_my_cocktails.html', form=form, cocktail=cocktail,
                           resolved_image=get_cocktail_image_url(cocktail))
