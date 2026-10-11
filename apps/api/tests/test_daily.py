DATE = "2026-09-18"


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
    assert body["records"][1]["recheck"]["result"] == "pass"
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


# ── DCR-017 / AC-43: 학생별 코멘트 ─────────────────────────────────────


def _comments(api, klass):
    return [record["comment"] for record in _daily(api, klass)["records"]]


def test_each_student_keeps_their_own_comment(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    first, second, _ = klass["student_ids"]

    saved = api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [
            {"student_id": first, "comment": "풀이 과정이 깔끔해졌어요."},
            {"student_id": second, "comment": "계산 실수를 줄여 봅시다."},
        ]},
    )

    assert saved.status_code == 200
    assert _comments(api, klass) == ["풀이 과정이 깔끔해졌어요.", "계산 실수를 줄여 봅시다.", None]


def test_a_comment_is_kept_when_other_fields_are_saved_and_cleared_when_emptied(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    first = klass["student_ids"][0]
    url = f"/api/daily/{session_id}/records"
    api.put(url, json={"records": [{"student_id": first, "comment": "좋아요"}]})

    api.put(url, json={"records": [{"student_id": first, "homework_grade": "A"}]})
    assert _comments(api, klass)[0] == "좋아요"

    api.put(url, json={"records": [{"student_id": first, "comment": "  "}]})
    assert _comments(api, klass)[0] is None  # 공백뿐이면 빈 구획이 문자에 나가지 않게 비운다

    api.put(url, json={"records": [{"student_id": first, "comment": " 잘했어요 "}]})
    assert _comments(api, klass)[0] == "잘했어요"


def test_a_comment_longer_than_500_characters_is_rejected(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    first = klass["student_ids"][0]

    response = api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": first, "comment": "가" * 501}]},
    )

    assert response.status_code == 422
    assert _comments(api, klass)[0] is None


def test_a_comment_can_be_saved_after_attendance_is_confirmed(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    api.post(f"/api/daily/{session_id}/attendance/confirm")

    response = api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": klass["student_ids"][0], "comment": "확정 뒤 코멘트"}]},
    )

    assert response.status_code == 200
    assert _comments(api, klass)[0] == "확정 뒤 코멘트"


def test_test_name_longer_than_100_characters_is_rejected(api, klass):
    """DCR-019 / AC-44 ⑥: 테스트명은 문자·카드에 그대로 나가는 값이라 100자 상한."""
    session_id = _daily(api, klass)["session"]["id"]

    response = api.put(f"/api/daily/{session_id}/notes", json={"test_name": "가" * 101})

    assert response.status_code == 422
    assert api.put(f"/api/daily/{session_id}/notes", json={"test_name": "가" * 100}).status_code == 200


def test_blank_test_name_is_stored_as_null(api, klass):
    session_id = _daily(api, klass)["session"]["id"]
    api.put(f"/api/daily/{session_id}/notes", json={"test_name": "4차연합고사"})

    api.put(f"/api/daily/{session_id}/notes", json={"test_name": "  "})

    assert _daily(api, klass)["session"]["test_name"] is None


# ── DCR-020 / AC-45·AC-46: 수업일 달력과 학생별 이력 ────────────────────────


def _session_on(api, klass, on):
    return api.get("/api/daily", params={"class_id": klass["class_id"], "date": on}).json()[
        "session"
    ]["id"]


def _save(api, session_id, student_id, **fields):
    response = api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": student_id, **fields}]},
    )
    assert response.status_code == 200, response.text


def _calendar(api, klass, month="2026-09"):
    return api.get("/api/daily/calendar", params={"class_id": klass["class_id"], "month": month})


def _history(api, klass, student_id, **params):
    return api.get(
        "/api/daily/history",
        params={"class_id": klass["class_id"], "student_id": student_id, "to": "2026-09-30", **params},
    )


def test_calendar_lists_only_days_with_records(api, klass):
    first = klass["student_ids"][0]
    _save(api, _session_on(api, klass, "2026-09-14"), first, attendance_status="present")
    api.put(f"/api/daily/{_session_on(api, klass, '2026-09-16')}/notes", json={"homework": "복습"})
    api.post(f"/api/daily/{_session_on(api, klass, '2026-09-21')}/attendance/confirm")
    _session_on(api, klass, "2026-09-18")  # 조회만 한 날
    _save(api, _session_on(api, klass, "2026-10-05"), first, attendance_status="present")

    response = _calendar(api, klass)

    assert response.status_code == 200
    assert response.json() == {"recorded_dates": ["2026-09-14", "2026-09-16", "2026-09-21"]}


def test_calendar_rejects_a_malformed_month_and_another_teachers_class(api, klass):
    assert _calendar(api, klass, month="2026-9").status_code == 422

    api.post("/api/auth/logout")
    api.sign_in("teacher_a")
    assert _calendar(api, klass).status_code == 403


def test_history_lists_recorded_sessions_newest_first_with_empty_rows(api, klass):
    first, second, _ = klass["student_ids"]
    monday = _session_on(api, klass, "2026-09-14")
    _save(api, monday, first, attendance_status="late", attendance_reason="버스 지연",
          homework_grade="B", test_score_num=78, comment="좋아요")
    _save(api, monday, second, test_score_num=66)
    api.put(f"/api/daily/{monday}/notes", json={"test_name": "4차연합고사"})
    wednesday = _session_on(api, klass, "2026-09-16")
    _save(api, wednesday, second, homework_grade="A")  # 첫 학생은 기록 없음
    _session_on(api, klass, "2026-09-18")  # 조회만 한 날
    _save(api, _session_on(api, klass, "2026-10-02"), first, attendance_status="present")  # to 이후

    body = _history(api, klass, first).json()

    assert body["student"] == {"id": first, "name": "김나윤"}
    assert body["klass"]["id"] == klass["class_id"]
    assert [row["date"] for row in body["rows"]] == ["2026-09-16", "2026-09-14"]
    newest, oldest = body["rows"]
    assert oldest["attendance_status"] == "late"
    assert oldest["attendance_reason"] == "버스 지연"
    assert oldest["homework_grade"] == "B"
    assert oldest["test_name"] == "4차연합고사"
    assert float(oldest["test_score_num"]) == 78
    assert oldest["class_average"] == 72.0
    assert oldest["comment"] == "좋아요"
    assert newest["attendance_status"] == "unchecked"
    assert newest["homework_grade"] is None
    assert newest["test_score_num"] is None
    assert newest["class_average"] is None
    assert newest["comment"] is None


def test_history_computes_recheck_for_each_date(api, klass):
    first = klass["student_ids"][0]
    _save(api, _session_on(api, klass, "2026-09-14"), first, homework_grade="B")
    wednesday = _session_on(api, klass, "2026-09-16")
    _save(api, wednesday, first, homework_grade="A")
    api.put(f"/api/daily/{wednesday}/records/{first}/recheck", json={"result": "pass"})
    _save(api, _session_on(api, klass, "2026-09-21"), first, attendance_status="present")

    rows = {row["date"]: row["recheck"] for row in _history(api, klass, first).json()["rows"]}

    assert rows["2026-09-14"] == {"target": False, "prev_grade": None, "prev_date": None, "result": None}
    assert rows["2026-09-16"] == {
        "target": True, "prev_grade": "B", "prev_date": "2026-09-14", "result": "pass",
    }
    assert rows["2026-09-21"]["target"] is False
    assert rows["2026-09-21"]["prev_grade"] == "A"


def test_history_skips_days_outside_enrollment_and_truncates_to_limit(api, klass):
    first = klass["student_ids"][0]
    # 배정 시작(2026-03-02) 전의 반 메모만 있는 수업
    api.put(f"/api/daily/{_session_on(api, klass, '2026-02-25')}/notes", json={"homework": "x"})
    for day in ("2026-09-07", "2026-09-09", "2026-09-14"):
        _save(api, _session_on(api, klass, day), first, attendance_status="present")

    assert [row["date"] for row in _history(api, klass, first).json()["rows"]] == [
        "2026-09-14", "2026-09-09", "2026-09-07",
    ]
    assert [row["date"] for row in _history(api, klass, first, limit=2).json()["rows"]] == [
        "2026-09-14", "2026-09-09",
    ]
    assert _history(api, klass, first, limit=51).status_code == 422


def test_history_is_refused_for_an_unenrolled_student_and_another_teacher(api, klass):
    outsider = api.post("/api/students", json={"name": "박외부", "omr_number": "10000900"}).json()["id"]
    assert _history(api, klass, outsider).status_code == 403

    api.post("/api/auth/logout")
    api.sign_in("teacher_a")
    assert _history(api, klass, klass["student_ids"][0]).status_code == 403
