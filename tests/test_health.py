def test_health_returns_ok(client):
    # Given: the app is running
    # When: I call /health
    response = client.get("/health")

    # Then: it answers with 200 and "ok"
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
