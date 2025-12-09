# Import necessary libraries and modules
from flask_wtf import FlaskForm
# Import FlaskForm to create forms
from flask_wtf.file import FileField, FileAllowed
# Import FileField to handle file uploads and FileAllowed to validate file types
from wtforms import StringField, PasswordField, SelectField, FieldList, TextAreaField, FormField, SubmitField
# Import various field types and validators from wtforms
from wtforms.validators import DataRequired, Email, InputRequired, Length, EqualTo, Optional
# Import validators to enforce rules on form fields

# Define a form for admin panel unlock
class AdminForm(FlaskForm):
    """Form for unlocking the admin panel."""
    admin_key = PasswordField("Admin Password Key", validators=[DataRequired()])
    # Password field for the admin unlock key
    submit = SubmitField('Unlock Admin Panel')
    # Submit button for unlocking the admin panel

# Define a form for user registration
class RegisterForm(FlaskForm):
    """Form for registering a user."""
    email = StringField("Email", validators=[DataRequired(), Email()])
    # Email field with data required and email validation
    username = StringField("Username", validators=[InputRequired()])
    # Username field with input required validation
    password = PasswordField("Password", validators=[InputRequired(), Length(min=8), EqualTo('confirm', message='Passwords must match')])
    # Password field with input required, minimum length, and confirmation validation
    confirm  = PasswordField('Repeat Password')
    # Confirm password field to match the password

# Define a form for user login
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired()])
    # Username field with input required validation
    password = PasswordField("Password", validators=[InputRequired()])
    # Password field with input required validation

# Define a form for selecting user preferences (alcoholic or non-alcoholic)
class PreferenceForm(FlaskForm):
    preference = SelectField('Preference', choices=[('alcoholic', 'Alcoholic'), ('non-alcoholic', 'Non-Alcoholic')], validators=[InputRequired()])
    # Select field for preference with predefined choices and input required validation

# Define a form for adding user's favorite ingredients
class UserFavoriteIngredientForm(FlaskForm):
    ingredient = SelectField('Ingredient', choices=[])
    # Select field for ingredient, choices to be populated dynamically
    add_ingredient = SubmitField('Add Ingredient')
    # Submit button for adding the ingredient

# Define a form for ingredient details
class IngredientForm(FlaskForm):
    ingredient = StringField('Ingredient', validators=[DataRequired()])
    # String field for ingredient name with data required validation
    measure = StringField('Measure', validators=[DataRequired()])
    # String field for ingredient measure with data required validation

# Define a form for cocktail details
class CocktailForm(FlaskForm):
    pre_existing_cocktail = SelectField('Pre-existing Cocktail', coerce=int)
    # Select field for choosing a pre-existing cocktail
    name = StringField('Cocktail Name', validators=[DataRequired()])
    # String field for cocktail name with data required validation
    ingredients = FieldList(FormField(IngredientForm), min_entries=1, max_entries=10)
    # Field list for multiple ingredient forms
    instructions = TextAreaField('Instructions')
    # Text area field for cocktail instructions
    submit = SubmitField('Add Cocktail')
    # Submit button for adding the cocktail
    image = FileField('Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    # File field for uploading an image with allowed file type validation

# Define a form for listing cocktails
class ListCocktailsForm(FlaskForm):
    cocktail = SelectField('Select Cocktail', coerce=int)
    # Select field for choosing a cocktail
    submit = SubmitField('View Details')
    # Submit button for viewing cocktail details

# Define a form for adding original cocktails
class OriginalCocktailForm(FlaskForm):
    image = FileField('Upload Cocktail Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'), Optional()])
    # File field for uploading an image with allowed file type validation
    name = StringField('Cocktail Name', validators=[DataRequired()])
    # String field for cocktail name with data required validation
    ingredients = FieldList(StringField('Ingredient', validators=[Optional()]), min_entries=1, max_entries=10)
    # Field list for multiple ingredient fields (Optional allows blank entries)
    measures = FieldList(StringField('Measure', validators=[Optional()]), min_entries=1, max_entries=10)
    # Field list for multiple measure fields (Optional allows blank entries)
    instructions = TextAreaField('Instructions', validators=[DataRequired()])
    # Text area field for cocktail instructions
    submit = SubmitField('Add Original Cocktail')
    # Submit button for adding the original cocktail

# Define a form for editing cocktails
class EditCocktailForm(FlaskForm):
    image = FileField('Upload Cocktail Image', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'), Optional()])
    # File field for uploading an image with allowed file type validation
    name = StringField('Cocktail Name', validators=[DataRequired()])
    # String field for cocktail name with data required validation
    ingredients = FieldList(FormField(IngredientForm), min_entries=1, max_entries=10)
    # Field list for multiple ingredient forms
    instructions = TextAreaField('Instructions', validators=[DataRequired()])
    # Text area field for cocktail instructions
    submit = SubmitField('Update Cocktail')
    # Submit button for updating the cocktail

# Define a form for users to send messages to admin
class UserMessageForm(FlaskForm):
    """Form for users to send messages/reports to admin."""
    message_type = SelectField('Message Type', choices=[
        ('suggestion', 'Suggestion'),
        ('bug_report', 'Bug Report'),
        ('incident_report', 'Incident Report')
    ], validators=[DataRequired()])
    # Select field for message type
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=255)])
    # Subject field with length validation
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=5000)])
    # Text area for the message content
    submit = SubmitField('Send Message')
    # Submit button for sending the message

# Define a form for admin to send messages to users
class AdminMessageForm(FlaskForm):
    """Form for admin to send messages/warnings to users."""
    subject = StringField('Subject', validators=[DataRequired(), Length(min=5, max=255)])
    # Subject field with length validation
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=5000)])
    # Text area for the message content
    submit = SubmitField('Send Message')
    # Submit button for sending the message

