# Security Quick Reference

## Critical Files

| File | Purpose | Commitment |
|------|---------|-----------|
| `.env` | Stores secret keys | ✗ NEVER (in .gitignore) |
| `SECURITY.md` | Security documentation | ✓ YES |
| `ENV_SETUP.md` | Environment setup guide | ✓ YES |
| `SECURITY_ENHANCEMENTS.md` | Feature summary | ✓ YES |
| `GITHUB_DEPLOYMENT.md` | Deployment guide | ✓ YES |
| `CHANGES.md` | Complete change log | ✓ YES |

---

## Key Values in `.env`

```env
SECRET_KEY=<32+ chars, random>              # Flask session secret
ADMIN_PASSWORD_KEY=<32+ chars, random>      # Master admin key
DATABASE_URL=<database connection>          # Database config
```

---

## Important Routes

| Route | Access | Purpose |
|-------|--------|---------|
| `/` | Logged in | Homepage |
| `/register` | Public | Register new account |
| `/login` | Public | Log in |
| `/admin/unlock` | Logged in | Enter admin password key |
| `/admin/panel` | Admin only | Admin dashboard |

---

## Admin Unlock Process

1. Register/login to app
2. Navigate to `/admin/unlock`
3. Enter `ADMIN_PASSWORD_KEY` from `.env`
4. Account promoted to admin
5. Access `/admin/panel` to manage users

---

## Security Layers

1. **Authentication** - Login required for most features
2. **Authorization** - Admin role required for admin features
3. **CSRF Protection** - All forms protected with tokens
4. **Session Security** - HTTPOnly, SameSite cookies
5. **Security Headers** - Prevent common web attacks
6. **Password Hashing** - Bcrypt with salt
7. **Input Validation** - Whitelist file types, sanitize input

---

## Before GitHub Push

```bash
# Step 1: Update .env with your keys
nano .env

# Step 2: Test locally
python -m flask run

# Step 3: Verify .env not in staging
git status

# Step 4: Commit and push
git add .
git commit -m "Add security features"
git push origin main
```

---

## What Others See on GitHub

✓ Complete app code with security features
✓ Admin panel exists (but locked)
✓ Documentation about security
✗ Your secret keys (protected by .env in .gitignore)
✗ Admin password key (local only)

---

## Giving Someone Admin Access

1. They register account
2. You securely share `ADMIN_PASSWORD_KEY` (NOT via email)
3. They visit `/admin/unlock`
4. They enter the key
5. They get admin access

---

## Production Setup

```env
FLASK_ENV=production
SECRET_KEY=<new-strong-random-key>
ADMIN_PASSWORD_KEY=<new-strong-random-key>
DATABASE_URL=postgresql://...
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
```

Then:
- Use HTTPS/SSL certificate
- Use PostgreSQL database
- Set DEBUG=False
- Use production WSGI server (Gunicorn, Waitress, etc.)

---

## Emergency: If .env Committed

```bash
git rm --cached .env
git commit -m "Stop tracking .env"
git push
```

Then:
- Change all keys immediately
- Check git history (keys were exposed)
- Rotate keys in production

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Admin unlock not working | Verify exact `.env` key, no spaces |
| `.env` module not found | `pip install python-dotenv` |
| Regular user can access admin | Check user.is_admin field, check decorator |
| 404 on admin panel | Must enter correct key first |
| `.env` in git staging | `git rm --cached .env` |

---

## Documentation Files Guide

| Document | Read When |
|----------|-----------|
| `SECURITY.md` | Want to understand all security features |
| `ENV_SETUP.md` | Setting up `.env` file |
| `SECURITY_ENHANCEMENTS.md` | Want summary of what was added |
| `GITHUB_DEPLOYMENT.md` | Ready to push to GitHub |
| `CHANGES.md` | Want complete list of all changes |

---

## Key Principles

1. **Never commit `.env`** - It's in .gitignore for a reason
2. **Strong keys** - At least 32 characters, random, no patterns
3. **Different keys** - Separate development and production keys
4. **Secure `.env`** - Restrict permissions, keep it safe
5. **Share key securely** - Never via email for sensitive accounts
6. **Monitor access** - Know who has admin access
7. **Update regularly** - Rotate keys periodically for production

---

## Security Deployment Phases

### Phase 1: Local Development ✓
- Create `.env` with your keys
- Test admin panel
- Test all app features
- Everything working?

### Phase 2: GitHub Push ✓
- Update `.env` with strong keys
- Verify `.env` not in staging
- Commit and push
- `.env` stays private ✓

### Phase 3: Production
- Create NEW `.env` on production server
- Use stronger keys than development
- Use HTTPS/SSL
- Use PostgreSQL
- Deploy app

---

## Admin Panel Statistics

The admin panel shows:
- **Total Users** - Number of registered accounts
- **Total Cocktails** - All cocktails in system
- **API Cocktails** - Original recipes from API
- **User Cocktails** - Custom recipes created by users

---

## User Management

As admin, you can:
- ✓ View all registered users
- ✓ See who has admin access
- ✓ Promote users to admin
- ✓ Demote users from admin
- ✗ Cannot demote yourself
- ✗ Cannot promote yourself

---

**Remember: Only you have the admin password key. Keep it safe!** 🔐

For detailed information, see the documentation files:
- `SECURITY.md`
- `ENV_SETUP.md`
- `GITHUB_DEPLOYMENT.md`
