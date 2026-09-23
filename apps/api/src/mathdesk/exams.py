"""시험지 등록과 분석 시작(REST 계약의 시험지 절).

시험 정보 편집·문항 확정 화면은 TASK-32가 확장한다. 여기는 분석 경로에 필요한 만큼이다.
"""
import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import analysis  # noqa: F401 — 분석 작업 핸들러를 등록한다
from .db import get_session
from .models import Exam, ExamQuestion, StoredFile
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
    confidence: float | None
    needs_review: bool


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
