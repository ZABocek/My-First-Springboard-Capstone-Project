import io
import unittest
from unittest.mock import patch

from app import app
from models import db, User, Ingredient, Cocktail, Cocktails_Users, Cocktails_Ingredients, UserAppeal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username='testuser', email='test@example.com',
               password='Testpass1', verified=True):
    """Create and persist a test user; mark email verified by default."""
    user = User.register(username=username, email=email, password=password)
    if verified:
        user.is_email_verified = True
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username='testuser', password='Testpass1'):
    """POST login credentials and return the response."""
    return client.post('/login', data={
        'username': username,
        'password': password,
    }, follow_redirects=True)


# ---------------------------------------------------------------------------
# Base test class
# ---------------------------------------------------------------------------

class FlaskTestCase(unittest.TestCase):
    def setUp(self):
        """Set up the test client and initialize an in-memory database."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False   # disable CSRF for form tests
        app.config['MAIL_SUPPRESS_SEND'] = True  # never actually send email

        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Drop all tables after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ------------------------------------------------------------------
    # Model-level tests (original 5)
    # ------------------------------------------------------------------

    def test_register_user(self):
        """User.register() persists a hashed-password row."""
        with app.app_context():
            user = User.register(username='testuser', email='test@example.com',
                                 password='Testpass1')
            db.session.add(user)
            db.session.commit()
            check = User.query.filter_by(username='testuser').first()
            self.assertIsNotNone(check)
            self.assertEqual(check.email, 'test@example.com')

    def test_login_user(self):
        """User.authenticate() accepts correct credentials and rejects wrong ones."""
        with app.app_context():
            user = User.register(username='testuser', email='test@example.com',
                                 password='Testpass1')
            db.session.add(user)
            db.session.commit()
            ok = User.authenticate(username='testuser', password='Testpass1')
            self.assertIsNotNone(ok)
            fail = User.authenticate(username='testuser', password='wrongpassword')
            self.assertFalse(fail)

    def test_add_ingredient(self):
        """Ingredient row can be created and queried."""
        with app.app_context():
            db.session.add(Ingredient(name='Vodka'))
            db.session.commit()
            check = Ingredient.query.filter_by(name='Vodka').first()
            self.assertIsNotNone(check)

    def test_add_cocktail(self):
        """Cocktail row can be created and queried."""
        import time
        with app.app_context():
            name = f'Test Cocktail {int(time.time())}'
            db.session.add(Cocktail(name=name, instructions='Shake well'))
            db.session.commit()
            check = Cocktail.query.filter_by(name=name).first()
            self.assertIsNotNone(check)
            self.assertEqual(check.instructions, 'Shake well')

    def test_cocktail_ingredient_relationship(self):
        """Cocktails_Ingredients join row links cocktail and ingredient correctly."""
        with app.app_context():
            db.session.add(Ingredient(name='Vodka'))
            db.session.commit()
            ing = Ingredient.query.filter_by(name='Vodka').first()
            db.session.add(Cocktail(name='Vodka Tonic', instructions='Mix well'))
            db.session.commit()
            c = Cocktail.query.filter_by(name='Vodka Tonic').first()
            db.session.add(Cocktails_Ingredients(
                cocktail_id=c.id, ingredient_id=ing.id, quantity='1 oz'))
            db.session.commit()
            assoc = Cocktails_Ingredients.query.filter_by(cocktail_id=c.id).first()
            self.assertIsNotNone(assoc)
            self.assertEqual(assoc.quantity, '1 oz')

    # ------------------------------------------------------------------
    # Route integration tests
    # ------------------------------------------------------------------

    def test_homepage_returns_200(self):
        # Unauthenticated visitors are redirected; follow to the register page.
        resp = self.client.get('/', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_login_page_returns_200(self):
        resp = self.client.get('/login')
        self.assertEqual(resp.status_code, 200)

    def test_register_page_returns_200(self):
        resp = self.client.get('/register')
        self.assertEqual(resp.status_code, 200)

    def test_register_post_creates_user(self):
        """POST /register with valid data creates a user and redirects."""
        resp = self.client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Newpass1',
            'confirm': 'Newpass1',
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            user = User.query.filter_by(username='newuser').first()
            self.assertIsNotNone(user)

    def test_register_duplicate_username_rejected(self):
        """POST /register with a taken username shows an error."""
        with app.app_context():
            _make_user(username='taken', email='taken@example.com')
        resp = self.client.post('/register', data={
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'Testpass1',
            'confirm': 'Testpass1',
        }, follow_redirects=True)
        self.assertIn(b'already taken', resp.data)

    def test_register_duplicate_email_rejected(self):
        """POST /register with a taken email shows an error."""
        with app.app_context():
            _make_user(username='user1', email='dup@example.com')
        resp = self.client.post('/register', data={
            'username': 'user2',
            'email': 'dup@example.com',
            'password': 'Testpass1',
            'confirm': 'Testpass1',
        }, follow_redirects=True)
        self.assertIn(b'already registered', resp.data)

    def test_login_success_redirects_home(self):
        """Valid login redirects to homepage."""
        with app.app_context():
            _make_user()
        resp = _login(self.client)
        self.assertEqual(resp.status_code, 200)

    def test_login_invalid_credentials(self):
        """Wrong password keeps user on/near login page."""
        with app.app_context():
            _make_user()
        resp = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'WrongPass1',
        }, follow_redirects=True)
        self.assertIn(b'Bad name/password', resp.data)

    def test_logout_requires_post(self):
        """GET /logout should return 405 Method Not Allowed (logout is now POST-only)."""
        resp = self.client.get('/logout')
        self.assertEqual(resp.status_code, 405)

    def test_logout_post_clears_session(self):
        """POST /logout redirects to login."""
        with app.app_context():
            _make_user()
        _login(self.client)
        resp = self.client.post('/logout', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # After logout, user lands on login page.
        self.assertIn(b'login', resp.data.lower())

    # ------------------------------------------------------------------
    # Auth boundary tests — unauthenticated access to protected routes
    # ------------------------------------------------------------------

    def test_my_cocktails_requires_login(self):
        resp = self.client.get('/my-cocktails', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    def test_add_original_cocktail_requires_login(self):
        resp = self.client.get('/add-original-cocktails', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    def test_add_api_cocktails_requires_login(self):
        resp = self.client.get('/add_api_cocktails', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    def test_profile_requires_login(self):
        resp = self.client.get('/users/profile/1', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    def test_admin_panel_requires_login(self):
        resp = self.client.get('/admin/panel', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    # ------------------------------------------------------------------
    # Image upload — magic-byte validation
    # ------------------------------------------------------------------

    def test_save_uploaded_image_rejects_invalid_content(self):
        """save_uploaded_image() raises ValueError for a non-image file."""
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage

        fake = FileStorage(
            stream=io.BytesIO(b"this is just text, not an image"),
            filename="bad.png",
            content_type="image/png",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_save_uploaded_image_accepts_valid_png(self):
        """save_uploaded_image() accepts a minimal valid PNG header."""
        import os
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage

        # Minimal 1×1 white PNG (67 bytes).
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
            b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        fake = FileStorage(
            stream=io.BytesIO(png_bytes),
            filename="test.png",
            content_type="image/png",
        )
        with app.app_context():
            app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'
            os.makedirs(
                os.path.join(app.root_path, 'static', 'uploads'), exist_ok=True
            )
            filename = save_uploaded_image(fake)
            self.assertIsNotNone(filename)
            self.assertTrue(filename.endswith('.png'))
            # Cleanup
            path = os.path.join(app.root_path, 'static', 'uploads', filename)
            if os.path.exists(path):
                os.remove(path)

    # ------------------------------------------------------------------
    # Appeal workflow
    # ------------------------------------------------------------------

    def test_banned_user_can_submit_appeal(self):
        """A banned user can reach the appeal form."""
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            db.session.commit()
            user_id = user.id
        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id
        resp = self.client.get('/appeal', follow_redirects=True)
        # Appeal page should load (not 404).
        self.assertNotEqual(resp.status_code, 404)

    def test_appeal_submission_creates_record(self):
        """POST to the appeal form creates a UserAppeal row."""
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            db.session.commit()
            user_id = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = user_id

        # Don't follow redirects: after submitting, the route redirects to /,
        # which enforce_ban() bounces back to /appeal (correct behaviour for a
        # still-banned user). The important thing is that the DB row was saved.
        self.client.post('/appeal', data={
            'appeal_text': (
                'I believe my ban was issued in error. I was not violating any '
                'community guidelines. Please review my case.'
            ),
        })

        with app.app_context():
            appeal = UserAppeal.query.filter_by(user_id=user_id).first()
            self.assertIsNotNone(appeal)

    # ------------------------------------------------------------------
    # Email (mock) — registration does not raise
    # ------------------------------------------------------------------

    def test_registration_email_sent_async(self):
        """Registration enqueues a background email task without blocking."""
        with patch('services.email_service._deliver.delay') as mock_delay:
            resp = self.client.post('/register', data={
                'username': 'emailuser',
                'email': 'email@example.com',
                'password': 'Emailpass1',
                'confirm': 'Emailpass1',
            }, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            mock_delay.assert_called_once()

    # ------------------------------------------------------------------
    # Password strength validation
    # ------------------------------------------------------------------

    def test_weak_password_no_digit_rejected(self):
        """Registration form rejects a password with no digit."""
        resp = self.client.post('/register', data={
            'username': 'weakuser',
            'email': 'weak@example.com',
            'password': 'NoDigitHere',
            'confirm': 'NoDigitHere',
        }, follow_redirects=True)
        self.assertIn(b'digit', resp.data)

    def test_weak_password_no_uppercase_rejected(self):
        """Registration form rejects a password with no uppercase letter."""
        resp = self.client.post('/register', data={
            'username': 'weakuser2',
            'email': 'weak2@example.com',
            'password': 'nouppercase1',
            'confirm': 'nouppercase1',
        }, follow_redirects=True)
        self.assertIn(b'uppercase', resp.data)


if __name__ == '__main__':
    unittest.main()
