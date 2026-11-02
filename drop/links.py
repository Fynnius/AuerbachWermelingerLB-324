"""Kurzlinks: erstellen (mit Login) und weiterleiten (öffentlich)."""

import io
import secrets
import string
from urllib.parse import urlparse

import qrcode
import qrcode.image.svg
from flask import Blueprint, Response, abort, flash, redirect, request, url_for

from drop.auth import login_required
from drop.database import db
from drop.models import Link

bp = Blueprint("links", __name__)

SLUG_ALPHABET = string.ascii_letters + string.digits
SLUG_LENGTH = 6


def is_valid_url(url):
    """Nur http(s)-URLs mit Host, damit z. B. `javascript:` nicht durchkommt."""
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def slug_exists(slug):
    return (
        db.session.execute(db.select(Link.id).filter_by(slug=slug)).first() is not None
    )


def new_slug():
    """Würfelt einen zufälligen Slug, bis er noch nicht vergeben ist."""
    while True:
        slug = "".join(secrets.choice(SLUG_ALPHABET) for _ in range(SLUG_LENGTH))
        if not slug_exists(slug):
            return slug


def get_url_link_or_404(slug):
    link = db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one_or_none()
    if link is None or link.kind != "url":
        abort(404)
    return link


@bp.post("/links")
@login_required
def create():
    url = request.form.get("url", "").strip()
    if not is_valid_url(url):
        flash("Bitte eine gültige http(s)-URL eingeben.", "error")
        return redirect(url_for("main.index"))

    link = Link(kind="url", target=url, slug=new_slug())
    db.session.add(link)
    db.session.commit()
    short_url = url_for("links.follow", slug=link.slug, _external=True)
    flash(f"Kurzlink erstellt: {short_url}", "success")
    return redirect(url_for("main.index"))


@bp.get("/<slug>")
def follow(slug):
    link = get_url_link_or_404(slug)
    link.clicks += 1
    db.session.commit()
    return redirect(link.target, code=302)


@bp.get("/<slug>/qr")
def qr(slug):
    """QR-Code des absoluten Kurzlinks als SVG (ohne Pillow)."""
    link = get_url_link_or_404(slug)
    short_url = url_for("links.follow", slug=link.slug, _external=True)
    image = qrcode.make(short_url, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = io.BytesIO()
    image.save(buffer)
    return Response(buffer.getvalue(), mimetype="image/svg+xml")
