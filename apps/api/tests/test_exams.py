"""TASK-32 — 시험 등록·문항 확인(FR-29~FR-31)."""
import time
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _wait(api, task_id, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("done", "failed"):
            return task
        time.sleep(0.1)
    raise AssertionError("작업이 끝나지 않았다")


@pytest.fixture
def analyzed(api, tmp_path, monkeypatch):
    """테스트 모드로 분석한 30문항 시험. 7·14·21·28번이 `확인 필요`다."""
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    monkeypatch.delenv("MATHDESK_LLM_PROVIDER", raising=False)
    api.sign_in("director_a")
    upload = api.post(
        "/api/exams/uploads",
        files={"file": ("강K 9회.pdf", (FIXTURES / "exam-30.pdf").read_bytes(), "application/pdf")},
    ).json()
    exam = api.post(
        "/api/exams", json={"name": "강K 9회", "source_file_id": upload["id"], "exam_date": "2026-09-19"}
    ).json()
    assert _wait(api, api.post(f"/api/exams/{exam['id']}/analyze").json()["task_id"])["status"] == "done"
    return exam


KEY = [3, 5, 1, 2, 4] * 3 + [12, 7, 150, 9, 21, 64, 3] + [2, 4, 1, 5, 3, 1] + [18, 240]


def test_exam_details_and_both_answer_keys_are_saved(api, analyzed):
    updated = api.patch(
        f"/api/exams/{analyzed['id']}",
        json={"question_count": 30, "max_score": 100, "answer_key_odd": KEY,
              "answer_key_even": list(reversed(KEY))},
    )

    assert updated.status_code == 200
    body = api.get(f"/api/exams/{analyzed['id']}").json()
    assert body["answer_key_odd"] == KEY
    assert body["answer_key_even"] == list(reversed(KEY))
    assert body["max_score"] == 100


def test_answer_key_must_match_the_question_count(api, analyzed):
    short = api.patch(f"/api/exams/{analyzed['id']}", json={"answer_key_odd": KEY[:29]})
    wild = api.patch(f"/api/exams/{analyzed['id']}", json={"answer_key_odd": KEY[:29] + [1000]})

    assert short.status_code == 422
    assert "30" in short.json()["detail"]
    assert wild.status_code == 422


def test_exam_list_shows_recent_exams_with_their_state(api, analyzed):
    rows = api.get("/api/exams").json()

    assert rows[0]["id"] == analyzed["id"]
    assert rows[0]["question_count"] == 30
    assert rows[0]["needs_review"] == 4
    assert rows[0]["status"] == "draft"


def test_difficulty_counts_follow_the_questions(api, analyzed):
    counts = api.get(f"/api/exams/{analyzed['id']}").json()["difficulty"]

    assert sum(counts.values()) == 30
    assert set(counts) == {"low", "mid", "high", "top"}


def test_editing_a_flagged_question_clears_the_flag(api, analyzed):
    edited = api.patch(
        f"/api/exams/{analyzed['id']}/questions",
        json={"questions": [{"no": 7, "difficulty": "top", "points": 4, "unit": "미분"},
                            {"no": 14}]},  # 14번은 값 그대로 확인만 한다
    )

    assert edited.status_code == 200
    questions = {q["no"]: q for q in api.get(f"/api/exams/{analyzed['id']}/questions").json()}
    assert questions[7]["needs_review"] is False
    assert (questions[7]["difficulty"], questions[7]["points"], questions[7]["unit"]) == ("top", 4, "미분")
    assert questions[14]["needs_review"] is False
    assert questions[21]["needs_review"] is True


def test_exam_cannot_be_confirmed_while_questions_need_review(api, analyzed):
    blocked = api.patch(f"/api/exams/{analyzed['id']}", json={"status": "confirmed"})
    api.patch(
        f"/api/exams/{analyzed['id']}/questions",
        json={"questions": [{"no": n} for n in (7, 14, 21, 28)]},
    )
    confirmed = api.patch(f"/api/exams/{analyzed['id']}", json={"status": "confirmed"})

    assert blocked.status_code == 409
    assert "4" in blocked.json()["detail"]
    assert confirmed.status_code == 200
    assert api.post(f"/api/exams/{analyzed['id']}/analyze").status_code == 409


def test_difficulty_card_is_rendered_as_an_image(api, analyzed):
    card = api.get(f"/api/exams/{analyzed['id']}/difficulty-card")

    assert card.status_code == 200
    assert card.headers["content-type"] == "image/png"
    assert card.content.startswith(b"\x89PNG")


def test_teacher_can_read_but_not_edit_exams(api, analyzed):
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert api.get(f"/api/exams/{analyzed['id']}").status_code == 200
    assert api.patch(f"/api/exams/{analyzed['id']}", json={"max_score": 90}).status_code == 403
    assert api.patch(
        f"/api/exams/{analyzed['id']}/questions", json={"questions": [{"no": 7}]}
    ).status_code == 403
