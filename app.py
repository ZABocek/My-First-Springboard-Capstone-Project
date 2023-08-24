import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import RegisterForm, LoginForm, AddCocktailToAccountForm
from models import db, connect_db, User

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///nameyourpoison'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

##############################################################################
# User signup/login/logout


@app.route("/")
def root():
    """Homepage: redirect to /playlists."""
    print("****************session************")
    print(session["username"])
    print(session["user_id"])

    print("****************session************")


    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    

    if 'user_id' in session:
        return redirect(f"/users/{session['user_id']}")

    form = RegisterForm()
    username = form.username.data
    password = form.password.data

    existing_user_count = User.query.filter_by(username=name).count()
    if existing_user_count > 0:
        flash("User already exists")
        return redirect('/login')

    if form.validate_on_submit():
        user = User.register(username, password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        
        print(user.id)
        session['user_id'] = user.id
        print('id', session['user_id'])

        return redirect(f"/users/{user.id}")

    else:
        return render_template("users/register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(f"/users/{session['user_id']}")

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)  
        if user:
            return redirect(f"/users/{user.id}")
        else:
            form.username.errors = ["Invalid username/password."]
            return render_template("users/login.html", form=form)

    return render_template("users/login.html", form=form)

@app.route("/logout")
def logout():
    if "user_id" in session:
        session.pop("username")
    return redirect("/login")

@app.route("/users/<int:user_id>", methods=["GET", "POST"])
def profile(user_id):
    if session.get["user_id"] not in session:
        flash("You must be logged in to view!")
        return redirect("/")
    form = AddCocktailToAccountForm()
    cocktails = Cocktail.query.filter_by(user_id=session['user_id']).all()
  
    if form.validate_on_submit():
        
        
        name = form.name.data
        new_cocktail = Cocktail(name=name, user_id=session['user_id'])
        db.session.add(new_cocktail)
        db.session.commit()
        cocktails.append(new_cocktail)

    return render_template("users/profile.html", cocktails=cocktails, form=form)

@app.route("/cocktails/<int:cocktail_id>")
def show_user_cocktails(cocktail_id):
    """Show detail on specific playlist."""

    # ADD THE NECESSARY CODE HERE FOR THIS ROUTE TO WORK
    cocktail = Cocktail.query.get_or_404(cocktail_id)
    ingredients = CocktailIngredient.query.filter_by(cocktail_id=cocktail_id)

    for b in ingredients:
        print('testing',b)


    return render_template("cocktail/cocktail.html", cocktail=cocktail)