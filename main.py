from sqlite3.dbapi2 import SQLITE_ABORT
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from email_validator import EmailNotValidError, validate_email

from flask import Flask, render_template, request, flash, redirect, url_for, session
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("Set SECRET_KEY to a random secret before starting the app.")
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE") == "1"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///project.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
ph = PasswordHasher()
dummy_hash = ph.hash(os.urandom(32))
CSRFProtect(app)
login_manager = LoginManager(app)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(128),
        nullable=False
    )


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except ValueError:
        return None


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sUsername = request.form.get('username', '').strip()
        sPassword = request.form.get('password', '')
        verified = False
        if sUsername and len(sUsername) <= 80 and sPassword and len(sPassword) <= 1024:
            user = db.session.execute(db.select(User).filter_by(username=sUsername)).scalar_one_or_none()
            try:
                verified = ph.verify(user.password if user else dummy_hash, sPassword) and user is not None
            except VerifyMismatchError:
                pass
            except (InvalidHashError, VerificationError):
                app.logger.exception("Invalid stored password hash")

        if verified:
            session.clear()
            login_user(user)
            flash("Login successful")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        sUsername = request.form.get('username', '').strip()
        sEmail = request.form.get('email', '').strip()
        sPassword = request.form.get('password', '')
        if (not sUsername or len(sUsername) > 80 or not sEmail or len(sEmail) > 120
                or not sPassword or len(sPassword) > 1024):
            flash("Enter a username (up to 80 characters), email (up to 120), and password (up to 1024).")
            return redirect(url_for('signup'))
        if sPassword != request.form.get('confirm-password'):
            flash("Passwords do not match.")
            return redirect(url_for('signup'))
        try:
            sEmail = validate_email(sEmail, check_deliverability=False).normalized.lower()
        except EmailNotValidError:
            flash("Enter a valid email address.")
            return redirect(url_for('signup'))
        if len(sEmail) > 120:
            flash("Email must be at most 120 characters.")
            return redirect(url_for('signup'))

        existing = db.session.execute(db.select(User.id).where(
            (User.username == sUsername) | (db.func.lower(User.email) == sEmail)
        )).first()
        if existing:
            flash("Username or email already registered.")
            return redirect(url_for('signup'))

        user = User(
            username=sUsername,
            email=sEmail,
            password=ph.hash(sPassword)
        )
        try:
            db.session.add(user)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            flash("Username or email already registered.")
            return redirect(url_for('signup'))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.exception("Account creation failed")
            flash("Account creation failed. Please try again.")
            return redirect(url_for('signup'))

        flash("Account created successfully!")
        return redirect(url_for('index'))

    return render_template("signup.html")

@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
