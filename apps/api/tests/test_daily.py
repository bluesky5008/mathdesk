import pytest

DATE = "2026-09-18"


@pytest.fixture
def klass(api):
    api.sign_in("director_a")
    class_id = api.post("/api/classes", json={"name": "고2 윤B", "grade": "고2"}).json()["id"]
    student_ids = []
    for index, name in enumerate(["김나윤", "김정현", "김태호"], start=1):
        student_id = api.post(
            "/api/students", json={"name": name, "omr_number": f"1000{index:02d}00"}
        ).json()["id"]
        api.post(
            f"/api/classes/{class_id}/enrollments",
            json={"student_id": student_id, "start_date": "2026-03-02"},
        )
        student_ids.append(student_id)
    return {"class_id": class_id, "student_ids": student_ids}


def _daily(api, klass):
    return api.get("/api/daily", params={"class_id": klass["class_id"], "date": DATE}).json()


def test_daily_lists_students_enrolled_on_that_date(api, klass):
    body = _daily(api, klass)

    assert [record["student_id"] for record in body["records"]] == klass["student_ids"]
    assert [record["attendance_status"] for record in body["records"]] == ["unchecked"] * 3
    assert body["summary"]["enrolled"] == 3


def test_saving_records_keeps_unsaved_notes_and_the_reverse(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    api.put(
        f"/api/daily/{session_id}/notes",
        json={
            "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
            "homework": "기출 풀어오기",
            "teacher_note": "전달 사항",
        },
    )

    api.put(
        f"/api/daily/{session_id}/records",
        json={
            "records": [
                {
                    "student_id": klass["student_ids"][0],
                    "attendance_status": "late",
                    "attendance_reason": "버스 지연",
                    "homework_grade": "B",
                }
            ]
        },
    )

    body = _daily(api, klass)
    assert body["session"]["homework"] == "기출 풀어오기"
    assert body["session"]["progress"] == [{"period": 1, "content": "2024 광문고 기출 시행"}]
    assert body["records"][0]["attendance_status"] == "late"
    assert body["records"][0]["homework_grade"] == "B"

    api.put(f"/api/daily/{session_id}/notes", json={"teacher_note": "다른 전달 사항"})

    body = _daily(api, klass)
    assert body["records"][0]["attendance_status"] == "late"
    assert body["records"][0]["attendance_reason"] == "버스 지연"
    assert body["session"]["teacher_note"] == "다른 전달 사항"


def test_recheck_is_saved_immediately_without_the_bulk_save(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    student_id = klass["student_ids"][1]

    response = api.put(
        f"/api/daily/{session_id}/records/{student_id}/recheck", json={"result": "pass"}
    )

    assert response.status_code == 200
    body = _daily(api, klass)
    assert body["records"][1]["recheck_result"] == "pass"
    assert body["records"][1]["attendance_status"] == "unchecked"


def test_class_test_average_is_computed_from_saved_scores(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    api.put(f"/api/daily/{session_id}/notes", json={"test_name": "4차연합고사", "test_max_score": 100})

    api.put(
        f"/api/daily/{session_id}/records",
        json={
            "records": [
                {"student_id": student_id, "test_score_num": score}
                for student_id, score in zip(klass["student_ids"], [78, 72, 65])
            ]
        },
    )

    summary = _daily(api, klass)["summary"]
    assert summary["test_average"] == 71.7
    assert summary["test_count"] == 3


def test_attendance_counts_present_late_and_early_leave(api, klass):
    session_id = _daily(api, klass)["session"]["id"]

    api.put(
        f"/api/daily/{session_id}/records",
        json={
            "records": [
                {"student_id": klass["student_ids"][0], "attendance_status": "present"},
                {"student_id": klass["student_ids"][1], "attendance_status": "late"},
                {"student_id": klass["student_ids"][2], "attendance_status": "absent"},
            ]
        },
    )

    assert _daily(api, klass)["summary"]["attending"] == 2


def test_teacher_cannot_touch_daily_records_of_another_class(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": DATE}
    ).status_code == 403
    assert api.put(f"/api/daily/{session_id}/notes", json={"homework": "x"}).status_code == 403
