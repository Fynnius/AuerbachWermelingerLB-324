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
