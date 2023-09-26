from flask import Flask, render_template, redirect, session, flash, url_for
from flask_login import login_required, current_user
import request
from flask_debugtoolbar import DebugToolbarExtension
from models import db, connect_db, User
from forms import RegisterForm, LoginForm
import os
app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY
app.config['DEBUG'] = True

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison')
#app.config["SQLALCHEMY_DATABASE_URI"] = "postgres:///new_music"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True


# db.create_all()


toolbar = DebugToolbarExtension(app)
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)

with app.app_context():
    db.drop_all()
    db.create_all()

@app.route("/")
def homepage():
    """Show homepage with links to site areas."""
    return redirect("/register")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user: produce form & handle form submission."""
    if "user_id" in session:
        return redirect(f"/users/profile/{session['user_id']}")
    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        pwd = form.password.data
        email = form.email.data
        existing_user_count = User.query.filter_by(username=username).count()
        if existing_user_count > 0:
            flash("User already exists")
            return redirect('/login')

        user = User.register(username, email, pwd)
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        # on successful login, redirect to profile page
        return redirect(f"/users/profile/{user.id}")
    
    return render_template("/users/register.html", form=form)

@app.route("/users/profile/<int:id>", methods=["GET", "POST"])
def profile(id):
    """Display and update user's profile."""
    # Ensure the user is logged in and the id in the URL matches the logged-in user id
    if "user_id" not in session or id != session['user_id']:
        flash("You must be logged in to view!")
        return redirect("/login")
    
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        preference = request.form.get('preference')
        # Save this preference to the database
        user.preference = preference  
        db.session.commit()
        flash("Preference Updated Successfully!")
        return redirect(url_for('profile', id=id))
    
    return render_template("users/profile.html", user=user)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Produce login form or handle login."""

    form = LoginForm()
    if not form.validate_on_submit():
        return render_template("users/login.html", form=form)
    # otherwise
    name = form.username.data
    pwd = form.password.data
    # authenticate will return a user or False
    user = User.authenticate(name, pwd)

    if not user:
        return render_template("users/login.html", form=form)
    # otherwise

    form.username.errors = ["Bad name/password"]
    session["user_id"] = user.id  
    return redirect(f"/users/profile/{user.id}")


@app.route("/logout")
def logout():
    """Logs user out and redirects to homepage."""
    session.pop("user_id")
    return redirect("/login")

