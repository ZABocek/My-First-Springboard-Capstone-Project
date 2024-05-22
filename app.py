# Import necessary Flask modules and other dependencies
from flask import current_app as app, Flask, render_template, redirect, send_from_directory, send_file, session, flash, url_for, request
# Import CSRF protection for Flask forms
from flask_wtf.csrf import CSRFProtect
# Import ThreadPoolExecutor for concurrent tasks
from concurrent.futures import ThreadPoolExecutor
# Import requests for making HTTP requests
import requests
# Import asyncio for asynchronous programming
import asyncio
# Import secure_filename to ensure safe file names for uploads
from werkzeug.utils import secure_filename
# Import FileStorage to handle file uploads
from werkzeug.datastructures import FileStorage
# Import DebugToolbarExtension for debugging purposes
from flask_debugtoolbar import DebugToolbarExtension
# Import the secret key for session management
from config import SECRET_KEY
# Import models for the database
from models import db, connect_db, User, UserFavoriteIngredients, Ingredient, Cocktails_Users, Cocktail, Cocktails_Ingredients
# Import forms for user input
from forms import RegisterForm, OriginalCocktailForm, IngredientForm, EditCocktailForm, LoginForm, PreferenceForm, UserFavoriteIngredientForm, ListCocktailsForm
# Import functions to interact with the cocktail API
from cocktaildb_api import list_ingredients, get_cocktail_detail, get_combined_cocktails_list, lookup_cocktail, get_random_cocktail, fetch_and_prepare_cocktails
# Import os for interacting with the operating system
import os

# Initialize the Flask application
app = Flask(__name__)

# Set the destination folder for uploaded photos
UPLOADED_PHOTOS_DEST = 'static/uploads'
# Define the allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# Configure the upload destination for Flask
app.config['UPLOADED_PHOTOS_DEST'] = UPLOADED_PHOTOS_DEST

# Set the secret key for session management
app.config['SECRET_KEY'] = SECRET_KEY
# Disable debug mode
app.config['DEBUG'] = False
# Set the database URI for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison')
# Disable track modifications for SQLAlchemy
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Enable echo for SQLAlchemy to log SQL queries
app.config["SQLALCHEMY_ECHO"] = True

# Set up the debug toolbar for Flask
toolbar = DebugToolbarExtension(app)
# Prevent the debug toolbar from intercepting redirects
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# Set up CSRF protection for Flask
csrf = CSRFProtect(app)

# Connect the Flask app to the database
connect_db(app)

with app.app_context():
    # Create the database schema within the app context
    db.drop_all()
    # Drop all existing database tables
    db.create_all()
    # Create all database tables

# Initialize a ThreadPoolExecutor for concurrent tasks
executor = ThreadPoolExecutor()
# Define the base URL for the cocktail API
BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

@app.route("/")
def homepage():
    """Show homepage with links to site areas."""
    # If the user is logged in, show the homepage, otherwise redirect to the registration page
    if "user_id" in session:
        return render_template("index.html")
    else:
        return redirect("/register")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user: produce form & handle form submission."""
    # If the user is already logged in, redirect to the homepage
    if "user_id" in session:
        return redirect(url_for('homepage'))
    # Create an instance of the registration form
    form = RegisterForm()

    # Check if the form is valid upon submission
    if form.validate_on_submit():
        # Get the username, password, and email from the form
        username = form.username.data
        pwd = form.password.data
        email = form.email.data
        # Check if the username already exists in the database
        existing_user_count = User.query.filter_by(username=username).count()
        if existing_user_count > 0:
            # If the username already exists, flash a message and redirect to the login page
            flash("User already exists")
            return redirect('/login')

        # Register the new user
        user = User.register(username, email, pwd)
        # Add the new user to the database session
        db.session.add(user)
        # Commit the new user to the database
        db.session.commit()
        # Store the user's ID in the session
        session["user_id"] = user.id
        # Redirect to the homepage
        return redirect(url_for('homepage'))
    
    # Render the registration template with the form
    return render_template("/users/register.html", form=form)

@app.route('/users/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    """Page where user selects their preferred ingredients and whether they prefer alcohol"""
    # Get the user from the database by their ID
    user = User.query.get_or_404(user_id)
    # Create instances of the preference and ingredient forms
    preference_form = PreferenceForm()
    ingredient_form = UserFavoriteIngredientForm()

    # Get the list of ingredients from the API asynchronously
    ingredients_from_api = asyncio.run(list_ingredients())
    # If ingredients are successfully retrieved from the API, populate the ingredient choices
    if ingredients_from_api:
        ingredient_form.ingredient.choices = [(i['strIngredient1'], i['strIngredient1']) for i in ingredients_from_api.get('drinks', [])]
    else:
        # If ingredients could not be retrieved, log an error message
        app.logger.error("Failed to retrieve ingredients from API")

    # Check if the request method is POST
    if request.method == 'POST':
        # Get the submit button value from the form
        submit_button = request.form.get('submit_button')
        
        # If the submit button is 'Save Preference' and the form is valid
        if submit_button == 'Save Preference' and preference_form.validate():
            # Get the preference data from the form
            preference = preference_form.preference.data
            try:
                # Try to add the preference to the user and commit to the database
                user.add_preference(preference)
                db.session.commit()
                # Flash a success message
                flash('Preference updated successfully!', 'success')
            except Exception as e:
                # If an error occurs, log the error and flash a danger message
                app.logger.error(f"Failed to update preference: {e}")
                db.session.rollback()
                flash('Failed to update preference!', 'danger')

        # If the submit button is 'Add Ingredient' and the form is valid
        elif submit_button == 'Add Ingredient' and ingredient_form.validate():
            # Get the ingredient name from the form
            ingredient_name = ingredient_form.ingredient.data

            # Check if the ingredient exists in the ingredient table
            ingredient = Ingredient.query.filter_by(name=ingredient_name).first()

            # If it doesn't exist, add it
            if not ingredient:
                ingredient = Ingredient(name=ingredient_name)
                db.session.add(ingredient)
                db.session.commit()

            # Check if the ingredient is already added to the user's favorites
            existing_ingredient = UserFavoriteIngredients.query.filter_by(user_id=user.id, ingredient_id=ingredient.id).first()
            if existing_ingredient:
                # If it is already added, flash a warning message
                flash('Ingredient already added!', 'warning')
            else:
                try:
                    # If it is not already added, add the ingredient to the user's favorites
                    favorite_ingredient = UserFavoriteIngredients(user_id=user.id, ingredient_id=ingredient.id)
                    db.session.add(favorite_ingredient)
                    db.session.commit()
                    # Flash a success message
                    flash('Ingredient added successfully!', 'success')
                except Exception as e:
                    # If an error occurs, log the error and flash a danger message
                    app.logger.error(f"Failed to add ingredient: {e}")
                    db.session.rollback()
                    flash('Failed to add ingredient!', 'danger')

    # Get the user's favorite ingredients
    user_favorite_ingredients = [i.ingredient for i in user.user_favorite_ingredients]
    # Render the profile template with the user, preference form, ingredient form, and favorite ingredients
    return render_template('/users/profile.html', user=user, preference_form=preference_form, ingredient_form=ingredient_form, user_favorite_ingredients=user_favorite_ingredients)

@app.route('/cocktails', methods=['GET', 'POST'])
def list_cocktails():
    """Place where users can go to see cocktails in a dropdown menu"""
    # Create an instance of the ListCocktailsForm
    form = ListCocktailsForm()
    try:
        # Create a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Run the coroutine within the loop
        cocktails = loop.run_until_complete(get_combined_cocktails_list())
        
        # Close the loop
        loop.close()

        if not cocktails:
            # If no cocktails are found, flash a warning message
            flash('No cocktails found!', 'warning')
        else:
            # Populate the cocktail choices from the API data
            form.cocktail.choices = [(cocktail[0], cocktail[1]) for cocktail in cocktails]
        # Check if the form is valid upon submission
        if form.validate_on_submit():
            # Redirect to the cocktail details page with the selected cocktail ID
            return redirect(url_for('cocktail_details', cocktail_id=form.cocktail.data))
    except Exception as e:
        # If an error occurs, log the error and flash a danger message
        app.logger.error(f"Failed to retrieve cocktails: {e}")
        flash('Failed to retrieve cocktails list. Please try again later.', 'danger')
        cocktails = []
    # Render the list_cocktails template with the form and cocktails
    return render_template('list_cocktails.html', form=form, cocktails=cocktails)

@app.route('/cocktail/<int:cocktail_id>')
def cocktail_details(cocktail_id):
    """Place where user can explore available cocktails in API"""
    try:
        # Get the cocktail details from the API
        cocktail = get_cocktail_detail(cocktail_id)
        if not cocktail:
            # If cocktail details are not found, flash a warning message and redirect to the list cocktails page
            flash('Cocktail details not found!', 'warning')
            return redirect(url_for('list_cocktails'))
    except Exception as e:
        # If an error occurs, log the error and flash a danger message
        app.logger.error(f"Failed to retrieve cocktail details: {e}")
        flash('Failed to retrieve cocktail details. Please try again later.', 'danger')
        return redirect(url_for('list_cocktails'))
    
    # Get user_id from the session
    user_id = session.get("user_id")
    # Render the cocktail_details template with the cocktail and user_id
    return render_template('cocktail_details.html', cocktail=cocktail, user_id=user_id)

@app.route('/add_api_cocktails', methods=['GET', 'POST'])
async def add_api_cocktails():
    """Add API cocktails to user's account"""
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to add cocktails!', 'danger')
        return redirect(url_for('login'))

    # Create an instance of the ListCocktailsForm
    form = ListCocktailsForm()
    # Get the user_id from the session
    user_id = session.get('user_id')

    # Get the list of cocktails from the API
    cocktails = await get_combined_cocktails_list()
    if cocktails:
        # Populate the cocktail choices from the API data
        form.cocktail.choices = [(c[0], c[1]) for c in cocktails]
    else:
        # If cocktails could not be retrieved, flash a danger message and render the add_api_cocktails template
        flash('Failed to retrieve cocktails. Please try again.', 'danger')
        return render_template('add_api_cocktails.html', form=form)

    # Check if the form is valid upon submission
    if form.validate_on_submit():
        # Get the selected cocktail ID from the form
        selected_cocktail_id = form.cocktail.data
        # Get the cocktail details from the API
        cocktail_detail = get_cocktail_detail(selected_cocktail_id)

        if cocktail_detail:
            # Process and store the new cocktail
            process_and_store_new_cocktail(cocktail_detail, user_id)
            # Flash a success message and redirect to the user's cocktails page
            flash(f"Added {cocktail_detail['strDrink']} to your cocktails!", 'success')
            return redirect(url_for('my_cocktails'))

        # If cocktail details could not be retrieved, flash a danger message
        flash('Failed to retrieve the selected cocktail.', 'danger')

    # Render the add_api_cocktails template with the form
    return render_template('add_api_cocktails.html', form=form)

@app.route('/my-cocktails')
def my_cocktails():
    """User views cocktails on their account"""
    # Get the user_id from the session
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to view your cocktails!', 'danger')
        return redirect(url_for('login'))

    # Get the user from the database by their ID
    user = User.query.get(user_id)
    # Get the cocktail_id from the query parameters
    cocktail_id = request.args.get('cocktail_id')

    # Initialize an empty list to store cocktail details
    cocktail_details = []
    cocktail_api = None

    if cocktail_id:
        # Fetch the specific cocktail from the API using its ID
        response = requests.get(f"{BASE_URL}/lookup.php?i={cocktail_id}")
        if response.status_code != 200:
            flash('Failed to retrieve the cocktail.', 'danger')
            return redirect(url_for('my_cocktails'))

        # Get the first cocktail data from the API response
        cocktail_api = response.json().get('drinks', [{}])[0]

        # Check if the cocktail already exists in the database
        existing_cocktail = Cocktail.query.filter_by(name=cocktail_api['strDrink']).first()

        # If not, create a new entry
        if not existing_cocktail:
            process_and_store_new_cocktail(cocktail_api, user_id)

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

    # Sort the cocktails alphabetically
    cocktail_details = sorted(cocktail_details, key=lambda x: x['strDrink'])

    # Render the my_cocktails template with the cocktail details
    return render_template('my_cocktails.html', cocktails=cocktail_details)

def process_and_store_new_cocktail(cocktail_api, user_id):
    """Helper function that assists in adding API cocktail to user's account"""
    try:
        # Create a new cocktail object
        new_cocktail = Cocktail(
            name=cocktail_api['strDrink'],
            instructions=cocktail_api['strInstructions'],
            strDrinkThumb=cocktail_api.get('strDrinkThumb')  # Save the strDrinkThumb from the API
        )
        # Save the new cocktail to the database
        db.session.add(new_cocktail)
        db.session.commit()

        # Loop through the ingredients from the API response
        for i in range(1, 16):  # Since there can be up to 15 ingredients in the API
            ingredient_name = cocktail_api.get(f'strIngredient{i}')
            measure = cocktail_api.get(f'strMeasure{i}')

            if ingredient_name:  # If there's an ingredient name
                ingredient_obj = store_or_get_ingredient(ingredient_name)  # Another function to simplify ingredient handling

                # Add to the Cocktails_Ingredients table
                ci_entry = Cocktails_Ingredients(cocktail_id=new_cocktail.id, ingredient_id=ingredient_obj.id, quantity=measure)
                db.session.add(ci_entry)
                db.session.commit()

        # Add relation between user and the new cocktail
        relation = Cocktails_Users(user_id=user_id, cocktail_id=new_cocktail.id)
        db.session.add(relation)
        db.session.commit()

    except Exception as e:
        # If an error occurs, log the error and rollback the database session
        app.logger.error(f"Failed to process or store new cocktail: {e}")
        db.session.rollback()

def store_or_get_ingredient(ingredient_name):
    """Helper function to store or retrieve an ingredient"""
    # Check if the ingredient already exists in the Ingredients table
    ingredient_obj = Ingredient.query.filter_by(name=ingredient_name).first()

    # If not, create a new ingredient
    if not ingredient_obj:
        ingredient_obj = Ingredient(name=ingredient_name)
        db.session.add(ingredient_obj)
        db.session.commit()

    return ingredient_obj

@app.route('/add-original-cocktails', methods=['GET', 'POST'])
def add_original_cocktails():
    """Route to add original cocktails"""
    # Create an instance of the OriginalCocktailForm
    form = OriginalCocktailForm()
    # Check if the form is valid upon submission
    if form.validate_on_submit():
        # Filter out empty ingredients and measures
        ingredients = [i for i in form.ingredients.data if i]
        measures = [m for m in form.measures.data if m]

        # Save the cocktail details to the database
        new_cocktail = Cocktail(name=form.name.data, instructions=form.instructions.data)
        db.session.add(new_cocktail)
        db.session.commit()

        # Get the user_id from the session
        user_id = session.get('user_id')
        # Create a relation between the user and the new cocktail
        relation = Cocktails_Users(user_id=user_id, cocktail_id=new_cocktail.id)
        db.session.add(relation)
        db.session.commit()

        # Loop through the ingredients and measures and add them to the database
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

        # Flash a success message and redirect to the user's cocktails page
        flash('Successfully added your original cocktail!', 'success')
        return redirect(url_for('my_cocktails'))

    # Render the add_original_cocktails template with the form
    return render_template('add_original_cocktails.html', form=form)

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Route to serve uploaded files"""
    return send_from_directory(app.config['UPLOADED_PHOTOS_DEST'], filename)

@app.route('/edit-cocktail/<int:cocktail_id>', methods=['GET', 'POST'])
def edit_cocktail(cocktail_id):
    """Route to edit an existing cocktail"""
    # Ensure the user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to edit cocktails!', 'danger')
        return redirect(url_for('login'))

    # Retrieve the cocktail the user wants to edit
    cocktail = Cocktail.query.get_or_404(cocktail_id)

    # Create and process the form for editing cocktails
    form = EditCocktailForm(obj=cocktail)  # Create an EditCocktailForm similar to the OriginalCocktailForm

    if request.method == 'POST' and 'add-ingredient' in request.form:
        form.ingredients.append_entry()

    elif form.validate_on_submit():
        # Update the cocktail name and instructions
        cocktail.name = form.name.data
        cocktail.instructions = form.instructions.data

        # Handle the image upload
        image = form.image.data
        if image and image.filename:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOADED_PHOTOS_DEST'], filename)
            image.save(filepath)
            cocktail.strDrinkThumb = filepath  # Update the image URL

        # Handle the ingredients
        new_ingredients = form.ingredients.data  # Get the new ingredients from the form

        # Detach ingredients that are no longer present
        for ci in cocktail.ingredients_relation[:]:  # Iterate over a copy of the list
            if ci.ingredient.name not in [ing['ingredient'] for ing in new_ingredients]:
                cocktail.ingredients_relation.remove(ci)
                db.session.delete(ci)  # Delete the ingredient from the database

        # Add or update ingredients
        for ingredient_data in new_ingredients:
            # Check if the ingredient is already associated with the cocktail
            assoc = next(
                (ci for ci in cocktail.ingredients_relation if ci.ingredient.name == ingredient_data['ingredient']), 
                None)
            if assoc:
                # Update existing association
                assoc.quantity = ingredient_data['measure']
            else:
                # Add new ingredient for this cocktail
                ingredient_obj = Ingredient.query.filter_by(name=ingredient_data['ingredient']).first()
                if ingredient_obj is None:
                    # Create a new ingredient if it doesn't exist
                    ingredient_obj = Ingredient(name=ingredient_data['ingredient'])
                    db.session.add(ingredient_obj)
                
                new_assoc = Cocktails_Ingredients(
                    cocktail=cocktail, 
                    ingredient=ingredient_obj, 
                    quantity=ingredient_data['measure']
                )
                db.session.add(new_assoc)

        # Commit the changes to the database
        db.session.commit()
        # Flash a success message and redirect to the user's cocktails page
        flash('Your cocktail has been updated!', 'success')
        return redirect(url_for('my_cocktails'))

    else:
        # If it's a GET request, populate the form with existing ingredients
        all_ingredients = Ingredient.query.all()
        IngredientForm.ingredient.choices = [(ing.name, ing.name) for ing in all_ingredients]

        # Clear existing ingredients
        form.ingredients.entries.clear()

        # Repopulate the ingredients from the relationship
        for assoc in cocktail.ingredients_relation:
            ingredient_form = IngredientForm()
            ingredient_form.ingredient.data = assoc.ingredient.name
            ingredient_form.measure.data = assoc.quantity
            form.ingredients.append_entry(ingredient_form.data)

    # Render the edit_my_cocktails template with the form and cocktail
    return render_template('edit_my_cocktails.html', form=form, cocktail=cocktail)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Produce login form or handle login."""
    # Create an instance of the LoginForm
    form = LoginForm()

    # Check if the form is valid upon submission
    if form.validate_on_submit():
        # Get the username and password from the form
        name = form.username.data
        pwd = form.password.data
        # Authenticate the user
        user = User.authenticate(name, pwd)

        if user:
            # If authentication is successful, store the user's ID in the session and redirect to the homepage
            session["user_id"] = user.id  
            return redirect(url_for('homepage'))

        # If authentication fails, flash an error message
        form.username.errors = ["Bad name/password"]

    # Render the login template with the form
    return render_template("users/login.html", form=form)

@app.route("/logout")
def logout():
    """Logs user out and redirects to homepage."""
    # Remove the user's ID from the session
    session.pop("user_id")
    # Redirect to the login page
    return redirect("/login")
