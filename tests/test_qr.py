from drop.database import db
from drop.models import Link


def test_qr_returns_svg_for_existing_slug(app, client):
    # Given: an existing slug
    with app.app_context():
        db.session.add(Link(slug="abc123", kind="url", target="https://example.com"))
        db.session.commit()

    # When: I open /<slug>/qr (no login needed)
    response = client.get("/abc123/qr")

    # Then: I get a non-empty SVG image
    assert response.status_code == 200
    assert response.mimetype == "image/svg+xml"
    assert b"<svg" in response.data


def test_qr_does_not_count_a_click(app, client):
    with app.app_context():
        db.session.add(Link(slug="abc123", kind="url", target="https://example.com"))
        db.session.commit()

    client.get("/abc123/qr")

    with app.app_context():
        link = db.session.execute(db.select(Link).filter_by(slug="abc123")).scalar_one()
        assert link.clicks == 0


def test_qr_unknown_slug_returns_404(client):
    response = client.get("/nope42/qr")

    assert response.status_code == 404
