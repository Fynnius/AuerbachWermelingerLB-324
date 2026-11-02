def test_index_redirects_to_login_when_logged_out(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/login"


def test_index_is_shown_when_logged_in(client):
    client.post("/login", data={"password": "test"})

    response = client.get("/")

    assert response.status_code == 200
    assert b"Logout" in response.data
