from datetime import date

import pytest

from mathdesk.messaging import MessageContext, render_daily_message

FULL = MessageContext(
    student_name="고주연",
    campus_name="전병훈 수학학원",
    teacher_name="홍성윤",
    session_date=date(2026, 9, 19),
    attendance="present",
    progress=[(1, "학교프린트 변형문제 방탈출 테스트"), (2, "학교프린트 변형문제 해설")],
    homework_grade="B",
    grade_comment="숙제는 대부분 완료했으나 오답이 다소 많아 추가적인 복습이 필요합니다.",
    test_name="4차연합고사",
    test_score="78",
    class_average=71.6,
    homework="1. 학교 기출 3개년 풀어오기",
    video_url="https://youtu.be/F3jgRW6-kEs",
)


def test_full_message_contains_every_section():
    body = render_daily_message(FULL)

    assert body.startswith("**고주연학생 학습피드백**")
    assert "전병훈 수학학원 홍성윤T입니다." in body
    assert "9월 19일(토) 수업 내용 및 과제피드백 안내드립니다." in body
    for section in ("■ 출결", "■ 수업진도", "■ 과제피드백", "■ 테스트", "■ 오늘의 과제", "■ 수업 영상 링크"):
        assert section in body


def test_sections_without_data_are_omitted():
    body = render_daily_message(
        FULL.model_copy(update={"test_name": None, "test_score": None, "video_url": None})
    )

    assert "■ 테스트" not in body
    assert "■ 수업 영상 링크" not in body
    assert "■ 과제피드백" in body


def test_attendance_and_grade_are_rendered_in_korean():
    body = render_daily_message(FULL)

    assert "■ 출결: 출석" in body
    assert "■ 과제피드백: B" in body
    assert "숙제는 대부분 완료했으나" in body


def test_progress_lines_are_numbered_by_period():
    body = render_daily_message(FULL)

    assert "[1교시] 학교프린트 변형문제 방탈출 테스트" in body
    assert "[2교시] 학교프린트 변형문제 해설" in body


def test_test_section_shows_score_and_class_average():
    body = render_daily_message(FULL)

    assert "■ 테스트: 4차연합고사" in body
    assert "학생점수: 78점" in body
    assert "반평균: 71.6점" in body


def test_grade_without_a_configured_comment_still_renders_the_grade():
    body = render_daily_message(FULL.model_copy(update={"grade_comment": None}))

    assert "■ 과제피드백: B" in body
    assert "숙제는" not in body


@pytest.mark.parametrize("attendance", ["unchecked", None])
def test_unchecked_attendance_omits_the_section(attendance):
    body = render_daily_message(FULL.model_copy(update={"attendance": attendance}))

    assert "■ 출결" not in body
