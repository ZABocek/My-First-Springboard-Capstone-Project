import unittest
from app import app, db, init_db
from models import User, Ingredient, Cocktail, Cocktails_Users, Cocktails_Ingredients

class FlaskTestCase(unittest.TestCase):
    def setUp(self):
        """Set up the test client and initialize the database"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = app.test_client()
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Tear down the database after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_register_user(self):
        """Test user registration"""
        with app.app_context():
            user = User.register(username='testuser', email='test@example.com', password='testpassword')
            db.session.add(user)
            db.session.commit()
            
            # Verify user was created
            check_user = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(check_user)
            self.assertEqual(check_user.email, 'test@example.com')

    def test_login_user(self):
        """Test user login"""
        with app.app_context():
            # First, register the user
            user = User.register(username='testuser', email='test@example.com', password='testpassword')
            db.session.add(user)
            db.session.commit()
            
            # Try to authenticate
            authenticated_user = User.authenticate(username='testuser', password='testpassword')
            self.assertIsNotNone(authenticated_user)
            self.assertEqual(authenticated_user.username, 'testuser')
            
            # Try with wrong password
            wrong_auth = User.authenticate(username='testuser', password='wrongpassword')
            self.assertFalse(wrong_auth)

    def test_add_ingredient(self):
        """Test adding an ingredient"""
        with app.app_context():
            ingredient = Ingredient(name='Vodka')
            db.session.add(ingredient)
            db.session.commit()
            
            # Verify ingredient was created
            check_ingredient = Ingredient.query.filter_by(name='Vodka').first()
            self.assertIsNotNone(check_ingredient)
            self.assertEqual(check_ingredient.name, 'Vodka')

    def test_add_cocktail(self):
        """Test adding a cocktail"""
        import time
        with app.app_context():
            cocktail_name = f'Test Cocktail {int(time.time())}'
            cocktail = Cocktail(name=cocktail_name, instructions='Shake well')
            db.session.add(cocktail)
            db.session.commit()
            
            # Verify cocktail was created
            check_cocktail = Cocktail.query.filter_by(name=cocktail_name).first()
            self.assertIsNotNone(check_cocktail)
            self.assertEqual(check_cocktail.instructions, 'Shake well')

    def test_cocktail_ingredient_relationship(self):
        """Test the relationship between cocktails and ingredients"""
        with app.app_context():
            # Create ingredient
            ingredient = Ingredient(name='Vodka')
            db.session.add(ingredient)
            db.session.commit()
            
            # Create cocktail
            cocktail = Cocktail(name='Vodka Tonic', instructions='Mix well')
            db.session.add(cocktail)
            db.session.commit()
            
            # Create relationship
            assoc = Cocktails_Ingredients(cocktail_id=cocktail.id, ingredient_id=ingredient.id, quantity='1 oz')
            db.session.add(assoc)
            db.session.commit()
            
            # Verify relationship
            check_assoc = Cocktails_Ingredients.query.filter_by(cocktail_id=cocktail.id).first()
            self.assertIsNotNone(check_assoc)
            self.assertEqual(check_assoc.quantity, '1 oz')

if __name__ == '__main__':
    unittest.main()
