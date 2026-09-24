"""시험지 등록과 분석 시작(REST 계약의 시험지 절).

시험 정보 편집·문항 확정 화면은 TASK-32가 확장한다. 여기는 분석 경로에 필요한 만큼이다.
"""
import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import analysis  # noqa: F401 — 분석 작업 핸들러를 등록한다
from .branding import load_brand
from .db import get_session
from .models import Campus, Exam, ExamQuestion, Klass, StoredFile
from .models.exam import DIFFICULTY
from .report import render_difficulty_html
from .scope import CurrentScope, ScopedRepository

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["exams"])


class ExamIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source_file_id: int | None = None
    class_id: int | None = None
    exam_date: date | None = None


class ExamOut(BaseModel):
    id: int
    name: str
    source_file_id: int | None
    class_id: int | None
    exam_date: date | None
    question_count: int | None
    status: str


class QuestionOut(BaseModel):
    no: int
    unit: str | None
    sub_type: str | None
    difficulty: str | None
    rationale: str | None
    points: int | None
    confidence: float | None
    needs_review: bool


class ExamRow(ExamOut):
    needs_review: int


class ExamDetail(ExamOut):
    max_score: int | None
    answer_key_odd: list[int | None] | None
    answer_key_even: list[int | None] | None
    difficulty: dict[str, int]


# 객관식은 1~5, 단답형은 0~999(백·십·일 세 자리, FR-33). 빈 칸(None)은 미입력이다
AnswerKey = list[Annotated[int, Field(ge=0, le=999)] | None]


class ExamPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    class_id: int | None = None
    exam_date: date | None = None
    question_count: int | None = Field(default=None, ge=1, le=100)
    max_score: int | None = Field(default=None, ge=1, le=1000)
    answer_key_odd: AnswerKey | None = None
    answer_key_even: AnswerKey | None = None
    status: str | None = Field(default=None, pattern="^(draft|confirmed)$")


class QuestionPatch(BaseModel):
    no: int
    unit: str | None = Field(default=None, max_length=200)
    sub_type: str | None = Field(default=None, max_length=200)
    difficulty: str | None = Field(default=None, pattern="^(low|mid|high|top)$")
    rationale: str | None = None
    points: int | None = Field(default=None, ge=0, le=100)


class QuestionsPatch(BaseModel):
    questions: list[QuestionPatch]


@router.post("/exams", status_code=status.HTTP_201_CREATED)
async def create_exam(payload: ExamIn, scope: CurrentScope, session: Db) -> ExamOut:
    scope.require_director()
    if payload.source_file_id is not None:
        await ScopedRepository(session, scope).get(StoredFile, payload.source_file_id)
    exam = Exam(campus_id=scope.campus_id, **payload.model_dump())
    session.add(exam)
    await session.commit()
    return ExamOut.model_validate(exam, from_attributes=True)


@router.post("/exams/{exam_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    exam_id: int, request: Request, scope: CurrentScope, session: Db
) -> dict[str, int]:
    scope.require_director()
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    if exam.status == "confirmed":
        # 확정한 문항을 다시 분석하면 사용자가 고친 내용이 초안으로 덮인다
        raise HTTPException(status.HTTP_409_CONFLICT, "확정된 시험은 다시 분석할 수 없습니다.")
    if exam.source_file_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "시험지 파일을 먼저 올려 주세요.")

    runner = request.app.state.task_runner
    task_id = await runner.enqueue(session, scope.campus_id, "exam_analyze", {"exam_id": exam.id})
    # 요청을 붙잡지 않는다. 진행 상태는 GET /tasks/{task_id}로 폴링한다(DES-18)
    running = asyncio.create_task(runner.run_pending())
    request.app.state.background.add(running)
    running.add_done_callback(request.app.state.background.discard)
    return {"task_id": task_id}


@router.get("/exams/{exam_id}/questions")
async def list_questions(exam_id: int, scope: CurrentScope, session: Db) -> list[QuestionOut]:
    await ScopedRepository(session, scope).get(Exam, exam_id)
    rows = await session.scalars(
        select(ExamQuestion).where(ExamQuestion.exam_id == exam_id).order_by(ExamQuestion.no)
    )
    return [QuestionOut.model_validate(row, from_attributes=True) for row in rows]


async def _flagged(session: AsyncSession, exam_id: int) -> int:
    return await session.scalar(
        select(func.count(ExamQuestion.id)).where(
            ExamQuestion.exam_id == exam_id, ExamQuestion.needs_review
        )
    ) or 0


async def _difficulty(session: AsyncSession, exam_id: int) -> dict[str, int]:
    rows = await session.execute(
        select(ExamQuestion.difficulty, func.count(ExamQuestion.id))
        .where(ExamQuestion.exam_id == exam_id, ExamQuestion.difficulty.is_not(None))
        .group_by(ExamQuestion.difficulty)
    )
    counts = dict.fromkeys(DIFFICULTY, 0)
    counts.update({level: count for level, count in rows})
    return counts


async def _detail(session: AsyncSession, exam: Exam) -> ExamDetail:
    return ExamDetail.model_validate(
        {**ExamOut.model_validate(exam, from_attributes=True).model_dump(),
         "max_score": exam.max_score, "answer_key_odd": exam.answer_key_odd,
         "answer_key_even": exam.answer_key_even,
         "difficulty": await _difficulty(session, exam.id)}
    )


@router.get("/exams")
async def list_exams(scope: CurrentScope, session: Db) -> list[ExamRow]:
    """최근 등록한 시험지 목록. 최신 등록이 앞이다."""
    exams = await session.scalars(
        ScopedRepository(session, scope).select(Exam).order_by(Exam.id.desc()).limit(50)
    )
    return [
        ExamRow(**ExamOut.model_validate(exam, from_attributes=True).model_dump(),
                needs_review=await _flagged(session, exam.id))
        for exam in exams
    ]


@router.get("/exams/{exam_id}")
async def read_exam(exam_id: int, scope: CurrentScope, session: Db) -> ExamDetail:
    return await _detail(session, await ScopedRepository(session, scope).get(Exam, exam_id))


@router.patch("/exams/{exam_id}")
async def update_exam(
    exam_id: int, payload: ExamPatch, scope: CurrentScope, session: Db
) -> ExamDetail:
    scope.require_director()
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("class_id") is not None:
        await ScopedRepository(session, scope).get(Klass, changes["class_id"])

    count = changes.get("question_count", exam.question_count)
    for form in ("answer_key_odd", "answer_key_even"):
        key = changes.get(form)
        if key is not None and len(key) != count:
            # 정답표 길이가 문항 수와 다르면 채점(TASK-37)에서 번호가 어긋난다
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"정답표는 문항 수({count})만큼이어야 합니다. 받은 값: {len(key)}개",
            )

    if changes.get("status") == "confirmed" and (flagged := await _flagged(session, exam.id)):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"확인 필요 문항 {flagged}개를 먼저 확인해 주세요."
        )

    for field, value in changes.items():
        setattr(exam, field, value)
    await session.commit()
    return await _detail(session, exam)


@router.patch("/exams/{exam_id}/questions")
async def update_questions(
    exam_id: int, payload: QuestionsPatch, scope: CurrentScope, session: Db
) -> list[QuestionOut]:
    """사용자가 손댄 문항은 확인된 것으로 본다. 값 없이 번호만 보내면 초안 그대로 확인한다(FR-29)."""
    scope.require_director()
    await ScopedRepository(session, scope).get(Exam, exam_id)
    rows = {
        row.no: row
        for row in await session.scalars(
            select(ExamQuestion).where(ExamQuestion.exam_id == exam_id)
        )
    }
    for item in payload.questions:
        row = rows.get(item.no)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"{item.no}번 문항이 없습니다.")
        for field, value in item.model_dump(exclude_unset=True, exclude={"no"}).items():
            setattr(row, field, value)
        row.needs_review = False
    await session.commit()
    return await list_questions(exam_id, scope, session)


@router.get("/exams/{exam_id}/difficulty-card")
async def difficulty_card(
    exam_id: int, request: Request, scope: CurrentScope, session: Db
) -> Response:
    """난이도 분석표 카드 이미지(FR-30). 화면의 [이미지 저장]이 이것을 내려받는다."""
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    campus = await session.get(Campus, scope.campus_id)
    colour, _ = await load_brand(session, scope.campus_id)
    klass = await session.get(Klass, exam.class_id) if exam.class_id else None
    meta = " · ".join(
        part for part in (
            klass.name if klass else None,
            exam.exam_date.isoformat() if exam.exam_date else None,
            f"{exam.question_count}문항" if exam.question_count else None,
        ) if part
    )
    html = render_difficulty_html(
        campus.name, exam.name, meta, await _difficulty(session, exam.id), colour
    )
    png = await request.app.state.report_renderer.render_html(html)
    return Response(
        content=png,
        media_type="image/png",
        headers={"content-disposition": f'attachment; filename="difficulty-{exam.id}.png"'},
    )
