"""TASK-37 — M8 카카오 알림톡(FR-37·FR-38, AC-26, ADR-005).

실제 알림톡은 보내지 않는다(Q-03: 카카오 채널·템플릿 심사 미확인). 알리고 알림톡 호출은
요청 모양만 가짜 HTTP로 검사하고, 폴백은 가짜 어댑터로 검사한다.
"""
import httpx
import pytest

from mathdesk import messaging, messaging_adapter
from mathdesk.messaging_adapter import AligoMessaging, Recipient, SendResult

from test_message_send import DATE, blocked_network, prepared  # noqa: F401 — 픽스처 재사용

TEMPLATE = {
    "code": "TPL_DAILY_01",
    "body": "#{학생명} 학생 #{수업일} 수업 안내\n출결: #{출결}\n과제: #{과제}",
    "variables": {"학생명": "student_name", "수업일": "session_date", "출결": "attendance", "과제": "homework"},
}
RENDERED = "김나윤 학생 9월 18일 수업 안내\n출결: 출석\n과제: 기출 풀어오기"


def _save(api, templates=(TEMPLATE,), fallback=True):
    return api.put("/api/messages/templates", json={"fallback_to_sms": fallback, "alimtalk": list(templates)})


def _send(api, prepared, **extra):
    body = {"session_id": prepared["session_id"], "student_id": prepared["student_id"], "recipients": ["guardian"]}
    return api.post("/api/messages/send", json=body | extra)


# ── 템플릿·변수 매핑(FR-37) ────────────────────────────────────────────


def test_templates_and_the_fallback_setting_are_saved(api, prepared):
    assert _save(api).status_code == 200

    saved = api.get("/api/messages/templates").json()

    assert saved["fallback_to_sms"] is True
    assert saved["alimtalk"] == [TEMPLATE]
    assert {"key": "homework", "label": "오늘의 과제"} in saved["fields"]


def test_template_variables_must_all_be_mapped_to_known_fields(api, prepared):
    unmapped = {**TEMPLATE, "variables": {"학생명": "student_name"}}
    unknown = {**TEMPLATE, "variables": {**TEMPLATE["variables"], "과제": "password"}}

    assert _save(api, [unmapped]).status_code == 422
    assert _save(api, [unknown]).status_code == 422
    assert _save(api, [{**TEMPLATE, "code": ""}]).status_code == 422
    assert _save(api, [TEMPLATE, TEMPLATE]).status_code == 422  # 같은 코드 두 번


def test_teachers_cannot_change_templates(api, prepared):
    api.sign_in("teacher_a")
    assert _save(api).status_code == 403


# ── 발송(FR-38) ────────────────────────────────────────────────────────


def test_alimtalk_in_test_mode_fills_the_template_and_stays_local(api, prepared, blocked_network):
    _save(api)

    response = _send(api, prepared, template_code="TPL_DAILY_01")

    assert response.status_code == 200, response.text
    assert response.json()["channel"] == "alimtalk"
    assert [r["status"] for r in response.json()["results"]] == ["test"]
    log = api.get("/api/messages/logs").json()[0]
    assert (log["channel"], log["body_snapshot"]) == ("alimtalk", RENDERED)


def test_unknown_template_is_rejected(api, prepared):
    _save(api)
    assert _send(api, prepared, template_code="NOPE").status_code == 422


class FailingKakao:
    """알림톡은 실패하고 문자는 성공하는 가짜 어댑터."""

    mode = "live"

    def __init__(self):
        self.calls = []

    async def send_alimtalk(self, template_code, recipients, body, fallback):
        self.calls.append(("alimtalk", template_code, body))
        return [SendResult(r.phone, r.kind, "failed", result_code="-99", error="카카오톡 미사용자") for r in recipients]

    async def send(self, channel, recipients, body):
        self.calls.append((channel, None, body))
        return [SendResult(r.phone, r.kind, "sent", result_code="1", cost_unit=1) for r in recipients]


def test_failed_alimtalk_falls_back_to_sms_and_both_attempts_are_logged(api, prepared, monkeypatch):
    """AC-26."""
    fake = FailingKakao()
    monkeypatch.setattr(messaging, "build_adapter", lambda: fake)
    _save(api, fallback=True)

    response = _send(api, prepared, template_code="TPL_DAILY_01")

    results = response.json()["results"]
    # 대체 채널은 문구 길이로 정한다(90바이트 이하 SMS)
    assert [(r["channel"], r["status"]) for r in results] == [("alimtalk", "failed"), ("sms", "fallback_sent")]
    assert [call[0] for call in fake.calls] == ["alimtalk", "sms"]
    logs = api.get("/api/messages/logs").json()[:2]
    assert {(log["channel"], log["status"]) for log in logs} == {("alimtalk", "failed"), ("sms", "fallback_sent")}
    assert all(log["body_snapshot"] == RENDERED for log in logs)
    assert any(log["error"] == "카카오톡 미사용자" for log in logs)


def test_without_fallback_a_failed_alimtalk_is_only_logged(api, prepared, monkeypatch):
    fake = FailingKakao()
    monkeypatch.setattr(messaging, "build_adapter", lambda: fake)
    _save(api, fallback=False)

    results = _send(api, prepared, template_code="TPL_DAILY_01").json()["results"]

    assert [(r["channel"], r["status"]) for r in results] == [("alimtalk", "failed")]
    assert [call[0] for call in fake.calls] == ["alimtalk"]


# ── 알리고 알림톡 요청 모양(실발송 미검증) ──────────────────────────────


@pytest.mark.parametrize(
    ("reply", "fallback", "expected"),
    [({"code": 0, "message": "성공"}, True, "sent"), ({"code": -99, "message": "템플릿 불일치"}, False, "failed")],
)
def test_aligo_alimtalk_request_carries_sender_key_template_and_body(monkeypatch, reply, fallback, expected):
    import asyncio

    sent = {}

    async def fake_post(self, url, data=None, **kwargs):
        sent.update(url=str(self.base_url) + url, data=data)
        return httpx.Response(200, json=reply)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    adapter = AligoMessaging("KEY", "user", "0212345678", sender_key="SENDERKEY")

    [result] = asyncio.run(
        adapter.send_alimtalk("TPL_DAILY_01", [Recipient("010-1111-2222", "guardian")], RENDERED, fallback)
    )

    assert sent["url"].startswith("https://kakaoapi.aligo.in/akv10/alimtalk/send")
    assert sent["data"].items() >= {
        "apikey": "KEY", "userid": "user", "senderkey": "SENDERKEY", "tpl_code": "TPL_DAILY_01",
        "sender": "0212345678", "receiver_1": "010-1111-2222", "message_1": RENDERED,
    }.items()
    # 접수 뒤 전달 단계의 실패(카카오톡 미사용자 등)는 알리고만 안다. 폴백이 켜져 있으면 알리고 대체 발송도 켠다
    assert sent["data"]["failover"] == ("Y" if fallback else "N")
    if fallback:
        assert sent["data"]["fmessage_1"] == RENDERED
    assert result.status == expected


def test_live_mode_needs_a_sender_key_for_alimtalk(monkeypatch):
    monkeypatch.setenv("MATHDESK_MESSAGING_MODE", "live")
    for name, value in (("ALIGO_API_KEY", "k"), ("ALIGO_USER_ID", "u"), ("ALIGO_SENDER", "s")):
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("ALIGO_SENDER_KEY", raising=False)

    adapter = messaging_adapter.build_adapter()

    assert adapter.sender_key is None  # 문자는 계속 보낼 수 있다. 알림톡은 발송 시점에 실패로 남는다


def test_preview_shows_the_filled_template_when_one_is_chosen(api, prepared):
    _save(api)
    params = {"session_id": prepared["session_id"], "student_id": prepared["student_id"]}

    plain = api.get("/api/messages/preview", params=params).json()["body"]
    filled = api.get("/api/messages/preview", params=params | {"template_code": "TPL_DAILY_01"}).json()["body"]

    assert filled == RENDERED
    assert plain != RENDERED
