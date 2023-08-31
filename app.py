import os

from flask import Flask, render_template, request, flash, redirect, session, g, abort
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import RegisterForm, LoginForm, SearchCocktailsForm, AddNewCocktailForm
from models import db, connect_db, User, Ingredients, Cocktail, Cocktails_Ingredients, Cocktails_Users, UserFavoriteIngredients

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///name_your_poison'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)

##############################################################################
# User signup/login/logout


@app.route("/")
def root():
    """Homepage: redirect to /cocktails."""
    print("****************session************")
    print(session["username"])
    print(session["user_id"])

    print("****************session************")


    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    

    if 'user_id' in session:
        return redirect(f"/users/{session['user_id']}")

    form = RegisterForm()
    username = form.username.data
    password = form.password.data

    existing_user_count = User.query.filter_by(username=username).count()
    if existing_user_count > 0:
        flash("User already exists")
        return redirect('/login')

    if form.validate_on_submit():
        user = User.register(username, password)
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        
        print(user.id)
        session['user_id'] = user.id
        print('id', session['user_id'])

        return redirect(f"/users/{user.id}")

    else:
        return render_template("users/register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(f"/users/{session['user_id']}")

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)  
        if user:
            return redirect(f"/users/{user.id}")
        else:
            form.username.errors = ["Invalid username/password."]
            return render_template("users/login.html", form=form)

    return render_template("users/login.html", form=form)

@app.route("/logout")
def logout():
    if "user_id" in session:
        session.pop("username")
    return redirect("/login")

@app.route("/users/<int:user_id>", methods=["GET", "POST"])
def profile(user_id):
    if session.get["user_id"] not in session:
        flash("You must be logged in to view!")
        return redirect("/")
    form = AddCocktailToAccountForm()
    cocktails = Cocktail.query.filter_by(user_id=session['user_id']).all()
  
    if form.validate_on_submit():
        
        
        name = form.name.data
        new_cocktail = Cocktail(name=name, user_id=session['user_id'])
        db.session.add(new_cocktail)
        db.session.commit()
        cocktails.append(new_cocktail)

    return render_template("users/profile.html", cocktails=cocktails, form=form)

@app.route("/cocktails/<int:cocktail_id>")
def show_cocktail(cocktail_id):
    """Show detail on specific playlist."""

    # ADD THE NECESSARY CODE HERE FOR THIS ROUTE TO WORK
    cocktail = Cocktail.query.get_or_404(cocktail_id)
    ingredients = Cocktails_Ingredients.query.filter_by(cocktail_id=cocktail_id)

    for b in ingredients:
        print('testing',b)


    return render_template("cocktail/new_cocktail.html", cocktail=cocktail)

@app.route("/cocktails/add", methods=["GET", "POST"])
def add_cocktail():
    form = SearchCocktailsForm()

    if form.validate_on_submit():
        cocktailname = form.cocktailname.data
        instructions = form.instructions.data
        new_cocktail = Cocktail(cocktailname=cocktailname, instructions=instructions)
        db.session.add(new_cocktail)
        db.session.commit()
        return redirect("/profile")

    return render_template("cocktail/new_cocktail.html", form=form)

@app.route("/ingredients")
def show_all_ingredients():
    """Show list of ingredients in cocktail."""

    ingredients = Ingredients.query.all()
    return render_template("ingredient/ingredients.html", ingredients=ingredients)


@app.route("/ingredients/<int:id>")
def show_ingredient(id):
   
    ingredient = Ingredients.query.get_or_404(id)
    cocktails = ingredient.is_alcohol


    return render_template("ingredient/ingredient.html", ingredient=ingredient, cocktails=cocktails)


@app.route("/ingredients/add", methods=["GET", "POST"])
def add_ingredient():
    
    form = SongForm()

    if form.validate_on_submit():
        title = request.form['title']
        artist = request.form['artist']
        new_song = Song(title=title, artist=artist)
        db.session.add(new_song)
        db.session.commit()
        return redirect("/songs")

    return render_template("song/new_song.html", form=form)



@app.route("/playlists/<int:playlist_id>/add-song", methods=["GET", "POST"])
def add_song_to_playlist(playlist_id):
    """Add a playlist and redirect to list."""
    
    playlist = Playlist.query.get_or_404(playlist_id)
    form = NewSongForPlaylistForm()

    curr_on_playlist = [s.id for s in playlist.songs]
    form.song.choices = (db.session.query(Song.id, Song.title).filter(Song.id.notin_(curr_on_playlist)).all())

    if form.validate_on_submit():

        playlist_song = PlaylistSong(song_id=form.song.data, playlist_id=playlist_id)
        db.session.add(playlist_song)
        db.session.commit()

        return redirect(f"/playlists/{playlist_id}")

    return render_template("song/add_song_to_playlist.html", playlist=playlist, form=form)