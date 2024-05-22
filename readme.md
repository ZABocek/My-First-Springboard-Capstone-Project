# Cocktail Recipe App

## Overview

The Cocktail Recipe App is a web application that allows users to discover, create, and save cocktail recipes. Users can register an account, log in, and manage their favorite ingredients and cocktail preferences. The app fetches cocktail data from an external API and allows users to add their own cocktail recipes, complete with instructions and images.

## Features

- **User Registration and Authentication**: Users can sign up, log in, and log out.
- **Profile Management**: Users can select their preferred ingredients and update their preferences for alcoholic or non-alcoholic cocktails.
- **Discover Cocktails**: Users can browse a list of cocktails fetched from an external API.
- **Cocktail Details**: Users can view detailed information about each cocktail, including ingredients and instructions.
- **Add API Cocktails**: Users can add cocktails from the API to their personal collection.
- **Create Original Cocktails**: Users can create and save their own cocktail recipes, including uploading images.
- **Edit Cocktails**: Users can edit their saved cocktail recipes.
- **Favorite Ingredients**: Users can save their favorite ingredients for easy reference.

## Installation

1. **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd SpringboardFirstCapstoneProject
    ```

2. **Set up the virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables**:
    Create a `.env` file in the root directory with the following content:
    ```env
    FLASK_APP=app.py
    FLASK_ENV=development
    SECRET_KEY=your_secret_key
    DATABASE_URL=postgresql:///name_your_poison
    ```

5. **Initialize the database**:
    ```bash
    flask db upgrade
    ```

6. **Run the application**:
    ```bash
    flask run
    ```

## File Structure

- `app.py`: Main application file. Defines routes and core functionality.
- `cocktaildb_api.py`: Handles interactions with the external cocktail API.
- `forms.py`: Defines the forms used for user input.
- `models.py`: Defines the database models and relationships.
- `static/`: Contains static files such as CSS.
- `templates/`: Contains HTML templates for rendering views.

## Detailed File Descriptions

### `app.py`

This file is the main entry point for the Flask application. It initializes the app, sets configuration variables, connects to the database, and defines the routes for various functionalities such as registration, login, viewing and managing cocktails, and more.

### `cocktaildb_api.py`

This file contains functions to interact with the external cocktail API. It includes functions to search for ingredients, list ingredients, get cocktail details, and more. The file utilizes asynchronous requests to efficiently fetch data from the API.

### `forms.py`

This file defines the forms used for user input throughout the application. It includes forms for user registration, login, managing preferences, adding ingredients, and creating or editing cocktails. The forms use Flask-WTF for validation and handling form submissions.

### `models.py`

This file defines the database models and their relationships using SQLAlchemy. It includes models for users, ingredients, cocktails, and the relationships between them. The file also includes methods for user authentication, registration, and updating preferences.

## API Integration

The application integrates with the [CocktailDB API](https://www.thecocktaildb.com/api.php) to fetch cocktail data. Functions in `cocktaildb_api.py` handle requests to the API and process the responses to retrieve and sort ingredients and cocktail details.

## Usage

1. **Register and Log In**: Start by creating an account and logging in.
2. **Manage Profile**: Select your preferred ingredients and set your preference for alcoholic or non-alcoholic cocktails.
3. **Discover Cocktails**: Browse the list of available cocktails from the external API.
4. **View Cocktail Details**: Click on a cocktail to view detailed information including ingredients and instructions.
5. **Add API Cocktails**: Add cocktails from the API to your personal collection.
6. **Create Original Cocktails**: Use the form to create and save your own cocktail recipes.
7. **Edit Cocktails**: Edit your saved cocktails to update the ingredients or instructions.

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Springboard](https://www.springboard.com/) for the capstone project guidelines.
- [TheCocktailDB](https://www.thecocktaildb.com/) for the cocktail data API.
- [Flask](https://flask.palletsprojects.com/) for the web framework.
- [SQLAlchemy](https://www.sqlalchemy.org/) for the ORM.
- [Flask-WTF](https://flask-wtf.readthedocs.io/) for form handling.

