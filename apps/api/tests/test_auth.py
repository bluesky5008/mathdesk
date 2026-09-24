import asyncio

import pytest
from fastapi.testclient import TestClient

from mathdesk.main import app
from mathdesk.security import hash_password

LOGIN_ID = "director"
PASSWORD = "sup3r-secret-pw"


@pytest.fixture
def client(migrated_database, scalar):
    asyncio.run(_create_user(migrated_database))
    with TestClient(app) as test_client:
        yield test_client


async def _create_user(database_url: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from mathdesk.models import AppUser

    engine = create_async_engine(database_url)
    async with async_sessionmaker(engine)() as session:
        session.add(
            AppUser(
                login_id=LOGIN_ID,
                password_hash=hash_password(PASSWORD),
                display_name="원장",
                role="director",
            )
        )
        await session.commit()
    await engine.dispose()


def test_login_then_me_then_logout_blocks_protected_access(client):
    login = client.post("/api/auth/login", json={"login_id": LOGIN_ID, "password": PASSWORD})
    assert login.status_code == 200

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["login_id"] == LOGIN_ID
    assert me.json()["role"] == "director"

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/api/auth/login", json={"login_id": LOGIN_ID, "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert PASSWORD not in response.text


def test_password_is_never_stored_or_returned_in_plaintext(client, scalar):
    client.post("/api/auth/login", json={"login_id": LOGIN_ID, "password": PASSWORD})

    stored = scalar(f"SELECT password_hash FROM app_user WHERE login_id = '{LOGIN_ID}'")
    assert PASSWORD not in stored
    assert stored.startswith("$argon2id$")
    assert PASSWORD not in client.get("/api/auth/me").text


def test_session_cookie_is_http_only(client):
    login = client.post("/api/auth/login", json={"login_id": LOGIN_ID, "password": PASSWORD})

    cookie = login.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_every_signed_in_request_extends_the_cookie_lifetime(api):
    """유휴 만료 12시간(설계): 쓰는 동안에는 브라우저 쿠키도 12시간 뒤로 다시 늘어나야 한다.
    로그인 때만 Max-Age를 주면 계속 써도 로그인 12시간 뒤에 쿠키가 사라진다(2026-09-24 테스트 운영 재현)."""
    api.sign_in("director_a")
    token = api.cookies["mathdesk_session"]

    for path in ("/api/auth/me", "/api/students"):
        response = api.get(path)
        assert response.status_code == 200, path
        cookie = response.headers.get("set-cookie", "").lower()
        assert f"mathdesk_session={token.lower()}" in cookie, path
        assert "max-age=43200" in cookie, path
        assert "httponly" in cookie and "samesite=lax" in cookie, path


def test_a_rejected_request_does_not_set_a_cookie(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "set-cookie" not in response.headers
