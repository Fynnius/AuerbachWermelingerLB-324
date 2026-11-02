from datetime import datetime, timezone

from drop.database import db


def utcnow():
    """Aktuelle Zeit in UTC, ohne Zeitzone (SQLite speichert keine Zeitzonen)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Link(db.Model):
    """Ein Kurzlink (kind="url") oder ein verschlüsselter Text-Drop (kind="text").

    Bei Drops speichert der Server nur ciphertext und iv, nie Klartext oder Schlüssel.
    """

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(16), unique=True, nullable=False, index=True)
    kind = db.Column(db.String(8), nullable=False)
    target = db.Column(db.Text)
    ciphertext = db.Column(db.Text)
    iv = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime)
    burn_after_read = db.Column(db.Boolean, nullable=False, default=False)
    clicks = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, **kwargs):
        kwargs.setdefault("burn_after_read", False)
        kwargs.setdefault("clicks", 0)
        kwargs.setdefault("created_at", utcnow())
        super().__init__(**kwargs)

    def is_expired(self, now=None):
        return self.expires_at is not None and (now or utcnow()) >= self.expires_at


class Visit(db.Model):
    """Ein Aufruf eines Links oder Drops.

    Bewusst ohne IP-Adresse und ohne vollständigen User-Agent: gespeichert wird
    nur der grobe Gerätetyp ("mobile", "desktop", "bot" oder "other").
    """

    id = db.Column(db.Integer, primary_key=True)
    link_id = db.Column(
        db.Integer, db.ForeignKey("link.id"), nullable=False, index=True
    )
    at = db.Column(db.DateTime, nullable=False, default=utcnow)
    device = db.Column(db.String(8), nullable=False)
