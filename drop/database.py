"""Datenbank-Objekt in eigenem Modul, damit Modelle und App es importieren können,
ohne sich gegenseitig zu importieren (vgl. LA 1650)."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
