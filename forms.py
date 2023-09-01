"""Forms for cocktail app."""

from wtforms import SelectField
from flask_wtf import FlaskForm
from wtforms import validators, StringField, EmailField, IntegerField, SelectField, TextAreaField, BooleanField, PasswordField
from wtforms.validators import InputRequired, Length, NumberRange, URL, Optional

class RegisterForm(FlaskForm):
    username = StringField("username", validators=[InputRequired()])
    password = PasswordField("password", validators=[InputRequired(), Length(min=8)])
    email = EmailField('E-mail', validators=[InputRequired()])

class LoginForm(FlaskForm):
    username = StringField("username", validators=[InputRequired()])
    password = PasswordField("password", validators=[InputRequired(), Length(min=8)])
    
class IngredientForm(FlaskForm):
    id = IntegerField("id")
    name = StringField("name")
    is_alcohol = BooleanField("is_alcohol")

class SearchCocktailsForm(FlaskForm):
    ingredient = StringField("Ingredient Name", required=False)
    cocktailname = StringField("Cocktail Name", required=False)
    instructions = TextAreaField("Preparation Instructions", required=False)

class AddNewCocktailForm(FlaskForm):
    cocktailname = StringField("Cocktail Name", validators=[InputRequired()])
    ingredient = StringField("Ingredient Name", validators=[InputRequired()])
    instructions = TextAreaField("Preparation Instructions", validators=[InputRequired()])
