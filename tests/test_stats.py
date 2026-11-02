import base64

import pytest

from drop.database import db
from drop.models import Link, Visit
from drop.stats import device_from_user_agent

IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
CIPHERTEXT = base64.b64encode(b"\x8f\x02encrypted-bytes\xfe").decode()
IV = base64.b64encode(bytes(range(12))).decode()


@pytest.fixture()
def stored(app):
    with app.app_context():
        db.session.add(Link(slug="abc123", kind="url", target="https://example.com"))
        db.session.add(Link(slug="Ab3dE9", kind="text", ciphertext=CIPHERTEXT, iv=IV))
        db.session.commit()


def visits(app):
    with app.app_context():
        rows = db.session.execute(db.select(Visit).order_by(Visit.id)).scalars()
        return [(visit.link_id, visit.at, visit.device) for visit in rows]


def login(client):
    client.post("/login", data={"password": "test"})


def test_two_follows_record_two_visits_with_device(app, client, stored):
    # Given: a short link
    # When: it is opened twice from different devices
    client.get("/abc123", headers={"User-Agent": IPHONE})
    client.get("/abc123", headers={"User-Agent": DESKTOP})

    # Then: two visits with time and device are stored
    recorded = visits(app)
    assert [device for _, _, device in recorded] == ["mobile", "desktop"]
    assert all(at is not None for _, at, _ in recorded)


def test_drop_data_records_a_visit(app, client, stored):
    client.get("/d/Ab3dE9/data", headers={"User-Agent": DESKTOP})

    assert [device for _, _, device in visits(app)] == ["desktop"]


def test_qr_does_not_record_a_visit(app, client, stored):
    client.get("/abc123/qr", headers={"User-Agent": DESKTOP})

    assert visits(app) == []


def test_visit_stores_no_ip_or_user_agent():
    assert set(Visit.__table__.columns.keys()) == {"id", "link_id", "at", "device"}


@pytest.mark.parametrize(
    ("ua", "device"),
    [
        (IPHONE, "mobile"),
        ("Mozilla/5.0 (Linux; Android 14; Pixel 8) Chrome/120.0 Mobile", "mobile"),
        (DESKTOP, "desktop"),
        ("Mozilla/5.0 (Macintosh) Gecko/20100101 Firefox/121.0", "desktop"),
        ("Googlebot/2.1 (+http://www.google.com/bot.html)", "bot"),
        ("Mozilla/5.0 (compatible; bingbot/2.0) Mobile Safari", "bot"),
        ("SomeSpider/1.0", "bot"),
        ("curl/8.4.0", "other"),
        ("", "other"),
        (None, "other"),
    ],
)
def test_device_from_user_agent(ua, device):
    assert device_from_user_agent(ua) == device


def test_dashboard_data_lists_two_visits_per_link(app, client, stored):
    # Given: a link that was opened twice
    client.get("/abc123", headers={"User-Agent": IPHONE})
    client.get("/abc123", headers={"User-Agent": DESKTOP})
    login(client)

    # When: I fetch GET /dashboard/data
    response = client.get("/dashboard/data")

    # Then: it lists the link with two visits including time and device
    assert response.status_code == 200
    entry = next(e for e in response.get_json() if e["slug"] == "abc123")
    assert entry["kind"] == "url"
    assert entry["target"] == "https://example.com"
    assert entry["clicks"] == 2
    assert [v["device"] for v in entry["visits"]] == ["mobile", "desktop"]
    assert all(v["at"].endswith("Z") for v in entry["visits"])


def test_dashboard_data_lists_newest_first(app, client):
    with app.app_context():
        db.session.add(Link(slug="old001", kind="url", target="https://a.example"))
        db.session.commit()
        db.session.add(Link(slug="new001", kind="url", target="https://b.example"))
        db.session.commit()
    login(client)

    slugs = [e["slug"] for e in client.get("/dashboard/data").get_json()]

    assert slugs == ["new001", "old001"]


def test_dashboard_data_hides_drop_contents(client, stored):
    client.get("/d/Ab3dE9/data")
    login(client)

    response = client.get("/dashboard/data")

    entry = next(e for e in response.get_json() if e["slug"] == "Ab3dE9")
    assert entry["kind"] == "text"
    assert entry["target"] is None
    assert "ciphertext" not in entry and "iv" not in entry
    assert CIPHERTEXT.encode() not in response.data
    assert IV.encode() not in response.data


def test_dashboard_data_requires_login(client):
    response = client.get("/dashboard/data")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"
