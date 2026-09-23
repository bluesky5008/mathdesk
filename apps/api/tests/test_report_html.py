"""리포트 카드 HTML 템플릿의 계약.

VER-30(카드 측) — 카드는 웹과 같은 토큰 파일을 인라인한다(AC-31 / NFR-18).
ADR-012 — 카드는 웹 테마를 따르지 않는다. :root 라이트 팔레트에 학원 시그니처 색만 얹는다.
"""

import re
from datetime import date

import pytest

from mathdesk.messaging import MessageContext
from mathdesk.report import TOKENS_CSS, render_report_html


@pytest.fixture
def context() -> MessageContext:
    return MessageContext(
        student_name="김나윤",
        campus_name="한영수학",
        teacher_name="윤",
        session_date=date(2026, 9, 18),
        attendance="present",
        progress=[(1, "2024 광문고 기출 시행")],
        homework_grade="B",
        test_name="4차연합고사",
        test_score="78",
        class_average=72.5,
        homework="기출 풀어오기",
    )


def test_card_inlines_the_same_token_file_the_web_uses(context):
    """토큰 파일을 통째로 인라인한다. 값을 베껴 적으면 웹과 갈라진다."""
    html = render_report_html(context)

    assert TOKENS_CSS.strip() in html
    for token in ("--md-color-brand", "--md-text-base", "--md-space-4", "--md-radius-lg"):
        assert token in html


def test_card_does_not_follow_the_web_theme(context):
    """학부모가 받는 자산이 강사 개인 취향에 좌우되면 안 된다(ADR-012 결정 7).

    인라인된 토큰 파일에는 `[data-theme=...]` 팔레트 선택자가 들어 있다. 문제는 그 존재가
    아니라 카드가 테마를 **적용**하는지이므로, 스타일 블록을 뺀 마크업에서만 확인한다.
    """
    markup = re.sub(r"<style>.*?</style>", "", render_report_html(context), flags=re.S)

    assert "data-theme" not in markup


def test_card_shows_the_message_content(context):
    html = render_report_html(context)

    for expected in ("김나윤", "한영수학", "출석", "2024 광문고 기출 시행", "기출 풀어오기", "78"):
        assert expected in html


def test_brand_colour_overrides_only_the_brand_token(context):
    """FR-40 시그니처 색은 --md-color-brand만 덮어쓴다."""
    html = render_report_html(context, brand_colour="#c2185b")

    assert "--md-color-brand: #c2185b" in html
    assert "--md-color-bg: #c2185b" not in html


def test_untrusted_text_is_escaped(context):
    """학생 이름·과제 내용은 사용자 입력이다. 템플릿에 그대로 넣으면 깨지거나 주입된다."""
    context.student_name = "<script>alert(1)</script>"
    html = render_report_html(context)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_brand_colour_must_be_a_colour(context):
    """브랜드 색은 CSS 안으로 들어간다. HTML 이스케이프는 CSS 주입을 막지 못한다.

    FR-40의 설정값은 원장이 넣는 값이지만 그래도 신뢰 경계다. 형식을 강제한다.
    """
    with pytest.raises(ValueError):
        render_report_html(context, brand_colour="red; } body { display: none; }")
    with pytest.raises(ValueError):
        render_report_html(context, brand_colour="url(https://evil.example/x)")

    # 정상 형식은 통과한다
    assert "#C2185B" in render_report_html(context, brand_colour="#C2185B")


# ── 시안 B(컬러 헤더형) 확정에 따른 계약 ──────────────────────────────────

def test_header_text_stays_readable_on_a_bright_brand_colour(context):
    """헤더는 브랜드 색 배경 위에 글자를 얹는다. 밝은 색이면 흰 글씨가 안 읽힌다.

    시그니처 색은 원장이 자유롭게 고르므로(FR-40) 글자색을 색에 맞춰 뒤집어야 한다.
    """
    from mathdesk.report import header_ink

    assert header_ink("#1D4ED8") == "light"   # 진한 파랑 → 흰 글씨
    assert header_ink("#C3457F") == "light"   # 핑크 스킨 → 흰 글씨
    assert header_ink("#FFEB3B") == "dark"    # 밝은 노랑 → 어두운 글씨
    assert header_ink("#FFFFFF") == "dark"


def test_card_without_a_logo_falls_back_to_the_academy_name(context):
    """로고 미설정 시 학원명 텍스트로 대체한다(FR-40)."""
    html = render_report_html(context)

    assert "<img" not in html
    assert escape_ok(html, context.campus_name)


def test_card_shows_the_logo_when_one_is_set(context):
    html = render_report_html(context, logo_data_url="data:image/png;base64,AAAA")

    assert 'src="data:image/png;base64,AAAA"' in html


def test_empty_record_says_so_instead_of_leaving_a_blank_band(context):
    """기록이 없는 학생의 카드가 빈 띠만 남긴 채 학부모에게 나간 일이 있었다."""
    bare = MessageContext(
        student_name="학생01", campus_name="한영수학", teacher_name="윤",
        session_date=date(2026, 9, 23),
    )
    html = render_report_html(bare)

    assert "오늘 기록된 내용이 없습니다" in html


def escape_ok(html: str, text: str) -> bool:
    from html import escape as _e
    return _e(text) in html
