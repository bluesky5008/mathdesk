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
