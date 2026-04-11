from __future__ import annotations

import os
from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from app.db import get_connection

auth_bp = Blueprint("auth", __name__)
login_manager = LoginManager()


# ---------------------------------------------------------------------------
# User model
# ---------------------------------------------------------------------------

class User(UserMixin):
    def __init__(self, id: int, email: str, name: str | None):
        self.id = id
        self.email = email
        self.name = name or email.split("@")[0]

    @staticmethod
    def get(user_id: int) -> "User | None":
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, email, name FROM users WHERE id = %s", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return User(row["id"], row["email"], row["name"])

    @staticmethod
    def get_by_email(email: str) -> "User | None":
        with get_connection() as conn:
            row = conn.execute(
                "SELECT id, email, name FROM users WHERE email = %s", (email,)
            ).fetchone()
        if row is None:
            return None
        return User(row["id"], row["email"], row["name"])


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return User.get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Email / password routes
# ---------------------------------------------------------------------------

@auth_bp.route("/signup", methods=["GET"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main.create_form"))
    return render_template("signup.html", error=None)


@auth_bp.route("/signup", methods=["POST"])
def signup_post():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")

    if not email or not password:
        return render_template("signup.html", error="Email and password are required."), 400
    if len(password) < 8:
        return render_template("signup.html", error="Password must be at least 8 characters."), 400
    if password != confirm:
        return render_template("signup.html", error="Passwords do not match."), 400

    with get_connection() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
        if existing:
            return render_template("signup.html", error="An account with that email already exists."), 400

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (%s, %s, %s, %s)",
            (email, name or None, generate_password_hash(password), now),
        )
        conn.commit()
        row = conn.execute("SELECT id, email, name FROM users WHERE email = %s", (email,)).fetchone()

    user = User(row["id"], row["email"], row["name"])
    login_user(user)
    return redirect(url_for("main.create_form"))


@auth_bp.route("/login", methods=["GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.create_form"))
    return render_template("login.html", error=None)


@auth_bp.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = %s", (email,)
        ).fetchone()

    if row is None or not row["password_hash"] or not check_password_hash(row["password_hash"], password):
        return render_template("login.html", error="Invalid email or password."), 401

    login_user(User(row["id"], row["email"], row["name"]))
    next_url = request.args.get("next")
    return redirect(next_url or url_for("main.create_form"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------

def init_google_oauth(app):
    """Register Google OAuth only if credentials are present in environment."""
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        return  # Google login silently disabled until credentials are set

    from authlib.integrations.flask_client import OAuth
    oauth = OAuth(app)
    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    app.extensions["oauth"] = oauth


@auth_bp.route("/auth/google/login")
def google_login():
    oauth = _get_oauth()
    if oauth is None:
        return render_template("login.html", error="Google login is not configured yet."), 503
    redirect_uri = url_for("auth.google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/google/callback")
def google_callback():
    oauth = _get_oauth()
    if oauth is None:
        return redirect(url_for("auth.login"))

    token = oauth.google.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.google.userinfo()

    google_id = userinfo["sub"]
    email = userinfo.get("email", "").lower()
    name = userinfo.get("name")
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        row = conn.execute("SELECT id, email, name FROM users WHERE google_id = %s", (google_id,)).fetchone()
        if row is None:
            # Check if email already exists (user registered with password before)
            row = conn.execute("SELECT id, email, name FROM users WHERE email = %s", (email,)).fetchone()
            if row:
                # Link Google ID to existing account
                conn.execute("UPDATE users SET google_id = %s WHERE id = %s", (google_id, row["id"]))
                conn.commit()
            else:
                # Brand new user via Google
                conn.execute(
                    "INSERT INTO users (email, name, google_id, created_at) VALUES (%s, %s, %s, %s)",
                    (email, name, google_id, now),
                )
                conn.commit()
                row = conn.execute("SELECT id, email, name FROM users WHERE email = %s", (email,)).fetchone()

    login_user(User(row["id"], row["email"], row["name"]))
    return redirect(url_for("main.create_form"))


def _get_oauth():
    from flask import current_app
    return current_app.extensions.get("oauth")
