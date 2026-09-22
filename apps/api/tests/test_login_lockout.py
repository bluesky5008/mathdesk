import time

import pytest

LOGIN_ID = "director_a"


def _login(api, password):
    return api.post("/api/auth/login", json={"login_id": LOGIN_ID, "password": password})


@pytest.fixture
def strict_lockout(monkeypatch):
    monkeypatch.setenv("MATHDESK_LOGIN_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("MATHDESK_LOGIN_LOCKOUT_SECONDS", "1")


def test_correct_password_is_rejected_while_locked(api, strict_lockout, scalar, password):
    for _ in range(3):
        assert _login(api, "wrong-password").status_code == 401

    locked = _login(api, password)

    assert locked.status_code == 401
    assert "잠" in locked.json()["detail"]
    assert scalar("SELECT count(*) FROM audit_log WHERE action = 'auth.lockout'") == 1


def test_login_succeeds_again_after_the_lockout_expires(api, strict_lockout, password):
    for _ in range(3):
        _login(api, "wrong-password")
    assert _login(api, password).status_code == 401

    time.sleep(1.1)

    assert _login(api, password).status_code == 200


def test_successful_login_clears_the_failure_count(api, strict_lockout, password):
    _login(api, "wrong-password")
    _login(api, "wrong-password")
    assert _login(api, password).status_code == 200

    api.post("/api/auth/logout")
    _login(api, "wrong-password")
    _login(api, "wrong-password")

    assert _login(api, password).status_code == 200
