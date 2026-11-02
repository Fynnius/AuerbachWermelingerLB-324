"""drop: Kurzlinks und im Browser verschlüsselte Text-Drops."""

import os

from dotenv import load_dotenv
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(config=None):
    """Erstellt die Flask-App. `config` überschreibt Werte aus der Umgebung (Tests)."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or os.urandom(24),
        PASSWORD=os.getenv("PASSWORD"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///drop.db"),
        # Azure App Service setzt WEBSITE_HOSTNAME selbst; dort endet TLS am Proxy.
        TRUST_PROXY=os.getenv("TRUST_PROXY") == "1"
        or bool(os.getenv("WEBSITE_HOSTNAME")),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    if app.config["TRUST_PROXY"]:
        # Ohne ProxyFix sieht die App nur HTTP und erzeugt http://-Links.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        app.config["SESSION_COOKIE_SECURE"] = True

    from drop import models  # noqa: F401  (registriert die Tabellen)
    from drop.database import db

    db.init_app(app)
    with app.app_context():
        db.create_all()

    from drop import auth, drops, links, main, stats

    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(links.bp)
    app.register_blueprint(drops.bp)
    app.register_blueprint(stats.bp)
    return app
