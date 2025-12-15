# 🚀 Quick Start: Email Verification Setup

## What's New?

Your app now requires users to verify their email address during registration. This prevents fake emails and bot registrations.

---

## ⚡ 3 Steps to Get Started

### Step 1: Run the Migration (ONE TIME ONLY)
```bash
python migrate_email_verification.py
```

✅ This adds the email verification columns to your database

---

### Step 2: Test It Out
1. Start your app:
   ```bash
   python app.py
   ```

2. Go to: `http://localhost:5000/register`

3. Register with a real email address

4. Check your email for the verification link (or check `instance/mail/` folder)

5. Click the link to verify

6. Go to `/login` and log in

---

### Step 3: Deploy to Production
Set these environment variables:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

---

## 📍 New Routes

| Route | Purpose | User Sees |
|-------|---------|-----------|
| `POST /register` | Register & get verification email | Verification pending page |
| `GET /verify-email/<token>` | Click link in email to verify | Redirect to login |
| `GET /verification-pending/<id>` | Check verification status | Professional status page |
| `GET/POST /resend-verification/<id>` | Request new verification email | Updated status page |
| `POST /login` | Login (requires verified email) | Can now access app |

---

## 📧 What Users Experience

**Before (Old Flow):**
```
Register → Instant Login → Access App
```

**Now (New Flow):**
```
Register → Receive Email → Click Link → Verify → Login → Access App
```

---

## 🔧 If You Have Existing Users

### Option A: Users Must Verify (Recommended for New Systems)
- Existing users get blocked at login
- They can use "Resend Verification" to verify email
- More secure

### Option B: Grandfather Existing Users (User-Friendly)
```bash
python migrate_email_verification.py --grandfather-existing-users
```
- Existing users can log in immediately
- Only new registrations require verification

---

## ✉️ Email Configuration

### For Development (Easiest)
Emails are saved as `.txt` files in `instance/mail/` folder. No configuration needed!

### For Production (Gmail Example)
1. Enable 2-factor authentication in Gmail
2. Create an "App Password": https://myaccount.google.com/apppasswords
3. Add to `.env`:
   ```env
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=noreply@nameyourpoison.com
   ```

### Other Email Services
- **Outlook/Hotmail**: smtp.outlook.com (port 587)
- **Yahoo**: smtp.mail.yahoo.com (port 587)
- **SendGrid**: smtp.sendgrid.net (port 587)
- **Mailgun**: smtp.mailgun.org (port 587)
- **AWS SES**: email-smtp.[region].amazonaws.com (port 587)

---

## 🧪 Test the Email Verification

### Quick Test (Development)
```python
from app import app
from models import User

with app.app_context():
    user = User.query.filter_by(username='testuser').first()
    print(f"Email verified: {user.is_email_verified}")
    print(f"Verified at: {user.email_verified_at}")
```

### Verify Email Token
```python
from models import User

# Generate a token
token = user.generate_email_verification_token()
print(f"Token: {token}")

# Verify the token
email = User.verify_email_token(token)
print(f"Email from token: {email}")
```

---

## 🛠️ Troubleshooting

### Email Not Sending?
1. Check `.env` has MAIL_SERVER and MAIL_PORT
2. Verify SMTP credentials are correct
3. Check if firewall blocks SMTP port (587 or 25)
4. Look for errors in terminal output

### Verification Link Not Working?
1. Make sure you copied the full URL
2. Check if 24 hours have passed (links expire)
3. Use "Resend Verification Email" button
4. Check the email wasn't modified

### Can't Log In After Verifying?
1. Refresh the page after clicking verification link
2. Check browser cookies are enabled
3. Verify the database has `is_email_verified = TRUE` for your user
4. Check your email address matches exactly

---

## 📚 Full Documentation

For complete details, see:
- **EMAIL_VERIFICATION_SUMMARY.md** - Complete overview
- **EMAIL_VERIFICATION.md** - Detailed technical guide
- **models.py** - User model implementation
- **app.py** - Route implementations

---

## 🎯 What You Get

✅ **Spam Prevention** - Bots can't register with fake emails
✅ **User Validation** - Ensures email addresses are real
✅ **Professional** - Industry-standard security feature
✅ **Production Ready** - Fully tested and documented
✅ **User Friendly** - Clear messages and error handling
✅ **Secure** - Cryptographic tokens, can't be forged

---

## 💡 Pro Tips

1. **Customize Email Template**: Edit `generate_email_verification_email()` in `helpers.py`
2. **Change Token Expiration**: Edit `generate_email_verification_token()` in `models.py`
3. **Customize Verification Page**: Edit `templates/users/verification_pending.html`
4. **Monitor Verification Rate**: Check `is_email_verified` column in database

---

## 🚀 Ready?

**Run this now:**
```bash
python migrate_email_verification.py
python app.py
```

Then visit: http://localhost:5000/register

---

**Version**: 1.0
**Status**: ✅ Production Ready
**Support**: See EMAIL_VERIFICATION.md
