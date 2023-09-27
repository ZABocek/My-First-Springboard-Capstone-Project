"""Forms for cocktail app."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FieldList,TextAreaField, FormField, SubmitField
from wtforms.validators import DataRequired, Email, InputRequired, Length, EqualTo

class RegisterForm(FlaskForm):
    """Form for registering a user."""
    email = StringField("email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo('confirm', message='Passwords must match') ])
    confirm  = PasswordField('Repeat Password')

class LoginForm(FlaskForm):
    """Form for registering a user."""

    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    
class PreferenceForm(FlaskForm):
    preference = SelectField('Preference', choices=[('alcoholic', 'Alcoholic'), ('non-alcoholic', 'Non-Alcoholic')], validators=[InputRequired()])

class UserFavoriteIngredientForm(FlaskForm):
    ingredient = SelectField('Ingredient', choices=[])  # You will populate choices dynamically from your ingredients table
    add_ingredient = SubmitField('Add Ingredient')

class IngredientForm(FlaskForm):
    ingredient = SelectField('Ingredient', choices=[])
    quantity = StringField('Quantity', validators=[DataRequired()])

class CocktailForm(FlaskForm):
    name = StringField('Cocktail Name', validators=[DataRequired()])
    ingredients = FieldList(FormField(IngredientForm), min_entries=1, max_entries=10)
    instructions = TextAreaField('Instructions')
    submit = SubmitField('Add Cocktail')

