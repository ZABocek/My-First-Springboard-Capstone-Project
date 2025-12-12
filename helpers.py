def first(iterable, default = None, condition = lambda x: True):
    """
    Returns the first item in the `iterable` that
    satisfies the `condition`.

    If the condition is not given, returns the first item of
    the iterable.

    If the `default` argument is given and the iterable is empty,
    or if it has no items matching the condition, the `default` argument
    is returned if it matches the condition.

    The `default` argument being None is the same as it not being given.

    Raises `StopIteration` if no item satisfying the condition is found
    and default is not given or doesn't satisfy the condition.

    >>> first( (1,2,3), condition=lambda x: x % 2 == 0)
    2
    >>> first(range(3, 100))
    3
    >>> first( () )
    Traceback (most recent call last):
    ...
    StopIteration
    >>> first([], default=1)
    1
    >>> first([], default=1, condition=lambda x: x % 2 == 0)
    Traceback (most recent call last):
    ...
    StopIteration
    >>> first([1,3,5], default=1, condition=lambda x: x % 2 == 0)
    Traceback (most recent call last):
    ...
    StopIteration
    """

    try:
        return next(x for x in iterable if condition(x))
    except StopIteration:
        if default is not None and condition(default):
            return default
        else:
            raise

# Email utility functions
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
Welcome to 'Name Your Poison', your ultimate guide for making delicious cocktails!

Hello {username},

Thank you for signing up for Name Your Poison! We're thrilled to have you join our community of cocktail enthusiasts.

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
The Name Your Poison Team
    """.strip()
    return email_body

def generate_email_resend_verification_email(username, verification_link):
    """Generate email for resending verification link."""
    email_body = f"""
Email Verification Link - Name Your Poison

Hello {username},

We've generated a new email verification link for your Name Your Poison account. 
Please verify your email address by following this link:

{verification_link}

This link will expire in 24 hours.

If you did not request this email, please ignore it.

Best regards,
The Name Your Poison Team
    """.strip()
    return email_body

