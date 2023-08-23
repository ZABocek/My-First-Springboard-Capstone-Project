"""Forms for cocktail app."""

from wtforms import SelectField
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, BooleanField, PasswordField
from wtforms.validators import InputRequired, Length, NumberRange, URL, Optional

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8)])
    email = StringField('E-mail', validators=[DataRequired(), Email()])

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8)])

class SearchCocktailsForm(FlaskForm):
    ingredient = StringField("Ingredient Name", validators=[InputRequired()])
    cocktailname = StringField("Cocktail Name", required=False)

class AddCocktailToAccountForm(FlaskForm):
    cocktailname = StringField("Cocktail Name", validators=[InputRequired()])

class AddNewCocktailForm(FlaskForm):
    cocktailname = StringField("Cocktail Name", validators=[InputRequired()])
    ingredient = StringField("Ingredient Name", validators=[InputRequired()])
    instructions = TextAreaField("Preparation Instructions", validators=[InputRequired()])
