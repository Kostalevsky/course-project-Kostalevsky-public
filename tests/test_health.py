def test_health_ok(client):
    """Тест health эндпоинта."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
