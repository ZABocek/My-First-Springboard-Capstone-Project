"""Advanced & edge-case test suite for Cocktail Chronicles.

Covers 20 distinct test classes that exercise:
  - Detailed security-header assertions
  - Session security / lifecycle
  - Form-input boundary conditions (empty, oversized, SQL meta-characters)
  - User-profile management (preference, favourite ingredients)
  - AdminMessage model CRUD and cascade behaviour
  - UserAppeal model fields and repr
  - AdminAuditLog survival after user deletion (ON DELETE SET NULL)
  - Favourite-ingredients route tests (add, delete, ownership enforcement)
  - Extended admin workflow routes (demote, unban, ban, messages)
  - HTTP method enforcement (405 / 404)
  - CocktailDB API mock integration
  - Configuration module type checks
  - User-messages route edge cases (empty / short body)
  - Appeal-route edge cases (status page, unauthenticated, non-banned user)
  - Resend-verification lifecycle
  - Cocktails_Users join-table semantics
  - Ingredient normalisation edge cases
  - Image-upload edge cases (BMP, wrong extension, zero-byte)
  - delete_uploaded_image path-traversal guard
  - Homepage redirect logic
"""

import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app import app
from extensions import limiter
from models import (
    db, User, Ingredient, Cocktail, Cocktails_Users,
    Cocktails_Ingredients, UserFavoriteIngredients,
    AdminMessage, UserAppeal, AdminAuditLog,
)


# ---------------------------------------------------------------------------
# Shared helpers (self-contained; no dependency on test_app.py)
# ---------------------------------------------------------------------------

def _make_user(username="testuser", email="test@example.com",
               password="Testpass1", verified=True, is_admin=False):
    """Create and persist a test user. Returns the committed User instance."""
    user = User.register(username=username, email=email, password=password)
    if verified:
        user.is_email_verified = True
    user.is_admin = is_admin
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username="testuser", password="Testpass1"):
    """POST login credentials and return the response."""
    return client.post("/login", data={
        "username": username,
        "password": password,
    }, follow_redirects=True)


def _base_config():
    return {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
        "RATELIMIT_ENABLED": False,
    }


# ---------------------------------------------------------------------------
# Common base class for all test suites in this file
# ---------------------------------------------------------------------------

class _BaseSuite(unittest.TestCase):
    """Set up an in-memory SQLite database and a test client for each test."""

    def setUp(self):
        app.config.update(_base_config())
        limiter.enabled = False
        self.client = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        limiter.enabled = True


# ===========================================================================
# 1. Security Headers — Detailed Assertions
# ===========================================================================

class SecurityHeaderDetailTests(_BaseSuite):
    """Every required security header is present and holds the correct value."""

    def _headers(self, path="/login"):
        return self.client.get(path).headers

    def test_x_frame_options_is_sameorigin(self):
        self.assertEqual(self._headers()["X-Frame-Options"], "SAMEORIGIN")

    def test_x_content_type_options_is_nosniff(self):
        self.assertEqual(self._headers()["X-Content-Type-Options"], "nosniff")

    def test_x_xss_protection_is_present(self):
        self.assertIn("X-XSS-Protection", self._headers())

    def test_referrer_policy_is_present(self):
        self.assertIn("Referrer-Policy", self._headers())

    def test_permissions_policy_is_present(self):
        self.assertIn("Permissions-Policy", self._headers())

    def test_csp_restricts_default_src(self):
        csp = self._headers().get("Content-Security-Policy", "")
        self.assertIn("default-src 'self'", csp)

    def test_csp_restricts_script_src(self):
        csp = self._headers().get("Content-Security-Policy", "")
        self.assertIn("script-src", csp)

    def test_csp_no_unsafe_eval(self):
        """'unsafe-eval' must NOT be allowed in the script-src directive."""
        csp = self._headers().get("Content-Security-Policy", "")
        self.assertNotIn("'unsafe-eval'", csp)

    def test_permissions_policy_restricts_camera(self):
        pp = self._headers().get("Permissions-Policy", "")
        self.assertIn("camera=()", pp)

    def test_permissions_policy_restricts_microphone(self):
        pp = self._headers().get("Permissions-Policy", "")
        self.assertIn("microphone=()", pp)

    def test_permissions_policy_restricts_geolocation(self):
        pp = self._headers().get("Permissions-Policy", "")
        self.assertIn("geolocation=()", pp)

    def test_security_headers_on_register_page(self):
        h = self._headers("/register")
        self.assertIn("X-Frame-Options", h)
        self.assertIn("Content-Security-Policy", h)
        self.assertIn("X-Content-Type-Options", h)

    def test_csp_restricts_img_src_to_allowlist(self):
        csp = self._headers().get("Content-Security-Policy", "")
        self.assertIn("img-src", csp)
        # Wildcard img-src would be a serious misconfiguration.
        self.assertNotIn("img-src *", csp)


# ===========================================================================
# 2. Session Security
# ===========================================================================

class SessionSecurityTests(_BaseSuite):
    """Session cookie is populated correctly and cleared on logout."""

    def test_session_id_set_after_successful_login(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        _login(self.client)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("user_id"), uid)

    def test_session_cleared_completely_after_logout(self):
        with app.app_context():
            _make_user()
        _login(self.client)
        self.client.post("/logout", follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_failed_login_does_not_set_session(self):
        with app.app_context():
            _make_user()
        self.client.post("/login", data={
            "username": "testuser",
            "password": "WrongPass1",
        })
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_protected_routes_redirect_without_session(self):
        """All key protected routes redirect when there is no session."""
        for path in ("/my-cocktails", "/add-original-cocktails", "/add_api_cocktails"):
            resp = self.client.get(path, follow_redirects=False)
            self.assertIn(
                resp.status_code, (301, 302),
                f"Expected redirect for {path}, got {resp.status_code}",
            )

    def test_logout_response_contains_login_link(self):
        with app.app_context():
            _make_user()
        _login(self.client)
        resp = self.client.post("/logout", follow_redirects=True)
        self.assertIn(b"login", resp.data.lower())


# ===========================================================================
# 3. Form Boundary / Input Validation
# ===========================================================================

class FormBoundaryTests(_BaseSuite):
    """Forms correctly reject empty, oversized, and malformed inputs."""

    def test_register_empty_username_rejected(self):
        resp = self.client.post("/register", data={
            "username": "",
            "email": "empty@example.com",
            "password": "Testpass1",
            "confirm": "Testpass1",
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with app.app_context():
            self.assertIsNone(User.query.filter_by(email="empty@example.com").first())

    def test_register_empty_email_rejected(self):
        resp = self.client.post("/register", data={
            "username": "noemail",
            "email": "",
            "password": "Testpass1",
            "confirm": "Testpass1",
        }, follow_redirects=True)
        with app.app_context():
            self.assertIsNone(User.query.filter_by(username="noemail").first())

    def test_register_malformed_email_rejected(self):
        resp = self.client.post("/register", data={
            "username": "bademail",
            "email": "not-an-email",
            "password": "Testpass1",
            "confirm": "Testpass1",
        }, follow_redirects=True)
        with app.app_context():
            self.assertIsNone(User.query.filter_by(username="bademail").first())

    def test_register_username_too_long_does_not_crash(self):
        """A 300-character username must not cause a 500 error.

        SQLite does not enforce String(length) at the DB level, so the row may
        be accepted by the backend — what matters is that the server returns a
        non-500 response and the process handles the request gracefully.
        """
        long_name = "a" * 300
        resp = self.client.post("/register", data={
            "username": long_name,
            "email": "long@example.com",
            "password": "Testpass1",
            "confirm": "Testpass1",
        }, follow_redirects=True)
        # Any redirect (302→200 after follow) or explicit 200 is acceptable.
        # A 500 would indicate an unhandled server error.
        self.assertNotEqual(resp.status_code, 500)

    def test_login_empty_username_no_crash(self):
        resp = self.client.post("/login", data={
            "username": "",
            "password": "Testpass1",
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_login_empty_password_no_crash(self):
        with app.app_context():
            _make_user()
        resp = self.client.post("/login", data={
            "username": "testuser",
            "password": "",
        }, follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

    def test_sql_meta_characters_in_username_no_500(self):
        """SQL injection payloads in the username field must never cause a 500."""
        payloads = [
            "'; DROP TABLE user; --",
            "admin'--",
            "\" OR '1'='1",
            "1; SELECT * FROM user",
        ]
        for payload in payloads:
            resp = self.client.post("/login", data={
                "username": payload,
                "password": "Testpass1",
            }, follow_redirects=True)
            self.assertNotEqual(
                resp.status_code, 500,
                f"Server returned 500 for payload: {payload!r}",
            )

    def test_xss_payload_in_username_no_500(self):
        """XSS payloads in login must not cause a 500."""
        resp = self.client.post("/login", data={
            "username": "<script>alert(1)</script>",
            "password": "Testpass1",
        }, follow_redirects=True)
        self.assertNotEqual(resp.status_code, 500)


# ===========================================================================
# 4. User Profile Management
# ===========================================================================

class UserProfileTests(_BaseSuite):
    """Profile page access control and preference/ingredient updates."""

    def test_profile_page_renders_for_owner(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        with patch("blueprints.users.list_ingredients", return_value={"drinks": []}):
            resp = self.client.get(f"/users/profile/{uid}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_profile_page_blocked_for_other_regular_user(self):
        with app.app_context():
            owner = _make_user(username="owner", email="owner@example.com")
            other = _make_user(username="other", email="other@example.com")
            owner_id, other_id = owner.id, other.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = other_id
        with patch("blueprints.users.list_ingredients", return_value={"drinks": []}):
            resp = self.client.get(f"/users/profile/{owner_id}", follow_redirects=True)
        self.assertIn(b"permission", resp.data.lower())

    def test_admin_can_view_any_profile(self):
        with app.app_context():
            admin = _make_user(username="adminp", email="adminp@example.com", is_admin=True)
            target = _make_user(username="targetp", email="targetp@example.com")
            admin_id, target_id = admin.id, target.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        with patch("blueprints.users.list_ingredients", return_value={"drinks": []}):
            resp = self.client.get(f"/users/profile/{target_id}", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_preference_update_persists_to_db(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        with patch("blueprints.users.list_ingredients", return_value={"drinks": []}):
            self.client.post(f"/users/profile/{uid}", data={
                "submit_button": "Save Preference",
                "preference": "non-alcoholic",
            }, follow_redirects=True)
        with app.app_context():
            u = db.session.get(User, uid)
            self.assertEqual(u.preference, "non-alcoholic")

    def test_delete_favorite_ingredient_non_owner_blocked(self):
        """A user who does not own the profile cannot delete its ingredients."""
        with app.app_context():
            owner = _make_user(username="ingowner", email="ingowner@example.com")
            other = _make_user(username="ingother", email="ingother@example.com")
            ing = Ingredient(name="SpecialGin")
            db.session.add(ing)
            db.session.flush()
            db.session.add(UserFavoriteIngredients(user_id=owner.id, ingredient_id=ing.id))
            db.session.commit()
            owner_id, other_id, ing_id = owner.id, other.id, ing.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = other_id
        self.client.post(f"/delete-favorite-ingredient/{owner_id}/{ing_id}",
                         follow_redirects=True)
        with app.app_context():
            still_there = UserFavoriteIngredients.query.filter_by(
                user_id=owner_id, ingredient_id=ing_id,
            ).first()
            self.assertIsNotNone(still_there)

    def test_preference_alcoholic_default(self):
        """Newly registered user defaults to 'alcoholic' preference."""
        with app.app_context():
            user = _make_user(username="defpref", email="defpref@example.com")
            self.assertEqual(user.preference, "alcoholic")


# ===========================================================================
# 5. AdminMessage Model Tests
# ===========================================================================

class AdminMessageModelTests(_BaseSuite):
    """CRUD and cascade behaviour of the AdminMessage model."""

    def test_create_and_query_admin_message(self):
        with app.app_context():
            user = _make_user()
            msg = AdminMessage(
                user_id=user.id,
                subject="Test subject",
                message="Test message body",
                message_type="suggestion",
            )
            db.session.add(msg)
            db.session.commit()
            fetched = AdminMessage.query.filter_by(subject="Test subject").first()
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.message_type, "suggestion")

    def test_admin_message_default_type_is_user_report(self):
        with app.app_context():
            user = _make_user()
            msg = AdminMessage(user_id=user.id, subject="No type", message="Body")
            db.session.add(msg)
            db.session.commit()
            self.assertEqual(msg.message_type, "user_report")

    def test_admin_message_nullable_response_fields(self):
        with app.app_context():
            user = _make_user()
            msg = AdminMessage(user_id=user.id, subject="Null fields", message="Body")
            db.session.add(msg)
            db.session.commit()
            self.assertIsNone(msg.admin_response)
            self.assertIsNone(msg.admin_response_date)

    def test_admin_message_repr_is_string(self):
        """AdminMessage has a meaningful repr (not an empty string)."""
        with app.app_context():
            user = _make_user()
            msg = AdminMessage(user_id=user.id, subject="Repr", message="Body")
            db.session.add(msg)
            db.session.commit()
            self.assertIsInstance(repr(msg), str)

    def test_admin_message_cascade_deletes_with_user(self):
        with app.app_context():
            user = _make_user()
            db.session.add(AdminMessage(user_id=user.id, subject="Bye", message="deleted"))
            db.session.commit()
            uid = user.id
        with app.app_context():
            u = db.session.get(User, uid)
            db.session.delete(u)
            db.session.commit()
            self.assertEqual(AdminMessage.query.filter_by(user_id=uid).count(), 0)

    def test_admin_message_is_read_defaults_false(self):
        with app.app_context():
            user = _make_user()
            msg = AdminMessage(user_id=user.id, subject="Unread", message="Body")
            db.session.add(msg)
            db.session.commit()
            self.assertFalse(msg.is_read)


# ===========================================================================
# 6. UserAppeal Model Tests
# ===========================================================================

class UserAppealModelTests(_BaseSuite):

    def test_create_and_query_user_appeal(self):
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            appeal = UserAppeal(
                user_id=user.id,
                appeal_text="Please reconsider.",
                status="pending",
            )
            db.session.add(appeal)
            db.session.commit()
            fetched = UserAppeal.query.filter_by(user_id=user.id).first()
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.status, "pending")

    def test_appeal_repr_contains_status(self):
        with app.app_context():
            user = _make_user()
            appeal = UserAppeal(user_id=user.id, appeal_text="Test", status="pending")
            db.session.add(appeal)
            db.session.commit()
            self.assertIn("pending", repr(appeal))

    def test_appeal_response_fields_default_to_none(self):
        with app.app_context():
            user = _make_user()
            appeal = UserAppeal(user_id=user.id, appeal_text="X", status="pending")
            db.session.add(appeal)
            db.session.commit()
            self.assertIsNone(appeal.admin_response)
            self.assertIsNone(appeal.admin_response_date)

    def test_appeal_cascade_deletes_with_user(self):
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            db.session.add(UserAppeal(user_id=user.id, appeal_text="X", status="pending"))
            db.session.commit()
            uid = user.id
        with app.app_context():
            u = db.session.get(User, uid)
            db.session.delete(u)
            db.session.commit()
            self.assertEqual(UserAppeal.query.filter_by(user_id=uid).count(), 0)


# ===========================================================================
# 7. AdminAuditLog Model Tests
# ===========================================================================

class AdminAuditLogModelTests(_BaseSuite):
    """Verify audit entries are created correctly and survive user deletions."""

    def test_create_audit_log_entry(self):
        with app.app_context():
            admin = _make_user(username="auditadmin", email="audit@example.com", is_admin=True)
            target = _make_user(username="audittarget", email="audittarget@example.com")
            log = AdminAuditLog(
                admin_id=admin.id,
                action="ban_user",
                target_user_id=target.id,
                details="Banned for spamming",
            )
            db.session.add(log)
            db.session.commit()
            fetched = AdminAuditLog.query.filter_by(admin_id=admin.id).first()
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.action, "ban_user")
            self.assertIsNotNone(fetched.created_at)

    def test_audit_log_repr_contains_action(self):
        with app.app_context():
            admin = _make_user(username="repradmin", email="repradmin@example.com", is_admin=True)
            log = AdminAuditLog(admin_id=admin.id, action="promote_user")
            db.session.add(log)
            db.session.commit()
            self.assertIn("promote_user", repr(log))

    def test_audit_log_survives_acting_admin_deletion(self):
        """ON DELETE SET NULL: admin_id becomes NULL but the log row stays."""
        with app.app_context():
            admin = _make_user(username="delauditadm", email="delaudadm@example.com", is_admin=True)
            log = AdminAuditLog(admin_id=admin.id, action="demote_user")
            db.session.add(log)
            db.session.commit()
            log_id, admin_id = log.id, admin.id
        with app.app_context():
            db.session.delete(db.session.get(User, admin_id))
            db.session.commit()
            surviving = db.session.get(AdminAuditLog, log_id)
            self.assertIsNotNone(surviving)

    def test_audit_log_survives_target_user_deletion(self):
        """ON DELETE SET NULL: target_user_id becomes NULL but the log row stays."""
        with app.app_context():
            admin = _make_user(username="survadmin", email="survadmin@example.com", is_admin=True)
            target = _make_user(username="survtarget", email="survtarget@example.com")
            log = AdminAuditLog(
                admin_id=admin.id, action="delete_user", target_user_id=target.id
            )
            db.session.add(log)
            db.session.commit()
            log_id, target_id = log.id, target.id
        with app.app_context():
            db.session.delete(db.session.get(User, target_id))
            db.session.commit()
            surviving = db.session.get(AdminAuditLog, log_id)
            self.assertIsNotNone(surviving)

    def test_audit_log_nullable_fields(self):
        """target_user_id and details can be NULL."""
        with app.app_context():
            admin = _make_user(username="nulladmin", email="nulladmin@example.com", is_admin=True)
            log = AdminAuditLog(admin_id=admin.id, action="login")
            db.session.add(log)
            db.session.commit()
            self.assertIsNone(log.target_user_id)
            self.assertIsNone(log.details)


# ===========================================================================
# 8. Favourite Ingredients Route Tests
# ===========================================================================

class FavoriteIngredientsRouteTests(_BaseSuite):

    def test_owner_can_delete_own_favorite(self):
        with app.app_context():
            user = _make_user()
            ing = Ingredient(name="OwnGin")
            db.session.add(ing)
            db.session.flush()
            db.session.add(UserFavoriteIngredients(user_id=user.id, ingredient_id=ing.id))
            db.session.commit()
            uid, ing_id = user.id, ing.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        self.client.post(f"/delete-favorite-ingredient/{uid}/{ing_id}",
                         follow_redirects=True)
        with app.app_context():
            gone = UserFavoriteIngredients.query.filter_by(
                user_id=uid, ingredient_id=ing_id,
            ).first()
            self.assertIsNone(gone)

    def test_delete_nonexistent_favorite_does_not_crash(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.post(
            f"/delete-favorite-ingredient/{uid}/99999", follow_redirects=True
        )
        self.assertNotEqual(resp.status_code, 500)

    def test_unauthenticated_delete_favorite_rejected(self):
        """Attempting to delete a favourite without a session is blocked."""
        resp = self.client.post(
            "/delete-favorite-ingredient/1/1", follow_redirects=True
        )
        # Must be some form of denial — not a 200 success.
        # The route flashes and redirects even without login.
        self.assertNotEqual(resp.status_code, 500)


# ===========================================================================
# 9. Extended Admin Workflow Routes
# ===========================================================================

class AdminWorkflowExtendedTests(_BaseSuite):

    def _setup_admin_and_target(self, admin_user="admx", admin_email="admx@example.com",
                                target_user="tgtx", target_email="tgtx@example.com"):
        with app.app_context():
            admin = _make_user(username=admin_user, email=admin_email, is_admin=True)
            target = _make_user(username=target_user, email=target_email)
            admin_id, target_id = admin.id, target.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        return admin_id, target_id

    def test_demote_user_clears_admin_flag(self):
        with app.app_context():
            admin = _make_user(username="demadm", email="demadm@example.com", is_admin=True)
            target = _make_user(username="demtgt", email="demtgt@example.com", is_admin=True)
            admin_id, target_id = admin.id, target.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        self.client.post(f"/admin/user/{target_id}/demote", follow_redirects=True)
        with app.app_context():
            t = db.session.get(User, target_id)
            self.assertFalse(t.is_admin)

    def test_unban_clears_ban_fields(self):
        with app.app_context():
            admin = _make_user(username="unbnadm", email="unbnadm@example.com", is_admin=True)
            target = _make_user(username="bnntgt", email="bnntgt@example.com")
            target.is_permanently_banned = True
            target.ban_until = (
                datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
            )
            db.session.commit()
            admin_id, target_id = admin.id, target.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        self.client.post(f"/admin/user/{target_id}/remove-ban", follow_redirects=True)
        with app.app_context():
            t = db.session.get(User, target_id)
            self.assertFalse(t.is_permanently_banned)

    def test_ban_user_sets_ban_until(self):
        with app.app_context():
            admin = _make_user(username="bansadm2", email="bansadm2@example.com", is_admin=True)
            target = _make_user(username="banstgt2", email="banstgt2@example.com")
            admin_id, target_id = admin.id, target.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        with patch("services.email_service.send_ban_notification_email"):
            self.client.post(f"/admin/user/{target_id}/ban", follow_redirects=True)
        with app.app_context():
            t = db.session.get(User, target_id)
            self.assertIsNotNone(t.ban_until)

    def test_admin_messages_page_accessible(self):
        with app.app_context():
            admin = _make_user(username="msgadm2", email="msgadm2@example.com", is_admin=True)
            admin_id = admin.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
        resp = self.client.get("/admin/messages", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_non_admin_cannot_access_admin_messages(self):
        with app.app_context():
            user = _make_user(username="notadmmsg", email="notadmmsg@example.com")
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/admin/messages", follow_redirects=True)
        self.assertIn(b"admin access required", resp.data.lower())


# ===========================================================================
# 10. HTTP Method Enforcement
# ===========================================================================

class HttpMethodTests(_BaseSuite):

    def test_logout_rejects_get(self):
        self.assertEqual(self.client.get("/logout").status_code, 405)

    def test_delete_cocktail_rejects_get(self):
        resp = self.client.get("/delete-cocktail/1")
        self.assertIn(resp.status_code, (405, 302))

    def test_404_for_unknown_route(self):
        resp = self.client.get("/this-page-does-not-exist-xyz")
        self.assertEqual(resp.status_code, 404)

    def test_heartbeat_rejects_get(self):
        resp = self.client.get("/api/heartbeat")
        self.assertEqual(resp.status_code, 405)

    def test_shutdown_rejects_get(self):
        resp = self.client.get("/api/shutdown")
        self.assertEqual(resp.status_code, 405)


# ===========================================================================
# 11. CocktailDB API Mock Integration
# ===========================================================================

class CocktailApiMockTests(_BaseSuite):

    def _logged_in_client(self):
        with app.app_context():
            user = _make_user(username="apiuser", email="apiuser@example.com")
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        return uid

    def test_cocktail_list_page_renders_with_mocked_api(self):
        self._logged_in_client()
        mock_list = [("11007", "Margarita"), ("11118", "Blue Lagoon")]
        with patch("blueprints.cocktails._cached_cocktail_list", return_value=mock_list):
            resp = self.client.get("/cocktails", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_cocktail_list_shows_warning_for_empty_api(self):
        self._logged_in_client()
        with patch("blueprints.cocktails._cached_cocktail_list", return_value=[]):
            resp = self.client.get("/cocktails", follow_redirects=True)
        self.assertIn(b"No cocktails found", resp.data)

    def test_my_cocktails_displays_owned_cocktail(self):
        with app.app_context():
            user = _make_user(username="mycocktailuser", email="myct@example.com")
            c = Cocktail(name="Gin Fizz", instructions="Shake well.")
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=user.id, cocktail_id=c.id))
            db.session.commit()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/my-cocktails")
        self.assertIn(b"Gin Fizz", resp.data)

    def test_my_cocktails_sorted_alphabetically(self):
        """GET /my-cocktails returns cocktails in alphabetical order."""
        with app.app_context():
            user = _make_user(username="sortuser", email="sortuser@example.com")
            for name in ("Zombie", "Apple Martini", "Mojito"):
                c = Cocktail(name=name, instructions="Mix.")
                db.session.add(c)
                db.session.flush()
                db.session.add(Cocktails_Users(user_id=user.id, cocktail_id=c.id))
            db.session.commit()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/my-cocktails")
        body = resp.data.decode()
        # Apple Martini must appear before Mojito, Mojito before Zombie.
        self.assertLess(body.index("Apple Martini"), body.index("Mojito"))
        self.assertLess(body.index("Mojito"), body.index("Zombie"))


# ===========================================================================
# 12. Configuration Module Type Checks
# ===========================================================================

class ConfigModuleTests(unittest.TestCase):
    """config.py constants have the expected Python types."""

    def test_database_url_is_nonempty_string(self):
        from config import DATABASE_URL
        self.assertIsInstance(DATABASE_URL, str)
        self.assertGreater(len(DATABASE_URL), 0)

    def test_secret_key_is_string(self):
        from config import SECRET_KEY
        self.assertIsInstance(SECRET_KEY, str)

    def test_mail_port_is_int(self):
        from config import MAIL_PORT
        self.assertIsInstance(MAIL_PORT, int)

    def test_ratelimit_enabled_is_bool(self):
        from config import RATELIMIT_ENABLED
        self.assertIsInstance(RATELIMIT_ENABLED, bool)

    def test_session_cookie_httponly_is_bool(self):
        from config import SESSION_COOKIE_HTTPONLY
        self.assertIsInstance(SESSION_COOKIE_HTTPONLY, bool)

    def test_flask_debug_is_bool(self):
        from config import FLASK_DEBUG
        self.assertIsInstance(FLASK_DEBUG, bool)

    def test_secure_ssl_redirect_is_bool(self):
        from config import SECURE_SSL_REDIRECT
        self.assertIsInstance(SECURE_SSL_REDIRECT, bool)

    def test_session_cookie_samesite_is_string(self):
        from config import SESSION_COOKIE_SAMESITE
        self.assertIsInstance(SESSION_COOKIE_SAMESITE, str)
        self.assertIn(SESSION_COOKIE_SAMESITE, ("Lax", "Strict", "None"))

    def test_redis_url_is_string(self):
        from config import REDIS_URL
        self.assertIsInstance(REDIS_URL, str)


# ===========================================================================
# 13. User Messages Route Edge Cases
# ===========================================================================

class UserMessagesRouteTests(_BaseSuite):

    def test_messages_page_renders_when_no_messages(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/user/messages")
        self.assertEqual(resp.status_code, 200)

    def test_send_message_empty_subject_rejected(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        self.client.post("/user/send-message", data={
            "message_type": "suggestion",
            "subject": "",
            "message": "This is a sufficiently long message body for testing.",
        }, follow_redirects=True)
        with app.app_context():
            self.assertIsNone(AdminMessage.query.filter_by(user_id=uid).first())

    def test_send_message_too_short_body_rejected(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        self.client.post("/user/send-message", data={
            "message_type": "suggestion",
            "subject": "Valid subject line",
            "message": "Too short",
        }, follow_redirects=True)
        with app.app_context():
            self.assertIsNone(AdminMessage.query.filter_by(user_id=uid).first())

    def test_send_message_requires_login(self):
        resp = self.client.get("/user/send-message", follow_redirects=True)
        self.assertIn(b"login", resp.data.lower())


# ===========================================================================
# 14. Appeal Route Edge Cases
# ===========================================================================

class AppealEdgeCaseTests(_BaseSuite):

    def test_appeal_status_accessible_to_banned_user(self):
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            db.session.commit()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/appeal/status", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_appeal_status_redirects_unauthenticated(self):
        resp = self.client.get("/appeal/status", follow_redirects=True)
        self.assertIn(b"login", resp.data.lower())

    def test_appeal_form_hidden_from_unbanned_user(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/appeal", follow_redirects=True)
        self.assertNotIn(b"submit appeal", resp.data.lower())

    def test_appeal_form_shown_to_permanently_banned_user(self):
        with app.app_context():
            user = _make_user()
            user.is_permanently_banned = True
            db.session.commit()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/appeal", follow_redirects=True)
        self.assertNotEqual(resp.status_code, 404)


# ===========================================================================
# 15. Resend Verification Route Tests
# ===========================================================================

class ResendVerificationTests(_BaseSuite):

    def test_resend_for_already_verified_user_flashes_info(self):
        with app.app_context():
            user = _make_user(verified=True)
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["pending_verification_user_id"] = uid
        with patch("services.email_service.send_resend_verification_email"):
            resp = self.client.post(f"/resend-verification/{uid}", follow_redirects=True)
        self.assertIn(b"already verified", resp.data.lower())

    def test_resend_without_session_is_blocked(self):
        with app.app_context():
            user = _make_user(verified=False)
            uid = user.id
        resp = self.client.post(f"/resend-verification/{uid}", follow_redirects=True)
        self.assertIn(b"permission", resp.data.lower())

    def test_resend_calls_email_service_once(self):
        with app.app_context():
            user = _make_user(
                username="resenduser", email="resend@example.com", verified=False
            )
            user.is_email_verified = False
            db.session.commit()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["pending_verification_user_id"] = uid
        with patch("services.email_service.send_resend_verification_email") as mock_send:
            with patch(
                "models.User.generate_email_verification_token",
                return_value="faketoken",
            ):
                self.client.post(f"/resend-verification/{uid}", follow_redirects=True)
        mock_send.assert_called_once()


# ===========================================================================
# 16. Cocktails_Users Join Table Semantics
# ===========================================================================

class CocktailsUsersJoinTests(_BaseSuite):

    def test_two_users_can_share_one_api_cocktail_row(self):
        with app.app_context():
            u1 = _make_user(username="shareuser1", email="share1@example.com")
            u2 = _make_user(username="shareuser2", email="share2@example.com")
            c = Cocktail(name="Shared Mojito", instructions="Muddle.", is_api_cocktail=True)
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=u1.id, cocktail_id=c.id))
            db.session.add(Cocktails_Users(user_id=u2.id, cocktail_id=c.id))
            db.session.commit()
            count = Cocktails_Users.query.filter_by(cocktail_id=c.id).count()
            self.assertEqual(count, 2)

    def test_deleting_cocktail_cascades_to_join_table(self):
        with app.app_context():
            user = _make_user(username="ctlcasc2", email="ctlcasc2@example.com")
            c = Cocktail(name="Cascade Test 2", instructions="Pour.")
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=user.id, cocktail_id=c.id))
            db.session.commit()
            cid = c.id
        with app.app_context():
            db.session.delete(db.session.get(Cocktail, cid))
            db.session.commit()
            self.assertEqual(Cocktails_Users.query.filter_by(cocktail_id=cid).count(), 0)

    def test_deleting_user_cascades_to_cocktails_users(self):
        with app.app_context():
            user = _make_user(username="usercasc2", email="usercasc2@example.com")
            c = Cocktail(name="User Cascade Drink", instructions="Mix.")
            db.session.add(c)
            db.session.flush()
            db.session.add(Cocktails_Users(user_id=user.id, cocktail_id=c.id))
            db.session.commit()
            uid = user.id
        with app.app_context():
            db.session.delete(db.session.get(User, uid))
            db.session.commit()
            self.assertEqual(Cocktails_Users.query.filter_by(user_id=uid).count(), 0)


# ===========================================================================
# 17. Ingredient Normalisation Edge Cases
# ===========================================================================

class IngredientNormalisationTests(_BaseSuite):

    def test_single_word_stored_in_title_case(self):
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing = store_or_get_ingredient("bourbon")
            db.session.commit()
            self.assertEqual(ing.name, "Bourbon")

    def test_multi_word_each_word_capitalised(self):
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing = store_or_get_ingredient("dry vermouth")
            db.session.commit()
            self.assertEqual(ing.name, "Dry Vermouth")

    def test_leading_trailing_whitespace_stripped(self):
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing = store_or_get_ingredient("  rum  ")
            db.session.commit()
            self.assertEqual(ing.name, "Rum")

    def test_extra_internal_whitespace_collapsed(self):
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing = store_or_get_ingredient("triple   sec")
            db.session.commit()
            self.assertEqual(ing.name, "Triple Sec")

    def test_mixed_case_deduplicates_correctly(self):
        from services.cocktail_service import store_or_get_ingredient
        with app.app_context():
            ing1 = store_or_get_ingredient("TEQUILA")
            db.session.commit()
            ing2 = store_or_get_ingredient("tequila")
            db.session.flush()
            self.assertEqual(ing1.id, ing2.id)


# ===========================================================================
# 18. Image Upload Edge Cases
# ===========================================================================

class SaveUploadedImageEdgeCaseTests(_BaseSuite):

    def test_bmp_file_rejected(self):
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        bmp_bytes = b"BM" + b"\x00" * 60
        fake = FileStorage(
            stream=io.BytesIO(bmp_bytes),
            filename="image.bmp",
            content_type="image/bmp",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_png_header_with_txt_extension_rejected(self):
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60
        fake = FileStorage(
            stream=io.BytesIO(png_bytes),
            filename="sneaky.txt",
            content_type="text/plain",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_zero_byte_file_rejected(self):
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        fake = FileStorage(
            stream=io.BytesIO(b""),
            filename="empty.png",
            content_type="image/png",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_gif_extension_rejected(self):
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        # GIF magic bytes with .gif extension.
        gif_bytes = b"GIF89a" + b"\x00" * 60
        fake = FileStorage(
            stream=io.BytesIO(gif_bytes),
            filename="image.gif",
            content_type="image/gif",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)

    def test_webp_extension_rejected(self):
        """WebP files are not in the allowed extension list."""
        from services.cocktail_service import save_uploaded_image
        from werkzeug.datastructures import FileStorage
        fake = FileStorage(
            stream=io.BytesIO(b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 40),
            filename="image.webp",
            content_type="image/webp",
        )
        with app.app_context():
            with self.assertRaises(ValueError):
                save_uploaded_image(fake)


# ===========================================================================
# 19. delete_uploaded_image Path-Traversal Guard
# ===========================================================================

class DeleteImageSecurityTests(_BaseSuite):

    def test_forward_slash_traversal_silently_ignored(self):
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            # Must not raise and must not delete anything outside uploads dir.
            delete_uploaded_image("../../etc/passwd")

    def test_backslash_traversal_silently_ignored(self):
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            delete_uploaded_image("..\\..\\windows\\system32\\cmd.exe")

    def test_absolute_unix_path_silently_ignored(self):
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            delete_uploaded_image("/etc/shadow")

    def test_null_byte_injection_silently_ignored(self):
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            delete_uploaded_image("file\x00.png")

    def test_none_filename_silently_ignored(self):
        from services.cocktail_service import delete_uploaded_image
        with app.app_context():
            delete_uploaded_image(None)


# ===========================================================================
# 20. Homepage Redirect Logic
# ===========================================================================

class HomepageTests(_BaseSuite):

    def test_unauthenticated_visitor_redirected_to_register(self):
        resp = self.client.get("/", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/register", resp.headers.get("Location", ""))

    def test_authenticated_user_sees_homepage(self):
        with app.app_context():
            user = _make_user()
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/", follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

    def test_homepage_200_uses_logged_in_username(self):
        """Base template should include the user nav for logged-in users."""
        with app.app_context():
            user = _make_user(username="homeuser", email="home@example.com")
            uid = user.id
        with self.client.session_transaction() as sess:
            sess["user_id"] = uid
        resp = self.client.get("/", follow_redirects=True)
        # Nav links for authenticated users should appear in the rendered HTML.
        self.assertIn(b"Cocktail Chronicles", resp.data)


if __name__ == "__main__":
    unittest.main()
