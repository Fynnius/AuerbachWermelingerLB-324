import base64

import pytest

from drop.database import db
from drop.models import Link

CIPHERTEXT = base64.b64encode(b"\x8f\x02encrypted-bytes\xfe").decode()
IV = base64.b64encode(bytes(range(12))).decode()


@pytest.fixture()
def stored_drop(app):
    with app.app_context():
        db.session.add(Link(slug="Ab3dE9", kind="text", ciphertext=CIPHERTEXT, iv=IV))
        db.session.commit()
    return "Ab3dE9"


def load(app, slug):
    with app.app_context():
        return db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one()


def test_data_returns_exactly_ciphertext_and_iv(client, stored_drop):
    # Given: a stored drop
    # When: I call GET /d/<slug>/data
    response = client.get(f"/d/{stored_drop}/data")

    # Then: I get exactly ciphertext and iv
    assert response.status_code == 200
    assert response.get_json() == {"ciphertext": CIPHERTEXT, "iv": IV}


def test_data_counts_clicks(app, client, stored_drop):
    client.get(f"/d/{stored_drop}/data")
    client.get(f"/d/{stored_drop}/data")

    assert load(app, stored_drop).clicks == 2


def test_view_is_public_and_contains_no_data(client, stored_drop):
    response = client.get(f"/d/{stored_drop}")

    assert response.status_code == 200
    assert f'data-slug="{stored_drop}"'.encode() in response.data
    assert CIPHERTEXT.encode() not in response.data
    assert IV.encode() not in response.data


@pytest.mark.parametrize("path", ["/d/nope42", "/d/nope42/data"])
def test_unknown_slug_is_404(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/d/{}", "/d/{}/data"])
def test_short_links_are_not_drops(app, client, path):
    # Given: a short link (kind="url") with the same slug format
    with app.app_context():
        db.session.add(Link(slug="url001", kind="url", target="https://example.com"))
        db.session.commit()

    # Then: the drop routes do not serve it
    assert client.get(path.format("url001")).status_code == 404


def login(client):
    client.post("/login", data={"password": "test"})


def test_create_returns_slug_and_url(app, client):
    # Given: valid ciphertext and iv
    login(client)

    # When: I POST /drops
    response = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV})

    # Then: I get a slug and the link to the drop page
    assert response.status_code == 201
    body = response.get_json()
    assert set(body) == {"slug", "url"}
    assert len(body["slug"]) == 6 and body["slug"].isalnum()
    assert body["url"] == f"http://localhost/d/{body['slug']}"


def test_create_stores_only_ciphertext_and_iv(app, client):
    login(client)

    slug = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV}).get_json()[
        "slug"
    ]

    drop = load(app, slug)
    assert drop.kind == "text"
    assert drop.ciphertext == CIPHERTEXT
    assert drop.iv == IV
    assert drop.target is None
    assert client.get(f"/d/{slug}/data").get_json() == {
        "ciphertext": CIPHERTEXT,
        "iv": IV,
    }


def test_create_rejects_plaintext_field(app, client):
    # Given: a request with a plaintext field
    login(client)

    # When: I send it
    response = client.post(
        "/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, "plaintext": "geheim"}
    )

    # Then: it is rejected with 400 and nothing is stored
    assert response.status_code == 400
    with app.app_context():
        assert db.session.execute(db.select(Link)).first() is None


@pytest.mark.parametrize(
    "payload",
    [
        {"ciphertext": CIPHERTEXT, "iv": IV, "expires_in": 3600},
        {"ciphertext": CIPHERTEXT},
        {"iv": IV},
        {"ciphertext": "", "iv": IV},
        {"ciphertext": 123, "iv": IV},
        {"ciphertext": "not base64!", "iv": IV},
        {"ciphertext": CIPHERTEXT, "iv": "%%%%"},
        {"ciphertext": base64.urlsafe_b64encode(b"\xfb\xff" * 3).decode(), "iv": IV},
        {"ciphertext": CIPHERTEXT, "iv": base64.b64encode(bytes(16)).decode()},
        {"ciphertext": CIPHERTEXT, "iv": base64.b64encode(bytes(11)).decode()},
        {"ciphertext": base64.b64encode(bytes(64 * 1024 + 1)).decode(), "iv": IV},
        ["ciphertext", "iv"],
    ],
    ids=[
        "unknown-field",
        "missing-iv",
        "missing-ciphertext",
        "empty-ciphertext",
        "ciphertext-not-string",
        "invalid-base64",
        "invalid-base64-iv",
        "urlsafe-alphabet",
        "iv-16-bytes",
        "iv-11-bytes",
        "ciphertext-too-large",
        "not-an-object",
    ],
)
def test_create_rejects_invalid_payload(client, payload):
    login(client)

    response = client.post("/drops", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_accepts_ciphertext_of_exactly_64_kib(client):
    login(client)
    ciphertext = base64.b64encode(bytes(64 * 1024)).decode()

    response = client.post("/drops", json={"ciphertext": ciphertext, "iv": IV})

    assert response.status_code == 201


def test_create_rejects_non_json_body(client):
    login(client)

    response = client.post("/drops", data={"ciphertext": CIPHERTEXT, "iv": IV})

    assert response.status_code == 400


def test_create_requires_login_with_json_401(client):
    response = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV})

    assert response.status_code == 401
    assert response.get_json() == {"error": "login required"}


def test_create_retries_on_slug_collision(app, client, stored_drop, monkeypatch):
    # Given: the random generator first returns an existing slug
    login(client)
    letters = iter(stored_drop + "Zz9Yy8")
    monkeypatch.setattr("drop.drops.secrets.choice", lambda alphabet: next(letters))

    response = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV})

    # Then: a new slug is drawn
    assert response.get_json()["slug"] == "Zz9Yy8"


def test_new_page_requires_login(client):
    response = client.get("/drops/new")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_new_page_is_shown_when_logged_in(client):
    login(client)

    assert client.get("/drops/new").status_code == 200
