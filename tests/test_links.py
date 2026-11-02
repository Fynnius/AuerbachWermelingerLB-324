from drop.database import db
from drop.models import Link


def add_link(app, slug="abc123", kind="url", target="https://example.com"):
    with app.app_context():
        db.session.add(Link(slug=slug, kind=kind, target=target))
        db.session.commit()


def clicks_of(app, slug):
    with app.app_context():
        return db.session.execute(
            db.select(Link.clicks).filter_by(slug=slug)
        ).scalar_one()


def test_follow_redirects_and_counts_click(app, client):
    # Given: an existing slug
    add_link(app)

    # When: I open /<slug> (no login needed)
    response = client.get("/abc123")

    # Then: I am redirected with 302 and the click counter increases
    assert response.status_code == 302
    assert response.headers["Location"] == "https://example.com"
    assert clicks_of(app, "abc123") == 1

    client.get("/abc123")
    assert clicks_of(app, "abc123") == 2


def test_follow_unknown_slug_returns_404(client):
    response = client.get("/nope42")

    assert response.status_code == 404


def test_follow_ignores_text_drops(app, client):
    add_link(app, slug="txt123", kind="text", target=None)

    response = client.get("/txt123")

    assert response.status_code == 404
