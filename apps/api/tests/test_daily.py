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
