"""TASK-93 — 포털 조회(FR-49 상세, AC-51, DES-26 상세, DCR-024)."""
import pytest

from mathdesk.models import ExamAnswer, ExamAttempt, MessageLog

from test_deletion import _db  # noqa: F401 — DB 헬퍼 재사용

DATE = "2026-09-18"
GUARDIAN_PHONE = "010-9876-5432"
GUARDIAN_ID = "01098765432"


@pytest.fixture
def world_with_records(api, klass, world, migrated_database):
    """김나윤(대상)·김정현(다른 학생)에게 수업일 기록·상담·시험·발송을 만들고 학부모 계정을 발급한다."""
    target, other = klass["student_ids"][:2]
    api.sign_in("director_a")
    api.patch(f"/api/classes/{klass['class_id']}",
              json={"name": "고2 윤B", "grade": "고2", "teacher_id": world["teacher_a"],
                    "schedules": [{"weekday": 0, "start_time": "18:00"}]})
    api.put("/api/messages/grade-comments", json={"comments": [{"grade": "A", "comment_text": "아주 잘했어요"}]})
    session_id = api.get("/api/daily", params={"class_id": klass["class_id"], "date": DATE}).json()["session"]["id"]
    api.put(f"/api/daily/{session_id}/notes", json={
        "progress": [{"period": 1, "content": "미적분 1단원"}], "homework": "기출 풀어오기",
        "video_url": "https://example.com/v", "teacher_note": "다들 수고", "test_name": "9월 3주 테스트",
    })
    api.put(f"/api/daily/{session_id}/records", json={"records": [
        {"student_id": target, "attendance_status": "late", "attendance_reason": "버스",
         "homework_grade": "A", "test_score_num": 80, "comment": "집중력 좋음"},
        {"student_id": other, "attendance_status": "present", "homework_grade": "B", "test_score_num": 60},
    ]})
    api.post(f"/api/students/{target}/consults", json={"consulted_on": DATE, "content": "진로 상담"})
    api.post(f"/api/students/{other}/consults", json={"consulted_on": DATE, "content": "다른 학생 상담"})
    exam = api.post("/api/exams", json={"name": "9월 모의", "class_id": klass["class_id"], "exam_date": DATE}).json()

    async def body(session):
        for student_id, score in ((target, 90), (other, 50)):
            attempt = ExamAttempt(exam_id=exam["id"], student_id=student_id, form_type="odd", score=score, source="omr")
            session.add(attempt)
            await session.flush()
            session.add(ExamAnswer(attempt_id=attempt.id, question_no=1, raw_value="3", is_correct=True))
            session.add(ExamAnswer(attempt_id=attempt.id, question_no=2, raw_value="1", is_correct=False))
        campus = api.ids["campus_a"]
        for recipient, is_test, status in (("guardian", False, "sent"), ("student", False, "sent"), ("guardian", True, "test")):
            session.add(MessageLog(campus_id=campus, student_id=target, session_id=session_id, recipient_type=recipient,
                                   recipient_phone="010", channel="lms", status=status, body_snapshot="실발송 본문",
                                   is_test=is_test))
        session.add(MessageLog(campus_id=campus, student_id=target, session_id=None, recipient_type="guardian",
                               recipient_phone="010", channel="sms", status="failed", body_snapshot="실패 본문", is_test=False))
        session.add(MessageLog(campus_id=campus, student_id=other, session_id=session_id, recipient_type="guardian",
                               recipient_phone="010", channel="sms", status="sent", body_snapshot="다른 학생 본문", is_test=False))
        await session.commit()

    _db(migrated_database, body)
    api.patch(f"/api/students/{target}", json={"name": "김나윤", "guardian_phone": GUARDIAN_PHONE})
    api.post(f"/api/students/{target}/portal-accounts", json={"kind": "guardian"})
    return {"target": target, "other": other, "class_id": klass["class_id"], "exam_id": exam["id"]}


@pytest.fixture
def portal(api, world_with_records):
    api.cookies.clear()
    assert api.post("/api/auth/login", json={"login_id": GUARDIAN_ID, "password": GUARDIAN_ID}).status_code == 200
    api.post("/api/auth/password", json={"current_password": GUARDIAN_ID, "new_password": "parent-password-1"})
    return world_with_records


def test_session_rows_carry_the_same_values_as_the_message_and_nothing_about_others(api, portal):
    response = api.get(f"/api/portal/students/{portal['target']}/sessions")

    assert response.status_code == 200, response.text
    [row] = response.json()
    assert row == {
        "date": DATE, "class_name": "고2 윤B",
        "progress": [{"period": 1, "content": "미적분 1단원"}], "homework": "기출 풀어오기",
        "video_url": "https://example.com/v", "teacher_note": "다들 수고", "test_name": "9월 3주 테스트",
        "attendance": "late", "attendance_reason": "버스", "homework_grade": "A", "grade_comment": "아주 잘했어요",
        "recheck": None, "test_score": "80", "class_average": 70.0, "comment": "집중력 좋음",
    }
    assert "김정현" not in response.text and "60" not in response.text.replace("70.0", "")


def test_unlinked_students_and_staff_endpoints_are_forbidden(api, portal):
    assert api.get(f"/api/portal/students/{portal['other']}/sessions").status_code == 403
    assert api.get(f"/api/portal/students/{portal['other']}/summary").status_code == 403
    assert api.get(f"/api/students").status_code == 403


def test_summary_counts_attendance_and_shows_timetable(api, portal):
    summary = api.get(f"/api/portal/students/{portal['target']}/summary").json()

    assert summary["attendance"]["all_time"] == {"present": 1, "total": 1}
    assert summary["latest_session"]["date"] == DATE
    assert [t["name"] for t in summary["latest_tests"]] == ["9월 3주 테스트", "9월 모의"]
    assert summary["timetable"] == [{"class_name": "고2 윤B", "weekday": 0, "start_time": "18:00:00", "end_time": "22:00:00"}]


def test_test_trend_lists_only_the_students_own_rounds(api, portal):
    trend = api.get(f"/api/portal/students/{portal['target']}/test-trend").json()

    assert [(r["name"], r["score"], r["class_average"]) for r in trend["rounds"]] == [
        ("9월 3주 테스트", 80.0, 70.0), ("9월 모의", 90.0, 70.0),
    ]


def test_exam_results_show_own_answers_without_class_statistics(api, portal):
    exams = api.get(f"/api/portal/students/{portal['target']}/exams").json()
    assert [(e["name"], e["score"]) for e in exams] == [("9월 모의", 90.0)]

    detail = api.get(f"/api/portal/students/{portal['target']}/exams/{portal['exam_id']}")
    assert detail.status_code == 200
    assert detail.json()["answers"] == [
        {"no": 1, "raw_value": "3", "is_correct": True, "points": None},
        {"no": 2, "raw_value": "1", "is_correct": False, "points": None},
    ]
    assert "김정현" not in detail.text and "average" not in detail.text


def test_consults_and_messages_are_the_students_own_successful_ones(api, portal):
    consults = api.get(f"/api/portal/students/{portal['target']}/consults").json()
    assert [c["content"] for c in consults] == ["진로 상담"]

    messages = api.get(f"/api/portal/students/{portal['target']}/messages").json()
    assert [m["body"] for m in messages] == ["실발송 본문"]  # 같은 세션의 학생·학부모 두 건은 한 건, 테스트·실패는 제외


# ── DCR-025: 달력과 그날 기록 ─────────────────────────────────────────


def test_calendar_lists_the_students_recorded_dates_of_the_month(api, portal):
    response = api.get(f"/api/portal/students/{portal['target']}/calendar", params={"month": "2026-09"})

    assert response.status_code == 200, response.text
    assert response.json() == {"recorded_dates": [DATE]}
    assert api.get(f"/api/portal/students/{portal['target']}/calendar", params={"month": "2026-08"}).json() == {"recorded_dates": []}
    assert api.get(f"/api/portal/students/{portal['other']}/calendar", params={"month": "2026-09"}).status_code == 403
    assert api.get(f"/api/portal/students/{portal['target']}/calendar", params={"month": "2026-9"}).status_code == 422


def test_sessions_on_a_day_return_only_that_day(api, portal):
    same_day = api.get(f"/api/portal/students/{portal['target']}/sessions", params={"on": DATE}).json()
    empty = api.get(f"/api/portal/students/{portal['target']}/sessions", params={"on": "2026-09-17"}).json()

    assert [row["date"] for row in same_day] == [DATE]
    assert empty == []
