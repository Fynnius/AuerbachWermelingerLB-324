import re

from drop import links
from drop.database import db
from drop.models import Link


def add_link(app, slug="abc123", kind="url", target="https://example.com"):
    with app.app_context():
        db.session.add(Link(slug=slug, kind=kind, target=target))
        db.session.commit()


def login(client):
    client.post("/login", data={"password": "test"})


def all_links(app):
    with app.app_context():
        return db.session.execute(db.select(Link)).scalars().all()


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


def test_create_link_when_logged_in(app, client):
    # Given: I am logged in
    login(client)

    # When: I shorten https://example.com
    response = client.post(
        "/links", data={"url": "https://example.com"}, follow_redirects=True
    )

    # Then: a link with a 6-character slug is stored and shown as success
    assert response.request.path == "/"
    links_ = all_links(app)
    assert len(links_) == 1
    assert links_[0].kind == "url"
    assert links_[0].target == "https://example.com"
    assert re.fullmatch(r"[A-Za-z0-9]{6}", links_[0].slug)
    assert b"flash-success" in response.data
    assert f"http://localhost/{links_[0].slug}".encode() in response.data


def test_create_link_rerolls_slug_on_collision(app, client, monkeypatch):
    # Given: the first random slug is already taken
    add_link(app, slug="aaaaaa")
    rolls = iter("aaaaaa" + "bbbbbb")
    monkeypatch.setattr(links.secrets, "choice", lambda _: next(rolls))
    login(client)

    # When: I shorten a URL
    client.post("/links", data={"url": "https://example.org"})

    # Then: a new slug is rolled
    assert {link.slug for link in all_links(app)} == {"aaaaaa", "bbbbbb"}


def test_create_link_rejects_javascript_url(app, client):
    login(client)

    response = client.post(
        "/links", data={"url": "javascript:alert(1)"}, follow_redirects=True
    )

    assert b"flash-error" in response.data
    assert all_links(app) == []


def test_create_link_rejects_url_without_host(app, client):
    login(client)

    client.post("/links", data={"url": "https://"})

    assert all_links(app) == []


def test_create_link_requires_login(app, client):
    response = client.post("/links", data={"url": "https://example.com"})

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
    assert all_links(app) == []
