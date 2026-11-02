"""Verschlüsselte Text-Drops.

Der Browser verschlüsselt den Text; der Server sieht nur ciphertext und iv.
Der Schlüssel steht ausschliesslich im #-Teil des Links und kommt nie hierher.
"""

from flask import (
    Blueprint,
    abort,
    jsonify,
    render_template,
)

from drop.database import db
from drop.models import Link

bp = Blueprint("drops", __name__)


def get_text_drop(slug):
    drop = db.session.execute(
        db.select(Link).filter_by(slug=slug, kind="text")
    ).scalar_one_or_none()
    if drop is None:
        abort(404)
    return drop


@bp.get("/d/<slug>")
def view(slug):
    drop = get_text_drop(slug)
    return render_template("drop_view.html", slug=drop.slug)


@bp.get("/d/<slug>/data")
def data(slug):
    drop = get_text_drop(slug)
    drop.clicks += 1
    db.session.commit()
    return jsonify(ciphertext=drop.ciphertext, iv=drop.iv)
