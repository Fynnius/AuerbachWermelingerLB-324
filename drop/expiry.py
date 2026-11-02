"""Ablaufzeit für Kurzlinks und Drops (gemeinsame Logik)."""

from datetime import timedelta

from flask import abort

from drop.models import utcnow

# Erlaubte Ablaufzeiten in Sekunden mit Beschriftung fürs Formular.
# "Nie" ist keine Option hier: Feld fehlt, leer oder null.
EXPIRY_CHOICES = {
    3600: "1 Stunde",
    86400: "1 Tag",
    604800: "7 Tage",
}


def parse_expires_in(value):
    """Liest `expires_in` aus Formular oder JSON.

    Gibt die Sekunden zurück oder None für "nie".
    Wirft ValueError bei allem, was keine erlaubte Ablaufzeit ist.
    """
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("invalid expires_in")
    if isinstance(value, str):
        if not value.isdigit():
            raise ValueError("invalid expires_in")
        value = int(value)
    if not isinstance(value, int) or value not in EXPIRY_CHOICES:
        raise ValueError("invalid expires_in")
    return value


def expires_at_from(seconds, now=None):
    """Zeitpunkt des Ablaufs (UTC, ohne Zeitzone) oder None für "nie"."""
    if seconds is None:
        return None
    return (now or utcnow()) + timedelta(seconds=seconds)


def abort_if_expired(link):
    """Antwortet mit 410 Gone, wenn der Link/Drop abgelaufen ist."""
    if link.is_expired():
        abort(410)
