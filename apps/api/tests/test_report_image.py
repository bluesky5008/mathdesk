import io

from PIL import Image

from mathdesk.report import CARD_WIDTH, SCALE

DATE = "2026-09-18"


def _prepare(api, klass):
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": DATE}
    ).json()["session"]["id"]
    api.put(
        f"/api/daily/{session_id}/notes",
        json={
            "progress": [{"period": 1, "content": "2024 광문고 기출 시행"}],
            "homework": "기출 풀어오기",
            "test_name": "4차연합고사",
        },
    )
    api.put(
        f"/api/daily/{session_id}/records",
        json={
            "records": [
                {
                    "student_id": klass["student_ids"][0],
                    "attendance_status": "present",
                    "homework_grade": "B",
                    "test_score_num": 78,
                }
            ]
        },
    )
    return session_id, klass["student_ids"][0]


def test_report_endpoint_returns_a_png_image(api, klass):
    session_id, student_id = _prepare(api, klass)

    response = api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": student_id},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    image = Image.open(io.BytesIO(response.content))
    assert image.format == "PNG"
    # 레이아웃은 CSS 픽셀 760이고 2배로 촬영한다. 카톡으로 받은 카드를 폰에서 확대해
    # 보는 일이 흔해 1배는 흐리다([ADR-011]).
    assert image.width == CARD_WIDTH * SCALE
    assert image.height > 300


def test_report_image_changes_when_the_message_changes(api, klass):
    session_id, student_id = _prepare(api, klass)
    params = {"session_id": session_id, "student_id": student_id}
    before = api.get("/api/messages/report-image", params=params).content

    api.put(
        f"/api/daily/{session_id}/notes", json={"homework": "완전히 다른 과제로 교체"}
    )
    after = api.get("/api/messages/report-image", params=params).content

    assert before != after


def test_report_response_is_never_cached(api, klass):
    """CDN이 인증된 학생 리포트를 캐시하면 URL만으로 열람할 수 있게 된다."""
    session_id, student_id = _prepare(api, klass)

    response = api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": student_id},
    )

    assert "no-store" in response.headers["cache-control"]


def test_api_responses_are_never_cached(api, klass):
    assert "no-store" in api.get("/api/students").headers["cache-control"]
    assert "no-store" in api.get("/api/health").headers["cache-control"]


def test_report_requires_authentication(api, klass):
    session_id, student_id = _prepare(api, klass)
    api.post("/api/auth/logout")

    response = api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": student_id},
    )

    assert response.status_code == 401


def test_report_respects_class_scope(api, klass):
    session_id, student_id = _prepare(api, klass)
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    response = api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": student_id},
    )

    assert response.status_code == 403

