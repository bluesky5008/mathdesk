PREV_DATE = "2026-09-16"
DATE = "2026-09-18"


def _daily(api, class_id, on=DATE):
    return api.get("/api/daily", params={"class_id": class_id, "date": on}).json()


def _records(api, session_id, items):
    return api.put(f"/api/daily/{session_id}/records", json={"records": items})


def test_attendance_toggles_back_to_unchecked(api, klass):
    session_id = _daily(api, klass["class_id"])["session"]["id"]
    student_id = klass["student_ids"][0]

    _records(api, session_id, [{"student_id": student_id, "attendance_status": "present"}])
    assert _daily(api, klass["class_id"])["records"][0]["attendance_status"] == "present"

    _records(api, session_id, [{"student_id": student_id, "attendance_status": "unchecked"}])
    assert _daily(api, klass["class_id"])["records"][0]["attendance_status"] == "unchecked"


def test_confirmed_attendance_is_locked_until_unlocked(api, klass):
    session_id = _daily(api, klass["class_id"])["session"]["id"]
    student_id = klass["student_ids"][0]
    _records(api, session_id, [{"student_id": student_id, "attendance_status": "present"}])

    confirmed = api.post(f"/api/daily/{session_id}/attendance/confirm")
    assert confirmed.status_code == 200
    assert confirmed.json()["session"]["attendance_confirmed_at"] is not None

    blocked = _records(api, session_id, [{"student_id": student_id, "attendance_status": "absent"}])
    assert blocked.status_code == 409
    assert _daily(api, klass["class_id"])["records"][0]["attendance_status"] == "present"

    assert api.post(f"/api/daily/{session_id}/attendance/unlock").status_code == 200
    assert _records(
        api, session_id, [{"student_id": student_id, "attendance_status": "absent"}]
    ).status_code == 200
    assert _daily(api, klass["class_id"])["records"][0]["attendance_status"] == "absent"


def test_grades_stay_editable_while_attendance_is_locked(api, klass):
    session_id = _daily(api, klass["class_id"])["session"]["id"]
    student_id = klass["student_ids"][0]
    api.post(f"/api/daily/{session_id}/attendance/confirm")

    response = _records(api, session_id, [{"student_id": student_id, "homework_grade": "A"}])

    assert response.status_code == 200
    assert _daily(api, klass["class_id"])["records"][0]["homework_grade"] == "A"


def test_confirm_and_unlock_are_audited(api, klass, scalar):
    session_id = _daily(api, klass["class_id"])["session"]["id"]

    api.post(f"/api/daily/{session_id}/attendance/confirm")
    api.post(f"/api/daily/{session_id}/attendance/unlock")

    actions = scalar(
        "SELECT string_agg(action, ',' ORDER BY id) FROM audit_log WHERE actor_id IS NOT NULL"
    )
    assert actions == "attendance.confirm,attendance.unlock"


def test_recheck_target_comes_from_the_previous_session_grade(api, klass):
    previous_id = _daily(api, klass["class_id"], PREV_DATE)["session"]["id"]
    below, above = klass["student_ids"][0], klass["student_ids"][1]
    _records(
        api,
        previous_id,
        [
            {"student_id": below, "homework_grade": "B"},
            {"student_id": above, "homework_grade": "A"},
        ],
    )

    records = {row["student_id"]: row for row in _daily(api, klass["class_id"])["records"]}

    assert records[below]["recheck"] == {
        "target": True,
        "prev_grade": "B",
        "prev_date": PREV_DATE,
        "result": None,
    }
    assert records[above]["recheck"]["target"] is False
    assert records[klass["student_ids"][2]]["recheck"]["prev_grade"] is None


def test_recheck_result_is_saved_immediately(api, klass):
    session_id = _daily(api, klass["class_id"])["session"]["id"]
    student_id = klass["student_ids"][1]

    api.put(f"/api/daily/{session_id}/records/{student_id}/recheck", json={"result": "pass"})

    records = {row["student_id"]: row for row in _daily(api, klass["class_id"])["records"]}
    assert records[student_id]["recheck"]["result"] == "pass"
    assert records[student_id]["attendance_status"] == "unchecked"
