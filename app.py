from flask import Flask, render_template, redirect, send_from_directory, session, flash, url_for, request
from werkzeug.datastructures import CombinedMultiDict
from werkzeug.utils import secure_filename

from flask_login import login_required, current_user
from config import SECRET_KEY
from flask_debugtoolbar import DebugToolbarExtension
from models import db, connect_db, User, UserFavoriteIngredients, Ingredient, Cocktail, Cocktails_Ingredients
from forms import RegisterForm, LoginForm, PreferenceForm, UserFavoriteIngredientForm, ListCocktailsForm, CocktailForm
from cocktaildb_api import search_ingredient, list_ingredients, lookup_cocktail, get_cocktails_list, get_cocktail_detail
import os
app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'  # define a folder to save uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison')
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgres:///new_music"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True


# db.create_all()


toolbar = DebugToolbarExtension(app)
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)

with app.app_context():
    db.drop_all()
    db.create_all()

@app.route("/")
def homepage():
    """Show homepage with links to site areas."""
    return redirect("/register")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user: produce form & handle form submission."""
    if "user_id" in session:
        return redirect(f"/users/profile/{session['user_id']}")
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        pwd = form.password.data
        email = form.email.data
        existing_user_count = User.query.filter_by(username=username).count()
        if existing_user_count > 0:
            flash("User already exists")
            return redirect('/login')

        user = User.register(username, email, pwd)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        # on successful login, redirect to profile page
        return redirect(f"/users/profile/{user.id}")
    
    return render_template("/users/register.html", form=form)

@app.route('/users/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user = User.query.get_or_404(user_id)
    preference_form = PreferenceForm()
    ingredient_form = UserFavoriteIngredientForm()

    ingredients_from_api = list_ingredients()
    if ingredients_from_api:
        ingredient_form.ingredient.choices = [(i['strIngredient1'], i['strIngredient1']) for i in ingredients_from_api.get('drinks', [])]
    else:
        app.logger.error("Failed to retrieve ingredients from API")

    if request.method == 'POST':
        submit_button = request.form.get('submit_button')
        
        if submit_button == 'Save Preference' and preference_form.validate():
            preference = preference_form.preference.data
            try:
                user.add_preference(preference)
                db.session.commit()
                flash('Preference updated successfully!', 'success')
            except Exception as e:
                app.logger.error(f"Failed to update preference: {e}")
                db.session.rollback()
                flash('Failed to update preference!', 'danger')

        elif submit_button == 'Add Ingredient' and ingredient_form.validate():
            ingredient_name = ingredient_form.ingredient.data

            # Check if ingredient exists in ingredient table
            ingredient = Ingredient.query.filter_by(name=ingredient_name).first()

            # If it doesn't exist, add it
            if not ingredient:
                ingredient = Ingredient(name=ingredient_name)
                db.session.add(ingredient)
                db.session.commit()

            # Check if already added to user's favorites, if not then add the ingredient
            existing_ingredient = UserFavoriteIngredients.query.filter_by(user_id=user.id, ingredient_id=ingredient.id).first()
            if existing_ingredient:
                flash('Ingredient already added!', 'warning')
            else:
                try:
                    favorite_ingredient = UserFavoriteIngredients(user_id=user.id, ingredient_id=ingredient.id)
                    db.session.add(favorite_ingredient)
                    db.session.commit()
                    flash('Ingredient added successfully!', 'success')
                except Exception as e:
                    app.logger.error(f"Failed to add ingredient: {e}")
                    db.session.rollback()
                    flash('Failed to add ingredient!', 'danger')

    user_favorite_ingredients = [i.ingredient for i in user.user_favorite_ingredients]
    return render_template('/users/profile.html', user=user, preference_form=preference_form, ingredient_form=ingredient_form, user_favorite_ingredients=user_favorite_ingredients)

@app.route('/cocktails', methods=['GET', 'POST'])
def list_cocktails():
    form = ListCocktailsForm()
    try:
        cocktails = get_cocktails_list()
        if not cocktails:
            flash('No cocktails found!', 'warning')
        else:
            form.cocktail.choices = cocktails
        if form.validate_on_submit():
            return redirect(url_for('cocktail_details', cocktail_id=form.cocktail.data))
    except Exception as e:
        app.logger.error(f"Failed to retrieve cocktails: {e}")
        flash('Failed to retrieve cocktails list. Please try again later.', 'danger')
        cocktails = []
    return render_template('list_cocktails.html', form=form, cocktails=cocktails)

@app.route('/cocktail/<int:cocktail_id>')
def cocktail_details(cocktail_id):
    try:
        cocktail = get_cocktail_detail(cocktail_id)
        if not cocktail:
            flash('Cocktail details not found!', 'warning')
            return redirect(url_for('list_cocktails'))
    except Exception as e:
        app.logger.error(f"Failed to retrieve cocktail details: {e}")
        flash('Failed to retrieve cocktail details. Please try again later.', 'danger')
        return redirect(url_for('list_cocktails'))
    
    user_id = session.get("user_id")  # Get user_id from the session
    return render_template('cocktail_details.html', cocktail=cocktail, user_id=user_id)  # Pass user_id to the template

@app.route('/add_cocktails', methods=['GET', 'POST'])
def add_cocktails():
    form = CocktailForm(CombinedMultiDict((request.files, request.form)))

    cocktails_from_api = get_cocktails_list()
    if cocktails_from_api:  
        form.pre_existing_cocktail.choices = cocktails_from_api

    ingredients_from_api = list_ingredients()
    if ingredients_from_api:
        for ingredient_form in form.ingredients:
            ingredient_form.ingredient.choices = [(i['strIngredient1'], i['strIngredient1']) for i in ingredients_from_api.get('drinks', [])]

    added_cocktails = session.get("added_cocktails", [])
    if form.validate_on_submit():
        if 'add_pre_existing' in request.form:
            cocktail_id = form.pre_existing_cocktail.data
            cocktail = get_cocktail_detail(cocktail_id)
            if cocktail:
                added_cocktails.append(cocktail)
                session["added_cocktails"] = added_cocktails  # store in the session
            else:
                flash('Failed to get cocktail details', 'danger')
        elif 'add_new' in request.form:
          # else, a new cocktail is being added
            cocktail_name = form.name.data
            cocktail = {"strDrink": cocktail_name, "strInstructions": form.instructions.data, "strDrinkThumb": None}
            ingredients = [{"ingredient": i.ingredient.data, "measure": i.measure.data} for i in form.ingredients]
            cocktail["ingredients"] = ingredients

            # save uploaded image if any
            image = form.image.data
            if image and image.filename:
                filename = secure_filename(image.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                cocktail["strDrinkThumb"] = url_for('uploaded_file', filename=filename)

            added_cocktails.append(cocktail)
        session["added_cocktails"] = added_cocktails
    
    return render_template('add_cocktails.html', form=form, added_cocktails=added_cocktails)
# Route to serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Produce login form or handle login."""

    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("users/login.html", form=form)
    # otherwise
    name = form.username.data
    pwd = form.password.data
    # authenticate will return a user or False
    user = User.authenticate(name, pwd)

    if not user:
        return render_template("users/login.html", form=form)
    # otherwise

    form.username.errors = ["Bad name/password"]
    session["user_id"] = user.id  
    return redirect(f"/users/profile/{user.id}")


@app.route("/logout")
def logout():
    """Logs user out and redirects to homepage."""
    session.pop("user_id")
    return redirect("/login")