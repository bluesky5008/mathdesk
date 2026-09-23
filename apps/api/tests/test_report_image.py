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



def test_short_card_has_no_empty_padding_below(api, klass):
    """내용이 짧은 카드에 빈 배경이 붙으면 안 된다.

    full_page 스크린샷은 뷰포트 높이를 하한으로 잡는다. 기록이 거의 없는 학생의 카드가
    아래쪽 절반이 빈 채로 학부모에게 나가는 일이 실제로 발생했다. 이미지 높이는 내용
    높이와 같아야 하고, 아래 여백은 카드 바깥 패딩 정도에 그쳐야 한다.
    """
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": DATE}
    ).json()["session"]["id"]
    # 기록을 전혀 넣지 않은 학생 — 카드가 머리말과 꼬리말만 갖는다
    student_id = klass["student_ids"][0]

    response = api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": student_id},
    )

    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    pixels = image.load()
    background = pixels[image.width // 2, image.height - 2]
    empty_rows = 0
    for y in range(image.height - 1, -1, -1):
        if all(pixels[x, y] == background for x in range(0, image.width, 40)):
            empty_rows += 1
        else:
            break

    # 바깥 패딩은 --md-space-5(20px) × SCALE. 그 두 배를 넘으면 빈 띠가 붙은 것이다.
    assert empty_rows < 20 * SCALE * 2, f"카드 아래 빈 배경 {empty_rows}px"
