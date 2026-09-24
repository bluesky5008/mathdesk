"""채점 엔진(DES-17) — OMR 반영, 시험 결과, 문항별 통계(FR-36, AC-25).

반영은 매번 **현재 스캔 상태로 이 시험의 OMR 시도 전체를 다시 계산**한다. 그래서 두 번
눌러도 결과가 같고(멱등), 교정·학생 재지정이 다음 반영에 그대로 들어간다.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import (
    AuditLog,
    Enrollment,
    Exam,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    OmrScan,
    Student,
)
from .scope import CurrentScope, ScopedRepository

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["omr"])

FOCUS_RATE = 40.0  # 정답률이 이보다 낮으면 집중 해설 문항(화면 ④ KPI)
FORM_NAME = {"odd": "홀수형", "even": "짝수형"}


def _keys(exam: Exam) -> dict[str, list | None]:
    return {"odd": exam.answer_key_odd, "even": exam.answer_key_even}


async def _points(session: AsyncSession, exam_id: int) -> dict[int, int | None]:
    rows = await session.execute(
        select(ExamQuestion.no, ExamQuestion.points).where(ExamQuestion.exam_id == exam_id)
    )
    return dict(rows.all())


def _uses_points(points: dict[int, int | None], total: int) -> bool:
    return total > 0 and all(points.get(no) for no in range(1, total + 1))


def _score(correct: list[int], graded: int, points: dict, max_score: int | None, total: int) -> Decimal:
    """모든 문항에 배점이 있으면 맞힌 문항의 배점 합, 없으면 맞힌 비율 × 만점(기본 100)."""
    if _uses_points(points, total):
        return Decimal(sum(points[no] for no in correct))
    if not graded:
        return Decimal(0)
    return round(Decimal(len(correct)) / graded * (max_score or 100), 2)


@router.post("/exams/{exam_id}/omr/apply")
async def apply_scans(exam_id: int, scope: CurrentScope, session: Db) -> dict:
    scope.require_director()
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    scans = (await session.scalars(
        select(OmrScan).where(OmrScan.exam_id == exam.id).order_by(OmrScan.file_id, OmrScan.page_no)
    )).all()

    # 검수 대기는 반영하지 않는다(FR-33, AC-25). 학생이 없는 스캔은 검수 대기이므로 여기 오지 않는다
    ready: dict[int, list[OmrScan]] = defaultdict(list)
    for scan in scans:
        if scan.status != "needs_review" and scan.matched_student_id:
            ready[scan.matched_student_id].append(scan)
    # 한 학생에 답안지가 둘 이상이면 어느 쪽이 맞는지 알 수 없다. 둘 다 보류하고 알린다
    chosen = {student: pages[0] for student, pages in ready.items() if len(pages) == 1}
    held = {student: pages for student, pages in ready.items() if len(pages) > 1}

    keys = _keys(exam)
    for scan in chosen.values():
        form = scan.read_payload.get("form")
        if not keys.get(form):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"{FORM_NAME.get(form, '문형 미지정')} 정답표를 먼저 입력해 주세요.",
            )

    points = await _points(session, exam.id)
    existing = {a.student_id: a for a in await session.scalars(
        select(ExamAttempt).where(ExamAttempt.exam_id == exam.id)
    )}
    replaced = removed = 0
    for student_id, attempt in existing.items():
        if student_id in chosen or attempt.source == "omr":
            await session.execute(delete(ExamAnswer).where(ExamAnswer.attempt_id == attempt.id))
        if student_id in chosen:
            replaced += 1
        elif attempt.source == "omr":
            # 이 시험의 OMR 시도는 현재 스캔에서만 나온다. 스캔이 다른 학생으로 옮겨 갔으면 지운다
            await session.delete(attempt)
            removed += 1

    for student_id, scan in chosen.items():
        form = scan.read_payload["form"]
        key = keys[form]
        answers = scan.read_payload.get("answers", {})
        attempt = existing.get(student_id) or ExamAttempt(exam_id=exam.id, student_id=student_id)
        attempt.form_type, attempt.source, attempt.flags = form, "omr", None
        session.add(attempt)
        await session.flush()
        correct, graded = [], 0
        for no, expected in enumerate(key, start=1):
            value = answers.get(str(no))
            # 정답표 칸이 비어 있으면 채점하지 않는다
            is_correct = None if expected is None else value == expected
            graded += expected is not None
            if is_correct:
                correct.append(no)
            session.add(ExamAnswer(
                attempt_id=attempt.id, question_no=no,
                raw_value=None if value is None else str(value), is_correct=is_correct,
            ))
        attempt.score = _score(correct, graded, points, exam.max_score, len(key))
        scan.status = "applied"
    for pages in held.values():
        for scan in pages:
            scan.status = "read"

    names = dict((await session.execute(
        select(Student.id, Student.name).where(Student.id.in_(held))
    )).all()) if held else {}
    conflicts = [
        {"student": {"id": student, "name": names.get(student)}, "pages": [s.page_no for s in pages]}
        for student, pages in held.items()
    ]
    waiting = sum(scan.status == "needs_review" for scan in scans)
    summary = {"applied": len(chosen), "replaced": replaced, "removed": removed,
               "waiting": waiting, "conflicts": conflicts}
    # 재반영은 기존 시도를 대체하므로 누가 언제 무엇을 바꿨는지 남긴다(설계 OMR 흐름 5)
    session.add(AuditLog(
        campus_id=scope.campus_id, actor_id=scope.user.id, action="omr.apply",
        target=f"exam:{exam.id}",
        detail=f"applied={len(chosen)} replaced={replaced} removed={removed} "
               f"waiting={waiting} conflicts={len(conflicts)}",
    ))
    await session.commit()
    return summary


# ── 조회 ─────────────────────────────────────────────────────────────


async def _graded(session: AsyncSession, exam_id: int):
    """(시도, 학생, 답 목록) — 학생 이름순."""
    attempts = (await session.execute(
        select(ExamAttempt, Student)
        .join(Student, Student.id == ExamAttempt.student_id)
        .where(ExamAttempt.exam_id == exam_id)
        .order_by(Student.name)
    )).all()
    answers: dict[int, list[ExamAnswer]] = defaultdict(list)
    if attempts:
        for answer in await session.scalars(
            select(ExamAnswer)
            .where(ExamAnswer.attempt_id.in_([a.id for a, _ in attempts]))
            .order_by(ExamAnswer.question_no)
        ):
            answers[answer.attempt_id].append(answer)
    return [(attempt, student, answers[attempt.id]) for attempt, student in attempts]


def _rate(part: int, whole: int) -> float | None:
    return round(part / whole * 100, 1) if whole else None


def _question_rates(graded) -> dict[int, tuple[int, int]]:
    """문항 번호 → (맞힌 수, 채점한 수)."""
    rates: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for _, _, answers in graded:
        for answer in answers:
            if answer.is_correct is not None:
                rates[answer.question_no][0] += answer.is_correct
                rates[answer.question_no][1] += 1
    return {no: (hit, total) for no, (hit, total) in rates.items()}


async def _enrolled(session: AsyncSession, exam: Exam) -> int | None:
    if exam.class_id is None:
        return None
    on = exam.exam_date or date.today()
    return await session.scalar(
        select(func.count()).select_from(Enrollment).where(
            Enrollment.class_id == exam.class_id,
            Enrollment.start_date <= on,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on),
        )
    )


@router.get("/exams/{exam_id}/results")
async def exam_results(exam_id: int, scope: CurrentScope, session: Db) -> dict:
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    graded = await _graded(session, exam.id)
    total = len(exam.answer_key_odd or exam.answer_key_even or [])
    scores = [float(attempt.score) for attempt, _, _ in graded if attempt.score is not None]
    rates = _question_rates(graded)
    hits = sum(hit for hit, _ in rates.values())
    marked = sum(whole for _, whole in rates.values())
    return {
        "score_basis": "points" if _uses_points(await _points(session, exam.id), total) else "ratio",
        "summary": {
            "attempts": len(graded),
            "enrolled": await _enrolled(session, exam),
            "average": round(sum(scores) / len(scores), 2) if scores else None,
            "highest": max(scores, default=None),
            "lowest": min(scores, default=None),
            "average_correct_rate": _rate(hits, marked),
            "focus_questions": sorted(
                no for no, (hit, whole) in rates.items() if _rate(hit, whole) < FOCUS_RATE
            ),
        },
        "students": [
            {
                "student": {"id": student.id, "name": student.name},
                "form": attempt.form_type,
                "source": attempt.source,
                "score": None if attempt.score is None else float(attempt.score),
                "correct": sum(bool(a.is_correct) for a in answers),
                "answers": [
                    {"no": a.question_no, "value": a.raw_value, "correct": a.is_correct}
                    for a in answers
                ],
            }
            for attempt, student, answers in graded
        ],
    }


@router.get("/exams/{exam_id}/question-stats")
async def question_stats(exam_id: int, scope: CurrentScope, session: Db) -> dict:
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    graded = await _graded(session, exam.id)
    rates = _question_rates(graded)
    meta = {q.no: q for q in await session.scalars(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam.id)
    )}
    odd, even = exam.answer_key_odd or [], exam.answer_key_even or []
    total = max(len(odd), len(even), max(rates, default=0))

    choices: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, _, answers in graded:
        for answer in answers:
            if answer.raw_value is not None:
                choices[answer.question_no][answer.raw_value] += 1

    questions = []
    by_unit: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])  # 문항 수, 틀린 수, 채점 수
    for no in range(1, total + 1):
        hit, whole = rates.get(no, (0, 0))
        question = meta.get(no)
        unit = question.unit if question and question.unit else "미분류"
        by_unit[unit][0] += 1
        by_unit[unit][1] += whole - hit
        by_unit[unit][2] += whole
        questions.append({
            "no": no,
            "answer": odd[no - 1] if no <= len(odd) else None,
            "answer_even": even[no - 1] if no <= len(even) else None,
            "correct_rate": _rate(hit, whole),
            "choices": dict(sorted(choices[no].items(), key=lambda item: int(item[0]))),
            "unit": question.unit if question else None,
            "sub_type": question.sub_type if question else None,
            "difficulty": question.difficulty if question else None,
        })
    # 오답 유형은 단원으로 묶는다. 세부 유형은 문항마다 달라 묶이지 않는다
    units = [
        {"unit": unit, "questions": count, "wrong_rate": _rate(wrong, whole)}
        for unit, (count, wrong, whole) in by_unit.items()
    ]
    units.sort(key=lambda row: (-(row["wrong_rate"] or 0), row["unit"]))
    return {"questions": questions, "units": units}
