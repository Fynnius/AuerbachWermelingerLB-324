def test_login_page_is_shown(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b'name="password"' in response.data


def test_login_with_correct_password(client):
    # Given: the app is running
    # When: I enter the correct password
    response = client.post("/login", data={"password": "test"})

    # Then: I am logged in and redirected to the start page
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    with client.session_transaction() as session:
        assert session["logged_in"] is True


def test_login_with_wrong_password(client):
    # When: I enter a wrong password
    response = client.post("/login", data={"password": "wrong"})

    # Then: I stay on the login page and see an error
    assert response.status_code == 200
    assert "Falsches Passwort".encode() in response.data
    with client.session_transaction() as session:
        assert "logged_in" not in session


def test_login_fails_without_configured_password(app):
    # Given: no PASSWORD is configured
    app.config["PASSWORD"] = None
    client = app.test_client()

    # When: someone submits an empty password
    response = client.post("/login", data={"password": ""})

    # Then: the login is refused
    assert response.status_code == 200
    with client.session_transaction() as session:
        assert "logged_in" not in session


def test_logout(client):
    client.post("/login", data={"password": "test"})

    response = client.get("/logout")

    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "logged_in" not in session
