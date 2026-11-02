"""Verschlüsselte Text-Drops.

Der Browser verschlüsselt den Text; der Server sieht nur ciphertext und iv.
Der Schlüssel steht ausschliesslich im #-Teil des Links und kommt nie hierher.
"""

import base64
import binascii
import functools
import secrets
import string

from flask import (
    Blueprint,
    abort,
    jsonify,
    render_template,
    request,
    session,
    url_for,
)

from drop.auth import login_required
from drop.database import db
from drop.expiry import abort_if_expired, expires_at_from, parse_expires_in
from drop.models import Link
from drop.stats import record_visit

bp = Blueprint("drops", __name__)

SLUG_ALPHABET = string.ascii_letters + string.digits
SLUG_LENGTH = 6
IV_BYTES = 12
MAX_CIPHERTEXT_BYTES = 64 * 1024
ALLOWED_FIELDS = {"ciphertext", "iv", "expires_in"}


def login_required_json(view):
    """Wie login_required, aber mit 401-JSON statt Redirect (Aufruf per fetch)."""

    @functools.wraps(view)
    def wrapped(**kwargs):
        if not session.get("logged_in"):
            return jsonify(error="login required"), 401
        return view(**kwargs)

    return wrapped


def bad_request(message):
    return jsonify(error=message), 400


def decode_base64(value):
    """Dekodiert Standard-Base64 streng; gibt None zurück, falls ungültig."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        return None


def new_slug():
    while True:
        slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(SLUG_LENGTH))
        if db.session.execute(db.select(Link.id).filter_by(slug=slug)).first() is None:
            return slug


def get_text_drop(slug):
    drop = db.session.execute(
        db.select(Link).filter_by(slug=slug, kind="text")
    ).scalar_one_or_none()
    if drop is None:
        abort(404)
    return drop


@bp.errorhandler(410)
def gone(error):
    """Abgelaufene Drops: JSON für fetch, sonst eine verständliche Seite."""
    if request.endpoint == "drops.data":
        return jsonify(error="expired"), 410
    return render_template("drop_view.html", expired=True), 410


@bp.get("/drops/new")
@login_required
def new():
    return render_template("drop_new.html")


@bp.post("/drops")
@login_required_json
def create():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return bad_request("JSON object expected")
    unknown = set(data) - ALLOWED_FIELDS
    if unknown:
        return bad_request("unknown fields: " + ", ".join(sorted(unknown)))

    # Grobe Längenprüfung vor dem Dekodieren (Base64 ist ca. 4/3 so lang).
    ciphertext = data.get("ciphertext")
    if (
        isinstance(ciphertext, str)
        and len(ciphertext) > MAX_CIPHERTEXT_BYTES * 4 // 3 + 4
    ):
        return bad_request("ciphertext too large")
    raw_ciphertext = decode_base64(ciphertext)
    if raw_ciphertext is None:
        return bad_request("ciphertext must be base64")
    if len(raw_ciphertext) > MAX_CIPHERTEXT_BYTES:
        return bad_request("ciphertext too large")

    raw_iv = decode_base64(data.get("iv"))
    if raw_iv is None:
        return bad_request("iv must be base64")
    if len(raw_iv) != IV_BYTES:
        return bad_request(f"iv must be {IV_BYTES} bytes")

    try:
        expires_in = parse_expires_in(data.get("expires_in"))
    except ValueError:
        return bad_request("expires_in must be 3600, 86400, 604800 or null")

    drop = Link(
        slug=new_slug(),
        kind="text",
        ciphertext=ciphertext,
        iv=data["iv"],
        expires_at=expires_at_from(expires_in),
    )
    db.session.add(drop)
    db.session.commit()
    return (
        jsonify(
            slug=drop.slug, url=url_for("drops.view", slug=drop.slug, _external=True)
        ),
        201,
    )


@bp.get("/d/<slug>")
def view(slug):
    drop = get_text_drop(slug)
    abort_if_expired(drop)
    return render_template("drop_view.html", slug=drop.slug)


@bp.get("/d/<slug>/data")
def data(slug):
    drop = get_text_drop(slug)
    abort_if_expired(drop)
    record_visit(drop)
    drop.clicks += 1
    db.session.commit()
    return jsonify(ciphertext=drop.ciphertext, iv=drop.iv)
