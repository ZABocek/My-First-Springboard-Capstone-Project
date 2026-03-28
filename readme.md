# Cocktail Chronicles

## Overview

Cocktail Chronicles is a Flask web application for discovering, creating, and saving cocktail recipes. Users register an account, verify their email, and can then browse cocktails from the CocktailDB API, add them to a personal collection, create original recipes (with optional image uploads), and manage favorite ingredients. An admin system handles user moderation, messaging, and ban appeals.

## Features

- **User Registration and Authentication**: Sign up, email verification, log in, and log out.
- **Profile Management**: Update drink-type preference and manage a list of favourite ingredients. Only the profile owner or an admin can make changes.
- **Discover Cocktails**: Browse a live list fetched from the CocktailDB API.
- **Cocktail Details**: View full ingredient lists and instructions for any API cocktail.
- **Add API Cocktails**: Save any API cocktail to your personal collection. API cocktail rows are shared across users — one DB row per drink, deduplicated by the stable `idDrink` key from TheCocktailDB (with a name-based fallback for legacy rows).
- **Create Original Cocktails**: Build and save your own recipe, including image upload (PNG/JPG/JPEG; validated by extension and magic-byte header).
- **Edit Cocktails**: Edit your saved cocktails. Editing an API cocktail automatically creates a personal copy so the shared record is not affected. Ownership is enforced via the `cocktails_users` join table and the `owner_id` field.
- **Favorite Ingredients**: Pin ingredients to your profile for quick reference. Ingredient names are normalised (whitespace-stripped, title-cased) so `"vodka"` and `" Vodka "` always resolve to the same row.
- **Admin Panel**: User management (promote, demote, temp-ban, permanent-ban, delete), statistics dashboard, messaging centre, and ban-appeal review.
- **Ban Appeals**: Banned users may submit a written appeal; admins can approve (lifting the ban) or reject it. Email notifications are sent at each stage.

---

## Application Architecture

The codebase uses Flask's **application factory** pattern with **blueprints** and a **service layer**.

```
app.py                  # create_app() factory — wires extensions and blueprints
config.py               # All environment-variable-driven configuration
decorators.py           # login_required and admin_required decorators
models.py               # SQLAlchemy models (User, Cocktail, Ingredient, …)
forms.py                # Flask-WTF form classes
helpers.py              # Email body generators
cocktaildb_api.py       # Async CocktailDB API client
seed.py                 # Optional development seed data

blueprints/
    auth.py             # /register, /login, /logout, /verify-email, /resend-verification
    cocktails.py        # /cocktails, /my-cocktails, /add-*, /edit-cocktail, /delete-cocktail
    admin.py            # /admin/* — panel, user management, messages, appeals
    users.py            # /, /users/profile/*, /user/messages, /appeal, /appeal/status

services/
    email_service.py    # Outbound email helpers (verification, ban notices, lifted notices)
    cocktail_service.py # Image upload/validation, image URL resolution, cocktail storage

migrations/             # Flask-Migrate / Alembic migration scripts
static/                 # CSS and user-uploaded images (static/uploads/)
templates/              # Jinja2 HTML templates
```

---

## Quick Start (Windows — double-click launcher)

The easiest way to run the app on Windows is to **double-click `start_app.bat`** in the project folder.

The launcher will:
1. Detect your virtual environment (`.venv/` or `venv/`) — or fall back to your system Python.
2. Install / verify all dependencies from `requirements.txt` automatically.
3. Start the Flask development server.
4. Open `http://127.0.0.1:5000` in your default browser after a 3-second delay.

To stop the server, press **CTRL+C** in the console window that opened.

> **Prerequisite**: **Python 3.11.x** is required (the project is pinned to
> `python-3.11.8` in `runtime.txt`).  Python 3.12+ and 3.13 are **not**
> currently supported — some pinned dependencies (e.g. `Pillow==10.0.0`,
> `SQLAlchemy==2.0.19`) fail to install or import on newer interpreter
> versions.  
> Download Python 3.11 from <https://www.python.org/downloads/> if needed.

---

## Manual Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/ZABocek/My-First-Springboard-Capstone-Project.git
    cd My-First-Springboard-Capstone-Project
    ```

2. **Set up the virtual environment**:
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS / Linux:
    source .venv/bin/activate
    ```

3. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables** (copy `.env.example` to `.env` and fill in real values):
    ```env
    SECRET_KEY=your-long-random-secret-key
    ADMIN_PASSWORD_KEY=your-admin-unlock-key
    DATABASE_URL=postgresql:///cocktail_chronicles   # omit for SQLite default
    FLASK_DEBUG=True                                  # development only; False in production
    SECURE_SSL_REDIRECT=False
    SESSION_COOKIE_SECURE=False
    SESSION_COOKIE_HTTPONLY=True
    SESSION_COOKIE_SAMESITE=Lax
    MAIL_SERVER=localhost
    MAIL_PORT=25
    MAIL_USE_TLS=False
    MAIL_USE_SSL=False
    MAIL_USERNAME=
    MAIL_PASSWORD=
    MAIL_DEFAULT_SENDER=noreply@cocktaildb.com
    RATELIMIT_ENABLED=True
    COCKTAILDB_API_KEY=1
    ```
    Generate a secure `SECRET_KEY` with:
    ```bash
    python -c "import secrets; print(secrets.token_hex(32))"
    ```

5. **Initialise the database**:
    ```bash
    flask db upgrade
    ```
    For a fresh development database you can also use:
    ```bash
    python init_db.py
    ```

6. **Run the application**:
    ```bash
    python run_app.py
    ```
    Then open `http://127.0.0.1:5000` in your browser.

---

## Database Setup

### SQLite (default — no setup required)

Out of the box the app uses an SQLite database (`cocktails.db`) in the project folder. Run `flask db upgrade` once after installation to apply the schema. No other configuration is needed.

### PostgreSQL (optional — for production or multi-user use)

1. **Create the database**:
    ```bash
    createdb cocktail_chronicles
    ```

2. **Add the connection string to your `.env` file**:
    ```env
    DATABASE_URL=postgresql:///cocktail_chronicles
    ```
    For a remote host:
    ```env
    DATABASE_URL=postgresql://username:password@hostname:5432/cocktail_chronicles
    ```

3. **Apply migrations**:
    ```bash
    flask db upgrade
    ```

### Schema Migrations (Flask-Migrate)

The project uses [Flask-Migrate](https://flask-migrate.readthedocs.io/) (Alembic) for schema version control.

| Command | Purpose |
|---|---|
| `flask db upgrade` | Apply all pending migrations to the database |
| `flask db migrate -m "description"` | Auto-generate a new migration after model changes |
| `flask db downgrade` | Roll back the last migration |
| `flask db history` | Show the migration history |

Always run `flask db upgrade` after pulling changes that include new migration files.

---

## Detailed File Descriptions

### `app.py`
Application factory (`create_app()`). Configures the Flask app, registers extensions (SQLAlchemy, Flask-Migrate, Flask-Mail, CSRFProtect, DebugToolbar), wires up the four blueprints, and attaches a security-headers `after_request` hook. A module-level `app = create_app()` is kept for Gunicorn / `run_app.py` compatibility.

### `config.py`
Reads all sensitive and environment-specific values from environment variables via `python-dotenv`, with safe development defaults. Imported by `app.py` (core Flask/mail/session config), `blueprints/admin.py` (`ADMIN_PASSWORD_KEY`), and `cocktaildb_api.py` (`COCKTAILDB_API_KEY`). The file contains **no hardcoded secrets** and is safe to track in version control; real secrets belong in `.env`.

### `decorators.py`
Provides two reusable route guards:
- `@login_required` — checks `session["user_id"]`; redirects to login if absent.
- `@admin_required` — checks session, then queries the DB to confirm `user.is_admin`; redirects non-admins to the homepage.

### `models.py`
SQLAlchemy model definitions for all eight tables. Key points:
- `User.register()` hashes the password with bcrypt before persisting.
- `User.authenticate()` verifies the bcrypt hash; returns `False` on failure.
- `User.generate_email_verification_token()` / `verify_email_token()` use `itsdangerous.URLSafeTimedSerializer` with the live `current_app.config['SECRET_KEY']` (app-factory-compatible; no global serializer).
- `Cocktail.owner_id` (FK → `user.id`, nullable) tracks which user owns a user-created or API-copied cocktail. Shared API cocktails have `owner_id = NULL`.

### `forms.py`
Flask-WTF form classes: `RegisterForm`, `LoginForm`, `PreferenceForm`, `UserFavoriteIngredientForm`, `OriginalCocktailForm`, `EditCocktailForm`, `ListCocktailsForm`, `UserMessageForm`, `AppealForm`, `AdminForm`, `AdminMessageForm`.

### `helpers.py`
Plain-text email body generators for verification emails, resend emails, ban notices, and ban-lifted notices. Called by `services/email_service.py`.

### `cocktaildb_api.py`
Async API client for [TheCocktailDB](https://www.thecocktaildb.com/api.php). Provides `get_cocktail_detail()`, `get_combined_cocktails_list()`, and `list_ingredients()`. Route handlers call these via an explicit event loop since Flask's WSGI context is synchronous. The API base URL is built from `config.COCKTAILDB_API_KEY` (defaults to `"1"`, the public free-tier key) so the key can be swapped via `.env` without touching source code. All synchronous `requests.get()` calls use an explicit `(5, 10)` connect/read timeout and are decorated with `@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)` for automatic retry on transient network errors.

### `blueprints/auth.py`
Handles the full authentication lifecycle:
- `register` — stages the user row, generates the signed token, commits only after the token is successfully created (so `rollback()` actually reverts the staged row if token generation fails), then dispatches the verification email in a background thread. Because SMTP delivery is asynchronous, logging records any background failure; users can request a resend from the verification-pending page.
- `verify_email` — decodes the signed token and stamps `email_verified_at`.
- `verification_pending` / `resend_verification` — manages the unverified-user waiting state.
- `login` — authenticates, then checks email verification and ban status before setting the session.
- `logout` — removes `user_id` from the session.

### `blueprints/cocktails.py`
All cocktail-related routes:
- `list_cocktails` — fetches the full API list and renders a selection form.
- `cocktail_details` — shows ingredients and instructions for a single API cocktail.
- `add_api_cocktails` — calls `process_and_store_new_cocktail()` which deduplicates shared rows.
- `my_cocktails` — assembles the user's collection using `get_cocktail_image_url()` for consistent image resolution.
- `add_original_cocktails` — creates a user-owned cocktail; validates image uploads via magic-byte check.
- `edit_cocktail` — uses a JOIN query to find the requesting user's personal copy (not any user's copy); creates it on first edit, swapping the `cocktails_users` link away from the shared API record.
- `delete_cocktail` — removes the user's join-table row; orphaned cocktails (user-created **or** API) are deleted when no other user references them; locally uploaded image files are removed from disk after the DB commit succeeds.
- `uploaded_file` — serves files from the configured uploads directory.

### `blueprints/admin.py`
Admin-only routes (all decorated with `@admin_required`):
- `admin_panel` — renders stats, full user list, and pending appeals.
- `promote_user` / `demote_user` — toggle `is_admin`.
- `ban_user` — sets a 365-day `ban_until`; sends email notification.
- `ban_user_permanently` — sets `is_permanently_banned`; sends email notification.
- `delete_user` — hard deletes the user row (cascade removes messages and appeals).
- `admin_messages` / `respond_to_message` — messaging centre; marks messages read on open.
- `approve_appeal` / `reject_appeal` — resolves a ban appeal; `approve` also clears both ban fields and sends a lifted-ban email.
- `remove_user_ban` — direct unban without going through the appeals system.

The `_guard_self_action()` helper prevents admins from acting on their own account across all management routes.

### `blueprints/users.py`
User-facing non-auth routes:
- `homepage` — renders the dashboard for logged-in users; redirects anonymous visitors to register.
- `profile` — manages preference and favourite-ingredient updates; enforces owner-or-admin access.
- `delete_favorite_ingredient` — owner-only DELETE via POST.
- `user_messages` — displays the user's message thread with admin, newest first.
- `send_user_message` — creates an `AdminMessage` row for admin review.
- `submit_appeal` — validates ban status, blocks duplicate pending appeals, persists the `UserAppeal` row; redirects to `appeal_status` (not the homepage) so still-banned users are not bounced back by the before-request ban check.
- `appeal_status` — ban-exempt stable landing page shown after a banned user submits (or already has) a pending appeal; prevents the `enforce_ban → submit_appeal → enforce_ban` redirect loop.

### `services/email_service.py`
Centralised outbound email dispatch. Emails are sent in background **daemon threads** so the HTTP request returns immediately without waiting for the SMTP round-trip. Each public function accepts only a `User` object (and a token where needed), builds the body via `helpers.py`, then hands the assembled `Message` to the internal `_dispatch()` helper. Functions: `send_verification_email`, `send_resend_verification_email`, `send_ban_notification_email`, `send_ban_lifted_email`.

### `services/cocktail_service.py`
Cocktail storage and image handling:
- `save_uploaded_image()` — validates file extension and magic bytes (JPEG `\xff\xd8`, PNG `\x89P`), then saves to `static/uploads/` using `secure_filename`.
- `get_cocktail_image_url()` — single authoritative resolver: prefers `image_url` (user uploads), falls back to `strDrinkThumb` (API URLs or legacy filenames).
- `store_or_get_ingredient()` — normalises the ingredient name (`strip` + `title()`) before lookup so spelling-case variants always resolve to the same canonical row; get-or-create without committing.
- `_find_existing_api_cocktail()` — private helper that looks up a shared API cocktail first by the stable `api_cocktail_id` (TheCocktailDB `idDrink`), then falls back to name for legacy rows and back-fills the stable ID.
- `process_and_store_new_cocktail()` — uses `_find_existing_api_cocktail()` for robust deduplication, uses `flush()` to obtain PKs before building FK rows, and emits a single `commit()`.

---

## API Integration

The application integrates with the [CocktailDB API](https://www.thecocktaildb.com/api.php) to fetch cocktail data. All API communication is handled asynchronously in `cocktaildb_api.py` and called from route handlers.

---

## Usage

1. **Register and verify your email**: Create an account and click the link sent to your inbox before logging in.
2. **Manage your profile**: Set your drink-type preference and pin favourite ingredients.
3. **Discover cocktails**: Browse the full API list and view detailed recipes.
4. **Add API cocktails**: Save any API cocktail to your personal collection.
5. **Create original cocktails**: Use the original-cocktail form to build your own recipes with custom ingredients and an optional image.
6. **Edit cocktails**: Click edit on any saved cocktail. API cocktails are automatically copied to your account on first edit so your changes stay private.
7. **Messaging**: Send a report or suggestion to admin via the messaging centre.

---

## Security

| Control | Details |
|---|---|
| CSRF protection | All state-changing routes protected by Flask-WTF CSRF tokens |
| Password hashing | bcrypt via Flask-Bcrypt; plaintext passwords are never stored |
| Email verification | Required before first login; token signed with `itsdangerous` (24 h expiry) |
| Session security | `HttpOnly`, `SameSite=Lax` (configurable via `SESSION_COOKIE_SAMESITE`), `Secure` (in production), 1-hour lifetime |
| Cookie flag correctness | `SESSION_COOKIE_SECURE` is set from its own `SESSION_COOKIE_SECURE` env var (independent of `SECURE_SSL_REDIRECT`); `HttpOnly` is controlled separately by `SESSION_COOKIE_HTTPONLY` |
| Image upload safety | File extension allow-list + magic-byte header check; `secure_filename` sanitisation |
| Cocktail ownership | `cocktails_users` join table verified before any edit or delete |
| API-cocktail copy isolation | JOIN query finds the *requesting user's own* copy, not any user's copy with that name |
| Admin self-action guard | `_guard_self_action()` prevents admins from banning or deleting themselves |
| SQL echo in production | `SQLALCHEMY_ECHO` is tied to `DEBUG`; never logs SQL in production |
| Security response headers | `X-Frame-Options`, `X-Content-Type-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, and a strict `Content-Security-Policy` added to every response |
| Ban enforcement on every request | `@app.before_request` hook checks ban status on every authenticated request, not just at login — temporary and permanent bans both redirect to the appeal form |
| Login rate limiting | `@limiter.limit("10 per minute")` on `/login` prevents automated brute-force password guessing |
| Registration rate limiting | `@limiter.limit("5 per hour")` on `/register` prevents bulk account creation and DB exhaustion |
| XSS protection in flash messages | Jinja2 auto-escaping is preserved for all flash messages; no `\| safe` override is used, preventing stored-XSS via user-controlled content (e.g. usernames) in admin-facing alerts |

---

## Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Springboard](https://www.springboard.com/) for the capstone project guidelines.
- [TheCocktailDB](https://www.thecocktaildb.com/) for the cocktail data API.
- [Flask](https://flask.palletsprojects.com/) for the web framework.
- [SQLAlchemy](https://www.sqlalchemy.org/) for the ORM.
- [Flask-WTF](https://flask-wtf.readthedocs.io/) for form handling and CSRF protection.
- [Flask-Migrate](https://flask-migrate.readthedocs.io/) for database schema migrations.
- [Flask-Bcrypt](https://flask-bcrypt.readthedocs.io/) for password hashing.
- [Flask-Mail](https://pythonhosted.org/Flask-Mail/) for transactional email.

---

## Database Schema (ERD)

```mermaid
erDiagram
    USER {
        int id PK
        text email UK
        text username UK
        text password
        string preference
        boolean is_admin
        datetime ban_until
        boolean is_permanently_banned
        datetime created_at
        boolean is_email_verified
        datetime email_verified_at
    }

    INGREDIENT {
        int id PK
        text name UK
    }

    COCKTAIL {
        int id PK
        text name
        text instructions
        string strDrinkThumb
        string image_url
        boolean is_api_cocktail
        string api_cocktail_id
        int owner_id FK
    }

    COCKTAILS_INGREDIENTS {
        int id PK
        int cocktail_id FK
        int ingredient_id FK
        text quantity
    }

    COCKTAILS_USERS {
        int user_id FK
        int cocktail_id FK
    }

    USER_FAVORITE_INGREDIENTS {
        int user_id FK
        int ingredient_id FK
    }

    ADMIN_MESSAGE {
        int id PK
        int user_id FK
        string subject
        text message
        string message_type
        datetime created_at
        boolean is_read
        text admin_response
        datetime admin_response_date
    }

    USER_APPEAL {
        int id PK
        int user_id FK
        text appeal_text
        datetime created_at
        string status
        text admin_response
        datetime admin_response_date
    }

    ADMIN_AUDIT_LOG {
        int id PK
        int admin_id FK
        string action
        int target_user_id FK
        text details
        datetime created_at
    }

    USER ||--o{ COCKTAILS_USERS : "owns"
    COCKTAIL ||--o{ COCKTAILS_USERS : "belongs to"
    USER ||--o{ USER_FAVORITE_INGREDIENTS : "saves"
    INGREDIENT ||--o{ USER_FAVORITE_INGREDIENTS : "saved by"
    COCKTAIL ||--o{ COCKTAILS_INGREDIENTS : "contains"
    INGREDIENT ||--o{ COCKTAILS_INGREDIENTS : "used in"
    USER ||--o{ ADMIN_MESSAGE : "sends"
    USER ||--o{ USER_APPEAL : "submits"
    USER ||--o{ COCKTAIL : "owns (user-created)"
    USER ||--o{ ADMIN_AUDIT_LOG : "performs (as admin)"
    USER ||--o{ ADMIN_AUDIT_LOG : "targeted by"
```


