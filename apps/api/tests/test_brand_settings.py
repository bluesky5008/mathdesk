"""학원 브랜드 설정 — FR-40 / AC-30 (VER-29).

학원명은 `campus.name`을 단일 소스로 쓰고, 로고와 시그니처 색만 `integration_setting`에 둔다.
같은 사실을 두 곳에 두면 갈라진다. 둘 다 민감값이 아니므로 평문으로 저장한다(DES-20은
민감값만 암호화하도록 규정한다).
"""

import io

from PIL import Image

LOGO = "data:image/png;base64,iVBORw0KGgo="
PINK = "#C3457F"


def test_brand_defaults_to_the_campus_name_without_a_logo_or_colour(api, klass):
    brand = api.get("/api/settings/brand").json()

    assert brand["campus_name"]
    assert brand["logo_data_url"] is None
    assert brand["brand_colour"] is None


def test_director_can_set_and_read_back_the_brand(api, klass):
    api.put(
        "/api/settings/brand",
        json={"campus_name": "전병훈 수학학원 고등관", "brand_colour": PINK, "logo_data_url": LOGO},
    )

    brand = api.get("/api/settings/brand").json()
    assert brand["campus_name"] == "전병훈 수학학원 고등관"
    assert brand["brand_colour"] == PINK
    assert brand["logo_data_url"] == LOGO


def test_brand_colour_must_be_a_hex_colour(api, klass):
    response = api.put(
        "/api/settings/brand",
        json={"campus_name": "한영수학", "brand_colour": "red; } body { display:none }"},
    )

    assert response.status_code == 422


def test_teachers_cannot_change_the_brand(api, klass):
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    response = api.put("/api/settings/brand", json={"campus_name": "몰래 바꾼 이름"})

    assert response.status_code == 403


def _report(api, klass):
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": "2026-09-18"}
    ).json()["session"]["id"]
    return api.get(
        "/api/messages/report-image",
        params={"session_id": session_id, "student_id": klass["student_ids"][0]},
    ).content


def test_the_report_card_reflects_the_signature_colour(api, klass):
    """AC-30 — 브랜드 설정을 지정하면 카드에 시그니처 색이 반영된다."""
    before = _report(api, klass)

    api.put("/api/settings/brand", json={"campus_name": "한영수학", "brand_colour": PINK})
    after = _report(api, klass)

    assert before != after
    # 헤더 띠가 시그니처 색이어야 한다. 카드 상단 여백(--md-space-5 × 2배) 바로 아래를 본다
    image = Image.open(io.BytesIO(after)).convert("RGB")
    assert image.getpixel((image.width // 2, 60)) == (195, 69, 127)


def test_the_report_card_reflects_the_academy_name(api, klass):
    api.put("/api/settings/brand", json={"campus_name": "전병훈 수학학원 고등관"})

    assert api.get("/api/settings/brand").json()["campus_name"] == "전병훈 수학학원 고등관"
    # 카드 본문에도 반영된다
    session_id = api.get(
        "/api/daily", params={"class_id": klass["class_id"], "date": "2026-09-18"}
    ).json()["session"]["id"]
    preview = api.get(
        "/api/messages/preview",
        params={"session_id": session_id, "student_id": klass["student_ids"][0]},
    ).json()
    assert "전병훈 수학학원 고등관" in preview["body"]
