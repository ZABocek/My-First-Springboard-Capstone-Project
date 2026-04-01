import io
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app import app
from extensions import limiter
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
        app.config['RATELIMIT_ENABLED'] = False  # disable rate limiting in tests
        limiter.enabled = False                  # Flask-Limiter 3.x reads this at init;
                                                 # set the instance flag directly too
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Drop all tables after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()
        limiter.enabled = True  # restore for safety

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


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class ModelEdgeCaseTests(unittest.TestCase):
    """Model-level edge cases not covered by the base suite."""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['MAIL_SUPPRESS_SEND'] = True
        app.config['RATELIMIT_ENABLED'] = False
        limiter.enabled = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        limiter.enabled = True

    def test_register_password_too_short(self):
        """Registration form rejects a password shorter than 8 characters."""
        resp = self.client.post('/register', data={
            'username': 'shortpwduser',
            'email': 'short@example.com',
            'password': 'Ab1',
            'confirm': 'Ab1',
        }, follow_redirects=True)
        self.assertIn(b'8 characters', resp.data)

    def test_register_password_mismatch_rejected(self):
        """Registration form rejects mismatched password/confirm fields."""
        resp = self.client.post('/register', data={
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password': 'Goodpass1',
            'confirm': 'Differentpass1',
        }, follow_redirects=True)
        self.assertIn(b'match', resp.data.lower())

    def test_user_authenticate_nonexistent_user(self):
        """authenticate() returns False for a username that does not exist."""
        with app.app_context():
            result = User.authenticate(username='nobody', password='Anything1')
        self.assertFalse(result)

    def test_user_repr(self):
        """User __repr__ includes username and email."""
        with app.app_context():
            user = _make_user(username='repruser', email='repr@example.com')
            self.assertIn('repruser', repr(user))
            self.assertIn('repr@example.com', repr(user))

    def test_ingredient_unique_constraint(self):
        """Inserting two Ingredient rows with the same name raises an IntegrityError."""
        from sqlalchemy.exc import IntegrityError
        with app.app_context():
            db.session.add(Ingredient(name='UniqueGin'))
            db.session.commit()
            db.session.add(Ingredient(name='UniqueGin'))
            with self.assertRaises(IntegrityError):
                db.session.commit()

    def test_store_or_get_ingredient_canonicalises_name(self):
        """store_or_get_ingredient normalises case and whitespace."""
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing1 = store_or_get_ingredient('  dry gin  ')
            db.session.commit()
            id1 = ing1.id
            # Different casing / whitespace should resolve to the same row.
            ing2 = store_or_get_ingredient('DRY GIN')
            db.session.flush()
            self.assertEqual(id1, ing2.id)

    def test_store_or_get_ingredient_creates_new(self):
        """store_or_get_ingredient creates a new row when the name is absent."""
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing = store_or_get_ingredient('BlueAgave')
            db.session.commit()
            # Python's .title() transforms 'BlueAgave' -> 'Blueagave'
            canonical = 'BlueAgave'.strip().title()  # 'Blueagave'
            fetched = Ingredient.query.filter_by(name=canonical).first()
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.id, ing.id)

    def test_user_email_verification_token_roundtrip(self):
        """generate/verify token round-trip returns the original email."""
        with app.app_context():
            user = _make_user(username='tokenuser', email='token@example.com', verified=False)
            token = user.generate_email_verification_token()
            self.assertIsNotNone(token)
            email = User.verify_email_token(token)
        self.assertEqual(email, 'token@example.com')

    def test_verify_email_token_invalid(self):
        """verify_email_token returns None for a garbage token."""
        with app.app_context():
            result = User.verify_email_token('notavalidtoken')
        self.assertIsNone(result)

    def test_mark_email_verified(self):
        """mark_email_verified sets is_email_verified and records the timestamp."""
        with app.app_context():
            user = _make_user(username='unverified', email='unverified@example.com',
                              verified=False)
            user.is_email_verified = False
            db.session.commit()
            user.mark_email_verified()
            self.assertTrue(user.is_email_verified)
            self.assertIsNotNone(user.email_verified_at)

    def test_add_preference(self):
        """add_preference() persists the chosen drink type."""
        with app.app_context():
            user = _make_user(username='prefuser', email='pref@example.com')
            user.add_preference('non-alcoholic')
            fetched = User.query.filter_by(username='prefuser').first()
            self.assertEqual(fetched.preference, 'non-alcoholic')

    def test_process_and_store_new_cocktail_deduplication(self):
        """Calling process_and_store_new_cocktail twice with the same API id
        creates only one Cocktail row (shared API record), not two."""
        from services.cocktail_service import process_and_store_new_cocktail
        api_data = {
            'idDrink': '99999',
            'strDrink': 'Dedup Test Cocktail',
            'strInstructions': 'Stir once.',
            'strDrinkThumb': None,
            'strIngredient1': 'Vodka',
            'strMeasure1': '2 oz',
        }
        with app.app_context():
            user1 = _make_user(username='dupuser1', email='dup1@example.com')
            user2 = _make_user(username='dupuser2', email='dup2@example.com')
            uid1, uid2 = user1.id, user2.id

        with app.app_context():
            process_and_store_new_cocktail(api_data, uid1)
            process_and_store_new_cocktail(api_data, uid2)
            count = Cocktail.query.filter_by(
                api_cocktail_id='99999', is_api_cocktail=True
            ).count()
            self.assertEqual(count, 1)

    def test_process_and_store_new_cocktail_duplicate_user_link(self):
        """Adding the same API cocktail twice for the same user does not create
        duplicate Cocktails_Users rows."""
        from services.cocktail_service import process_and_store_new_cocktail
        api_data = {
            'idDrink': '88888',
            'strDrink': 'Dup Link Test',
            'strInstructions': 'Mix it.',
            'strDrinkThumb': None,
        }
        with app.app_context():
            user = _make_user(username='duplinkuser', email='duplink@example.com')
            uid = user.id

        with app.app_context():
            process_and_store_new_cocktail(api_data, uid)
            process_and_store_new_cocktail(api_data, uid)
            cocktail = Cocktail.query.filter_by(api_cocktail_id='88888').first()
            link_count = Cocktails_Users.query.filter_by(
                user_id=uid, cocktail_id=cocktail.id
            ).count()
            self.assertEqual(link_count, 1)

    def test_delete_uploaded_image_path_traversal_rejected(self):
        """delete_uploaded_image silently ignores filenames with path separators."""
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            # Should not raise, and must not delete any file outside uploads dir.
            delete_uploaded_image('../secret.txt')
            delete_uploaded_image('../../etc/passwd')

    def test_allowed_file_rejects_bad_extensions(self):
        """allowed_file() returns False for non-image extensions."""
        from services.cocktail_service import allowed_file
        self.assertFalse(allowed_file('script.php'))
        self.assertFalse(allowed_file('shell.sh'))
        self.assertFalse(allowed_file('doc.pdf'))
        self.assertFalse(allowed_file('noextension'))

    def test_allowed_file_accepts_valid_extensions(self):
        """allowed_file() returns True for PNG, JPG, and JPEG."""
        from services.cocktail_service import allowed_file
        self.assertTrue(allowed_file('photo.png'))
        self.assertTrue(allowed_file('photo.jpg'))
        self.assertTrue(allowed_file('photo.jpeg'))
        self.assertTrue(allowed_file('PHOTO.PNG'))  # case-insensitive

    def test_save_uploaded_image_rejects_bad_extension(self):
        """save_uploaded_image raises ValueError for a disallowed extension."""
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        # Build a fake file with a valid PNG header but a .gif extension.
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 60
        fake = FileStorage(
            stream=io.BytesIO(png_bytes),
            filename='malicious.gif',
            content_type='image/gif',
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_save_uploaded_image_no_file_returns_none(self):
        """save_uploaded_image returns None when no file is provided."""
        from services.cocktail_service import save_uploaded_image
        with app.app_context():
            result = save_uploaded_image(None)
        self.assertIsNone(result)

    def test_save_uploaded_image_empty_filename_returns_none(self):
        """save_uploaded_image returns None when FileStorage has an empty filename."""
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        fake = FileStorage(stream=io.BytesIO(b''), filename='', content_type='image/png')
        with app.app_context():
            result = save_uploaded_image(fake)
        self.assertIsNone(result)

    def test_save_uploaded_image_accepts_valid_jpeg(self):
        """save_uploaded_image accepts a minimal JPEG (FF D8 FF header)."""
        import os
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        # Minimal synthetic JPEG data (only the magic bytes need to be valid).
        jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        fake = FileStorage(
            stream=io.BytesIO(jpeg_bytes),
            filename='test.jpg',
            content_type='image/jpeg',
        )
        with app.app_context():
            app.config['UPLOADED_PHOTOS_DEST'] = 'static/uploads'
            os.makedirs(
                os.path.join(app.root_path, 'static', 'uploads'), exist_ok=True
            )
            filename = save_uploaded_image(fake)
            self.assertIsNotNone(filename)
            self.assertTrue(filename.lower().endswith('.jpg'))
            path = os.path.join(app.root_path, 'static', 'uploads', filename)
            if os.path.exists(path):
                os.remove(path)

    def test_get_cocktail_image_url_returns_upload_url(self):
        """get_cocktail_image_url prefers image_url over strDrinkThumb."""
        from services.cocktail_service import get_cocktail_image_url
        # url_for() requires an active request or application context with SERVER_NAME.
        with app.test_request_context('/'):
            c = Cocktail(name='ImgTest', instructions='x', image_url='myfile.png',
                         strDrinkThumb='http://external.com/img.jpg')
            url = get_cocktail_image_url(c)
        self.assertIn('myfile.png', url)

    def test_get_cocktail_image_url_fallback_to_external(self):
        """get_cocktail_image_url falls back to strDrinkThumb when image_url is absent."""
        from services.cocktail_service import get_cocktail_image_url
        with app.app_context():
            c = Cocktail(name='ThumbTest', instructions='x',
                         strDrinkThumb='http://external.com/thumb.jpg')
            url = get_cocktail_image_url(c)
        self.assertEqual(url, 'http://external.com/thumb.jpg')

    def test_get_cocktail_image_url_no_image_returns_none(self):
        """get_cocktail_image_url returns None when neither field is set."""
        from services.cocktail_service import get_cocktail_image_url
        with app.app_context():
            c = Cocktail(name='NoImg', instructions='x')
            result = get_cocktail_image_url(c)
        self.assertIsNone(result)


class RouteEdgeCaseTests(unittest.TestCase):
    """Route / integration edge cases."""

    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['MAIL_SUPPRESS_SEND'] = True
        app.config['RATELIMIT_ENABLED'] = False
        limiter.enabled = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        limiter.enabled = True

    # ------------------------------------------------------------------
    # Email verification flow
    # ------------------------------------------------------------------

    def test_verify_email_valid_token(self):
        """GET /verify-email/<token> marks the user as verified and redirects."""
        with app.app_context():
            user = _make_user(username='verifyme', email='verifyme@example.com',
                              verified=False)
            user.is_email_verified = False
            db.session.commit()
            token = user.generate_email_verification_token()
            uid = user.id

        resp = self.client.get(f'/verify-email/{token}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            u = db.session.get(User, uid)
            self.assertTrue(u.is_email_verified)

    def test_verify_email_invalid_token_redirects_to_login(self):
        """GET /verify-email/<bad_token> flashes error and redirects to login."""
        resp = self.client.get('/verify-email/totallyfaketoken', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'invalid or has expired', resp.data.lower())

    def test_verify_email_already_verified(self):
        """Clicking verify link when already verified flashes info and redirects."""
        with app.app_context():
            user = _make_user(username='alreadyv', email='alreadyv@example.com',
                              verified=True)
            token = user.generate_email_verification_token()

        resp = self.client.get(f'/verify-email/{token}', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'already verified', resp.data.lower())

    def test_login_unverified_email_blocked(self):
        """Login is blocked until the user verifies their email."""
        with app.app_context():
            _make_user(username='unverifuser', email='unverif@example.com', verified=False)
        resp = self.client.post('/login', data={
            'username': 'unverifuser',
            'password': 'Testpass1',
        }, follow_redirects=True)
        self.assertIn(b'verify your email', resp.data.lower())

    def test_verification_pending_page_requires_session(self):
        """Accessing verification-pending without being the registering session redirects."""
        with app.app_context():
            user = _make_user(username='penduser', email='pend@example.com', verified=False)
            uid = user.id
        # No session key set — should be denied.
        resp = self.client.get(f'/verification-pending/{uid}', follow_redirects=True)
        self.assertIn(b"permission", resp.data.lower())

    # ------------------------------------------------------------------
    # Ban enforcement
    # ------------------------------------------------------------------

    def test_temporarily_banned_user_redirected_to_appeal(self):
        """A temporarily-banned logged-in user is redirected to the appeal page."""
        from datetime import timedelta
        with app.app_context():
            user = _make_user(username='tmpbanned', email='tmpban@example.com')
            user.ban_until = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/', follow_redirects=False)
        # enforce_ban() should redirect away from homepage.
        self.assertIn(resp.status_code, (301, 302))

    def test_expired_ban_does_not_block_user(self):
        """A user whose ban_until is in the past can access the homepage."""
        from datetime import timedelta
        with app.app_context():
            user = _make_user(username='expbanned', email='expban@example.com')
            user.ban_until = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_permanently_banned_user_redirected_to_appeal(self):
        """A permanently-banned logged-in user accessing any protected route
        is redirected to the appeal page, not the homepage."""
        with app.app_context():
            user = _make_user(username='permban', email='permban@example.com')
            user.is_permanently_banned = True
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/my-cocktails', follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn('/appeal', resp.headers.get('Location', ''))

    def test_duplicate_appeal_rejected(self):
        """A second appeal submission while one is pending shows an info flash."""
        with app.app_context():
            user = _make_user(username='dupappeal', email='dupappeal@example.com')
            user.is_permanently_banned = True
            db.session.add(UserAppeal(
                user_id=user.id,
                appeal_text='First appeal - already pending.',
                status='pending',
            ))
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/appeal', follow_redirects=True)
        self.assertIn(b'pending appeal', resp.data.lower())

    def test_unbanned_user_cannot_access_appeal_form(self):
        """A user who is not banned is redirected away from the appeal form."""
        with app.app_context():
            user = _make_user(username='normaluser', email='normal@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/appeal', follow_redirects=True)
        # Must not see the appeal form.
        self.assertNotIn(b'submit appeal', resp.data.lower())

    # ------------------------------------------------------------------
    # Auth: already-logged-in user visits register
    # ------------------------------------------------------------------

    def test_register_redirects_when_already_logged_in(self):
        """Visiting /register while already logged in redirects to homepage."""
        with app.app_context():
            user = _make_user()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/register', follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))

    # ------------------------------------------------------------------
    # Admin routes: non-admin access
    # ------------------------------------------------------------------

    def test_admin_panel_non_admin_redirected(self):
        """A regular (non-admin) logged-in user is bounced from /admin/panel."""
        with app.app_context():
            user = _make_user(username='reguser', email='reg@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/admin/panel', follow_redirects=True)
        self.assertIn(b'admin access required', resp.data.lower())

    def test_admin_panel_accessible_to_admin(self):
        """An admin user can load /admin/panel (200)."""
        with app.app_context():
            user = _make_user(username='adminuser', email='admin@example.com')
            user.is_admin = True
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/admin/panel', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_admin_cannot_ban_themselves(self):
        """An admin trying to ban their own account is rejected with a flash warning."""
        with app.app_context():
            user = _make_user(username='selfbanadmin', email='selfban@example.com')
            user.is_admin = True
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.post(f'/admin/user/{uid}/ban', follow_redirects=True)
        self.assertIn(b'cannot', resp.data.lower())
        # Ban must NOT have been applied.
        with app.app_context():
            u = db.session.get(User, uid)
            self.assertIsNone(u.ban_until)

    def test_admin_cannot_delete_themselves(self):
        """An admin cannot delete their own account through the admin panel."""
        with app.app_context():
            user = _make_user(username='selfdeladmin', email='selfdel@example.com')
            user.is_admin = True
            db.session.commit()
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.post(f'/admin/user/{uid}/delete', follow_redirects=True)
        self.assertIn(b'cannot', resp.data.lower())

    def test_promote_user_sets_admin_flag(self):
        """POST /admin/user/<id>/promote sets is_admin=True on the target user."""
        with app.app_context():
            admin = _make_user(username='promoteadmin', email='promoteadmin@example.com')
            admin.is_admin = True
            target = _make_user(username='targetpromote', email='targetpromote@example.com')
            db.session.commit()
            admin_id, target_id = admin.id, target.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id

        resp = self.client.post(f'/admin/user/{target_id}/promote', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            t = db.session.get(User, target_id)
            self.assertTrue(t.is_admin)

    def test_permanently_ban_user(self):
        """POST /admin/user/<id>/ban-permanent sets is_permanently_banned."""
        with app.app_context():
            admin = _make_user(username='permbandmin', email='permbandmin@example.com')
            admin.is_admin = True
            target = _make_user(username='permtarget', email='permtarget@example.com')
            db.session.commit()
            admin_id, target_id = admin.id, target.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id

        resp = self.client.post(f'/admin/user/{target_id}/ban-permanent',
                                follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            t = db.session.get(User, target_id)
            self.assertTrue(t.is_permanently_banned)

    def test_delete_user_removes_record(self):
        """POST /admin/user/<id>/delete removes the user from the database."""
        with app.app_context():
            admin = _make_user(username='deladmin', email='deladmin@example.com')
            admin.is_admin = True
            target = _make_user(username='deltarget', email='deltarget@example.com')
            db.session.commit()
            admin_id, target_id = admin.id, target.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = admin_id

        self.client.post(f'/admin/user/{target_id}/delete', follow_redirects=True)

        with app.app_context():
            gone = db.session.get(User, target_id)
            self.assertIsNone(gone)

    # ------------------------------------------------------------------
    # Cocktail routes
    # ------------------------------------------------------------------

    def test_my_cocktails_empty_for_new_user(self):
        """A new user with no cocktails sees an empty list (200)."""
        with app.app_context():
            user = _make_user(username='emptycktl', email='empty@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.get('/my-cocktails', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_delete_cocktail_not_owned(self):
        """POST /delete-cocktail/<id> from a user who doesn't own it is blocked."""
        with app.app_context():
            owner = _make_user(username='cktlowner', email='cktlowner@example.com')
            other = _make_user(username='notowner', email='notowner@example.com')
            c = Cocktail(name='Owned drink', instructions='shake')
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=owner.id, cocktail_id=c.id))
            db.session.commit()
            other_id, cktl_id = other.id, c.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = other_id

        resp = self.client.post(f'/delete-cocktail/{cktl_id}', follow_redirects=True)
        self.assertIn(b'permission', resp.data.lower())
        # Cocktail row must still exist.
        with app.app_context():
            still_there = db.session.get(Cocktail, cktl_id)
            self.assertIsNotNone(still_there)

    def test_add_original_cocktail_missing_ingredient_blocked(self):
        """Submitting an original cocktail with ingredient but no measure is rejected."""
        with app.app_context():
            user = _make_user(username='partialerr', email='partialerr@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.post('/add-original-cocktails', data={
            'name': 'Partial Cocktail',
            'instructions': 'Do stuff',
            'ingredients-0': 'Vodka',
            'measures-0': '',   # Measure intentionally left blank → partial error
        }, follow_redirects=True)
        self.assertIn(b'measure', resp.data.lower())

    def test_add_original_cocktail_no_ingredients_blocked(self):
        """Submitting an original cocktail with all blank ingredients is rejected."""
        with app.app_context():
            user = _make_user(username='noinguser', email='noinguser@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        resp = self.client.post('/add-original-cocktails', data={
            'name': 'Empty Cocktail',
            'instructions': 'Nothing here',
            'ingredients-0': '',
            'measures-0': '',
        }, follow_redirects=True)
        self.assertIn(b'ingredient', resp.data.lower())

    # ------------------------------------------------------------------
    # Security headers
    # ------------------------------------------------------------------

    def test_security_headers_present(self):
        """Every response carries the required security headers."""
        resp = self.client.get('/login')
        self.assertIn('X-Frame-Options', resp.headers)
        self.assertIn('X-Content-Type-Options', resp.headers)
        self.assertIn('Content-Security-Policy', resp.headers)
        self.assertEqual(resp.headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(resp.headers['X-Content-Type-Options'], 'nosniff')

    # ------------------------------------------------------------------
    # User messages
    # ------------------------------------------------------------------

    def test_send_user_message_creates_record(self):
        """POST /user/send-message creates an AdminMessage row."""
        with app.app_context():
            user = _make_user(username='msguser', email='msg@example.com')
            uid = user.id

        with self.client.session_transaction() as sess:
            sess['user_id'] = uid

        self.client.post('/user/send-message', data={
            'message_type': 'suggestion',
            'subject': 'Great idea here',
            'message': 'This is a long enough message body to pass validation.',
        }, follow_redirects=True)

        with app.app_context():
            from models import AdminMessage
            msg = AdminMessage.query.filter_by(user_id=uid).first()
            self.assertIsNotNone(msg)
            self.assertEqual(msg.subject, 'Great idea here')

    def test_user_messages_list_requires_login(self):
        """GET /user/messages redirects unauthenticated visitors to login."""
        resp = self.client.get('/user/messages', follow_redirects=True)
        self.assertIn(b'login', resp.data.lower())

    # ------------------------------------------------------------------
    # Cascade delete
    # ------------------------------------------------------------------

    def test_cascade_delete_removes_cocktails_users(self):
        """Deleting a user cascades to remove their Cocktails_Users rows."""
        with app.app_context():
            user = _make_user(username='cascadeuser', email='cascade@example.com')
            c = Cocktail(name='Cascade Drink', instructions='pour')
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=user.id, cocktail_id=c.id))
            db.session.commit()
            uid = user.id

        with app.app_context():
            u = db.session.get(User, uid)
            db.session.delete(u)
            db.session.commit()
            remaining = Cocktails_Users.query.filter_by(user_id=uid).count()
            self.assertEqual(remaining, 0)

    def test_cascade_delete_removes_appeals(self):
        """Deleting a user cascades to remove their UserAppeal rows."""
        with app.app_context():
            user = _make_user(username='appealcascade', email='appealcascade@example.com')
            user.is_permanently_banned = True
            db.session.add(UserAppeal(user_id=user.id, appeal_text='Please unban me today!', status='pending'))
            db.session.commit()
            uid = user.id

        with app.app_context():
            u = db.session.get(User, uid)
            db.session.delete(u)
            db.session.commit()
            remaining = UserAppeal.query.filter_by(user_id=uid).count()
            self.assertEqual(remaining, 0)

    def test_cocktail_cascade_removes_ingredients_relation(self):
        """Deleting a Cocktail cascades to remove its Cocktails_Ingredients rows."""
        with app.app_context():
            c = Cocktail(name='DelMe', instructions='gone')
            db.session.add(c)
            db.session.flush()
            ing = Ingredient(name='GoneJuice')
            db.session.add(ing)
            db.session.flush()
            db.session.add(Cocktails_Ingredients(
                cocktail_id=c.id, ingredient_id=ing.id, quantity='1 oz'
            ))
            db.session.commit()
            cid = c.id

        with app.app_context():
            cock = db.session.get(Cocktail, cid)
            db.session.delete(cock)
            db.session.commit()
            remaining = Cocktails_Ingredients.query.filter_by(cocktail_id=cid).count()
            self.assertEqual(remaining, 0)


if __name__ == '__main__':
    unittest.main()
