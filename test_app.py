import unittest
from app import app, db
from models import User, Ingredient, Cocktail, Cocktails_Users, Cocktails_Ingredients

class FlaskTestCase(unittest.TestCase):
    def setUp(self):
        """Set up the test client and initialize the database"""
        self.app = app.test_client()
        self.app.testing = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///test_name_your_poison'
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Tear down the database after each test"""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_register_user(self):
        """Test user registration"""
        response = self.app.post('/register', data=dict(
            username='testuser',
            password='testpassword',
            email='test@example.com',
            confirm='testpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Preference updated successfully!', response.data)

    def test_login_user(self):
        """Test user login"""
        # First, register the user
        self.app.post('/register', data=dict(
            username='testuser',
            password='testpassword',
            email='test@example.com',
            confirm='testpassword'
        ), follow_redirects=True)
        
        # Then, try to log in
        response = self.app.post('/login', data=dict(
            username='testuser',
            password='testpassword'
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Name Your Poison', response.data)

    def test_add_cocktail(self):
        """Test adding a cocktail"""
        # Register and log in the user
        self.app.post('/register', data=dict(
            username='testuser',
            password='testpassword',
            email='test@example.com',
            confirm='testpassword'
        ), follow_redirects=True)
        
        self.app.post('/login', data=dict(
            username='testuser',
            password='testpassword'
        ), follow_redirects=True)

        # Add a new cocktail
        response = self.app.post('/add-original-cocktails', data=dict(
            name='Test Cocktail',
            instructions='Shake well',
            ingredients=['Vodka', 'Orange Juice'],
            measures=['1 oz', '2 oz']
        ), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Successfully added your original cocktail!', response.data)

    def test_view_cocktail(self):
        """Test viewing a cocktail"""
        # Register and log in the user
        self.app.post('/register', data=dict(
            username='testuser',
            password='testpassword',
            email='test@example.com',
            confirm='testpassword'
        ), follow_redirects=True)
        
        self.app.post('/login', data=dict(
            username='testuser',
            password='testpassword'
        ), follow_redirects=True)

        # Add a new cocktail
        self.app.post('/add-original-cocktails', data=dict(
            name='Test Cocktail',
            instructions='Shake well',
            ingredients=['Vodka', 'Orange Juice'],
            measures=['1 oz', '2 oz']
        ), follow_redirects=True)

        # View the cocktail
        response = self.app.get('/my-cocktails', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Cocktail', response.data)

if __name__ == '__main__':
    unittest.main()
