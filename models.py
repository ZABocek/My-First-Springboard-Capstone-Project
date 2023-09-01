from datetime import datetime
from operator import length_hint
from turtle import title
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

bcrypt = Bcrypt()
db = SQLAlchemy()

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

    cocktails1 = db.relationship('Cocktails', secondary='cocktails_users', backref='user')
    ct_users = db.relationship('Cocktails_Users', backref='user')
    use_fav_ingr = db.relationship('UserFavoriteIngredients', backref='user')
    
    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"
    
    @classmethod
    def signup(cls, username, email, password):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
        )

        db.session.add(user)
        return user
    
    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If can't find matching user (or if password is wrong), returns False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False
    
class Ingredients(db.Model):
    """Ingredients from the API that the user can select"""

    __tablename__ = "ingredients"

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

    is_alcohol = db.Column(
        db.Boolean,
        nullable=True,
    )

    ct_ingr = db.relationship('Cocktails_Ingredients', backref='ingredients')
    use_fav_ingr2 = db.relationship('UserFavoriteIngredients', backref='ingredients')

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

    sweet = db.Column(
        db.Boolean,
        nullable=True,
    )

    user1 = db.relationship('User', backref='cocktails')
    ct_users2 = db.relationship('Cocktails_Users', backref='cocktails')
    ct_ingr2 = db.relationship('Cocktails_Ingredients', backref='cocktails')

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
        db.ForeignKey('ingredients.id'),
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
    )

    cocktail_id = db.Column(
        db.Integer,
        db.ForeignKey('cocktails.id'),
    )
    
    user2 = db.relationship('User', backref='cocktails_users')
    ct_users3 = db.relationship('Cocktail', backref='cocktails_users')

class UserFavoriteIngredients(db.Model):
    """This table is so users can save their favorite ingredients for making cocktails in their account"""
    
    __tablename__ = "user_favorite_ingredients"

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
    )

    ingredient_id = db.Column(
        db.Integer,
        db.ForeignKey('ingredients.id')
    )

def connect_db(app):
    """Connect this database to provided Flask app. 
    You should call this in your Flask app."""

    db.app = app
    db.init_app(app)