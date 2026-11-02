"""drop: Kurzlinks und im Browser verschlüsselte Text-Drops."""

import os

from dotenv import load_dotenv
from flask import Flask


def create_app(config=None):
    """Erstellt die Flask-App. `config` überschreibt Werte aus der Umgebung (Tests)."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or os.urandom(24),
        PASSWORD=os.getenv("PASSWORD"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///drop.db"),
    )
    if config:
        app.config.update(config)

    from drop import models  # noqa: F401  (registriert die Tabellen)
    from drop.database import db

    db.init_app(app)
    with app.app_context():
        db.create_all()

    from drop import auth, main

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)

    from drop.links import bp as links_bp

    app.register_blueprint(links_bp)
    return app
