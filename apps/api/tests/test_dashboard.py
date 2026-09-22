import pytest

THIS_WEEK = "2026-09-18"  # 금요일. 주간 범위는 2026-09-14(월)~09-20(일)
EARLIER_THIS_WEEK = "2026-09-16"
LAST_WEEK = "2026-09-11"


@pytest.fixture
def big_class(api):
    api.sign_in("director_a")
    class_id = api.post("/api/classes", json={"name": "고2 윤B", "grade": "고2"}).json()["id"]
    student_ids = []
    for index in range(1, 14):
        student_id = api.post(
            "/api/students", json={"name": f"학생{index:02d}", "omr_number": f"1000{index:02d}00"}
        ).json()["id"]
        api.post(
            f"/api/classes/{class_id}/enrollments",
            json={"student_id": student_id, "start_date": "2026-03-02"},
        )
        student_ids.append(student_id)
    return {"class_id": class_id, "student_ids": student_ids}


def _session(api, class_id, date):
    return api.get("/api/daily", params={"class_id": class_id, "date": date}).json()["session"]["id"]


def _save(api, session_id, records):
    api.put(f"/api/daily/{session_id}/records", json={"records": records})


def _dashboard(api, class_id, date=THIS_WEEK):
    return api.get("/api/dashboard", params={"class_id": class_id, "date": date}).json()


def test_campus_totals_count_enrolled_students_and_active_classes(api, big_class):
    body = _dashboard(api, big_class["class_id"])

    assert body["campus"] == {"enrolled_students": 13, "active_classes": 1}


def test_attendance_shows_attending_over_enrolled(api, big_class):
    session_id = _session(api, big_class["class_id"], THIS_WEEK)
    ids = big_class["student_ids"]
    _save(api, session_id, [
        {"student_id": ids[0], "attendance_status": "present"},
        {"student_id": ids[1], "attendance_status": "present"},
        {"student_id": ids[2], "attendance_status": "late"},
        {"student_id": ids[3], "attendance_status": "early_leave"},
        {"student_id": ids[4], "attendance_status": "absent"},
    ])

    attendance = _dashboard(api, big_class["class_id"])["attendance"]

    assert attendance["attending"] == 4
    assert attendance["enrolled"] == 13


def test_weekly_homework_rate_and_delta_against_last_week(api, big_class):
    ids = big_class["student_ids"]
    last = _session(api, big_class["class_id"], LAST_WEEK)
    _save(api, last, [
        {"student_id": ids[0], "homework_grade": "A"},
        {"student_id": ids[1], "homework_grade": "C"},
    ])  # 지난주 완수율 50%

    this = _session(api, big_class["class_id"], THIS_WEEK)
    _save(api, this, [
        {"student_id": ids[0], "homework_grade": "A"},
        {"student_id": ids[1], "homework_grade": "B"},
        {"student_id": ids[2], "homework_grade": "D"},
        {"student_id": ids[3], "homework_grade": "F"},
    ])  # 금주 완수율 50%, 미제출(F) 1건

    homework = _dashboard(api, big_class["class_id"])["homework"]

    assert homework["completion_rate"] == 50.0
    assert homework["delta_points"] == 0.0
    assert homework["missing"] == 1


def test_weekly_homework_counts_recheck_targets(api, big_class):
    ids = big_class["student_ids"]
    earlier = _session(api, big_class["class_id"], EARLIER_THIS_WEEK)
    _save(api, earlier, [
        {"student_id": ids[0], "homework_grade": "C"},
        {"student_id": ids[1], "homework_grade": "A"},
    ])
    _session(api, big_class["class_id"], THIS_WEEK)

    assert _dashboard(api, big_class["class_id"])["homework"]["recheck_targets"] == 1


def test_weekly_test_summary_reports_n_max_and_min(api, big_class):
    ids = big_class["student_ids"]
    session_id = _session(api, big_class["class_id"], THIS_WEEK)
    _save(api, session_id, [
        {"student_id": ids[0], "test_score_num": 100},
        {"student_id": ids[1], "test_score_num": 100},
        {"student_id": ids[2], "test_score_num": 58},
    ])

    summary = _dashboard(api, big_class["class_id"])["test"]

    assert summary == {"average": 86.0, "count": 3, "max": 100.0, "max_count": 2, "min": 58.0}


def test_empty_week_reports_nulls_instead_of_zero(api, big_class):
    body = _dashboard(api, big_class["class_id"])

    assert body["test"]["average"] is None
    assert body["homework"]["completion_rate"] is None
    assert body["last_session"] is None


def test_last_session_summary_comes_from_the_previous_class_day(api, big_class):
    previous = _session(api, big_class["class_id"], EARLIER_THIS_WEEK)
    api.put(
        f"/api/daily/{previous}/notes",
        json={
            "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
            "homework": "기출 풀어오기",
        },
    )
    _session(api, big_class["class_id"], THIS_WEEK)

    last = _dashboard(api, big_class["class_id"])["last_session"]

    assert last["session_date"] == EARLIER_THIS_WEEK
    assert last["progress"] == [{"period": 1, "content": "2024 광문고 기출 시행"}]
    assert last["homework"] == "기출 풀어오기"
