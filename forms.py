from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, FieldList,TextAreaField, FormField, SubmitField
from wtforms.validators import DataRequired, Email, InputRequired, Length, EqualTo, Optional

class RegisterForm(FlaskForm):
    """Form for registering a user."""
    email = StringField("email", validators=[DataRequired(), Email()])
    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo('confirm', message='Passwords must match') ])
    confirm  = PasswordField('Repeat Password')

class LoginForm(FlaskForm):

    username = StringField("Username", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])
    
class PreferenceForm(FlaskForm):
    preference = SelectField('Preference', choices=[('alcoholic', 'Alcoholic'), ('non-alcoholic', 'Non-Alcoholic')], validators=[InputRequired()])

class UserFavoriteIngredientForm(FlaskForm):
    ingredient = SelectField('Ingredient', choices=[])  # You will populate choices dynamically from your ingredients table
    add_ingredient = SubmitField('Add Ingredient')

class IngredientForm(FlaskForm):
    ingredient = SelectField('Ingredient', choices=[])
    measure = StringField('Measure', validators=[DataRequired()])  # Changed from quantity to measure

class CocktailForm(FlaskForm):
    pre_existing_cocktail = SelectField('Pre-existing Cocktail', coerce=int)  # This is for cocktails from the API
    name = StringField('Cocktail Name', validators=[DataRequired()])
    ingredients = FieldList(FormField(IngredientForm), min_entries=1, max_entries=10)
    instructions = TextAreaField('Instructions')
    submit = SubmitField('Add Cocktail')
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])

class ListCocktailsForm(FlaskForm):
    cocktail = SelectField('Select Cocktail', coerce=int)
    submit = SubmitField('View Details')
    
class OriginalCocktailForm(FlaskForm):
    image = FileField('Upload Cocktail Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'), Optional()])
    name = StringField('Cocktail Name', validators=[DataRequired()])
    ingredients = FieldList(StringField('Ingredient', validators=[DataRequired()]), min_entries=1, max_entries=10)
    measures = FieldList(StringField('Measure', validators=[DataRequired()]), min_entries=1, max_entries=10)
    instructions = TextAreaField('Instructions', validators=[DataRequired()])
    submit = SubmitField('Add Original Cocktail')
    
class EditCocktailForm(FlaskForm):
    image = FileField('Upload Cocktail Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'), Optional()])
    # Add the same fields as in your OriginalCocktailForm, or adjust as necessary for editing.
    name = StringField('Cocktail Name', validators=[DataRequired()])
    ingredients = FieldList(StringField('Ingredient', validators=[DataRequired()]), min_entries=1, max_entries=10)
    measure = FieldList(StringField('Measure', validators=[DataRequired()]), min_entries=1, max_entries=10)
    instructions = TextAreaField('Instructions', validators=[DataRequired()])                
    submit = SubmitField('Update Cocktail')