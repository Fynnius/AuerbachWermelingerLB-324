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
    )
    if config:
        app.config.update(config)

    from drop import main

    app.register_blueprint(main.bp)
    return app
