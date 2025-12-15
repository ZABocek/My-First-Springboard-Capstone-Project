# Environment Setup Guide

This guide explains how to set up and configure the `.env` file for the "Name Your Poison" application.

## What is the `.env` File?

The `.env` file is a configuration file that stores **sensitive information** that should NOT be committed to GitHub. It includes:

- Secret keys
- Admin password
- Database configuration
- Security settings

## How to Set Up the `.env` File

### 1. Create the `.env` File

In the root directory of the project (same level as `app.py`), create a file named `.env`:

```
.env
```

### 2. Copy the Template

Copy the following content into your `.env` file:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this-in-production-2025
DEBUG=False

# Admin Panel Security Key
# Change this to a strong password that only you know
# This key is required to access the admin panel for modifications
ADMIN_PASSWORD_KEY=your-super-secret-admin-key-change-this

# Database
DATABASE_URL=sqlite:///cocktails.db

# Security Headers
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# Rate Limiting
RATELIMIT_ENABLED=True
```

### 3. Customize Your Keys

Replace the placeholder values with **strong, random keys**:

#### For `SECRET_KEY`
- Minimum 32 characters
- Mix of uppercase, lowercase, numbers, and symbols
- Examples:
  ```
  SECRET_KEY=aB9!xK2$mP7@qR5&nW3#lT8*jH6^gS4%
  SECRET_KEY=FkL9p2@mN4$xY7#wZ1%bC6&vJ3!qR8*sT
  ```

#### For `ADMIN_PASSWORD_KEY`
- Minimum 32 characters
- Different from SECRET_KEY
- Strong and memorable (for you only!)
- Examples:
  ```
  ADMIN_PASSWORD_KEY=MySecureAdminKey2025!@#$%^&*
  ADMIN_PASSWORD_KEY=C0cktailAdmin@2025#Secure!123
  ```

### 4. Keep It Secure

- **DO NOT** share your `.env` file
- **DO NOT** commit it to GitHub
- **DO NOT** share your ADMIN_PASSWORD_KEY with anyone
- Restrict file permissions (Linux/Mac):
  ```bash
  chmod 600 .env
  ```

## Using Your Configuration

### During Development

The Flask app automatically loads variables from `.env`. Just run:

```bash
python -m flask run
```

### Accessing the Admin Panel

1. Register and log in to the app
2. Navigate to `/admin/unlock`
3. Enter your `ADMIN_PASSWORD_KEY` from the `.env` file
4. You will be promoted to admin and can access `/admin/panel`

## For GitHub & Production

### GitHub

- The `.env` file is already in `.gitignore`
- It will NEVER be committed to GitHub
- Your keys remain completely private

### Production Deployment

1. Create a NEW `.env` file on your production server
2. Use **different, stronger keys** than development
3. Set `SECURE_SSL_REDIRECT=True`
4. Set `SESSION_COOKIE_SECURE=True`
5. Use HTTPS/SSL certificates
6. Restrict file permissions to owner-only: `chmod 600 .env`

## Troubleshooting

### "Module 'dotenv' not found"

Solution:
```bash
pip install python-dotenv
```

### Environment variables not loading

Solution:
1. Ensure `.env` is in the correct directory (root of project)
2. Restart Flask after creating `.env`
3. Check that variable names match exactly

### Admin unlock not working

Solution:
1. Verify you entered the exact `ADMIN_PASSWORD_KEY` from `.env`
2. Check for extra spaces or typos
3. Ensure the `.env` file is in the project root

## Example `.env` File for Testing

For testing purposes only (NOT for production):

```env
FLASK_ENV=development
SECRET_KEY=test-secret-key-development-only-1234567890
ADMIN_PASSWORD_KEY=test-admin-key-development-only
DATABASE_URL=sqlite:///cocktails.db
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
RATELIMIT_ENABLED=True
```

## Need Help?

See `SECURITY.md` for more information about the security features and best practices.

---

**Important**: Change the keys before committing and pushing your app to production!
