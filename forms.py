"""Forms for cocktail app."""

from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, IntegerField, BooleanField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Email, InputRequired, Length, EqualTo, Optional

class RegisterForm(FlaskForm):
    """Form for registering a user."""

    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo('confirm', message='Passwords must match') ])
    confirm  = PasswordField('Repeat Password')
    email = EmailField("email", validators=[DataRequired(), Email()])


class LoginForm(FlaskForm):
    """Form for registering a user."""

    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])

class IngredientForm(FlaskForm):
    id = IntegerField("id", validators=[Optional()])
    name = TextAreaField("name", validators=[InputRequired()])
    is_alcohol = BooleanField("Is it alcohol?", validators=[Optional()])

class AddCocktailToAccountForm(FlaskForm):
    ingredient = TextAreaField("Ingredient Name", validators=[Optional()])
    cocktailname = StringField("Cocktail Name", validators=[InputRequired()])
    instructions = TextAreaField("Preparation Instructions", validators=[Optional()])

class AddNewCocktailForm(FlaskForm):
    cocktailname2 = StringField("New Cocktail Name", validators=[InputRequired()])
    ingredient2 = TextAreaField("Ingredient Names", validators=[InputRequired()])
    instructions2 = TextAreaField("Preparation Instructions", validators=[Optional()])
