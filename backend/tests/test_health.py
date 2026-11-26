def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model_version" in body


def test_unknown_route_uses_error_shape(client):
    r = client.get("/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_sentry_scrubs_personal_data(monkeypatch):
    import sentry_sdk

    from app.main import init_sentry

    captured = {}
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: captured.update(kw))
    init_sentry("https://key@example.ingest.sentry.io/1", "test", "v1")
    event = {
        "request": {
            "data": "photo bytes",
            "cookies": {"a": "b"},
            "headers": {"authorization": "Bearer x", "x-forwarded-for": "1.2.3.4", "accept": "*/*"},
        }
    }
    out = captured["before_send"](event, None)
    assert captured["send_default_pii"] is False
    assert "data" not in out["request"] and "cookies" not in out["request"]
    assert out["request"]["headers"] == {"accept": "*/*"}
