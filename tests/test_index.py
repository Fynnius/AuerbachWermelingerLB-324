from drop.database import db
from drop.models import Link


def test_index_redirects_to_login_when_logged_out(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_index_is_shown_when_logged_in(client):
    client.post("/login", data={"password": "test"})

    response = client.get("/")

    assert response.status_code == 200
    assert b"Logout" in response.data


def test_index_shows_form_and_created_link(client):
    # Given: I am logged in and have shortened a link
    client.post("/login", data={"password": "test"})
    client.post("/links", data={"url": "https://example.com/page"})

    # When: I open the start page
    response = client.get("/")

    # Then: I see the form and my link with short URL and click count
    html = response.get_data(as_text=True)
    assert "Link kürzen" in html
    assert 'action="/links"' in html
    assert "https://example.com/page" in html
    assert "http://localhost/" in html
    assert "0 Klicks" in html


def test_index_lists_newest_link_first(client):
    client.post("/login", data={"password": "test"})
    client.post("/links", data={"url": "https://first.example"})
    client.post("/links", data={"url": "https://second.example"})

    html = client.get("/").get_data(as_text=True)

    assert html.index("https://second.example") < html.index("https://first.example")


def test_index_shows_qr_code_for_link(app, client):
    # Given: a created link
    client.post("/login", data={"password": "test"})
    client.post("/links", data={"url": "https://example.com"})
    with app.app_context():
        slug = db.session.execute(db.select(Link.slug)).scalar_one()

    # When: I open the start page
    html = client.get("/").get_data(as_text=True)

    # Then: I see its QR code
    assert f'class="qr" src="/{slug}/qr"' in html
