"""TASK-36 — 채점 엔진과 문항별 통계(FR-36, AC-25, DES-17).

판독은 TASK-34·35에서 검사했으므로 여기서는 `omr_scan` 행을 직접 넣어 채점만 본다.
"""
import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.models import AuditLog, ExamAnswer, ExamAttempt, ExamQuestion, OmrScan

N = 30
ODD = [1] * 15 + [10] * 7 + [2] * 6 + [100, 200]  # 1~15:1, 16~22:10, 23~28:2, 29:100, 30:200
EVEN = [5] * 15 + [20] * 7 + [4] * 6 + [300, 400]


def answers(key, wrong=()):
    """정답표대로 칠하고 `wrong` 번호만 틀리게(객관식은 다른 번호, 단답형은 +1) 칠한 답."""
    out = {}
    for q, value in enumerate(key, start=1):
        out[str(q)] = (value % 5 + 1 if value <= 5 else value + 1) if q in wrong else value
    return out


def _db(database_url, body):
    async def run():
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await body(session)
        finally:
            await engine.dispose()

    return asyncio.run(run())


@pytest.fixture
def exam(api, migrated_database):
    """정답표 2벌이 있는 30문항 시험과 학생 넷. 스캔은 `add_scan`으로 넣는다."""
    api.sign_in("director_a")
    klass = api.post("/api/classes", json={"name": "고3 윤A", "grade": "고3"}).json()["id"]
    students = {}
    for i, name in enumerate(("가", "나", "다", "라"), start=1):
        students[name] = api.post("/api/students", json={"name": name, "omr_number": f"1000{i:02d}00"}).json()["id"]
        api.post(f"/api/classes/{klass}/enrollments", json={"student_id": students[name], "start_date": "2026-03-02"})
    created = api.post("/api/exams", json={"name": "9월 모의", "class_id": klass, "exam_date": "2026-09-19"}).json()
    response = api.patch(
        f"/api/exams/{created['id']}",
        json={"question_count": N, "max_score": 100, "answer_key_odd": ODD, "answer_key_even": EVEN},
    )
    assert response.status_code == 200, response.text

    def add_scan(student, form="odd", wrong=(), status="read", flags=(), page=None):
        async def body(session):
            scan = OmrScan(
                exam_id=created["id"], page_no=page or len(pages) + 1, status=status,
                matched_student_id=students[student] if student else None,
                read_payload={"template_id": "ksat-2027-math", "exam_number": None, "form": form,
                              "absent": False, "answers": answers(ODD if form == "odd" else EVEN, wrong)},
                flags=list(flags),
            )
            session.add(scan)
            await session.commit()
            return scan.id

        scan_id = _db(migrated_database, body)
        pages.append(scan_id)
        return scan_id

    pages: list[int] = []
    return {"id": created["id"], "class_id": klass, "students": students, "add_scan": add_scan}


def _apply(api, exam):
    return api.post(f"/api/exams/{exam['id']}/omr/apply")


def _results(api, exam):
    return api.get(f"/api/exams/{exam['id']}/results").json()


def _scores(api, exam) -> dict[str, float]:
    return {row["student"]["name"]: row["score"] for row in _results(api, exam)["students"]}


def _set_points(migrated_database, exam_id, points):
    async def body(session):
        for no, value in enumerate(points, start=1):
            session.add(ExamQuestion(exam_id=exam_id, no=no, points=value, unit="수열" if no <= 10 else "미분"))
        await session.commit()

    _db(migrated_database, body)


def _count(migrated_database, model) -> int:
    return _db(migrated_database, lambda s: s.scalar(select(func.count()).select_from(model)))


# ── 반영 게이트(AC-25 전반부) ─────────────────────────────────────────


def test_scans_waiting_for_review_are_not_scored(api, exam):
    exam["add_scan"]("가")
    exam["add_scan"]("나", wrong=(3,))
    exam["add_scan"]("다", status="needs_review", flags=[{"field": "3", "code": "multi"}])

    response = _apply(api, exam)

    assert response.status_code == 200, response.text
    assert response.json()["applied"] == 2
    assert response.json()["waiting"] == 1
    assert set(_scores(api, exam)) == {"가", "나"}


# ── 점수(FR-36) ────────────────────────────────────────────────────────


def test_score_is_the_sum_of_points_for_correct_answers(api, exam, migrated_database):
    _set_points(migrated_database, exam["id"], [2] * 4 + [3] * 12 + [4] * 14)  # 1~4번 2점, 5~16번 3점, 17~30번 4점 = 100
    exam["add_scan"]("가")
    exam["add_scan"]("나", wrong=(1, 30))  # 2점 + 4점

    _apply(api, exam)

    assert _scores(api, exam) == {"가": 100, "나": 94}
    assert _results(api, exam)["score_basis"] == "points"


def test_without_points_the_score_is_the_share_of_correct_answers(api, exam):
    exam["add_scan"]("가", wrong=(1, 2, 3))

    _apply(api, exam)

    assert _scores(api, exam) == {"가": 90}
    assert _results(api, exam)["score_basis"] == "ratio"


def test_each_form_is_graded_against_its_own_answer_key(api, exam):
    exam["add_scan"]("가", form="odd")
    exam["add_scan"]("나", form="even")

    _apply(api, exam)

    assert _scores(api, exam) == {"가": 100, "나": 100}
    forms = {row["student"]["name"]: row["form"] for row in _results(api, exam)["students"]}
    assert forms == {"가": "odd", "나": "even"}


def test_a_missing_answer_key_for_a_used_form_stops_the_apply(api, exam):
    api.patch(f"/api/exams/{exam['id']}", json={"answer_key_even": None})
    exam["add_scan"]("가", form="even")

    response = _apply(api, exam)

    assert response.status_code == 422
    assert "짝수형" in response.json()["detail"]


# ── 재반영(AC-25 후반부, 멱등) ──────────────────────────────────────────


def test_correcting_an_applied_scan_updates_score_and_question_rate(api, exam):
    exam["add_scan"]("가")
    scan = exam["add_scan"]("나", wrong=(7,))
    _apply(api, exam)
    before = {q["no"]: q["correct_rate"] for q in api.get(f"/api/exams/{exam['id']}/question-stats").json()["questions"]}
    assert before[7] == 50.0

    corrected = api.patch(f"/api/exams/{exam['id']}/omr/scans/{scan}", json={"answers": {"7": 1}})
    assert corrected.json()["status"] == "read"  # 다시 반영해야 한다
    _apply(api, exam)

    after = {q["no"]: q["correct_rate"] for q in api.get(f"/api/exams/{exam['id']}/question-stats").json()["questions"]}
    assert after[7] == 100.0
    assert _scores(api, exam)["나"] == 100


def test_applying_twice_replaces_attempts_and_leaves_an_audit_trail(api, exam, migrated_database):
    exam["add_scan"]("가")
    exam["add_scan"]("나")

    first = _apply(api, exam).json()
    second = _apply(api, exam).json()

    assert (first["applied"], first["replaced"]) == (2, 0)
    assert (second["applied"], second["replaced"]) == (2, 2)
    assert _count(migrated_database, ExamAttempt) == 2
    assert _count(migrated_database, ExamAnswer) == 2 * N
    logs = _db(migrated_database, lambda s: s.scalars(select(AuditLog).where(AuditLog.action == "omr.apply")))
    assert len(list(logs)) == 2


def test_reassigning_a_scan_moves_the_attempt_to_the_new_student(api, exam):
    scan = exam["add_scan"]("가")
    _apply(api, exam)

    api.patch(f"/api/exams/{exam['id']}/omr/scans/{scan}", json={"student_id": exam["students"]["라"]})
    result = _apply(api, exam).json()

    assert result["removed"] == 1
    assert set(_scores(api, exam)) == {"라"}


def test_two_sheets_for_one_student_are_held_back_as_a_conflict(api, exam):
    exam["add_scan"]("가")
    exam["add_scan"]("가", wrong=(1,))
    exam["add_scan"]("나")

    result = _apply(api, exam).json()

    assert result["applied"] == 1
    assert result["conflicts"] == [{"student": {"id": exam["students"]["가"], "name": "가"}, "pages": [1, 2]}]
    assert set(_scores(api, exam)) == {"나"}


# ── 시험 결과와 문항 통계(FR-36, 화면 ④ KPI·탭) ────────────────────────


def test_results_summarize_the_class(api, exam, migrated_database):
    _set_points(migrated_database, exam["id"], [2] * 4 + [3] * 12 + [4] * 14)
    exam["add_scan"]("가")  # 100
    exam["add_scan"]("나", wrong=(1, 2, 16, 17, 18))  # 100 - 2 - 2 - 3 - 4 - 4 = 85
    exam["add_scan"]("다", wrong=(1, 2, 16, 30))  # 100 - 2 - 2 - 3 - 4 = 89
    _apply(api, exam)

    summary = _results(api, exam)["summary"]

    assert summary["attempts"] == 3
    assert summary["enrolled"] == 4
    assert summary["average"] == pytest.approx(91.33, abs=0.01)
    assert (summary["highest"], summary["lowest"]) == (100, 85)
    # 문항 30개 × 3명 중 틀린 답 9개 → 81/90
    assert summary["average_correct_rate"] == pytest.approx(90.0)
    # 1·2·16번이 1/3 정답(33.3%)으로 40% 미만
    assert summary["focus_questions"] == [1, 2, 16]


def test_question_stats_show_rates_choice_spread_and_wrong_rate_by_unit(api, exam, migrated_database):
    _set_points(migrated_database, exam["id"], [3] * 30)
    exam["add_scan"]("가")
    exam["add_scan"]("나", wrong=(1, 11))
    _apply(api, exam)

    stats = api.get(f"/api/exams/{exam['id']}/question-stats").json()

    first = stats["questions"][0]
    assert first == {
        "no": 1, "answer": 1, "answer_even": 5, "correct_rate": 50.0, "choices": {"1": 1, "2": 1},
        "unit": "수열", "sub_type": None, "difficulty": None,
    }
    # 오답률이 높은 단원부터(집중 해설 대상을 먼저 보이게)
    assert stats["units"] == [
        {"unit": "수열", "questions": 10, "wrong_rate": 5.0},
        {"unit": "미분", "questions": 20, "wrong_rate": 2.5},
    ]


def test_teachers_see_results_but_cannot_apply(api, exam):
    exam["add_scan"]("가")
    _apply(api, exam)

    api.sign_in("teacher_a")

    assert api.get(f"/api/exams/{exam['id']}/results").status_code == 200
    assert api.get(f"/api/exams/{exam['id']}/question-stats").status_code == 200
    assert _apply(api, exam).status_code == 403
