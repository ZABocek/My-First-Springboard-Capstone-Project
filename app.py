from flask import Flask, render_template, redirect, session, flash, request


from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from models import db, connect_db, Ingredient, Cocktail, Cocktails_Ingredients, User
from forms import CocktailForm, RegisterForm, LoginForm, DeleteForm, IngredientForm, SearchIngredientsForm
from helpers import first
import json
import os
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison')
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgres:///new_music"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', 'abc12345678')


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
    username = form.username.data
    pwd = form.password.data
    email = form.email.data
    existing_user_count = User.query.filter_by(username=username).count()
    if existing_user_count > 0:
        flash("User already exists")
        return redirect('/login')

    if form.validate_on_submit():
        user = User.register(username, email, pwd)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        # on successful login, redirect to profile page
        return redirect(f"/users/profile/{user.id}")
    else:
        return render_template("/users/register.html", form=form)


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
        instructions = form.instructions.data
        ingredient = form.ingredient.data
        cocktails = Cocktail.query.filter_by(id=id).all()
        if form.validate_on_submit(): 
            new_cocktail = Cocktail.profile(Cocktail, cocktailname, instructions, ingredient)
            db.session.add(new_cocktail)
            db.session.commit()
            return redirect(f"/users/profile/{id}")
        return render_template("users/profile.html", cocktails=cocktails, form=form, user=user)


@app.route("/logout")
def logout():
    """Logs user out and redirects to homepage."""
    session.pop("user_id")
    return redirect("/login")


@app.route("/cocktails/<int:cocktail_id>", methods=['POST', 'GET'])
def show_cocktail(cocktail_id):
    """Show detail on specific playlist."""
    cocktail= Cocktail.query.get_or_404(cocktail_id)
    if "user_id" not in session or  cocktail.user_id != session['user_id']:
        flash("You must be logged in to view!")
        return redirect("/login")
    
    ingredients = Cocktails_Ingredients.query.filter_by(cocktail_id=cocktail_id)
    form = request.form
    if request.method == 'POST' and form['remove'] and form['ingredient']:
        ingredient_id = form['ingredient']
        ingredient_to_delete = Cocktails_Ingredients.query.get(ingredient_id)
        db.session.delete(ingredient_to_delete)
        # raise 'here'
        db.session.commit()
    return render_template("cocktail/cocktail.html", cocktail=cocktail, ingredients=ingredients)


@app.route('/cocktails/<int:cocktail_id>/search', methods=["GET", "POST"])
def show_form(cocktail_id):
    """Show form that searches new form, and show results"""
    cocktail = Cocktail.query.get(cocktail_id)
    cocktail_id  = cocktail_id
    form = SearchIngredientsForm()
    resultsIngredient = []
    checkbox_form = request.form

    list_of_ingredients_thecocktaildb_id_on_cocktail = []
    for ingredient in cocktail.ingredients:
      list_of_ingredients_thecocktaildb_id_on_cocktail.append(ingredient.thecocktaildb_id)
    ingredients_on_cocktail_set = set(list_of_ingredients_thecocktaildb_id_on_cocktail)
    

    if form.validate_on_submit() and checkbox_form['form'] == 'search_ingredients': 
        ingredient_data = form.ingredient.data   

        # get search results, don't inclue songs that are on playlist already
       

    # search results checkbox form
    if 'form' in checkbox_form and checkbox_form['form'] == 'pick_ingredients':
        list_of_picked_ingredients = checkbox_form.getlist('ingredient')
        # map each item in list of picked songs
        jsonvalues = [ json.loads(item) for item in  list_of_picked_ingredients ]


        for item in jsonvalues:
            name = item['name']
            thecocktaildb_id = item['thecocktaildb_id']
            cocktail_name = item['cocktail_name']
            cocktail_image = item['cocktail_image']
        
            # print(title)
            new_ingredients = Ingredient(name=name, thecocktaildb_id=thecocktaildb_id, cocktail_name=cocktail_name, cocktail_image=cocktail_image)
            db.session.add(new_ingredients)
            db.session.commit()
            # add new song to its playlist
            cocktail_ingredient = Cocktails_Ingredients(ingredient_id=new_ingredients.id, cocktail_id=cocktail_id)
            db.session.add(cocktail_ingredient)
            db.session.commit()
  
        return redirect(f'/cocktails/{cocktail_id}')
    def serialize(obj):
        return json.dumps(obj)
    return render_template('ingredient/search_new_ingredients.html', cocktail=cocktail, form=form, resultsIngredient=resultsIngredient, serialize=serialize)

@app.route("/cocktails/<int:cocktail_id>/update", methods=["GET", "POST"])
def update_cocktail(cocktail_id):
    """Show update form and process it."""
    cocktail = Cocktail.query.get(cocktail_id)
    if "user_id" not in session or cocktail.user_id != session['user_id']:
        flash("You must be logged in to view!")
        return redirect("/login")
    form = CocktailForm(obj=cocktail)
    if form.validate_on_submit():
        cocktail.name = form.name.data
        db.session.commit()
        return redirect(f"/users/profile/{session['user_id']}")
    return render_template("/cocktail/edit.html", form=form, cocktail=cocktail)

@app.route("/ingredients/<int:ingredient_id>/update", methods=["GET", "POST"])
def update_ingredient(ingredient_id):
    """Show update form and process it."""
    ingredient = Ingredient.query.get(ingredient_id)
    if "user_id" not in session or ingredient.user_id != session['user_id']:
        flash("You must be logged in to view!")
        return redirect("/login")
    form = IngredientForm(obj=ingredient)
    if form.validate_on_submit():
        ingredient.name = form.name.data
        db.session.commit()
        return redirect(f"/users/profile/{session['user_id']}")
    return render_template("/ingredient/edit.html", form=form, ingredient=ingredient)

@app.route("/cocktails/<int:cocktail_id>/delete", methods=["POST"])
def delete_cocktail(cocktail_id):
    """Delete playlist."""

    cocktail = Cocktail.query.get(cocktail_id)
    if "user_id" not in session or cocktail.user_id != session['user_id']:
        raise Unauthorized()

    form = DeleteForm()

    if form.validate_on_submit():
        db.session.delete(cocktail)
        db.session.commit()

    return redirect(f"/users/profile/{session['user_id']}")