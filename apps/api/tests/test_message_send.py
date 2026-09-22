import httpx
import pytest

DATE = "2026-09-18"


@pytest.fixture
def blocked_network(monkeypatch):
    """테스트 모드가 외부로 나가지 않는지 확인하기 위해 HTTP 호출을 막는다."""

    async def explode(*args, **kwargs):
        raise AssertionError("테스트 모드에서 외부 호출이 발생했다")

    monkeypatch.setattr(httpx.AsyncClient, "post", explode)
    monkeypatch.setattr(httpx.AsyncClient, "get", explode)


@pytest.fixture
def prepared(api, klass):
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": DATE}
    ).json()["session"]["id"]
    student_id = klass["student_ids"][0]
    api.put(f"/api/daily/{session_id}/notes", json={"homework": "기출 풀어오기"})
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": student_id, "attendance_status": "present"}]},
    )
    api.post(
        f"/api/students/{student_id}/guardians",
        json={"relation": "모", "name": "학부모", "phone": "010-1111-2222"},
    )
    return {"session_id": session_id, "student_id": student_id}


def _send(api, prepared, **overrides):
    payload = {
        "session_id": prepared["session_id"],
        "student_id": prepared["student_id"],
        "recipients": ["guardian"],
    } | overrides
    return api.post("/api/messages/send", json=payload)


def test_test_mode_sends_without_calling_the_provider(api, prepared, blocked_network):
    response = _send(api, prepared)

    assert response.status_code == 200
    results = response.json()["results"]
    assert [result["status"] for result in results] == ["test"]
    assert results[0]["recipient_phone"] == "010-1111-2222"


def test_send_writes_a_log_with_an_immutable_body_snapshot(api, prepared, blocked_network):
    _send(api, prepared)
    original = api.get("/api/messages/logs").json()[0]["body_snapshot"]
    assert "기출 풀어오기" in original

    api.put(
        f"/api/daily/{prepared['session_id']}/notes", json={"homework": "완전히 바뀐 과제"}
    )

    stored = api.get("/api/messages/logs").json()[0]
    assert stored["body_snapshot"] == original
    assert "완전히 바뀐 과제" not in stored["body_snapshot"]
    assert stored["channel"] in {"sms", "lms"}
    assert stored["recipient_type"] == "guardian"


def test_long_bodies_are_sent_as_lms(api, prepared, blocked_network):
    api.put(
        f"/api/daily/{prepared['session_id']}/notes", json={"homework": "가" * 200}
    )

    _send(api, prepared)

    assert api.get("/api/messages/logs").json()[0]["channel"] == "lms"


def test_recipients_can_include_the_student_and_the_guardian(api, prepared, blocked_network):
    api.patch(
        f"/api/students/{prepared['student_id']}",
        json={"name": "김나윤", "phone": "010-3333-4444", "omr_number": "10000100"},
    )

    response = _send(api, prepared, recipients=["student", "guardian"])

    phones = {result["recipient_phone"] for result in response.json()["results"]}
    assert phones == {"010-3333-4444", "010-1111-2222"}


def test_sending_without_a_reachable_recipient_fails(api, klass, blocked_network):
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": DATE}
    ).json()["session"]["id"]

    response = api.post(
        "/api/messages/send",
        json={
            "session_id": session_id,
            "student_id": klass["student_ids"][1],
            "recipients": ["guardian"],
        },
    )

    assert response.status_code == 422


def test_balance_is_reported_in_test_mode(api, prepared, blocked_network):
    body = api.get("/api/messages/balance").json()

    assert body["mode"] == "test"
    assert set(body) >= {"mode", "sms", "lms", "mms", "checked_at"}
