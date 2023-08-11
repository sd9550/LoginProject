from flask import Flask, render_template, request, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
import datetime as dt
import requests
import os

API_KEY = os.environ["API_KEY"]
API_ENDPOINT = "https://api.mobygames.com/v1/games"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
login_manager = LoginManager()
db = SQLAlchemy()
db.init_app(app)
login_manager.init_app(app)
year = dt.datetime.now().year

# 2 database tables
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(30))
    img = relationship("Images", back_populates="author")


class Images(db.Model):
    __tablename__ = "images"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    img_url = db.Column(db.String(100))
    author = relationship("User", back_populates="img")


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# home page with login form
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("inputEmail")
        plain_password = request.form.get("inputPassword")
        user_data = db.session.execute(db.select(User).where(User.email == email)).scalar()

        if user_data is None:
            error = "Email does not exist."
            return render_template("index.html", error=error, current_user=current_user)

        if check_password_hash(user_data.password, plain_password):
            login_user(user_data)
            return redirect(url_for("profile"))
        else:
            error = "Invalid password"
            return render_template("index.html", error=error, current_user=current_user)

    return render_template("index.html", year=year, current_user=current_user)


# register page with creation form
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("inputEmail")
        plain_password = request.form.get("inputPassword")
        hashed_password = generate_password_hash(password=plain_password, method='pbkdf2', salt_length=8)
        new_user = User(
            email=email,
            password=hashed_password
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            return redirect(url_for('profile'))
        except IntegrityError:
            error = "Email already exists"
            return render_template("register.html", error=error, year=year)

    return render_template("register.html", year=year, current_user=current_user)


# page to search and display game covers
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    query = db.session.execute(db.select(Images).where(Images.user_id == current_user.id))
    library = query.scalars().all()

    if request.method == "POST":
        title = request.form.get("gameTitle")
        params = {
            "api_key": API_KEY,
            "title": title
        }
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
        game_data = response.json()["games"]
        results = len(game_data)

        return render_template("search.html", games=game_data, results=results)

    return render_template("profile.html", current_user=current_user, library=library)


@app.route("/search")
@login_required
def search():
    img_url = request.args.get("img")
    db.session.execute(db.select(Images))
    new_image = Images(
        user_id=current_user.id,
        img_url=img_url
    )
    db.session.add(new_image)
    db.session.commit()

    return redirect(url_for("profile"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
