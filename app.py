import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import RegisterForm, LoginForm, AddNewCocktailForm, AddCocktailToAccountForm, IngredientForm, UserAddForm
from models import db, connect_db, User, Ingredients, Cocktail, Cocktails_Ingredients, Cocktails_Users, UserFavoriteIngredients

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

##############################################################################
# User signup/login/logout

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError as e:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()

    flash("You have successfully logged out.", 'success')
    return redirect("/login")

@app.route("/cocktails/<int:cocktail_id>")
def show_cocktail(cocktail_id):
    """Show detail on specific playlist."""

    # ADD THE NECESSARY CODE HERE FOR THIS ROUTE TO WORK
    cocktail = Cocktail.query.get_or_404(cocktail_id)
    ingredients = Cocktails_Ingredients.query.filter_by(cocktail_id=cocktail_id)

    for b in ingredients:
        print('testing',b)


    return render_template("cocktail/new_cocktail.html", cocktail=cocktail)

@app.route("/cocktails/add", methods=["GET", "POST"])
def add_cocktail():
    form = AddCocktailToAccountForm()

    if form.validate_on_submit():
        cocktailname = form.cocktailname.data
        instructions = form.instructions.data
        new_cocktail = Cocktail(cocktailname=cocktailname, instructions=instructions)
        db.session.add(new_cocktail)
        db.session.commit()
        return redirect("/profile")

    return render_template("cocktail/new_cocktail.html", form=form)

@app.route("/ingredients")
def show_all_ingredients():
    """Show list of ingredients in cocktail."""

    ingredients = Ingredients.query.all()
    return render_template("ingredient/ingredients.html", ingredients=ingredients)


@app.route("/ingredients/<int:id>")
def show_ingredient(id):
   
    ingredient = Ingredients.query.get_or_404(id)
    cocktails = ingredient.is_alcohol


    return render_template("ingredient/ingredient.html", ingredient=ingredient, cocktails=cocktails)


@app.route("/ingredients/add", methods=["GET", "POST"])
def add_ingredient():
    
    form = IngredientForm()

    if form.validate_on_submit():
        id = request.form['id']
        name = request.form['name']
        new_ingredient = Ingredients(id=id,name=name)
        db.session.add(new_ingredient)
        db.session.commit()
        return redirect("/ingredients")

    return render_template("ingredient/new_ingredient.html", form=form)



@app.route("/cocktails/<int:cocktail_id>/add-ingredient", methods=["GET", "POST"])
def add_ingredient_to_cocktail(cocktail_id):
    """Add a playlist and redirect to list."""
    
    cocktail = Cocktail.query.get_or_404(cocktail_id)
    form = AddNewCocktailForm()

    curr_on_cocktail = [s.id for s in cocktail.ingredients]
    form.ingredient.choices = (db.session.query(Ingredients.id, Ingredients.name).filter(Ingredients.id.notin_(curr_on_cocktail)).all())

    if form.validate_on_submit():

        cocktails_users = Cocktails_Users(user_id=form.user.data, cocktail_id=cocktail_id)
        db.session.add(cocktails_users)
        db.session.commit()

        return redirect(f"/cocktails/{cocktail_id}")

    return render_template("ingredient/add_ingredient_to_cocktail.html", cocktail=cocktail, form=form)