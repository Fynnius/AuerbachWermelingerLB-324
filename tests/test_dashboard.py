def login(client):
    client.post("/login", data={"password": "test"})


def test_dashboard_page_when_logged_in(client):
    # Given: I am logged in
    login(client)

    # When: I open the dashboard
    response = client.get("/dashboard")

    # Then: the page with the clicks table and the chart area is shown
    assert response.status_code == 200
    assert b'id="dashboard-links"' in response.data
    assert b'id="dashboard-chart"' in response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_nav_links_to_dashboard_when_logged_in(client):
    login(client)

    response = client.get("/")

    assert b'href="/dashboard"' in response.data


def test_nav_hides_dashboard_when_logged_out(client):
    response = client.get("/login")

    assert b'href="/dashboard"' not in response.data
