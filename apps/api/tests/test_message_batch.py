"""반 단위 일괄 발송(DCR-023 / AC-49)."""

import time
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select

from mathdesk.messaging_adapter import Balance, Recipient, SendResult

DATE = "2026-09-18"


class FakeLive:
    """실발송 흉내. 특정 번호는 실패시킨다. 외부로 나가지 않는다."""

    mode = "live"

    def __init__(self, failing: set[str] | None = None) -> None:
        self.failing = failing or set()
        self.sent: list[tuple[str, str]] = []

    async def send(self, channel, recipients, body):
        results = []
        for recipient in recipients:
            self.sent.append((recipient.phone, body))
            if recipient.phone in self.failing:
                results.append(SendResult(recipient.phone, recipient.kind, "failed", "E", "수신 거부"))
            else:
                results.append(SendResult(recipient.phone, recipient.kind, "sent", "1", None, 1))
        return results

    async def send_alimtalk(self, template_code, recipients, body, fallback):
        return await self.send("alimtalk", recipients, body)

    async def balance(self):
        return Balance("live", 1, 1, 1, datetime.now(UTC).isoformat())


@pytest.fixture
def blocked_network(monkeypatch):
    async def explode(*args, **kwargs):
        raise AssertionError("테스트 모드에서 외부 호출이 발생했다")

    monkeypatch.setattr(httpx.AsyncClient, "post", explode)
    monkeypatch.setattr(httpx.AsyncClient, "get", explode)


@pytest.fixture
def batch(api, klass):
    """학생 3명 중 둘은 학부모 번호가 있고 셋째는 연락처가 없다. 출결은 서로 다르다."""
    session_id = api.get("/api/daily", params={"class_id": klass["class_id"], "date": DATE}).json()["session"]["id"]
    first, second, third = klass["student_ids"]
    api.put(f"/api/daily/{session_id}/notes", json={"homework": "기출 풀어오기"})
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [
            {"student_id": first, "attendance_status": "present"},
            {"student_id": second, "attendance_status": "late"},
        ]},
    )
    for student_id, phone in ((first, "010-1111-0001"), (second, "010-1111-0002")):
        api.post(f"/api/students/{student_id}/guardians", json={"relation": "모", "name": "학부모", "phone": phone})
    return {"session_id": session_id, "first": first, "second": second, "third": third}


def _preview(api, batch, **params):
    return api.get(
        "/api/messages/send-batch/preview",
        params={"session_id": batch["session_id"], "recipients": ["guardian"], **params},
    )


def _start(api, batch, **overrides):
    return api.post(
        "/api/messages/send-batch",
        json={"session_id": batch["session_id"], "recipients": ["guardian"], **overrides},
    )


def _wait(api, task_id, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("done", "failed"):
            return task
        time.sleep(0.05)
    raise AssertionError(f"작업이 끝나지 않았다: {task}")


def _logs(api, session_id):
    return [log for log in api.get("/api/messages/logs").json() if log["session_id"] == session_id]


def test_preview_lists_targets_and_names_students_without_contacts(api, batch):
    body = _preview(api, batch).json()

    assert [s["student_id"] for s in body["planned"]] == [batch["first"], batch["second"]]
    assert body["skipped"] == [{"student_id": batch["third"], "name": "김태호", "reason": "no_recipient"}]


def test_batch_sends_each_student_their_own_body_in_test_mode(api, batch, blocked_network):
    started = _start(api, batch).json()
    assert [s["student_id"] for s in started["planned"]] == [batch["first"], batch["second"]]

    task = _wait(api, started["task_id"])

    assert task["status"] == "done"
    assert task["result"]["test"] == 2 and task["result"]["sent"] == 0 and task["result"]["failed"] == 0
    assert [s["status"] for s in task["result"]["students"]] == ["test", "test"]
    logs = _logs(api, batch["session_id"])
    assert sorted(log["student_id"] for log in logs) == sorted([batch["first"], batch["second"]])
    bodies = {log["student_id"]: log["body_snapshot"] for log in logs}
    assert all("기출 풀어오기" in body for body in bodies.values())  # 공통 구획은 같다
    assert "출석" in bodies[batch["first"]] and "지각" in bodies[batch["second"]]  # 개별 구획은 다르다
    assert all(log["is_test"] for log in logs)


def test_already_sent_students_are_excluded_unless_included(api, batch, monkeypatch):
    monkeypatch.setattr("mathdesk.messaging.build_adapter", lambda: FakeLive())
    _wait(api, _start(api, batch).json()["task_id"])

    again = _preview(api, batch).json()
    assert again["planned"] == []
    assert sorted(s["reason"] for s in again["skipped"]) == ["already_sent", "already_sent", "no_recipient"]

    included = _preview(api, batch, include_already_sent="true").json()
    assert [s["student_id"] for s in included["planned"]] == [batch["first"], batch["second"]]
    # 테스트 모드 로그는 이미 보냄으로 치지 않는다 — 위 FakeLive는 실발송이라 집계되었다
    assert _start(api, batch).status_code == 422


def test_failed_student_is_reported_and_can_be_resent_alone(api, batch, monkeypatch):
    fake = FakeLive(failing={"010-1111-0002"})
    monkeypatch.setattr("mathdesk.messaging.build_adapter", lambda: fake)

    task = _wait(api, _start(api, batch).json()["task_id"])

    by_student = {s["student_id"]: s for s in task["result"]["students"]}
    assert by_student[batch["first"]]["status"] == "sent"
    assert by_student[batch["second"]]["status"] == "failed"
    assert by_student[batch["second"]]["error"] == "수신 거부"
    assert task["result"] | {"students": None} == {"sent": 1, "failed": 1, "test": 0, "skipped": 0, "students": None}

    # 실패한 학생은 이미 보냄이 아니므로 그 학생만 다시 보낼 수 있다
    fake.failing.clear()
    retry = _start(api, batch, student_ids=[batch["second"]]).json()
    assert [s["student_id"] for s in retry["planned"]] == [batch["second"]]
    assert _wait(api, retry["task_id"])["result"]["sent"] == 1


def test_batch_rejects_an_empty_target_and_too_many_students(api, batch):
    assert _start(api, batch, student_ids=[batch["third"]]).status_code == 422
    assert _start(api, batch, student_ids=list(range(1, 502))).status_code == 422


def test_resumed_task_skips_students_already_sent_after_it_was_created(api, batch, monkeypatch):
    """재시작 재개: 작업 생성 뒤에 성공 로그가 생긴 학생은 다시 보내지 않는다(AC-49 ⑦)."""
    from mathdesk.main import app
    from mathdesk.models import AppUser, BackgroundTask, MessageLog

    fake = FakeLive()
    monkeypatch.setattr("mathdesk.messaging.build_adapter", lambda: fake)

    async def arrange():
        async with app.state.session_factory() as session:
            actor = await session.scalar(select(AppUser).where(AppUser.login_id == "director_a"))
            task = BackgroundTask(
                campus_id=api.ids["campus_a"], kind="message_batch",
                payload={"session_id": batch["session_id"], "student_ids": [batch["first"], batch["second"]],
                         "recipients": ["guardian"], "template_code": None, "actor_id": actor.id},
            )
            session.add(task)
            await session.flush()
            session.add(MessageLog(
                campus_id=task.campus_id, student_id=batch["first"], session_id=batch["session_id"],
                recipient_type="guardian", recipient_phone="01011110001", channel="lms", status="sent",
                body_snapshot="이미 보냄", is_test=False,
                requested_at=datetime.now(UTC) + timedelta(seconds=1),
            ))
            await session.commit()
            return task.id

    task_id = api.portal.call(arrange)
    api.portal.call(app.state.task_runner.run_pending)

    task = _wait(api, task_id)
    assert task["result"]["skipped"] == 1 and task["result"]["sent"] == 1
    assert [phone for phone, _ in fake.sent] == ["010-1111-0002"]


def test_teacher_cannot_batch_another_class(api, batch):
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert _preview(api, batch).status_code == 403
    assert _start(api, batch).status_code == 403
