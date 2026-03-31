from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
import logging

# Initialize Bcrypt for hashing passwords
bcrypt = Bcrypt()
# Initialize SQLAlchemy for database interactions
db = SQLAlchemy()
# Configure logging to display debug messages
logging.basicConfig(level=logging.DEBUG)


def connect_db(app):
    """Bind the SQLAlchemy instance to the Flask app."""
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
    
    is_admin = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    
    ban_until = db.Column(
        db.DateTime,
        nullable=True,
        default=None
    )
    
    is_permanently_banned = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    is_email_verified = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    
    email_verified_at = db.Column(
        db.DateTime,
        nullable=True,
        default=None
    )
    
    # Relationship to admin messages
    admin_messages = db.relationship('AdminMessage', foreign_keys='AdminMessage.user_id', backref='user', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"
    
    @classmethod
    def register(cls, username, email, password):
        """Sign up user. Hashes password and adds user to system."""
        try:
            # Hash the user's password
            hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
            # Create a new user instance with the hashed password
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
        # Query the database for a user with the given username
        user = cls.query.filter_by(username=username).first()

        if user:
            # Check if the provided password matches the stored hashed password
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False
    
    def generate_email_verification_token(self, expires_in=86400):
        """Generate a signed token for email verification (valid for 24 h by default)."""
        from flask import current_app
        from itsdangerous import URLSafeTimedSerializer
        try:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            return s.dumps(self.email, salt='email-verification')
        except Exception as e:
            logging.error(f"Error generating email verification token: {e}")
            raise

    @staticmethod
    def verify_email_token(token, expires_in=86400):
        """Verify a signed email-verification token; return the email or None."""
        from flask import current_app
        from itsdangerous import URLSafeTimedSerializer
        try:
            s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
            return s.loads(token, salt='email-verification', max_age=expires_in)
        except Exception as e:
            logging.error(f"Error verifying email token: {e}")
            return None
    
    def mark_email_verified(self):
        """Mark the user's email as verified."""
        try:
            self.is_email_verified = True
            self.email_verified_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.session.commit()
            logging.debug(f"Email verified for user: {self}")
        except Exception as e:
            logging.error(f"Error marking email as verified: {e}")
            db.session.rollback()
            raise
    
    def add_preference(self, preference):
        """Update the user's cocktail preference."""
        try:
            self.preference = preference
            db.session.commit()
            logging.debug(f"Preference updated: {self}")
        except Exception as e:
            logging.error(f"Error updating preference: {e}")
            db.session.rollback()
            raise
        
    # Define the relationship between User and UserFavoriteIngredients
    user_favorite_ingredients = db.relationship('UserFavoriteIngredients', backref='user', cascade="all, delete-orphan")
    # Define the relationship between User and Cocktails_Users
    # Issue #10: cascade="all" (includes delete) ensures Cocktails_Users rows are removed
    # when a User is deleted. delete-orphan is intentionally omitted here to avoid
    # a SQLAlchemy conflict with the authoritative cascade on Cocktail.ct_users2.
    cocktails_relation = db.relationship('Cocktails_Users', backref='user', cascade="all")
    # Issue #10: cascade appeals so no orphan appeal rows remain after a user deletion.
    user_appeals = db.relationship('UserAppeal', foreign_keys='UserAppeal.user_id', backref='appeal_owner', cascade="all, delete-orphan")

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
    # Define the relationship between Ingredient and UserFavoriteIngredients
    user_favorite_ingredients = db.relationship('UserFavoriteIngredients', backref='ingredient', cascade="all, delete-orphan")

class Cocktail(db.Model):
    """Cocktails a user selects for their account or self-made cocktails, can also enter instructions for how to make, and have the option of labeling cocktail as sweet or dry"""
    __tablename__ = "cocktails"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    name = db.Column(
        db.Text,
        nullable=False,
    )

    instructions = db.Column(
        db.Text,
        nullable=True,
    )
    
    strDrinkThumb = db.Column(
        db.String, 
        nullable=True
    )

    image_url = db.Column(
        db.String,
        nullable=True
    )
    
    is_api_cocktail = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )

    # Stable external identifier from TheCocktailDB (idDrink).  Stored so that
    # deduplication of shared API rows uses a robust key instead of the drink
    # name, which may change or collide.
    api_cocktail_id = db.Column(
        db.String,
        nullable=True,
        unique=False,  # uniqueness enforced in service layer (is_api_cocktail=True scope)
        index=True,
    )

    # owner_id is set for user-created / user-edited cocktails so that
    # personal copies of API cocktails are clearly owned and can be found
    # without relying on a name match across all users.
    owner_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True,
        default=None,
    )

    # Define the relationship between Cocktail and Cocktails_Users
    # Issue #10: cascade="all, delete-orphan" removes join-table rows when a Cocktail is deleted.
    ct_users2 = db.relationship('Cocktails_Users', backref='cocktails', cascade="all, delete-orphan")
    # Define the relationship between Cocktail and Cocktails_Ingredients
    # Issue #10: cascade="all, delete-orphan" removes ingredient associations when a Cocktail is deleted.
    ingredients_relation = db.relationship('Cocktails_Ingredients', backref='cocktail', cascade="all, delete-orphan")

class Cocktails_Ingredients(db.Model):
    """Binds cocktails table and ingredients table together and allows user to select quantity"""
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
    
    # Define the relationship between Cocktails_Ingredients and Ingredient
    ingredient = db.relationship('Ingredient', backref='cocktails_ingredients')

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

class AdminMessage(db.Model):
    """Messages between admin and users for warnings, suggestions, and incident reports"""
    __tablename__ = "admin_message"
    
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )
    
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False,
    )
    
    subject = db.Column(
        db.String(255),
        nullable=False,
    )
    
    message = db.Column(
        db.Text,
        nullable=False,
    )
    
    message_type = db.Column(
        db.String(50),
        nullable=False,
        default='user_report'
    )
    
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    is_read = db.Column(
        db.Boolean,
        nullable=False,
        default=False
    )
    
    admin_response = db.Column(
        db.Text,
        nullable=True,
        default=None
    )
    
    admin_response_date = db.Column(
        db.DateTime,
        nullable=True,
        default=None
    )
    
    def __repr__(self):
        return f"<AdminMessage #{self.id}: from {self.user_id} - {self.subject}>"
class UserAppeal(db.Model):
    """Appeals submitted by banned users requesting removal of their ban"""
    __tablename__ = "user_appeal"
    
    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )
    
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False,
    )
    
    appeal_text = db.Column(
        db.Text,
        nullable=False,
    )
    
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    
    status = db.Column(
        db.String(50),
        nullable=False,
        default='pending'  # pending, approved, rejected
    )
    
    admin_response = db.Column(
        db.Text,
        nullable=True,
        default=None
    )
    
    admin_response_date = db.Column(
        db.DateTime,
        nullable=True,
        default=None
    )
    
    def __repr__(self):
        return f"<UserAppeal #{self.id}: from {self.user_id} - {self.status}>"


class AdminAuditLog(db.Model):
    """Issue #9: Central audit trail for all admin actions.

    Rows are retained even when the acting admin or target user is later
    deleted (FKs use ON DELETE SET NULL so no orphan errors occur).
    """
    __tablename__ = "admin_audit_log"

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
    )

    # The admin who performed the action; set to NULL if that user is deleted.
    admin_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
    )

    action = db.Column(
        db.String(100),
        nullable=False,
    )

    # The user the action was performed on; set to NULL if that user is deleted.
    target_user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id', ondelete='SET NULL'),
        nullable=True,
    )

    details = db.Column(
        db.Text,
        nullable=True,
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def __repr__(self):
        return f"<AdminAuditLog #{self.id}: {self.action} by admin={self.admin_id}>"