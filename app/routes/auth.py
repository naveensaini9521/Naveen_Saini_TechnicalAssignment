"""
Auth routes: login, logout.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.services.auth_service import authenticate, AuthError

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        try:
            user = authenticate(email, password)
        except AuthError as e:
            flash(str(e), "error")
            return render_template("auth/login.html"), 401

        login_user(user)
        next_url = request.args.get("next") or url_for("dashboard.index")
        return redirect(next_url)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))