"""Forms for cocktail app."""

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, IntegerField, BooleanField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, InputRequired, Length, EqualTo, Optional

class RegisterForm(FlaskForm):
    """Form for registering a user."""
    email = EmailField("email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo('confirm', message='Passwords must match') ])
    confirm  = PasswordField('Repeat Password')
   

class LoginForm(FlaskForm):
    """Form for registering a user."""

    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

class IngredientForm(FlaskForm):
    id = IntegerField("id", validators=[Optional()])
    name = StringField("name", validators=[InputRequired()])
    is_alcohol = BooleanField("Is it alcohol?", validators=[Optional()])

class CocktailForm(FlaskForm):
    ingredient = TextAreaField("Ingredient Name", validators=[Optional()])
    cocktailname = StringField("Cocktail Name", validators=[InputRequired()])
    instructions = TextAreaField("Preparation Instructions", validators=[Optional()])

class NewIngredientForCocktailForm(FlaskForm):
    """Form for adding an ingredient to a cocktail."""

class SearchIngredientsForm(FlaskForm):
    """Form for searching music"""
    name = StringField("Search for song or word on a song", validators=[InputRequired()] )

class DeleteForm(FlaskForm):
    """Delete form -- this form is intentionally blank."""