from flask import Flask, abort, render_template, redirect, session, flash, url_for
from config import SECRET_KEY
import requests
import logging
from flask_debugtoolbar import DebugToolbarExtension
from models import db, connect_db, Ingredient, Cocktail, Cocktails_Ingredients, User
from forms import CocktailForm, RegisterForm, LoginForm
import os
app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = True

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

@app.route("/users/profile/<int:id>",  methods=["GET", "POST"])
def profile(id):
    """Example hidden page for logged-in users only."""

    # raise 'here'
    if "user_id" not in session or id != session['user_id']:
        flash("You must be logged in to view!")
        return redirect("/login")
    else:
        id = session["user_id"]
        user = User.query.get_or_404(id)
        form = CocktailForm()
        cocktailname = form.cocktailname.data
        ingredient = form.ingredient.data
        instructions = form.instructions.data
        cocktails = Cocktail.query.filter_by(id=id).all()
        if form.validate_on_submit(): 
            new_cocktail = Cocktail.profile(Cocktail, cocktailname, ingredient, instructions)
            db.session.add(new_cocktail)
            db.session.commit()
            new_cocktail.cursor1(cocktailname, ingredient, instructions)
            return redirect(f"/users/profile/{id}")
        return render_template("users/profile.html", cocktails=cocktails, form=form, user=user)

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

@app.route('/add_cocktail', methods=['GET', 'POST'])
def add_cocktail():
    form = CocktailForm()

    # Populate ingredient choices from the database
    ingredient_choices = [(str(ingredient.id), ingredient.name) for ingredient in Ingredient.query.all()]
    for ingredient_field in form.ingredients:
        ingredient_field.ingredient.choices = ingredient_choices

    if form.validate_on_submit():
        cocktail_name = form.name.data

        # Fetch cocktail details from CocktailDB API
        cocktail_data = cocktaildb_api.get_cocktail_by_name(cocktail_name)
        
        # If cocktail_data is not None, then you can use it for additional information or validation.
        # For example, verifying if the instructions match, or auto-filling the ingredients if they are empty.
        if cocktail_data:
            # ... (Additional logic, if needed)
            pass
        
        cocktail = Cocktail(name=cocktail_name, instructions=form.instructions.data)
        db.session.add(cocktail)
        db.session.flush()  # This is to get the ID of the newly created cocktail record
        
        # Add ingredients and their quantities to Cocktails_Ingredients table
        for ingredient_data in form.ingredients.data:
            cocktail_ingredient = Cocktails_Ingredients(cocktail_id=cocktail.id, ingredient_id=ingredient_data['Ingredient'], quantity=ingredient_data['Measure'])
            db.session.add(cocktail_ingredient)
        
        db.session.commit()

        flash('Cocktail added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_cocktail.html', form=form)
