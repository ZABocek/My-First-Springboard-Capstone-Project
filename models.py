
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
import logging
bcrypt = Bcrypt()
db = SQLAlchemy()
logging.basicConfig(level=logging.DEBUG)
def connect_db(app):
    """Connect to database."""

    db.app = app
    db.init_app(app)

class User(db.Model):
    """User in the system."""

    __tablename__ = "user"
    
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )
    
    password = db.Column(
        db.Text,
        nullable=False,
    )
    
    preference = db.Column(
        db.String,
        nullable=True,
        default='alcoholic'
    )
    
    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"
    
    @classmethod
    def register(cls, username, email, password):
        """Sign up user. Hashes password and adds user to system."""
        try:
            hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
            user = cls(username=username, email=email, password=hashed_pwd)
            logging.debug(f"User registered: {user}")
            return user
        except Exception as e:
            logging.error(f"Error registering user: {e}")
            raise

    @classmethod
    def authenticate(cls, username, password):
        """Validate that user exists & password is correct.
        
        Return user if valid; else return False."""

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False
    
    def add_preference(self, preference):
        """Add preference to the user"""
        try:
            self.preference = preference
            db.session.commit()
            logging.debug(f"Preference updated: {self}")
        except Exception as e:
            logging.error(f"Error updating preference: {e}")
            db.session.rollback()
            raise
        
    user_favorite_ingredients = db.relationship('UserFavoriteIngredients', backref='user')

   
class Ingredient(db.Model):
    """Ingredients from the API that the user can select"""

    __tablename__ = "ingredient"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    name = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    user_favorite_ingredients = db.relationship('UserFavoriteIngredients', backref='ingredient')

class Cocktail(db.Model):
    """Cocktails a user selects for their account or self-made coctails, can also enter instructions for how to make, and have the option of labeling cocktail as sweet or dry"""

    __tablename__ = "cocktails"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    name = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    instructions = db.Column(
        db.Text,
        nullable=True,
    )

    ct_users2 = db.relationship('Cocktails_Users', backref='cocktails')
    
class Cocktails_Ingredients(db.Model):
    """binds cocktails table and ingredients table together and allows user to select quantity"""

    __tablename__ = "cocktails_ingredients"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    cocktail_id = db.Column(
        db.Integer,
        db.ForeignKey('cocktails.id'),
    )

    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey('ingredient.id'),
    )

    quantity = db.Column(
        db.Text,
        nullable=False,
    )

class Cocktails_Users(db.Model):
    """This table is set up so that users can create their own cocktails if they want to."""
        
    __tablename__ = "cocktails_users"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        primary_key=True
    )
    cocktail_id = db.Column(
        db.Integer,
        db.ForeignKey('cocktails.id'),
        primary_key=True
    )

    
class UserFavoriteIngredients(db.Model):
    """This table is so users can save their favorite ingredients for making cocktails in their account"""
    
    __tablename__ = "user_favorite_ingredients"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        primary_key=True
    )

    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey('ingredient.id'),
        primary_key=True
    )