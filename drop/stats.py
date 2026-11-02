"""Klickstatistik: Besuche erfassen, ohne IP-Adressen zu speichern."""

from collections import defaultdict

from flask import Blueprint, jsonify, render_template, request

from drop.auth import login_required
from drop.database import db
from drop.models import Link, Visit

bp = Blueprint("stats", __name__)

BOT_MARKERS = ("bot", "crawler", "spider")
MOBILE_MARKERS = ("mobile", "android", "iphone")
DESKTOP_MARKERS = ("firefox", "chrome", "safari", "edg", "opera", "opr/")


def device_from_user_agent(ua):
    """Ordnet einen User-Agent grob einem Gerätetyp zu.

    Reihenfolge wichtig: Bots geben sich oft als Mobile-Browser aus, und
    Mobile-Browser enthalten fast immer auch "Safari" oder "Chrome".
    """
    ua = (ua or "").lower()
    if any(marker in ua for marker in BOT_MARKERS):
        return "bot"
    if any(marker in ua for marker in MOBILE_MARKERS):
        return "mobile"
    if any(marker in ua for marker in DESKTOP_MARKERS):
        return "desktop"
    return "other"


def record_visit(link):
    """Legt einen Besuch für `link` an. Committet nicht; das macht der Aufrufer."""
    device = device_from_user_agent(request.headers.get("User-Agent", ""))
    db.session.add(Visit(link_id=link.id, device=device))


def iso_utc(moment):
    """ISO 8601 mit "Z", damit der Browser die Zeit als UTC versteht."""
    return moment.isoformat(timespec="seconds") + "Z"


@bp.get("/dashboard")
@login_required
def dashboard():
    """Seite mit Klicks pro Link; die Daten lädt dashboard.js per fetch."""
    return render_template("dashboard.html")


@bp.get("/dashboard/data")
@login_required
def data():
    """Alle Links mit Klicks und Besuchen, neueste zuerst.

    Für Drops gehen weder ciphertext noch iv hinaus, nur Metadaten.
    """
    links = (
        db.session.execute(
            db.select(Link).order_by(Link.created_at.desc(), Link.id.desc())
        )
        .scalars()
        .all()
    )
    visits_by_link = defaultdict(list)
    for visit in db.session.execute(db.select(Visit).order_by(Visit.at)).scalars():
        visits_by_link[visit.link_id].append(
            {"at": iso_utc(visit.at), "device": visit.device}
        )
    return jsonify(
        [
            {
                "slug": link.slug,
                "kind": link.kind,
                "target": link.target if link.kind == "url" else None,
                "clicks": link.clicks,
                "created_at": iso_utc(link.created_at),
                "visits": visits_by_link[link.id],
            }
            for link in links
        ]
    )
