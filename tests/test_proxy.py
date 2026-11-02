import base64

import pytest

from drop import create_app

PROXY_HEADERS = {"X-Forwarded-Proto": "https", "X-Forwarded-Host": "drop.example.net"}
DROP = {
    "ciphertext": base64.b64encode(b"encrypted").decode(),
    "iv": base64.b64encode(bytes(12)).decode(),
}


def make_app(**extra):
    config = {
        "TESTING": True,
        "PASSWORD": "test",
        "SECRET_KEY": "test",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    }
    config.update(extra)
    return create_app(config)


@pytest.fixture()
def proxied_client():
    return make_app(TRUST_PROXY=True).test_client()


def login(client, **kwargs):
    return client.post("/login", data={"password": "test"}, **kwargs)


def test_links_use_https_behind_proxy(proxied_client):
    # Given: the app runs behind the Azure proxy, which terminates TLS
    login(proxied_client, headers=PROXY_HEADERS)

    # When: I create a drop
    response = proxied_client.post("/drops", json=DROP, headers=PROXY_HEADERS)

    # Then: the link uses https and the public host name
    assert response.status_code == 201
    assert response.get_json()["url"].startswith("https://drop.example.net/d/")


def test_short_link_on_start_page_uses_https_behind_proxy(proxied_client):
    login(proxied_client, headers=PROXY_HEADERS)
    proxied_client.post(
        "/links", data={"url": "https://example.com"}, headers=PROXY_HEADERS
    )

    page = proxied_client.get("/", headers=PROXY_HEADERS).get_data(as_text=True)

    assert "https://drop.example.net/" in page
    assert "http://localhost/" not in page


def test_forwarded_headers_are_ignored_without_proxy(client):
    # Given: the app runs locally, not behind a proxy
    login(client)

    # When: a client sends forged forwarding headers
    response = client.post("/drops", json=DROP, headers=PROXY_HEADERS)

    # Then: they are ignored
    assert response.get_json()["url"].startswith("http://localhost/d/")


def test_session_cookie_is_secure_behind_proxy(proxied_client):
    response = login(proxied_client, headers=PROXY_HEADERS)

    cookie = response.headers["Set-Cookie"]
    assert "Secure" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_session_cookie_works_over_http_locally(client):
    response = login(client)

    cookie = response.headers["Set-Cookie"]
    assert "Secure" not in cookie
    assert "SameSite=Lax" in cookie


def test_azure_is_detected_by_website_hostname(monkeypatch):
    # Given: App Service sets WEBSITE_HOSTNAME automatically
    monkeypatch.setenv("WEBSITE_HOSTNAME", "drop.example.net")

    # Then: the app trusts the proxy without extra configuration
    assert make_app().config["TRUST_PROXY"] is True


def test_proxy_is_not_trusted_by_default(monkeypatch):
    monkeypatch.delenv("WEBSITE_HOSTNAME", raising=False)
    monkeypatch.delenv("TRUST_PROXY", raising=False)

    assert make_app().config["TRUST_PROXY"] is False
