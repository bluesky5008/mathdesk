DATE = "2026-09-18"


def _session(api, class_id, date=DATE):
    return api.get("/api/daily", params={"class_id": class_id, "date": date}).json()["session"]["id"]


def test_preview_merges_session_and_student_records(api, klass):
    session_id = _session(api, klass["class_id"])
    student_id = klass["student_ids"][0]
    api.put(
        f"/api/daily/{session_id}/notes",
        json={
            "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
            "homework": "기출 풀어오기",
            "video_url": "https://youtu.be/abc",
            "test_name": "4차연합고사",
        },
    )
    api.put(
        f"/api/daily/{session_id}/records",
        json={
            "records": [
                {"student_id": student_id, "attendance_status": "present",
                 "homework_grade": "B", "test_score_num": 78},
                {"student_id": klass["student_ids"][1], "test_score_num": 72},
            ]
        },
    )

    body = api.get(
        "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
    ).json()["body"]

    assert "학습피드백" in body
    assert "[1교시] 2024 광문고 기출 시행" in body
    assert "■ 과제피드백: B" in body
    assert "학생점수: 78점" in body
    assert "반평균: 75.0점" in body


def test_editing_a_grade_comment_changes_the_preview(api, klass):
    session_id = _session(api, klass["class_id"])
    student_id = klass["student_ids"][0]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": student_id, "homework_grade": "B"}]},
    )

    api.put(
        "/api/messages/grade-comments",
        json={"comments": [{"grade": "B", "comment_text": "복습이 필요합니다."}]},
    )

    body = api.get(
        "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
    ).json()["body"]
    assert "복습이 필요합니다." in body

    api.put(
        "/api/messages/grade-comments",
        json={"comments": [{"grade": "B", "comment_text": "많이 좋아졌습니다."}]},
    )

    updated = api.get(
        "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
    ).json()["body"]
    assert "많이 좋아졌습니다." in updated
    assert "복습이 필요합니다." not in updated


def test_teacher_cannot_preview_another_class(api, klass):
    session_id = _session(api, klass["class_id"])
    student_id = klass["student_ids"][0]
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    response = api.get(
        "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
    )

    assert response.status_code == 403


def test_two_students_share_the_common_part_and_get_their_own_comment(api, klass):
    """DCR-017 / AC-43 ②: 공통(진도·과제·영상·선생님 코멘트) 아래에 학생별 코멘트가 붙는다."""
    session_id = _session(api, klass["class_id"])
    first, second, _ = klass["student_ids"]
    api.put(
        f"/api/daily/{session_id}/notes",
        json={
            "progress": [{"period": 1, "content": "이차부등식"}],
            "homework": "교재 10p",
            "teacher_note": "토요일 보충 있습니다.",
        },
    )
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [
            {"student_id": first, "attendance_status": "present", "comment": "잘했어요."},
            {"student_id": second, "attendance_status": "late", "comment": "지각 주의."},
        ]},
    )

    def preview(student_id):
        return api.get(
            "/api/messages/preview", params={"session_id": session_id, "student_id": student_id}
        ).json()["body"]

    one, two = preview(first), preview(second)
    common = lambda body: body[body.index("■ 수업진도"):body.index("■ 출결")]  # noqa: E731
    assert common(one) == common(two)
    assert "■ 선생님 코멘트\n토요일 보충 있습니다." in common(one)
    assert one.endswith("■ 개별 코멘트\n잘했어요.")
    assert two.endswith("■ 개별 코멘트\n지각 주의.")
