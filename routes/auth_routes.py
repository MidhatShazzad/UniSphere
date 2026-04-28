from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from models.db import get_db

auth_bp = Blueprint("auth", __name__)


def password_matches(stored_password, candidate_password):
    if stored_password == candidate_password:
        return True

    try:
        return check_password_hash(stored_password, candidate_password)
    except ValueError:
        return False


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

        if not user or not password_matches(user["password_hash"], password):
            error = "Invalid username or password."
        elif not user["is_active"]:
            error = "This account is currently suspended."
        else:
            session.clear()
            session["user_id"] = user["id"]
            session["user"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard_router"))

    return render_template("login.html", error=error)