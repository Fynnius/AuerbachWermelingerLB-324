import base64
from datetime import datetime, timedelta

import pytest
from werkzeug.exceptions import Gone

from drop.database import db
from drop.expiry import (
    EXPIRY_CHOICES,
    abort_if_expired,
    expires_at_from,
    parse_expires_in,
)
from drop.models import Link, utcnow

NOW = datetime(2026, 1, 1, 12, 0, 0)
CIPHERTEXT = base64.b64encode(b"\x8f\x02encrypted-bytes\xfe").decode()
IV = base64.b64encode(bytes(range(12))).decode()


def test_choices_are_one_hour_one_day_seven_days():
    assert set(EXPIRY_CHOICES) == {3600, 86400, 604800}


@pytest.mark.parametrize("value", [None, ""])
def test_parse_never(value):
    assert parse_expires_in(value) is None


@pytest.mark.parametrize("value", [3600, 86400, 604800, "3600", "604800"])
def test_parse_allowed_values(value):
    assert parse_expires_in(value) == int(value)


@pytest.mark.parametrize(
    "value", [0, 60, -3600, "abc", "3600.0", " 3600", 3600.0, True, [3600], {}]
)
def test_parse_rejects_other_values(value):
    with pytest.raises(ValueError):
        parse_expires_in(value)


def test_expires_at_from_adds_seconds():
    assert expires_at_from(3600, now=NOW) == NOW + timedelta(hours=1)
    assert expires_at_from(None, now=NOW) is None


def test_abort_if_expired_raises_410_only_after_expiry():
    abort_if_expired(Link(slug="a", kind="url"))  # nie
    abort_if_expired(Link(slug="b", kind="url", expires_at=datetime(2999, 1, 1)))

    with pytest.raises(Gone):
        abort_if_expired(Link(slug="c", kind="url", expires_at=datetime(2000, 1, 1)))


# --- Hilfen für Tests mit gesteuerter Zeit ---------------------------------


def login(client):
    client.post("/login", data={"password": "test"})


def add_link(app, slug="abc123", kind="url", expires_at=None, **fields):
    with app.app_context():
        db.session.add(Link(slug=slug, kind=kind, expires_at=expires_at, **fields))
        db.session.commit()
    return slug


def load(app, slug):
    with app.app_context():
        return db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one()


def only_link(app):
    with app.app_context():
        return db.session.execute(db.select(Link)).scalar_one()


def set_expires_at(app, slug, expires_at):
    """Verschiebt den Ablauf direkt in der DB, statt zu warten."""
    with app.app_context():
        link = db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one()
        link.expires_at = expires_at
        db.session.commit()


# --- Kurzlinks ---------------------------------------------------------------


@pytest.mark.parametrize("seconds", [3600, 86400, 604800])
def test_create_link_with_expiry_sets_expires_at(app, client, seconds):
    # Given: I am logged in
    login(client)
    before = utcnow()

    # When: I shorten a URL with an expiry
    client.post(
        "/links", data={"url": "https://example.com", "expires_in": str(seconds)}
    )

    # Then: expires_at lies that many seconds in the future
    link = only_link(app)
    assert before + timedelta(seconds=seconds) <= link.expires_at
    assert link.expires_at <= utcnow() + timedelta(seconds=seconds)


def test_create_link_without_expiry_never_expires(app, client):
    login(client)

    client.post("/links", data={"url": "https://example.com", "expires_in": ""})

    assert only_link(app).expires_at is None


def test_create_link_rejects_invalid_expiry(app, client):
    login(client)

    response = client.post(
        "/links",
        data={"url": "https://example.com", "expires_in": "60"},
        follow_redirects=True,
    )

    assert b"flash-error" in response.data
    with app.app_context():
        assert db.session.execute(db.select(Link)).first() is None


def test_link_works_before_expiry(app, client):
    add_link(
        app,
        target="https://example.com",
        expires_at=utcnow() + timedelta(hours=1),
    )

    assert client.get("/abc123").status_code == 302
    assert client.get("/abc123/qr").status_code == 200


@pytest.mark.parametrize("path", ["/abc123", "/abc123/qr"])
def test_expired_link_is_gone_and_counts_no_click(app, client, path):
    # Given: a link with 1 hour expiry, created 2 hours ago
    add_link(
        app,
        target="https://example.com",
        created_at=utcnow() - timedelta(hours=2),
        expires_at=utcnow() - timedelta(hours=1),
    )

    # When: I open it now
    response = client.get(path)

    # Then: 410 Gone, no redirect, no click
    assert response.status_code == 410
    assert "Location" not in response.headers
    assert load(app, "abc123").clicks == 0


def test_link_expires_while_in_use(app, client):
    add_link(
        app, target="https://example.com", expires_at=utcnow() + timedelta(hours=1)
    )
    assert client.get("/abc123").status_code == 302

    set_expires_at(app, "abc123", utcnow() - timedelta(seconds=1))

    assert client.get("/abc123").status_code == 410
    assert load(app, "abc123").clicks == 1


def test_index_shows_expiry_state(app, client):
    add_link(app, slug="never1", target="https://example.com/never")
    add_link(
        app,
        slug="later1",
        target="https://example.com/later",
        expires_at=datetime(2999, 1, 2, 3, 4),
    )
    add_link(
        app,
        slug="gone01",
        target="https://example.com/gone",
        expires_at=utcnow() - timedelta(minutes=1),
    )
    login(client)

    html = client.get("/").get_data(as_text=True)

    assert 'name="expires_in"' in html
    assert "läuft ab: 02.01.2999 03:04 UTC" in html
    assert "abgelaufen" in html
    assert html.count('class="muted expiry"') == 2
    # Kein QR-Bild für abgelaufene Links (die Route antwortet mit 410)
    assert "/gone01/qr" not in html
    assert "/later1/qr" in html


# --- Drops -------------------------------------------------------------------


def add_drop(app, slug="Ab3dE9", **fields):
    return add_link(app, slug=slug, kind="text", ciphertext=CIPHERTEXT, iv=IV, **fields)


@pytest.mark.parametrize("seconds", [3600, 86400, 604800])
def test_create_drop_with_expiry_sets_expires_at(app, client, seconds):
    login(client)
    before = utcnow()

    response = client.post(
        "/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, "expires_in": seconds}
    )

    assert response.status_code == 201
    drop = load(app, response.get_json()["slug"])
    assert before + timedelta(seconds=seconds) <= drop.expires_at
    assert drop.expires_at <= utcnow() + timedelta(seconds=seconds)


@pytest.mark.parametrize("extra", [{}, {"expires_in": None}])
def test_create_drop_without_expiry_never_expires(app, client, extra):
    login(client)

    response = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, **extra})

    assert response.status_code == 201
    assert load(app, response.get_json()["slug"]).expires_at is None


@pytest.mark.parametrize("value", [60, "abc", True, -3600, 3600.5])
def test_create_drop_rejects_invalid_expiry(app, client, value):
    login(client)

    response = client.post(
        "/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, "expires_in": value}
    )

    assert response.status_code == 400
    assert "expires_in" in response.get_json()["error"]
    with app.app_context():
        assert db.session.execute(db.select(Link)).first() is None


def test_drop_works_before_expiry(app, client):
    add_drop(app, expires_at=utcnow() + timedelta(hours=1))

    assert client.get("/d/Ab3dE9").status_code == 200
    assert client.get("/d/Ab3dE9/data").status_code == 200


@pytest.mark.parametrize("path", ["/d/Ab3dE9", "/d/Ab3dE9/data"])
def test_drop_with_one_hour_expiry_is_gone_after_two_hours(app, client, path):
    # Given: a drop with expiry 1 hour, created 2 hours ago
    created = utcnow() - timedelta(hours=2)
    add_drop(app, created_at=created, expires_at=created + timedelta(hours=1))

    # When: I fetch it now
    response = client.get(path)

    # Then: 410 Gone, no data and no click
    assert response.status_code == 410
    assert CIPHERTEXT.encode() not in response.data
    assert load(app, "Ab3dE9").clicks == 0


def test_expired_drop_page_says_so(app, client):
    add_drop(app, expires_at=utcnow() - timedelta(minutes=1))

    response = client.get("/d/Ab3dE9")

    assert response.status_code == 410
    html = response.get_data(as_text=True)
    assert "Dieser Drop ist abgelaufen." in html
    assert "drop_view.js" not in html


def test_expired_drop_data_is_json(app, client):
    add_drop(app, expires_at=utcnow() - timedelta(minutes=1))

    response = client.get("/d/Ab3dE9/data")

    assert response.status_code == 410
    assert response.get_json() == {"error": "expired"}


def test_new_drop_form_offers_expiry_choices(client):
    login(client)

    html = client.get("/drops/new").get_data(as_text=True)

    assert 'id="drop-expires-in"' in html
    for seconds in ("3600", "86400", "604800"):
        assert f'<option value="{seconds}">' in html
    assert '<option value="" selected>Nie</option>' in html
