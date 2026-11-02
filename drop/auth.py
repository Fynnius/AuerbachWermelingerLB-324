import functools
import hmac

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

bp = Blueprint("auth", __name__)


def password_matches(given):
    expected = current_app.config.get("PASSWORD")
    if not expected or given is None:
        return False
    return hmac.compare_digest(given.encode(), expected.encode())


def login_required(view):
    """Leitet auf die Login-Seite um, falls niemand eingeloggt ist."""

    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if password_matches(request.form.get("password")):
            session.clear()
            session["logged_in"] = True
            return redirect(url_for("main.index"))
        flash("Falsches Passwort.", "error")
    return render_template("login.html")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
