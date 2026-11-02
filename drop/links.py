"""Kurzlinks: erstellen (mit Login) und weiterleiten (öffentlich)."""

from flask import Blueprint, abort, redirect

from drop.database import db
from drop.models import Link

bp = Blueprint("links", __name__)


def get_url_link_or_404(slug):
    link = db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one_or_none()
    if link is None or link.kind != "url":
        abort(404)
    return link


@bp.get("/<slug>")
def follow(slug):
    link = get_url_link_or_404(slug)
    link.clicks += 1
    db.session.commit()
    return redirect(link.target, code=302)
