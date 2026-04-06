"""Email body generators for Cocktail Chronicles.

Each ``generate_*`` function returns a plain-text string that is consumed
by ``services/email_service.py`` and passed to Flask-Mail for dispatch.

Functions
---------
generate_ban_appeal_email        -- ban notification with an appeal link
generate_ban_lifted_email        -- ban-lifted confirmation
generate_email_verification_email -- initial email-verification link
generate_email_resend_verification_email -- re-send of the verification link

``first()`` is a legacy utility included from an early version of the
project.  It is not called by any route or service code and is kept only
for backwards compatibility with any external script that may reference it.
"""


def first(iterable, default=None, condition=lambda x: True):
    """Return the first item in *iterable* that satisfies *condition*.

    .. note::
        This helper is not used by any route or service in the current
        application.  It is retained for backwards compatibility only.
    """

    try:
        return next(x for x in iterable if condition(x))
    except StopIteration:
        if default is not None and condition(default):
            return default
        else:
            raise


def generate_ban_appeal_email(username, appeal_link):
    """Generate ban notification email with appeal link."""
    email_body = f"""
Dear {username},

We regret to inform you that your account has been suspended due to a violation of our Community Guidelines. 
This action was taken to maintain a respectful and safe environment for all our users.

However, we understand that circumstances can be complex, and we want to ensure that our decisions are fair and just. 
If you believe this suspension was made in error or if you have additional context you would like us to consider, 
you have the right to submit a formal appeal.

To submit your appeal, please visit the following link:
{appeal_link}

In your appeal, we ask that you:
1. Clearly explain why you believe the suspension was made in error
2. Provide any relevant context or evidence that supports your case
3. Describe how you will ensure compliance with our Community Guidelines going forward
4. Remain respectful and professional in your communication

Our admin team will carefully review your appeal and respond within 5-7 business days. Please note that submitting 
an appeal does not guarantee that your suspension will be lifted, but we are committed to reviewing every appeal fairly 
and thoroughly.

If you have any questions about this process or need further assistance, please do not hesitate to reach out to our 
support team.

Thank you for understanding, and we hope to see you back in our community soon.

Best regards,
The Cocktail Chronicles Admin Team
    """.strip()
    return email_body

def generate_ban_lifted_email(username):
    """Generate email notifying user that their ban has been lifted."""
    email_body = f"""
Dear {username},

Good news! After careful review of your appeal, we are pleased to inform you that the suspension on your account 
has been lifted.

Your account is now active, and you are welcome to log in and use all features of Cocktail Chronicles as before. 
We appreciate your patience throughout the appeals process and your commitment to following our Community Guidelines.

If you have any questions or concerns, or if you experience any issues accessing your account, please don't hesitate 
to contact our support team.

We look forward to having you back in our community!

Best regards,
The Cocktail Chronicles Admin Team
    """.strip()
    return email_body

def generate_email_verification_email(username, verification_link):
    """Generate email verification email with verification link."""
    email_body = f"""
Welcome to 'Cocktail Chronicles', your ultimate guide for making delicious cocktails!

Hello {username},

Thank you for signing up for Cocktail Chronicles! We're thrilled to have you join our community of cocktail enthusiasts.

To complete your registration and unlock all the features of our app, we need to verify that you own this email address. 
It's just a formality, but please verify your email address by following this link:

{verification_link}

Once you've verified your email, you'll be able to:
- Create and save your favorite cocktail recipes
- Share your original cocktail creations with the community
- Access personalized cocktail recommendations
- Connect with other mixology enthusiasts

This verification link will expire in 24 hours for security purposes. If the link has expired, you can request a new one 
by logging into your account.

If you did not create this account, please ignore this email.

Let the mixology begin!

Best regards,
The Cocktail Chronicles Team
    """.strip()
    return email_body

def generate_email_verification_html(username, verification_link):
    """Return an HTML email body for email verification (both initial and resend).

    Using an HTML anchor tag prevents plain-text quoted-printable line-wrapping
    from breaking the verification URL when email clients encode long lines.
    """
    escaped_link = verification_link.replace('&', '&amp;').replace('"', '&quot;')
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;color:#222;max-width:600px;margin:0 auto;padding:20px">
  <h2 style="color:#c0392b">Cocktail Chronicles</h2>
  <p>Hello <strong>{username}</strong>,</p>
  <p>Thank you for signing up! Please verify your email address by clicking the button below:</p>
  <p style="text-align:center;margin:30px 0">
    <a href="{escaped_link}"
       style="background:#c0392b;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:16px">
      Verify My Email
    </a>
  </p>
  <p>If the button does not work, copy and paste this link into your browser:</p>
  <p style="word-break:break-all;font-size:13px;color:#555">{escaped_link}</p>
  <p style="font-size:12px;color:#888">This link expires in 24 hours. If you did not create an account, you can safely ignore this email.</p>
  <p>The Cocktail Chronicles Team</p>
</body>
</html>"""


def generate_email_resend_verification_email(username, verification_link):
    """Generate email for resending verification link."""
    email_body = f"""
Email Verification Link - Cocktail Chronicles

Hello {username},

We've generated a new email verification link for your Cocktail Chronicles account. 
Please verify your email address by following this link:

{verification_link}

This link will expire in 24 hours.

If you did not request this email, please ignore it.

Best regards,
The Cocktail Chronicles Team
    """.strip()
    return email_body


def generate_appeal_rejection_email(username):
    """Generate email notifying a user that their ban appeal has been rejected."""
    email_body = f"""
Dear {username},

Thank you for submitting a ban appeal. After careful review, we regret to inform you
that your appeal has been rejected and the account suspension will remain in effect.

If you believe this decision was made in error, or if your circumstances change in the
future, you are welcome to submit a new appeal at a later time.

We appreciate your patience and understanding.

Best regards,
The Cocktail Chronicles Admin Team
    """.strip()
    return email_body

