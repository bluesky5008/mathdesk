from pathlib import Path

from fastapi.testclient import TestClient

from mathdesk.main import create_app


def _dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir(parents=True)
    (tmp_path / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "index.html").write_text("<!doctype html><title>mathdesk</title>")
    return tmp_path


def test_spa_fallback_does_not_swallow_api_routes(tmp_path, migrated_database):
    with TestClient(create_app(web_dist=_dist(tmp_path))) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/does-not-exist").status_code == 404
        assert "<!doctype html>" not in client.get("/api/does-not-exist").text


def test_spa_fallback_serves_index_for_client_routes(tmp_path, migrated_database):
    with TestClient(create_app(web_dist=_dist(tmp_path))) as client:
        assert "<title>mathdesk</title>" in client.get("/daily").text
        assert client.get("/assets/app.js").text == "console.log('app')"


def test_cookie_is_marked_secure_when_configured(monkeypatch, api, password):
    monkeypatch.setenv("MATHDESK_COOKIE_SECURE", "true")

    login = api.post("/api/auth/login", json={"login_id": "director_a", "password": password})

    cookie = login.headers["set-cookie"].lower()
    assert "secure" in cookie
    assert "httponly" in cookie


def test_cookie_is_not_secure_by_default(api, password):
    login = api.post("/api/auth/login", json={"login_id": "director_a", "password": password})

    assert "secure" not in login.headers["set-cookie"].lower()
