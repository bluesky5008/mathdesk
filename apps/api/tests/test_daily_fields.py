"""TASK-98 — 일일 기록 항목의 학원별 구성(FR-50, AC-54, DES-27, DCR-028)."""
from datetime import date

from mathdesk.daily import DailyFields, ExtraField, HistoryOut, HistoryRow, RecheckOut
from mathdesk.messaging import MessageContext, render_daily_message
from mathdesk.report import render_history_html

from test_portal import portal, world_with_records  # noqa: F401 — 포털 준비 재사용

DATE = "2026-09-18"
EARLIER = "2026-09-16"
URL = "/api/settings/daily-fields"


def _session(api, klass, on=DATE):
    return api.get("/api/daily", params={"class_id": klass["class_id"], "date": on}).json()


def _attitude(api, recheck=False):
    """재검사를 끄고 "수업태도" 항목을 만든다. 발급된 항목 id를 돌려준다."""
    saved = api.put(URL, json={"recheck": recheck, "extra": [{"label": "수업태도"}]})
    assert saved.status_code == 200, saved.text
    return saved.json()["extra"][0]["id"]


# ── 설정 ─────────────────────────────────────────────────────────────


def test_defaults_keep_the_recheck_and_have_no_extra_fields(api, klass):
    assert api.get(URL).json() == {"recheck": True, "extra": []}
    assert _session(api, klass)["fields"] == {"recheck": True, "extra": []}


def test_director_saves_fields_and_ids_are_never_reused(api, klass):
    first = _attitude(api)
    assert api.get(URL).json() == {"recheck": False, "extra": [{"id": first, "label": "수업태도"}]}

    renamed = api.put(URL, json={"recheck": False, "extra": [{"id": first, "label": "태도"}]}).json()
    assert renamed["extra"] == [{"id": first, "label": "태도"}]

    api.put(URL, json={"recheck": True, "extra": []})
    again = api.put(URL, json={"recheck": True, "extra": [{"label": "수업태도"}]}).json()
    assert again["extra"][0]["id"] != first


def test_invalid_settings_are_rejected(api, klass):
    def put(extra):
        return api.put(URL, json={"recheck": True, "extra": extra}).status_code

    assert put([{"label": f"항목{n}"} for n in range(6)]) == 422
    assert put([{"label": "  "}]) == 422
    assert put([{"label": "가" * 21}]) == 422
    assert put([{"label": "태도"}, {"label": "태도"}]) == 422
    assert put([{"id": "x99", "label": "없는 항목"}]) == 422


def test_teachers_read_but_cannot_change_the_fields(api, klass):
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert api.get(URL).status_code == 200
    assert api.put(URL, json={"recheck": False, "extra": []}).status_code == 403


# ── 일일 입력과 학생별 정보 ───────────────────────────────────────────


def test_extra_values_are_saved_with_the_bulk_save_and_shown_in_history(api, klass):
    field = _attitude(api)
    session_id = _session(api, klass)["session"]["id"]
    student_id = klass["student_ids"][0]

    saved = api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": student_id, "extra": {field: " 집중 좋음 "}}]},
    )
    assert saved.status_code == 200, saved.text

    body = _session(api, klass)
    assert body["fields"] == {"recheck": False, "extra": [{"id": field, "label": "수업태도"}]}
    assert body["records"][0]["extra"] == {field: "집중 좋음"}
    assert body["records"][1]["extra"] == {}

    history = api.get(
        "/api/daily/history", params={"class_id": klass["class_id"], "student_id": student_id, "to": DATE}
    ).json()
    assert history["fields"]["extra"] == [{"id": field, "label": "수업태도"}]
    assert history["rows"][0]["extra"] == {field: "집중 좋음"}

    # 다른 칸을 저장해도 지워지지 않고, 빈 값은 지운다
    api.put(f"/api/daily/{session_id}/records", json={"records": [{"student_id": student_id, "comment": "메모"}]})
    assert _session(api, klass)["records"][0]["extra"] == {field: "집중 좋음"}
    api.put(f"/api/daily/{session_id}/records", json={"records": [{"student_id": student_id, "extra": {field: ""}}]})
    assert _session(api, klass)["records"][0]["extra"] == {}


def test_unknown_or_too_long_extra_values_are_rejected(api, klass):
    field = _attitude(api)
    session_id = _session(api, klass)["session"]["id"]

    def save(extra):
        return api.put(
            f"/api/daily/{session_id}/records",
            json={"records": [{"student_id": klass["student_ids"][0], "extra": extra}]},
        ).status_code

    assert save({"x99": "값"}) == 422
    assert save({field: "가" * 101}) == 422
    assert save({field: "가" * 100}) == 200


def test_turning_the_recheck_back_on_shows_the_stored_result(api, klass):
    student_id = klass["student_ids"][0]
    earlier = _session(api, klass, EARLIER)["session"]["id"]
    api.put(f"/api/daily/{earlier}/records", json={"records": [{"student_id": student_id, "homework_grade": "C"}]})
    session_id = _session(api, klass)["session"]["id"]
    api.put(f"/api/daily/{session_id}/records/{student_id}/recheck", json={"result": "pass"})

    field = _attitude(api, recheck=False)
    api.put(URL, json={"recheck": True, "extra": [{"id": field, "label": "수업태도"}]})

    assert _session(api, klass)["records"][0]["recheck"]["result"] == "pass"


def test_a_deleted_field_disappears_but_a_renamed_one_keeps_its_values(api, klass):
    field = _attitude(api)
    session_id = _session(api, klass)["session"]["id"]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": klass["student_ids"][0], "extra": {field: "집중 좋음"}}]},
    )

    api.put(URL, json={"recheck": False, "extra": [{"id": field, "label": "태도"}]})
    assert _session(api, klass)["records"][0]["extra"] == {field: "집중 좋음"}

    api.put(URL, json={"recheck": False, "extra": []})
    body = _session(api, klass)
    assert body["fields"]["extra"] == []
    assert body["records"][0]["extra"] == {}


# ── 이미지 ───────────────────────────────────────────────────────────


def _history(fields: DailyFields) -> HistoryOut:
    return HistoryOut(
        student={"id": 1, "name": "김나윤"},
        klass={"id": 1, "name": "고2 윤B"},
        fields=fields,
        rows=[
            HistoryRow(
                date=date(2026, 9, 18), attendance_status="present", attendance_reason=None,
                recheck=RecheckOut(target=True, prev_grade="C", prev_date=date(2026, 9, 16), result="pass"),
                homework_grade="A", test_name=None, test_score_num=None, class_average=None, comment=None,
                extra={"x1": "집중 <좋음>"},
            )
        ],
    )


def test_history_card_replaces_the_recheck_column_with_extra_fields():
    html = render_history_html(
        _history(DailyFields(recheck=False, extra=[ExtraField(id="x1", label="수업태도")])),
        date(2026, 9, 18), "한영수학",
    )

    assert "이전 과제 재검사" not in html and "합격" not in html
    assert "<th>출결</th><th>수업태도</th><th>과제피드백</th>" in html
    assert "집중 &lt;좋음&gt;" in html


def test_history_card_keeps_the_recheck_column_by_default():
    html = render_history_html(_history(DailyFields()), date(2026, 9, 18), "한영수학")

    assert "<th>출결</th><th>이전 과제 재검사</th><th>과제피드백</th>" in html
    assert "합격" in html and "집중" not in html


# ── 문자 ─────────────────────────────────────────────────────────────


def test_message_puts_extra_fields_before_the_student_comment():
    body = render_daily_message(
        MessageContext(
            student_name="김나윤", campus_name="한영수학", teacher_name="윤", session_date=date(2026, 9, 18),
            extra=[("수업태도", "집중 좋음")], student_comment="수고했어요",
        )
    )

    assert body.endswith("■ 수업태도\n집중 좋음\n\n■ 개별 코멘트\n수고했어요")


def test_preview_includes_only_extra_fields_that_have_a_value(api, klass):
    field = _attitude(api)
    session_id = _session(api, klass)["session"]["id"]
    first, second = klass["student_ids"][:2]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [
            {"student_id": first, "attendance_status": "present", "extra": {field: "집중 좋음"}},
            {"student_id": second, "attendance_status": "present"},
        ]},
    )

    def preview(student_id):
        return api.get(
            "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
        ).json()["body"]

    assert "■ 수업태도\n집중 좋음" in preview(first)
    assert "수업태도" not in preview(second)


# ── 대시보드 ─────────────────────────────────────────────────────────


def test_dashboard_drops_recheck_targets_when_the_recheck_is_off(api, klass):
    earlier = _session(api, klass, EARLIER)["session"]["id"]
    api.put(
        f"/api/daily/{earlier}/records",
        json={"records": [{"student_id": klass["student_ids"][0], "homework_grade": "C"}]},
    )
    _session(api, klass)

    def targets():
        return api.get(
            "/api/dashboard", params={"class_id": klass["class_id"], "date": DATE}
        ).json()["homework"]["recheck_targets"]

    assert targets() == 1
    _attitude(api, recheck=False)
    assert targets() is None


# ── 포털 ─────────────────────────────────────────────────────────────


def test_portal_shows_extra_fields_with_values_and_hides_the_recheck(api, world_with_records):  # noqa: F811
    target, class_id = world_with_records["target"], world_with_records["class_id"]
    klass = {"class_id": class_id}
    earlier = _session(api, klass, EARLIER)["session"]["id"]
    api.put(f"/api/daily/{earlier}/records", json={"records": [{"student_id": target, "homework_grade": "C"}]})
    field = _attitude(api, recheck=True)
    session_id = _session(api, klass)["session"]["id"]
    api.put(f"/api/daily/{session_id}/records", json={"records": [{"student_id": target, "extra": {field: "집중 좋음"}}]})

    api.cookies.clear()
    assert api.post("/api/auth/login", json={"login_id": "01098765432", "password": "01098765432"}).status_code == 200
    api.post("/api/auth/password", json={"current_password": "01098765432", "new_password": "parent-password-1"})

    def rows():
        return {row["date"]: row for row in api.get(f"/api/portal/students/{target}/sessions").json()}

    shown = rows()
    assert shown[DATE]["recheck"]["prev_grade"] == "C"
    assert shown[DATE]["extra"] == [{"label": "수업태도", "value": "집중 좋음"}]
    assert shown[EARLIER]["extra"] == []

    api.cookies.clear()
    api.sign_in("director_a")
    api.put(URL, json={"recheck": False, "extra": [{"id": field, "label": "수업태도"}]})
    api.cookies.clear()
    assert api.post("/api/auth/login", json={"login_id": "01098765432", "password": "parent-password-1"}).status_code == 200

    assert rows()[DATE]["recheck"] is None
