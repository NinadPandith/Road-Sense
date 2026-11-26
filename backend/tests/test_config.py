from app.core.config import Settings


def test_allowed_origins_accepts_comma_separated_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://roadsense.vercel.app, http://localhost:5173")
    assert Settings().allowed_origins == ["https://roadsense.vercel.app", "http://localhost:5173"]


def test_allowed_origins_accepts_json_list(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", '["https://a.example"]')
    assert Settings().allowed_origins == ["https://a.example"]
