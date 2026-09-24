"""AC-39: 비밀번호 본인 변경, 원장 재설정, 원장이 정한 비밀번호의 변경 강제 (DCR-009)."""

import asyncio

from mathdesk.auth import SESSION_COOKIE

NEW_PASSWORD = "brand-new-pw-1"
TEMP_PASSWORD = "temporary-pw-9"


def _login(client, login_id, password):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


def _signed_in_token(client, login_id, password):
    """다른 기기의 로그인을 흉내 낸다 — 새 세션 토큰을 받아 두고 쿠키는 비운다."""
    client.cookies.clear()
    assert _login(client, login_id, password).status_code == 200
    token = client.cookies.get(SESSION_COOKIE)
    client.cookies.clear()
    return token


def _me_status_with(client, token):
    saved = client.cookies.get(SESSION_COOKIE)
    client.cookies.set(SESSION_COOKIE, token)
    status = client.get("/api/auth/me").status_code
    client.cookies.clear()
    if saved:
        client.cookies.set(SESSION_COOKIE, saved)
    return status


def test_self_change_requires_the_current_password(api, password):
    api.sign_in("teacher_a")

    wrong = api.post(
        "/api/auth/password",
        json={"current_password": "not-my-password", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 400

    api.post("/api/auth/logout")
    assert _login(api, "teacher_a", password).status_code == 200


def test_self_change_replaces_the_password(api, password):
    api.sign_in("teacher_a")

    changed = api.post(
        "/api/auth/password",
        json={"current_password": password, "new_password": NEW_PASSWORD},
    )

    assert changed.status_code == 204
    api.post("/api/auth/logout")
    assert _login(api, "teacher_a", password).status_code == 401
    assert _login(api, "teacher_a", NEW_PASSWORD).status_code == 200


def test_self_change_rejects_a_short_or_unchanged_password(api, password):
    api.sign_in("teacher_a")

    for new_password in ("short", password):
        response = api.post(
            "/api/auth/password",
            json={"current_password": password, "new_password": new_password},
        )
        assert response.status_code == 422


def test_self_change_signs_out_other_sessions_but_keeps_this_one(api, password):
    other = _signed_in_token(api, "teacher_a", password)
    api.sign_in("teacher_a")

    api.post(
        "/api/auth/password",
        json={"current_password": password, "new_password": NEW_PASSWORD},
    )

    assert api.get("/api/auth/me").status_code == 200
    assert _me_status_with(api, other) == 401


def test_director_reset_forces_a_change_before_anything_else(api, password):
    teacher_session = _signed_in_token(api, "teacher_a", password)
    api.sign_in("director_a")

    reset = api.post(
        f"/api/users/{api.ids['teacher_a']}/password", json={"new_password": TEMP_PASSWORD}
    )
    assert reset.status_code == 204

    # 기존 로그인은 모두 끊긴다.
    assert _me_status_with(api, teacher_session) == 401
    api.cookies.clear()

    assert _login(api, "teacher_a", password).status_code == 401
    assert _login(api, "teacher_a", TEMP_PASSWORD).status_code == 200
    assert api.get("/api/auth/me").json()["must_change_password"] is True

    blocked = api.get("/api/classes")
    assert blocked.status_code == 403
    assert "비밀번호" in blocked.json()["detail"]

    changed = api.post(
        "/api/auth/password",
        json={"current_password": TEMP_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 204
    assert api.get("/api/auth/me").json()["must_change_password"] is False
    assert api.get("/api/classes").status_code == 200


def test_reset_clears_a_login_lockout(api, scalar):
    scalar(
        "UPDATE app_user SET locked_until = now() + interval '1 hour', "
        "failed_login_count = 3 WHERE login_id = 'teacher_a' RETURNING id"
    )
    api.sign_in("director_a")

    api.post(f"/api/users/{api.ids['teacher_a']}/password", json={"new_password": TEMP_PASSWORD})

    assert scalar("SELECT failed_login_count FROM app_user WHERE login_id = 'teacher_a'") == 0
    api.post("/api/auth/logout")
    assert _login(api, "teacher_a", TEMP_PASSWORD).status_code == 200


def test_only_a_director_of_the_same_campus_can_reset(api):
    api.sign_in("teacher_a")
    assert (
        api.post(
            f"/api/users/{api.ids['director_a']}/password", json={"new_password": TEMP_PASSWORD}
        ).status_code
        == 403
    )

    api.sign_in("director_a")
    other_campus = api.post(
        f"/api/users/{api.ids['director_b']}/password", json={"new_password": TEMP_PASSWORD}
    )
    assert other_campus.status_code == 403

    own = api.post(
        f"/api/users/{api.ids['director_a']}/password", json={"new_password": TEMP_PASSWORD}
    )
    assert own.status_code == 422


def test_password_changes_are_audited_without_the_value(api, scalar, password):
    api.sign_in("director_a")
    api.post(f"/api/users/{api.ids['teacher_a']}/password", json={"new_password": TEMP_PASSWORD})
    api.post(
        "/api/auth/password",
        json={"current_password": password, "new_password": NEW_PASSWORD},
    )

    assert scalar("SELECT count(*) FROM audit_log WHERE action = 'password.reset'") == 1
    assert scalar("SELECT count(*) FROM audit_log WHERE action = 'password.change'") == 1
    leaked = scalar(
        "SELECT count(*) FROM audit_log WHERE coalesce(detail, '') || coalesce(target, '') "
        f"LIKE '%{TEMP_PASSWORD}%' OR coalesce(detail, '') LIKE '%{NEW_PASSWORD}%'"
    )
    assert leaked == 0


def test_an_account_created_by_the_director_must_change_its_password(api):
    api.sign_in("director_a")
    api.post(
        "/api/users",
        json={
            "login_id": "new_teacher",
            "display_name": "새 강사",
            "role": "teacher",
            "password": TEMP_PASSWORD,
        },
    )
    api.post("/api/auth/logout")

    assert _login(api, "new_teacher", TEMP_PASSWORD).status_code == 200
    assert api.get("/api/auth/me").json()["must_change_password"] is True
    assert api.get("/api/students").status_code == 403


def test_existing_accounts_are_not_forced(api):
    api.sign_in("director_a")

    assert api.get("/api/auth/me").json()["must_change_password"] is False


def test_a_newly_created_initial_director_must_change_its_password(
    migrated_database, scalar, monkeypatch
):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from mathdesk.auth import ensure_initial_director

    monkeypatch.setenv("MATHDESK_INITIAL_ADMIN_ID", "owner")
    monkeypatch.setenv("MATHDESK_INITIAL_ADMIN_PASSWORD", TEMP_PASSWORD)

    async def run():
        engine = create_async_engine(migrated_database)
        await ensure_initial_director(async_sessionmaker(engine))
        await engine.dispose()

    asyncio.run(run())

    assert scalar("SELECT must_change_password FROM app_user WHERE login_id = 'owner'") is True


def test_the_last_active_director_cannot_be_demoted_or_deactivated(api):
    api.sign_in("director_a")
    me = api.ids["director_a"]

    assert api.patch(f"/api/users/{me}", json={"role": "teacher"}).status_code == 409
    assert api.patch(f"/api/users/{me}", json={"is_active": False}).status_code == 409

    second = api.post(
        "/api/users",
        json={
            "login_id": "second_director",
            "display_name": "부원장",
            "role": "director",
            "password": TEMP_PASSWORD,
        },
    ).json()["id"]
    assert api.patch(f"/api/users/{second}", json={"is_active": False}).status_code == 200
    assert api.patch(f"/api/users/{me}", json={"role": "teacher"}).status_code == 409
