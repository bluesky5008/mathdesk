"""TASK-93 — 포털 계정 발급(FR-48 상세, AC-50)과 퇴원·삭제 연동(AC-52, DCR-024)."""
import pytest

from mathdesk.auth import SESSION_COOKIE

STUDENT_PHONE = "010-1234-5678"
GUARDIAN_PHONE = "010-9876-5432"
STUDENT_ID = "01012345678"
GUARDIAN_ID = "01098765432"


def _login(client, login_id, password):
    client.cookies.clear()
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


def _change(client, current, new):
    return client.post("/api/auth/password", json={"current_password": current, "new_password": new})


@pytest.fixture
def student(api, klass):
    """연락처가 둘 다 있는 학생(김나윤)."""
    api.sign_in("director_a")
    target = klass["student_ids"][0]
    api.patch(
        f"/api/students/{target}",
        json={"name": "김나윤", "phone": STUDENT_PHONE, "guardian_phone": GUARDIAN_PHONE},
    )
    return target


def _issue(api, student_id, kind, **extra):
    return api.post(f"/api/students/{student_id}/portal-accounts", json={"kind": kind, **extra})


def _accounts(api, student_id):
    return api.get(f"/api/students/{student_id}/portal-accounts").json()


# ── AC-50 발급 ───────────────────────────────────────────────────────


def test_issued_student_account_uses_phone_digits_and_waits_for_password_change(api, student):
    assert _accounts(api, student)["student"]["state"] == "none"

    issued = _issue(api, student, "student")

    assert issued.status_code == 201, issued.text
    assert issued.json()["login_id"] == STUDENT_ID
    assert issued.json()["state"] == "pending"
    assert _accounts(api, student)["student"]["state"] == "pending"
    listed = {s["id"]: s for s in api.get("/api/students").json()}
    assert listed[student]["portal"] == {"student": "pending", "guardian": "none"}


def test_portal_account_must_change_password_before_portal_opens(api, student):
    _issue(api, student, "student")

    signed = _login(api, STUDENT_ID, STUDENT_ID)
    assert signed.status_code == 200
    assert signed.json()["role"] == "student"
    assert signed.json()["must_change_password"] is True
    assert api.get("/api/portal/students").status_code == 403

    assert _change(api, STUDENT_ID, "my-own-password-1").status_code == 204
    opened = api.get("/api/portal/students")
    assert opened.status_code == 200
    assert [s["name"] for s in opened.json()] == ["김나윤"]
    assert _login(api, STUDENT_ID, STUDENT_ID).status_code == 401

    api.sign_in("director_a")
    assert _accounts(api, student)["student"]["state"] == "active"


def test_student_account_needs_a_student_phone(api, klass):
    api.sign_in("director_a")
    without_phone = klass["student_ids"][1]

    assert _accounts(api, without_phone)["student"]["state"] == "none"
    assert _issue(api, without_phone, "student").status_code == 422


def test_siblings_share_one_guardian_account_only_after_confirmation(api, klass, student):
    """DCR-026: 오타로 남의 학부모에게 연결되지 않도록, 기존 계정 연결은 확인이 있어야 한다."""
    sibling = klass["student_ids"][1]
    api.patch(f"/api/students/{sibling}", json={"name": "김정현", "guardian_phone": GUARDIAN_PHONE})

    first = _issue(api, student, "guardian")
    assert first.status_code == 201 and first.json()["linked"] is False
    assert _accounts(api, sibling)["guardians"][0]["existing"] == {"login_id": GUARDIAN_ID, "students": ["김나윤"]}
    assert _accounts(api, student)["guardians"][0]["existing"] is None

    unconfirmed = _issue(api, sibling, "guardian")
    assert unconfirmed.status_code == 409
    assert _accounts(api, sibling)["guardians"][0]["state"] == "none"

    second = _issue(api, sibling, "guardian", confirm_link=True)
    assert second.status_code == 201 and second.json()["linked"] is True
    assert first.json()["user_id"] == second.json()["user_id"]
    assert _accounts(api, sibling)["guardians"][0]["existing"] is None

    assert _login(api, GUARDIAN_ID, GUARDIAN_ID).status_code == 200
    _change(api, GUARDIAN_ID, "parent-password-1")
    assert sorted(s["name"] for s in api.get("/api/portal/students").json()) == ["김나윤", "김정현"]


def test_only_directors_issue_accounts(api, student):
    api.sign_in("teacher_a")

    assert _issue(api, student, "student").status_code == 403


def test_unchanged_account_expires_after_the_issue_window(api, student, scalar):
    _issue(api, student, "student")
    scalar(f"UPDATE app_user SET issued_at = now() - interval '8 days' WHERE login_id = '{STUDENT_ID}'")

    expired = _login(api, STUDENT_ID, STUDENT_ID)
    assert expired.status_code == 401
    assert "발급 기간" in expired.json()["detail"]
    api.sign_in("director_a")
    assert _accounts(api, student)["student"]["state"] == "expired"

    user_id = _accounts(api, student)["student"]["user_id"]
    assert api.post(f"/api/students/{student}/portal-accounts/{user_id}/reissue").status_code == 204
    assert _login(api, STUDENT_ID, STUDENT_ID).status_code == 200


def test_reissue_resets_the_password_and_ends_every_session(api, student):
    user_id = _issue(api, student, "student").json()["user_id"]
    _login(api, STUDENT_ID, STUDENT_ID)
    _change(api, STUDENT_ID, "my-own-password-1")
    token = api.cookies.get(SESSION_COOKIE)

    api.sign_in("director_a")
    assert api.post(f"/api/students/{student}/portal-accounts/{user_id}/reissue").status_code == 204

    api.cookies.clear()
    api.cookies.set(SESSION_COOKIE, token)
    assert api.get("/api/auth/me").status_code == 401
    assert _login(api, STUDENT_ID, "my-own-password-1").status_code == 401
    assert _login(api, STUDENT_ID, STUDENT_ID).status_code == 200


def test_a_phone_already_used_by_a_staff_account_is_rejected(api, student):
    api.post("/api/users", json={
        "login_id": STUDENT_ID, "display_name": "겹치는 강사", "role": "teacher", "password": "whatever-pw-1",
    })

    assert _issue(api, student, "student").status_code == 409


def test_a_student_phone_that_is_already_a_guardian_account_is_rejected(api, klass, student):
    sibling = klass["student_ids"][1]
    api.patch(f"/api/students/{sibling}", json={"name": "김정현", "phone": GUARDIAN_PHONE})
    _issue(api, student, "guardian")

    assert _issue(api, sibling, "student").status_code == 409


# ── AC-52 퇴원·삭제 연동 ─────────────────────────────────────────────


def test_withdrawal_deactivates_and_re_enrolment_restores_the_account(api, student):
    _issue(api, student, "student")
    _login(api, STUDENT_ID, STUDENT_ID)
    _change(api, STUDENT_ID, "my-own-password-1")

    api.sign_in("director_a")
    api.patch(f"/api/students/{student}", json={"name": "김나윤", "status": "withdrawn"})
    assert _accounts(api, student)["student"]["state"] == "inactive"
    assert _login(api, STUDENT_ID, "my-own-password-1").status_code == 401

    api.sign_in("director_a")
    api.patch(f"/api/students/{student}", json={"name": "김나윤", "status": "enrolled"})
    assert _login(api, STUDENT_ID, "my-own-password-1").status_code == 200


def test_a_guardian_keeps_access_while_one_sibling_remains(api, klass, student):
    sibling = klass["student_ids"][1]
    api.patch(f"/api/students/{sibling}", json={"name": "김정현", "guardian_phone": GUARDIAN_PHONE})
    _issue(api, student, "guardian")
    _issue(api, sibling, "guardian", confirm_link=True)

    api.patch(f"/api/students/{sibling}", json={"name": "김정현", "status": "withdrawn"})

    assert _login(api, GUARDIAN_ID, GUARDIAN_ID).status_code == 200
    _change(api, GUARDIAN_ID, "parent-password-1")
    assert [s["name"] for s in api.get("/api/portal/students").json()] == ["김나윤"]


def test_deleting_a_student_removes_orphaned_portal_accounts_only(api, klass, student, scalar):
    sibling = klass["student_ids"][1]
    api.patch(f"/api/students/{sibling}", json={"name": "김정현", "guardian_phone": GUARDIAN_PHONE})
    _issue(api, student, "student")
    _issue(api, student, "guardian")
    _issue(api, sibling, "guardian", confirm_link=True)
    _login(api, STUDENT_ID, STUDENT_ID)
    token = api.cookies.get(SESSION_COOKIE)

    api.sign_in("director_a")
    assert api.get(f"/api/students/{student}/deletion-preview").json()["counts"]["portal_accounts"] == 1
    assert api.delete(f"/api/students/{student}").status_code == 204

    assert scalar(f"SELECT count(*) FROM app_user WHERE login_id = '{STUDENT_ID}'") == 0
    assert scalar(f"SELECT count(*) FROM app_user WHERE login_id = '{GUARDIAN_ID}'") == 1
    api.cookies.clear()
    api.cookies.set(SESSION_COOKIE, token)
    assert api.get("/api/auth/me").status_code == 401
    assert _login(api, GUARDIAN_ID, GUARDIAN_ID).status_code == 200
