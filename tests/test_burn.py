import base64

import pytest

from drop.database import db
from drop.models import Link

CIPHERTEXT = base64.b64encode(b"\x8f\x02encrypted-bytes\xfe").decode()
IV = base64.b64encode(bytes(range(12))).decode()


def login(client):
    client.post("/login", data={"password": "test"})


def create(client, **extra):
    response = client.post("/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, **extra})
    assert response.status_code == 201
    return response.get_json()["slug"]


def load(app, slug):
    with app.app_context():
        return db.session.execute(db.select(Link).filter_by(slug=slug)).scalar_one()


def test_burn_after_read_drop_is_gone_after_first_read(client):
    # Given: a drop with burn_after_read
    login(client)
    slug = create(client, burn_after_read=True)

    # When: it is read twice
    first = client.get(f"/d/{slug}/data")
    second = client.get(f"/d/{slug}/data")

    # Then: the first read returns the content and the second one 404
    assert first.status_code == 200
    assert first.get_json() == {"ciphertext": CIPHERTEXT, "iv": IV}
    assert second.status_code == 404


def test_burn_after_read_deletes_the_content_on_the_server(app, client):
    login(client)
    slug = create(client, burn_after_read=True)

    client.get(f"/d/{slug}/data")

    drop = load(app, slug)
    assert drop.ciphertext is None
    assert drop.iv is None
    assert drop.clicks == 1


def test_opening_the_page_does_not_burn_the_drop(client):
    # Link previews in messengers only load the HTML page, never the data.
    login(client)
    slug = create(client, burn_after_read=True)

    assert client.get(f"/d/{slug}").status_code == 200
    assert client.get(f"/d/{slug}").status_code == 200
    assert client.get(f"/d/{slug}/data").status_code == 200


def test_page_of_a_burnt_drop_is_404(client):
    login(client)
    slug = create(client, burn_after_read=True)
    client.get(f"/d/{slug}/data")

    page = client.get(f"/d/{slug}")
    assert page.status_code == 404
    assert "Diesen Drop gibt es nicht (mehr)." in page.get_data(as_text=True)


def test_normal_drop_can_be_read_several_times(app, client):
    login(client)
    slug = create(client)

    assert client.get(f"/d/{slug}/data").status_code == 200
    assert client.get(f"/d/{slug}/data").status_code == 200
    assert load(app, slug).burn_after_read is False


@pytest.mark.parametrize("value", ["yes", 1, None, []])
def test_burn_after_read_must_be_a_boolean(client, value):
    login(client)

    response = client.post(
        "/drops", json={"ciphertext": CIPHERTEXT, "iv": IV, "burn_after_read": value}
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_dashboard_still_counts_a_burnt_drop_without_content(client):
    login(client)
    slug = create(client, burn_after_read=True)
    client.get(f"/d/{slug}/data")

    entries = client.get("/dashboard/data").get_json()

    entry = next(e for e in entries if e["slug"] == slug)
    assert entry["clicks"] == 1
    assert "ciphertext" not in entry


def test_new_drop_page_offers_burn_after_reading(client):
    login(client)

    page = client.get("/drops/new").get_data(as_text=True)

    assert 'id="drop-burn"' in page
    assert "Nach dem ersten Lesen löschen" in page


@pytest.mark.parametrize("burn, expected", [(True, "true"), (False, "false")])
def test_view_page_tells_the_script_whether_the_drop_burns(client, burn, expected):
    login(client)
    slug = create(client, burn_after_read=burn)

    page = client.get(f"/d/{slug}").get_data(as_text=True)

    assert f'data-burn="{expected}"' in page
