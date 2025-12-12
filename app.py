# Import necessary Flask modules and other dependencies
from flask import current_app as app, Flask, render_template, redirect, send_from_directory, send_file, session, flash, url_for, request
# Import CSRF protection for Flask forms
from flask_wtf.csrf import CSRFProtect
# Import Flask-Mail for sending emails
from flask_mail import Mail, Message
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
# Import security configuration and secrets
from config import SECRET_KEY, ADMIN_PASSWORD_KEY, SESSION_COOKIE_HTTPONLY, SESSION_COOKIE_SAMESITE, SECURE_SSL_REDIRECT, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
# Import models for the database
from models import db, connect_db, User, UserFavoriteIngredients, Ingredient, Cocktails_Users, Cocktail, Cocktails_Ingredients, AdminMessage, UserAppeal
# Import forms for user input
from forms import RegisterForm, OriginalCocktailForm, IngredientForm, EditCocktailForm, LoginForm, PreferenceForm, UserFavoriteIngredientForm, ListCocktailsForm, AdminForm, UserMessageForm, AdminMessageForm, AppealForm
# Import email utility functions
from helpers import generate_ban_appeal_email, generate_ban_lifted_email
# Import functions to interact with the cocktail API
from cocktaildb_api import list_ingredients, get_cocktail_detail, get_combined_cocktails_list, lookup_cocktail, get_random_cocktail, fetch_and_prepare_cocktails
# Import os for interacting with the operating system
import os
# Import functools for creating decorators
from functools import wraps
# Import datetime for ban tracking
from datetime import datetime, timedelta

# Initialize the Flask application
app = Flask(__name__)

# Set the destination folder for uploaded photos
UPLOADED_PHOTOS_DEST = 'static/uploads'
# Define the allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# Configure the upload destination for Flask
app.config['UPLOADED_PHOTOS_DEST'] = UPLOADED_PHOTOS_DEST

# Set the secret key for session management and CSRF protection
app.config['SECRET_KEY'] = SECRET_KEY
# Enable debug mode for development
app.config['DEBUG'] = True
# Set the database URI for SQLAlchemy
# Use SQLite for development/testing, PostgreSQL for production
default_db_uri = os.environ.get('DATABASE_URL', 'sqlite:///cocktails.db')
if default_db_uri.startswith('postgresql://'):
    # PostgreSQL URL format
    app.config['SQLALCHEMY_DATABASE_URI'] = default_db_uri
else:
    # Use SQLite if DATABASE_URL is not set or doesn't start with postgresql://
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cocktails.db'
# Disable track modifications for SQLAlchemy
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Enable echo for SQLAlchemy to log SQL queries
app.config["SQLALCHEMY_ECHO"] = True

# Security configuration for sessions
app.config['SESSION_COOKIE_SECURE'] = SESSION_COOKIE_HTTPONLY  # HTTPS only in production
app.config['SESSION_COOKIE_HTTPONLY'] = SESSION_COOKIE_HTTPONLY  # No JS access to cookies
app.config['SESSION_COOKIE_SAMESITE'] = SESSION_COOKIE_SAMESITE  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expires after 1 hour of inactivity
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request

# Set up the debug toolbar for Flask
toolbar = DebugToolbarExtension(app)
# Prevent the debug toolbar from intercepting redirects
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
# Set up CSRF protection for Flask
csrf = CSRFProtect(app)

# Set up Flask-Mail configuration
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER
mail = Mail(app)

# Connect the Flask app to the database
connect_db(app)

# Initialize the database schema (will be called separately for testing/development)
def init_db():
    """Initialize the database schema."""
    with app.app_context():
        try:
            # Drop all existing tables to ensure schema matches models
            db.drop_all()
            # Create all tables with the current schema
            db.create_all()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")

# Initialize a ThreadPoolExecutor for concurrent tasks
executor = ThreadPoolExecutor()
# Define the base URL for the cocktail API
BASE_URL = "https://www.thecocktaildb.com/api/json/v1/1"

# ===== SECURITY DECORATORS AND MIDDLEWARE =====

def login_required(f):
    """Decorator to require user to be logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to access this page.", "danger")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require user to be an admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to access this page.", "danger")
            return redirect(url_for('login'))
        
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            flash("You do not have permission to access this page. Admin access required.", "danger")
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    # Prevent clickjacking attacks
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Enable XSS protection
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Control referrer information
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Control permissions
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response

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

    # Get the user's favorite ingredients with their IDs
    user_favorite_ingredients = [(i.ingredient.id, i.ingredient.name) for i in user.user_favorite_ingredients]
    # Render the profile template with the user, preference form, ingredient form, and favorite ingredients
    return render_template('/users/profile.html', user=user, preference_form=preference_form, ingredient_form=ingredient_form, user_favorite_ingredients=user_favorite_ingredients)

@app.route('/delete-favorite-ingredient/<int:user_id>/<int:ingredient_id>', methods=['POST'])
def delete_favorite_ingredient(user_id, ingredient_id):
    """Delete a favorite ingredient from user's profile"""
    # Check if user is logged in and matches the user_id
    if 'user_id' not in session or session.get('user_id') != user_id:
        flash('You do not have permission to delete this ingredient.', 'danger')
        return redirect(url_for('profile', user_id=user_id))
    
    try:
        # Find and delete the favorite ingredient relationship
        favorite = UserFavoriteIngredients.query.filter_by(user_id=user_id, ingredient_id=ingredient_id).first()
        if favorite:
            db.session.delete(favorite)
            db.session.commit()
            flash('Ingredient deleted successfully!', 'success')
        else:
            flash('Ingredient not found.', 'danger')
    except Exception as e:
        app.logger.error(f"Failed to delete favorite ingredient: {e}")
        db.session.rollback()
        flash('Failed to delete ingredient!', 'danger')
    
    return redirect(url_for('profile', user_id=user_id))

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
def add_api_cocktails():
    """Add API cocktails to user's account"""
    # Check if the user is logged in
    if 'user_id' not in session:
        flash('You must be logged in to add cocktails!', 'danger')
        return redirect(url_for('login'))

    # Create an instance of the ListCocktailsForm
    form = ListCocktailsForm()
    # Get the user_id from the session
    user_id = session.get('user_id')

    # Get the list of cocktails from the API using asyncio
    try:
        cocktails = asyncio.run(get_combined_cocktails_list())
    except Exception as e:
        print(f"Error fetching cocktails: {e}")
        cocktails = None
    
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
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    
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
            # If it's just a filename (user-edited), convert to URL; if it's a URL, use as-is
            if cocktail.strDrinkThumb.startswith('http'):
                detail['strDrinkThumb'] = cocktail.strDrinkThumb
            else:
                detail['strDrinkThumb'] = url_for('uploaded_file', filename=cocktail.strDrinkThumb)

        cocktail_details.append(detail)

    # Sort the cocktails alphabetically
    cocktail_details = sorted(cocktail_details, key=lambda x: x['strDrink'])

    # Render the my_cocktails template with the cocktail details
    return render_template('my_cocktails.html', cocktails=cocktail_details)

@app.route('/delete-cocktail/<int:cocktail_id>', methods=['POST'])
def delete_cocktail(cocktail_id):
    """Delete a cocktail from the user's account"""
    # Get the user_id from the session
    user_id = session.get('user_id')
    if not user_id:
        flash('You must be logged in to delete cocktails!', 'danger')
        return redirect(url_for('login'))
    
    # Get the user from the database
    user = User.query.get(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    
    # Get the cocktail from the database
    cocktail = Cocktail.query.get(cocktail_id)
    if not cocktail:
        flash('Cocktail not found.', 'danger')
        return redirect(url_for('my_cocktails'))
    
    # Check if the cocktail belongs to the user
    user_cocktails = [relation.cocktails for relation in user.cocktails_relation]
    if cocktail not in user_cocktails:
        flash('You do not have permission to delete this cocktail.', 'danger')
        return redirect(url_for('my_cocktails'))
    
    try:
        # Remove the cocktail from the user's collection
        cocktails_user_relation = Cocktails_Users.query.filter_by(user_id=user_id, cocktail_id=cocktail_id).first()
        if cocktails_user_relation:
            db.session.delete(cocktails_user_relation)
            db.session.commit()
            
            # Only delete the cocktail if it's user-created (not from API)
            if not cocktail.is_api_cocktail:
                # Check if any other users have this cocktail
                other_users = Cocktails_Users.query.filter_by(cocktail_id=cocktail_id).count()
                if other_users == 0:
                    # If no other users have this cocktail, delete it from the database
                    db.session.delete(cocktail)
                    db.session.commit()
            
            flash('Cocktail deleted successfully!', 'success')
        else:
            flash('Cocktail not found in your collection.', 'danger')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error deleting cocktail: {e}")
        flash('Failed to delete cocktail. Please try again.', 'danger')
    
    return redirect(url_for('my_cocktails'))

def process_and_store_new_cocktail(cocktail_api, user_id):
    """Helper function that assists in adding API cocktail to user's account"""
    try:
        # Always check if the API cocktail exists
        existing_cocktail = Cocktail.query.filter_by(name=cocktail_api['strDrink'], is_api_cocktail=True).first()
        
        if existing_cocktail:
            # If API cocktail already exists, just add the user relationship
            new_cocktail = existing_cocktail
        else:
            # Create a new API cocktail object
            new_cocktail = Cocktail(
                name=cocktail_api['strDrink'],
                instructions=cocktail_api['strInstructions'],
                strDrinkThumb=cocktail_api.get('strDrinkThumb'),
                is_api_cocktail=True  # Mark this as an API cocktail
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

        # Add relation between user and the cocktail (whether new or existing)
        existing_relation = Cocktails_Users.query.filter_by(user_id=user_id, cocktail_id=new_cocktail.id).first()
        if not existing_relation:
            # Only add if the user doesn't already have this cocktail
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
        # Filter out ingredient-measure pairs where either ingredient or measure is empty
        filtered_ingredients = [
            (i, m) for i, m in zip(form.ingredients.data, form.measures.data) 
            if i and m
        ]

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

        # Loop through the filtered ingredients and measures and add them to the database
        for ingredient, measure in filtered_ingredients:
            ingredient_obj = Ingredient.query.filter_by(name=ingredient).first()
            if not ingredient_obj:
                ingredient_obj = Ingredient(name=ingredient)
                db.session.add(ingredient_obj)
                db.session.commit()
            ci_entry = Cocktails_Ingredients(cocktail_id=new_cocktail.id, ingredient_id=ingredient_obj.id, quantity=measure)
            db.session.add(ci_entry)
            db.session.commit()
            
        # Handle image upload - THIS IS THE CRITICAL PART
        image = form.image.data
        print(f"DEBUG: Image data = {image}")
        print(f"DEBUG: Image filename = {image.filename if image else 'None'}")
        
        if image and image.filename:
            try:
                filename = secure_filename(image.filename)
                print(f"DEBUG: Secured filename = {filename}")
                
                # Create absolute path to uploads directory
                uploads_dir = os.path.join(os.path.dirname(__file__), app.config['UPLOADED_PHOTOS_DEST'])
                print(f"DEBUG: Uploads dir = {uploads_dir}")
                
                os.makedirs(uploads_dir, exist_ok=True)  # Ensure directory exists
                filepath = os.path.join(uploads_dir, filename)
                print(f"DEBUG: Full filepath = {filepath}")
                
                image.save(filepath)
                print(f"DEBUG: Image saved successfully!")
                
                new_cocktail.image_url = filename  # Store just the filename
                db.session.commit()
                print(f"DEBUG: Database updated with image_url = {filename}")
            except Exception as e:
                print(f"DEBUG: ERROR saving image: {e}")
                flash(f'Error uploading image: {str(e)}', 'danger')

        # Flash a success message and redirect to the user's cocktails page
        flash('Successfully added your original cocktail!', 'success')
        return redirect(url_for('my_cocktails'))
    else:
        # Print form errors for debugging
        if request.method == 'POST':
            print(f"DEBUG: Form validation failed. Errors: {form.errors}")

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

    user_id = session.get('user_id')
    
    # Retrieve the cocktail the user wants to edit
    original_cocktail = Cocktail.query.get_or_404(cocktail_id)
    
    # If this is an API cocktail, create a user copy for editing
    if original_cocktail.is_api_cocktail:
        # Check if user already has a personal copy of this API cocktail
        user_copy = Cocktail.query.filter_by(
            name=original_cocktail.name, 
            is_api_cocktail=False
        ).first()
        
        if not user_copy:
            # Create a new user-created copy of the API cocktail
            user_copy = Cocktail(
                name=original_cocktail.name,
                instructions=original_cocktail.instructions,
                strDrinkThumb=original_cocktail.strDrinkThumb,
                image_url=original_cocktail.image_url,
                is_api_cocktail=False  # Mark as user-created
            )
            db.session.add(user_copy)
            db.session.flush()  # Get the ID without committing yet
            
            # Copy ingredients from the API cocktail
            for ci in original_cocktail.ingredients_relation:
                new_ci = Cocktails_Ingredients(
                    cocktail_id=user_copy.id,
                    ingredient_id=ci.ingredient_id,
                    quantity=ci.quantity
                )
                db.session.add(new_ci)
            
            db.session.commit()
        
        # Remove user from API cocktail and add to user copy
        api_relation = Cocktails_Users.query.filter_by(user_id=user_id, cocktail_id=original_cocktail.id).first()
        if api_relation:
            db.session.delete(api_relation)
            db.session.commit()
        
        copy_relation = Cocktails_Users.query.filter_by(user_id=user_id, cocktail_id=user_copy.id).first()
        if not copy_relation:
            copy_relation = Cocktails_Users(user_id=user_id, cocktail_id=user_copy.id)
            db.session.add(copy_relation)
            db.session.commit()
        
        cocktail = user_copy
    else:
        cocktail = original_cocktail

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
            # Create absolute path to uploads directory
            uploads_dir = os.path.join(os.path.dirname(__file__), app.config['UPLOADED_PHOTOS_DEST'])
            os.makedirs(uploads_dir, exist_ok=True)  # Ensure directory exists
            filepath = os.path.join(uploads_dir, filename)
            image.save(filepath)
            # Store just the filename, not the full path
            cocktail.strDrinkThumb = filename
            # Clear image_url since we're using strDrinkThumb for this edit
            cocktail.image_url = None

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

@app.route("/admin/unlock", methods=["GET", "POST"])
def admin_unlock():
    """Admin unlock page - requires admin password key."""
    # If already an admin, redirect to admin panel
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        if user and user.is_admin:
            return redirect(url_for('admin_panel'))
    
    # Create an instance of the AdminForm
    form = AdminForm()
    
    if form.validate_on_submit():
        # Get the admin password key from the form
        provided_key = form.admin_key.data
        
        # Verify the key matches the one in config
        if provided_key == ADMIN_PASSWORD_KEY:
            # If user is logged in, mark them as admin
            if "user_id" in session:
                user = User.query.get(session["user_id"])
                if user:
                    user.is_admin = True
                    db.session.commit()
                    flash("Admin access granted!", "success")
                    return redirect(url_for('admin_panel'))
            else:
                flash("You must be logged in to access the admin panel.", "danger")
        else:
            flash("Invalid admin password key.", "danger")
    
    return render_template("admin/unlock.html", form=form)

@app.route("/admin/panel")
@admin_required
def admin_panel():
    """Admin panel for managing the application."""
    # Get statistics
    total_users = User.query.count()
    total_cocktails = Cocktail.query.count()
    total_api_cocktails = Cocktail.query.filter_by(is_api_cocktail=True).count()
    total_user_cocktails = Cocktail.query.filter_by(is_api_cocktail=False).count()
    
    # Get all users
    users = User.query.all()
    
    stats = {
        'total_users': total_users,
        'total_cocktails': total_cocktails,
        'total_api_cocktails': total_api_cocktails,
        'total_user_cocktails': total_user_cocktails
    }
    
    return render_template("admin/panel.html", stats=stats, users=users, now=datetime.utcnow())

@app.route("/admin/user/<int:user_id>/promote", methods=["POST"])
@admin_required
def promote_user(user_id):
    """Promote a user to admin status."""
    # Current user must be admin
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    # Can't promote yourself
    if user_id == current_user.id:
        flash("You cannot promote yourself.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    user.is_admin = True
    db.session.commit()
    flash(f"User {user.username} promoted to admin.", "success")
    return redirect(url_for('admin_panel'))

@app.route("/admin/user/<int:user_id>/demote", methods=["POST"])
@admin_required
def demote_user(user_id):
    """Demote a user from admin status."""
    # Current user must be admin
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    # Can't demote yourself
    if user_id == current_user.id:
        flash("You cannot demote yourself.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    user.is_admin = False
    db.session.commit()
    flash(f"User {user.username} demoted from admin.", "success")
    return redirect(url_for('admin_panel'))

@app.route("/admin/user/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    """Ban a user for one year."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    if user_id == current_user.id:
        flash("You cannot ban yourself.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    # Ban for one year
    user.ban_until = datetime.utcnow() + timedelta(days=365)
    db.session.commit()
    
    # Send appeal notification email
    try:
        appeal_link = url_for('submit_appeal', _external=True)
        email_body = generate_ban_appeal_email(user.username, appeal_link)
        msg = Message(
            subject='Account Suspension Notice - Appeal Process Available',
            body=email_body,
            recipients=[user.email]
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending ban notification email: {e}")
    
    flash(f"User {user.username} has been banned for one year.", "warning")
    return redirect(url_for('admin_panel'))

@app.route("/admin/user/<int:user_id>/ban-permanent", methods=["POST"])
@admin_required
def ban_user_permanently(user_id):
    """Permanently ban a user."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    if user_id == current_user.id:
        flash("You cannot ban yourself.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    user.is_permanently_banned = True
    db.session.commit()
    
    # Send appeal notification email
    try:
        appeal_link = url_for('submit_appeal', _external=True)
        email_body = generate_ban_appeal_email(user.username, appeal_link)
        msg = Message(
            subject='Permanent Account Suspension Notice - Appeal Process Available',
            body=email_body,
            recipients=[user.email]
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending permanent ban notification email: {e}")
    
    flash(f"User {user.username} has been permanently banned.", "danger")
    return redirect(url_for('admin_panel'))

@app.route("/admin/user/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    """Delete a user from the system."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    if user_id == current_user.id:
        flash("You cannot delete yourself.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f"User {username} has been deleted from the system.", "success")
    return redirect(url_for('admin_panel'))

@app.route("/admin/messages")
@admin_required
def admin_messages():
    """View all user messages for the admin."""
    messages = AdminMessage.query.order_by(AdminMessage.created_at.desc()).all()
    return render_template("admin/messages.html", messages=messages)

@app.route("/admin/message/<int:message_id>/respond", methods=["GET", "POST"])
@admin_required
def respond_to_message(message_id):
    """Admin responds to a user message."""
    message = AdminMessage.query.get(message_id)
    if not message:
        flash("Message not found.", "danger")
        return redirect(url_for('admin_messages'))
    
    form = AdminMessageForm()
    if form.validate_on_submit():
        message.admin_response = form.message.data
        message.admin_response_date = datetime.utcnow()
        message.is_read = True
        db.session.commit()
        flash("Response sent to user.", "success")
        return redirect(url_for('admin_messages'))
    
    message.is_read = True
    db.session.commit()
    return render_template("admin/respond_message.html", message=message, form=form)

@app.route("/user/messages")
@login_required
def user_messages():
    """View all messages sent to/from the admin for the current user."""
    user_id = session.get("user_id")
    messages = AdminMessage.query.filter_by(user_id=user_id).order_by(AdminMessage.created_at.desc()).all()
    return render_template("user_messages.html", messages=messages)

@app.route("/user/send-message", methods=["GET", "POST"])
@login_required
def send_user_message():
    """User sends a message to admin."""
    form = UserMessageForm()
    if form.validate_on_submit():
        user_id = session.get("user_id")
        message = AdminMessage(
            user_id=user_id,
            subject=form.subject.data,
            message=form.message.data,
            message_type=form.message_type.data
        )
        db.session.add(message)
        db.session.commit()
        flash("Your message has been sent to the admin.", "success")
        return redirect(url_for('user_messages'))
    
    return render_template("send_user_message.html", form=form)

@app.route("/appeal", methods=["GET", "POST"])
def submit_appeal():
    """Submit an appeal for a ban."""
    user_id = session.get("user_id")
    
    if not user_id:
        flash("You must be logged in to submit an appeal.", "warning")
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))
    
    # Check if user is banned
    if not (user.is_permanently_banned or (user.ban_until and user.ban_until > datetime.utcnow())):
        flash("Your account is not currently banned.", "info")
        return redirect(url_for('index'))
    
    # Check if user already has a pending appeal
    existing_appeal = UserAppeal.query.filter_by(user_id=user_id, status='pending').first()
    if existing_appeal:
        flash("You already have a pending appeal. Please wait for a response.", "info")
        return redirect(url_for('index'))
    
    form = AppealForm()
    if form.validate_on_submit():
        appeal = UserAppeal(
            user_id=user_id,
            appeal_text=form.appeal_text.data,
            status='pending'
        )
        db.session.add(appeal)
        db.session.commit()
        flash("Your appeal has been submitted. Our admin team will review it shortly.", "success")
        return redirect(url_for('index'))
    
    return render_template("users/appeal.html", form=form, user=user)

@app.route("/admin/appeal/<int:appeal_id>/approve", methods=["POST"])
@admin_required
def approve_appeal(appeal_id):
    """Admin approves a ban appeal and lifts the ban."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    appeal = UserAppeal.query.get(appeal_id)
    if not appeal:
        flash("Appeal not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(appeal.user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    # Lift the ban
    user.ban_until = None
    user.is_permanently_banned = False
    appeal.status = 'approved'
    appeal.admin_response_date = datetime.utcnow()
    db.session.commit()
    
    # Send ban lifted email
    try:
        email_body = generate_ban_lifted_email(user.username)
        msg = Message(
            subject='Your Account Suspension Has Been Lifted',
            body=email_body,
            recipients=[user.email]
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending ban lifted email: {e}")
    
    flash(f"Appeal approved. Ban lifted for user {user.username}.", "success")
    return redirect(url_for('admin_panel'))

@app.route("/admin/appeal/<int:appeal_id>/reject", methods=["POST"])
@admin_required
def reject_appeal(appeal_id):
    """Admin rejects a ban appeal."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    appeal = UserAppeal.query.get(appeal_id)
    if not appeal:
        flash("Appeal not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    appeal.status = 'rejected'
    appeal.admin_response_date = datetime.utcnow()
    db.session.commit()
    
    flash("Appeal rejected.", "warning")
    return redirect(url_for('admin_panel'))

@app.route("/admin/user/<int:user_id>/remove-ban", methods=["POST"])
@admin_required
def remove_user_ban(user_id):
    """Admin removes a ban from a user."""
    current_user = User.query.get(session.get("user_id"))
    if not current_user or not current_user.is_admin:
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for('admin_panel'))
    
    if user_id == current_user.id:
        flash("You cannot remove your own ban.", "warning")
        return redirect(url_for('admin_panel'))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))
    
    # Remove the ban
    user.ban_until = None
    user.is_permanently_banned = False
    db.session.commit()
    
    # Send ban lifted email
    try:
        email_body = generate_ban_lifted_email(user.username)
        msg = Message(
            subject='Your Account Suspension Has Been Lifted',
            body=email_body,
            recipients=[user.email]
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending ban lifted email: {e}")
    
    flash(f"Ban lifted for user {user.username}.", "success")
    return redirect(url_for('admin_panel'))
