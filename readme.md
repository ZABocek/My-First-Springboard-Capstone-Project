app.py contains:
def homepage():
    """Show homepage with links to site areas."""
def register():
    """Register user: produce form & handle form submission."""
def profile(user_id):
    """Page where user selects their preferred ingredients and whether they prefer alcohol"""
def list_cocktails():
    """Place where users can go to see cocktails in a dropdown menu"""
def cocktail_details(cocktail_id):
    """Place where user can explore available cocktails in API"""
async def add_api_cocktails():
    """Add API cocktails to user's account"""
def my_cocktails():
    """User views cocktails on their account"""
def process_and_store_new_cocktail(cocktail_api, user_id):
    """Helper function that assists in adding API cocktail to user's account"""
You can also add user's own original cocktail, edit cocktail information, including picture, log in if user already exists.
cocktaildb_api.py contains essential functions in order for app.py functions to be able to retrieve and store cocktails from API onto user's account.
forms.py supplies the necessary WTF forms for each web page.
helpers.py contains helper function def first().
models.py contains all of the database models used to complete tables showing user account information. All relationships between the tables are stored here.
User can pay for API service if they wish and then change the base url for each function that uses it, but I stuck with the free version. 
Also, I never made use of the Gunicorn tool to assist my app, so the user can implement the Procfile by writing additional code or deleting it.
The requirements.txt file is essential in order for this application to run successfully. User will have to install all necessary requirements in order to run this application from their terminal. They will need Flask, SQL Alchemy, PostgresQL, Jinja 2, WTF Forms, Python, JavaScript, and various other installments in order for this application to work. They can also change the name of their own database to their liking if they wish.
Using the free VS Code that comes with Microsoft computers can prove greatly beneficial if you want to install all the requirements. I would also recommend setting up a free GitHub account and knowing how to write basic Bash code in your terminal. Using Ubuntu as the default Operating System in your terminal may also make it easier to run this Flask application, after you set up a virtual environment in which to run the application, of course.
Happy cocktail searching!! Enjoy the app if you choose to use it!