# Security Documentation - Name Your Poison

This document outlines the security measures implemented in the "Name Your Poison" cocktail application to protect the app and ensure only authorized users can modify it.

## Overview

The application implements multiple layers of security to protect against unauthorized access and modifications:

1. **Environment Variables & Secrets Management**
2. **Admin Authentication System**
3. **User Role Management**
4. **Session Security**
5. **Security Headers**
6. **CSRF Protection**
7. **Password Hashing**
8. **Input Validation**

---

## 1. Environment Variables & Secrets Management

### `.env` File

All sensitive configuration is stored in a `.env` file that is **NOT committed to GitHub**. This file includes:

```
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this-in-production-2025
ADMIN_PASSWORD_KEY=your-super-secret-admin-key-change-this
DATABASE_URL=sqlite:///cocktails.db
```

### Configuration

- **`SECRET_KEY`**: Used for Flask session management and CSRF token generation
- **`ADMIN_PASSWORD_KEY`**: Required to access the admin panel and grant admin privileges
- **`DATABASE_URL`**: Database connection string (supports SQLite and PostgreSQL)

### Security Best Practices

1. **Change both keys** before deploying to production
2. **Never commit `.env`** to version control (already in `.gitignore`)
3. **Use strong, random values** for both keys (at least 32 characters)
4. **Store the `.env` file securely** on your production server
5. **Restrict file permissions** to owner-only access: `chmod 600 .env`

---

## 2. Admin Authentication System

### Admin Panel Access

The admin panel is protected by a two-step authentication process:

#### Step 1: Unlock Admin Access
- Navigate to `/admin/unlock`
- Enter your `ADMIN_PASSWORD_KEY` from the `.env` file
- If correct, your user account is promoted to admin status

#### Step 2: Admin Functions
Once promoted to admin, you can:
- View application statistics
- Manage user accounts (promote/demote admins)
- Access the admin panel at `/admin/panel`

### How It Works

1. User visits `/admin/unlock`
2. User enters the admin password key
3. If the key matches `ADMIN_PASSWORD_KEY` from `.env`:
   - The user's `is_admin` flag is set to `True` in the database
   - User is granted access to the admin panel
4. Only users with `is_admin=True` can access `/admin/panel`

---

## 3. User Role Management

### User Model Changes

The `User` model now includes an `is_admin` field:

```python
is_admin = db.Column(
    db.Boolean,
    nullable=False,
    default=False
)
```

### Admin Decorator

Two decorators protect sensitive routes:

```python
@login_required  # Requires user to be logged in
@admin_required  # Requires user to have admin privileges
```

### Admin Functions

- **`/admin/unlock`**: Unlock admin access with password key
- **`/admin/panel`**: View admin dashboard (admin only)
- **`/admin/user/<id>/promote`**: Promote user to admin (admin only)
- **`/admin/user/<id>/demote`**: Demote user from admin (admin only)

---

## 4. Session Security

### Session Configuration

```python
SESSION_COOKIE_SECURE = True           # HTTPS only (production)
SESSION_COOKIE_HTTPONLY = True         # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'        # CSRF protection
PERMANENT_SESSION_LIFETIME = 3600      # 1 hour timeout
SESSION_REFRESH_EACH_REQUEST = True    # Refresh on each request
```

### Session Behavior

- Sessions expire after **1 hour of inactivity**
- Session cookies cannot be accessed by JavaScript (prevents XSS attacks)
- Session cookies are only sent over HTTPS in production
- SameSite cookie attribute prevents CSRF attacks

---

## 5. Security Headers

All responses include security headers to protect against common attacks:

```python
X-Frame-Options: SAMEORIGIN                    # Prevent clickjacking
X-Content-Type-Options: nosniff                # Prevent MIME sniffing
X-XSS-Protection: 1; mode=block               # Enable XSS protection
Referrer-Policy: strict-origin-when-cross-origin  # Control referrer info
Permissions-Policy: geolocation=(), microphone=(), camera=()  # Disable risky APIs
```

---

## 6. CSRF Protection

### CSRF Token Implementation

All forms include CSRF tokens via Flask-WTF:

```html
<form method="POST">
    {{ form.hidden_tag() }}  <!-- Includes CSRF token -->
    ...
</form>
```

### Protection

- Every POST/PUT/DELETE request is validated against the CSRF token
- Tokens are unique per session and request
- Invalid tokens are rejected with a 400 error

---

## 7. Password Hashing

### Bcrypt Hashing

User passwords are hashed using bcrypt with a salt:

```python
hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')
```

### Security Features

- Passwords are **never stored in plain text**
- Each password is hashed with a **unique salt**
- Bcrypt has a **work factor** that makes brute-force attacks impractical
- Invalid login attempts don't reveal whether username or password was wrong

---

## 8. Input Validation

### File Upload Security

- **Whitelist extensions**: Only `.png`, `.jpg`, `.jpeg` allowed
- **Secure filenames**: Using `secure_filename()` from Werkzeug
- **File size limits**: Can be implemented if needed
- **Upload directory**: Separate directory (`/static/uploads/`) for user uploads

### Form Validation

- **Email validation**: Via Flask-WTF
- **Password requirements**: Enforced by `RegisterForm`
- **Username validation**: Unique usernames, alphanumeric characters

---

## Production Deployment Checklist

Before deploying to production, ensure:

- [ ] Create a strong `.env` file with random keys (32+ characters)
- [ ] Set `SECURE_SSL_REDIRECT = True` in `.env`
- [ ] Set `SESSION_COOKIE_SECURE = True` in `.env`
- [ ] Use HTTPS/SSL certificate
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `DEBUG = False` in Flask config
- [ ] Store `.env` securely on production server
- [ ] Restrict `.env` file permissions: `chmod 600 .env`
- [ ] Set up regular database backups
- [ ] Enable logging and monitoring
- [ ] Use strong admin password key (32+ characters, mix of upper/lower/numbers/symbols)
- [ ] Test admin login flow before going live

---

## Preventing Unauthorized Modifications

### Who Can Modify the App?

1. **Only admin users** can access the admin panel
2. **Only you** have the `ADMIN_PASSWORD_KEY` for the admin panel
3. **Only admins** can create other admins
4. Regular users can only manage their own data

### GitHub Security

- `.env` file is in `.gitignore` and never committed
- `ADMIN_PASSWORD_KEY` is never exposed in version control
- Only you have access to the `.env` file on your server
- Other contributors cannot access sensitive keys

### API Security

- All modification endpoints require CSRF tokens
- All admin endpoints require authentication
- Rate limiting can be enabled (see config)
- Input validation prevents injection attacks

---

## Monitoring & Auditing

To track changes, consider implementing:

1. **Logging**: Log all admin actions
2. **Audit trail**: Track who modified what and when
3. **Alerts**: Notify you of failed admin login attempts
4. **Backups**: Regular database backups

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** create a public GitHub issue
2. **Do not** share the vulnerability publicly
3. Contact the developer privately
4. Provide details and proof of concept
5. Allow time for a fix before disclosure

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security](https://flask.palletsprojects.com/en/2.3.x/security/)
- [Bcrypt Documentation](https://flask-bcrypt.readthedocs.io/)
- [CSRF Protection](https://flask-wtf.readthedocs.io/en/1.0.x/csrf/)

---

## Version History

- **v1.0** (Dec 2025): Initial security implementation
  - Added `.env` configuration
  - Implemented admin authentication
  - Added security headers
  - Enhanced session security
  - Added user role management

---

**Last Updated**: December 6, 2025

For questions about security, contact the app creator directly.
