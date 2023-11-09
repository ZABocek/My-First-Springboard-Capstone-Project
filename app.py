from flask import current_app as app, Flask, render_template, redirect, send_from_directory, send_file, session, flash, url_for, request
from flask_wtf.csrf import CSRFProtect
from concurrent.futures import ThreadPoolExecutor
import requests
import asyncio
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_debugtoolbar import DebugToolbarExtension
from config import SECRET_KEY
from models import db, connect_db, User, UserFavoriteIngredients, Ingredient, Cocktails_Users, Cocktail, Cocktails_Ingredients
from forms import RegisterForm, OriginalCocktailForm, IngredientForm, EditCocktailForm, LoginForm, PreferenceForm, UserFavoriteIngredientForm, ListCocktailsForm
from cocktaildb_api import list_ingredients, get_cocktail_detail, get_combined_cocktails_list, lookup_cocktail, get_random_cocktail, fetch_and_prepare_cocktails
import os
app = Flask(__name__)
UPLOADED_PHOTOS_DEST = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# Set the folder where you want to store the uploaded images
app.config['UPLOADED_PHOTOS_DEST'] = UPLOADED_PHOTOS_DEST

# Configure the application with the upload sets
app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

toolbar = DebugToolbarExtension(app)
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
csrf = CSRFProtect(app)

connect_db(app)

with app.app_context():
    db.drop_all()
    db.create_all()
executor = ThreadPoolExecutor()
BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"
@app.route("/")
def homepage():
    """Show homepage with links to site areas."""
    if "user_id" in session:
        return render_template("index.html")
    else:
        return redirect("/register")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user: produce form & handle form submission."""
    if "user_id" in session:
        return redirect(url_for('homepage'))
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
        return redirect(url_for('homepage'))
    
    return render_template("/users/register.html", form=form)

@app.route('/users/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user = User.query.get_or_404(user_id)
    preference_form = PreferenceForm()
    ingredient_form = UserFavoriteIngredientForm()

    ingredients_from_api = asyncio.run(list_ingredients())
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
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the coroutine within the loop
        cocktails = loop.run_until_complete(get_combined_cocktails_list())
        
        loop.close()  # Close the loop

        if not cocktails:
            flash('No cocktails found!', 'warning')
        else:
            form.cocktail.choices = [(cocktail[0], cocktail[1]) for cocktail in cocktails]  # Assumes the function returns a list of tuples (id, cocktail_name)
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

@app.route('/add_api_cocktails', methods=['GET', 'POST'])
async def add_api_cocktails():
    if 'user_id' not in session:
        flash('You must be logged in to add cocktails!', 'danger')
        return redirect(url_for('login'))

    form = ListCocktailsForm()
    user_id = session.get('user_id')

    # Get the list of cocktails from the API
    cocktails = await get_combined_cocktails_list()
    if cocktails:
        form.cocktail.choices = [(c[0], c[1]) for c in cocktails]
    else:
        flash('Failed to retrieve cocktails. Please try again.', 'danger')
        return render_template('add_api_cocktails.html', form=form)

    if form.validate_on_submit():
        selected_cocktail_id = form.cocktail.data
        cocktail_detail = get_cocktail_detail(selected_cocktail_id)

        if cocktail_detail:
            process_and_store_new_cocktail(cocktail_detail, user_id)
            flash(f"Added {cocktail_detail['strDrink']} to your cocktails!", 'success')
            return redirect(url_for('my_cocktails'))

        flash('Failed to retrieve the selected cocktail.', 'danger')

    return render_template('add_api_cocktails.html', form=form)


# Similar changes should be made wherever you are calling the async functions.

@app.route('/my-cocktails')
def my_cocktails():
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to view your cocktails!', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    cocktail_id = request.args.get('cocktail_id')  # Get the cocktail_id from the query parameters

    # Initialize an empty list to store cocktail details:
    cocktail_details = []
    cocktail_api = None

    if cocktail_id:
        # Fetch the specific cocktail from the API using its ID:
        response = requests.get(f"{BASE_URL}/lookup.php?i={cocktail_id}")
        if response.status_code != 200:
            flash('Failed to retrieve the cocktail.', 'danger')
            return redirect(url_for('my_cocktails'))

        cocktail_api = response.json().get('drinks', [{}])[0]  # Get the first cocktail data from the API response

        # Check if the cocktail already exists in the database:
        existing_cocktail = Cocktail.query.filter_by(name=cocktail_api['strDrink']).first()

        # If not, create a new entry:
        if not existing_cocktail:
            process_and_store_new_cocktail(cocktail_api, user_id)  # New function to abstract some tasks

    # Fetch all cocktails related to the user
    user_cocktails = [relation.cocktails for relation in user.cocktails_relation]

    for cocktail in user_cocktails:
        # Retrieve ingredients through the 'ingredients_relation' attribute
        ingredients_list = cocktail.ingredients_relation
        ingredients = [{'ingredient': i.ingredient.name, 'measure': i.quantity} for i in ingredients_list]

        detail = {
            'id': cocktail.id,
            'strDrink': cocktail.name,
            'strInstructions': cocktail.instructions,
            'ingredients': ingredients
        }

        # If it's a user-uploaded cocktail, set image URL accordingly
        if hasattr(cocktail, 'image_url') and cocktail.image_url:
            detail['strDrinkThumb'] = url_for('uploaded_file', filename=cocktail.image_url)
        elif hasattr(cocktail, 'strDrinkThumb') and cocktail.strDrinkThumb:
            detail['strDrinkThumb'] = cocktail.strDrinkThumb

        cocktail_details.append(detail)

    # Sort the cocktails alphabetically:
    cocktail_details = sorted(cocktail_details, key=lambda x: x['strDrink'])

    return render_template('my_cocktails.html', cocktails=cocktail_details)

def process_and_store_new_cocktail(cocktail_api, user_id):
    try: 
        new_cocktail = Cocktail(
            name=cocktail_api['strDrink'],
            instructions=cocktail_api['strInstructions'],
            strDrinkThumb=cocktail_api.get('strDrinkThumb')  # Save the strDrinkThumb from the API
        )
        # ... rest of the function ...
        db.session.add(new_cocktail)
        db.session.commit()

        # Loop through the ingredients from the API response
        for i in range(1, 16):  # Since there can be up to 15 ingredients in the API
            ingredient_name = cocktail_api.get(f'strIngredient{i}')
            measure = cocktail_api.get(f'strMeasure{i}')

            if ingredient_name:  # If there's an ingredient name
                ingredient_obj = store_or_get_ingredient(ingredient_name)  # Another function to simplify ingredient handling

                # Add to the Cocktails_Ingredients table:
                ci_entry = Cocktails_Ingredients(cocktail_id=new_cocktail.id, ingredient_id=ingredient_obj.id, quantity=measure)
                db.session.add(ci_entry)
                db.session.commit()

        # Add relation between user and the new cocktail:
        relation = Cocktails_Users(user_id=user_id, cocktail_id=new_cocktail.id)
        db.session.add(relation)
        db.session.commit()

    except Exception as e:
        app.logger.error(f"Failed to process or store new cocktail: {e}")
        db.session.rollback()

def store_or_get_ingredient(ingredient_name):
    # Check if the ingredient already exists in the Ingredients table:
    ingredient_obj = Ingredient.query.filter_by(name=ingredient_name).first()

    # If not, create a new ingredient:
    if not ingredient_obj:
        ingredient_obj = Ingredient(name=ingredient_name)
        db.session.add(ingredient_obj)
        db.session.commit()

    return ingredient_obj

@app.route('/add-original-cocktails', methods=['GET', 'POST'])
def add_original_cocktails():
    form = OriginalCocktailForm()
    if form.validate_on_submit():
        # Filter out empty ingredients and measures
        ingredients = [i for i in form.ingredients.data if i]
        measures = [m for m in form.measures.data if m]

        # Save the cocktail details to the database
        new_cocktail = Cocktail(name=form.name.data, instructions=form.instructions.data)
        db.session.add(new_cocktail)
        db.session.commit()

        user_id = session.get('user_id')
        relation = Cocktails_Users(user_id=user_id, cocktail_id=new_cocktail.id)
        db.session.add(relation)
        db.session.commit()


        for ingredient, measure in zip(form.ingredients.data, form.measures.data):
            ingredient_obj = Ingredient.query.filter_by(name=ingredient).first()
            if not ingredient_obj:
                ingredient_obj = Ingredient(name=ingredient)
                db.session.add(ingredient_obj)
                db.session.commit()
            ci_entry = Cocktails_Ingredients(cocktail_id=new_cocktail.id, ingredient_id=ingredient_obj.id, quantity=measure)
            db.session.add(ci_entry)
            db.session.commit()
            
        # Optionally, save the image if it was provided
        cocktail_name = form.name.data
        cocktail = {"strDrink": cocktail_name, "strInstructions": form.instructions.data, "strDrinkThumb": None}
        image = form.image.data
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
            image.save(filepath)
            cocktail["strDrinkThumb"] = url_for('uploaded_file', filename=filename)
            new_cocktail.image_url = filename
            db.session.commit()

        flash('Successfully added your original cocktail!', 'success')
        return redirect(url_for('my_cocktails'))

    return render_template('add_original_cocktails.html', form=form)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

@app.route('/edit-cocktail/<int:cocktail_id>', methods=['GET', 'POST'])
def edit_cocktail(cocktail_id):
    # Ensure the user is logged in.
    if 'user_id' not in session:
        flash('You must be logged in to edit cocktails!', 'danger')
        return redirect(url_for('login'))
    


    # Retrieve the cocktail the user wants to edit.
    cocktail = Cocktail.query.get_or_404(cocktail_id)

    # Create and process the form for editing cocktails.
    form = EditCocktailForm(obj=cocktail)  # You need to create an EditCocktailForm similar to your OriginalCocktailForm.

    
    
    if request.method == 'POST' and 'add-ingredient' in request.form:
        form.ingredients.append_entry()

    elif form.validate_on_submit():
        cocktail.name = form.name.data
        cocktail.instructions = form.instructions.data

        image = form.image.data
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
            image.save(filepath)
            cocktail.strDrinkThumb = filepath  # Be consistent with your model

        # Handle the ingredients - this part changes significantly
        new_ingredients = form.ingredients.data  # This assumes your form's field is named 'ingredients'

        # First, let's find and detach ingredients that are no longer present
        for ci in cocktail.ingredients_relation[:]:  # iterate over a copy of the list
            if ci.ingredient.name not in [ing['ingredient'] for ing in new_ingredients]:
                cocktail.ingredients_relation.remove(ci)
                db.session.delete(ci)  # This might be optional depending on your cascade settings

        # Now, handle adding/updating ingredients
        for ingredient_data in new_ingredients:
            # Check if the ingredient is already associated with the cocktail
            assoc = next(
                (ci for ci in cocktail.ingredients_relation if ci.ingredient.name == ingredient_data['ingredient']), 
                None)
            if assoc:
                # Update existing association
                assoc.quantity = ingredient_data['measure']
            else:
                # New ingredient for this cocktail
                ingredient_obj = Ingredient.query.filter_by(name=ingredient_data['ingredient']).first()
                if ingredient_obj is None:
                    # Safety check if the ingredient doesn't exist, though it should
                    ingredient_obj = Ingredient(name=ingredient_data['ingredient'])
                    db.session.add(ingredient_obj)
                
                new_assoc = Cocktails_Ingredients(
                    cocktail=cocktail, 
                    ingredient=ingredient_obj, 
                    quantity=ingredient_data['measure']
                )
                db.session.add(new_assoc)

        db.session.commit()
        flash('Your cocktail has been updated!', 'success')
        return redirect(url_for('my_cocktails'))

    # If it's a GET request, we'll need to populate the form with existing ingredients.
    else:
        all_ingredients = Ingredient.query.all()
        IngredientForm.ingredient.choices = [(ing.name, ing.name) for ing in all_ingredients]

        # Clear existing ingredients.
        form.ingredients.entries.clear()

        # Repopulate the ingredients from the relationship.
        for assoc in cocktail.ingredients_relation:
            ingredient_form = IngredientForm()
            ingredient_form.ingredient.data = assoc.ingredient.name
            ingredient_form.measure.data = assoc.quantity
            form.ingredients.append_entry(ingredient_form.data)
        
        
        # Debugging: Print populated ingredient data to console.
       
        # Render the editing form with the current cocktail details.

    return render_template('edit_my_cocktails.html', form=form, cocktail=cocktail)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Produce login form or handle login."""
    form = LoginForm()

    if form.validate_on_submit():
        name = form.username.data
        pwd = form.password.data
        user = User.authenticate(name, pwd)

        if user:
            session["user_id"] = user.id  
            return redirect(url_for('homepage'))

        form.username.errors = ["Bad name/password"]

    return render_template("users/login.html", form=form)

@app.route("/logout")
def logout():
    """Logs user out and redirects to homepage."""
    session.pop("user_id")
    return redirect("/login")