"""학생별 정보 카드(DCR-021 / AC-47) — 템플릿 계약과 PNG 엔드포인트."""

import io
import re
from datetime import date
from decimal import Decimal

import pytest
from PIL import Image

from mathdesk.daily import HistoryOut, HistoryRow, RecheckOut
from mathdesk.report import HISTORY_WIDTH, SCALE, render_history_html

DATE = "2026-09-18"


@pytest.fixture
def history() -> HistoryOut:
    return HistoryOut(
        student={"id": 12, "name": "김나윤"},
        klass={"id": 3, "name": "고2 윤B"},
        rows=[
            HistoryRow(
                date=date(2026, 9, 16),
                attendance_status="unchecked",
                attendance_reason=None,
                recheck=RecheckOut(target=False, prev_grade=None, prev_date=None, result=None),
                homework_grade=None,
                test_name=None,
                test_score_num=None,
                class_average=None,
                comment=None,
            ),
            HistoryRow(
                date=date(2026, 9, 14),
                attendance_status="late",
                attendance_reason="버스 지연",
                recheck=RecheckOut(target=True, prev_grade="B", prev_date=date(2026, 9, 9), result="pass"),
                homework_grade="A",
                test_name="4차연합고사",
                test_score_num=Decimal("78.00"),
                class_average=72.0,
                comment="<b>풀이</b>가 깔끔해졌어요",
            ),
        ],
    )


def test_card_shows_the_header_summary_and_every_row_value(history):
    html = render_history_html(history, to=date(2026, 9, 30), campus_name="한영수학")

    for text in (
        "한영수학", "김나윤 학습 기록", "고2 윤B · 2026-09-30까지 최근 2회",
        "출석", "1 / 2회", "테스트 평균", "78점 (1회)",
        "09/16(수)", "미확인", "09/14(월)", "지각", "버스 지연", "직전 B · 09/09", "합격",
        ">A<", "4차연합고사", "78 / 72",
    ):
        assert text in html, text
    assert "&lt;b&gt;풀이&lt;/b&gt;가 깔끔해졌어요" in html
    assert "<b>풀이</b>" not in html
    assert html.index("09/16(수)") < html.index("09/14(월)")
    assert f"width: {HISTORY_WIDTH}px" in html


def test_card_without_rows_says_so(history):
    html = render_history_html(history.model_copy(update={"rows": []}), to=date(2026, 9, 30), campus_name="한영수학")

    assert "선택한 날짜까지 기록이 있는 수업이 없습니다" in html
    assert "0 / 0회" in html
    assert "<table" not in html


def test_card_takes_the_brand_colour_but_not_the_web_theme(history):
    html = render_history_html(history, to=date(2026, 9, 30), campus_name="한영수학", brand_colour="#123456")

    assert "--md-color-brand: #123456" in html
    # 토큰 파일에는 테마 선택자가 있다. 카드가 테마를 적용하는지는 스타일을 뺀 마크업에서 본다
    assert "data-theme" not in re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    with pytest.raises(ValueError):
        render_history_html(history, to=date(2026, 9, 30), campus_name="한영수학", brand_colour="red; }")


def _prepare(api, klass):
    session_id = api.get("/api/daily", params={"class_id": klass["class_id"], "date": DATE}).json()["session"]["id"]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": klass["student_ids"][0], "attendance_status": "present", "test_score_num": 78}]},
    )
    return {"class_id": klass["class_id"], "student_id": klass["student_ids"][0], "to": DATE}


def test_history_image_endpoint_returns_a_wide_png(api, klass):
    response = api.get("/api/daily/history-image", params=_prepare(api, klass))

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    image = Image.open(io.BytesIO(response.content))
    assert image.width == HISTORY_WIDTH * SCALE
    assert image.height > 300


def test_history_image_respects_login_and_class_scope(api, klass):
    params = _prepare(api, klass)
    api.post("/api/auth/logout")
    assert api.get("/api/daily/history-image", params=params).status_code == 401

    api.sign_in("teacher_a")
    assert api.get("/api/daily/history-image", params=params).status_code == 403
