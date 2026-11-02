"""Klickstatistik: Besuche erfassen, ohne IP-Adressen zu speichern."""

from flask import request

from drop.database import db
from drop.models import Visit

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
