"""상담일지(FR-39, DES-04) — 학생별 상담 날짜·내용·후속 조치의 등록·조회·수정.

삭제는 두지 않는다(FR-39가 요구하지 않고, 상담 이력은 지도 판단의 근거라 남겨 둔다).
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .masterdata import visible_students
from .models import AppUser, ConsultLog, Student
from .scope import CurrentScope, Scope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["consults"])


class ConsultIn(BaseModel):
    consulted_on: date
    content: str = Field(max_length=5000)
    follow_up: str | None = Field(default=None, max_length=2000)

    @field_validator("content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("상담 내용을 입력해 주세요.")
        return value


class Author(BaseModel):
    id: int
    name: str


class ConsultOut(BaseModel):
    id: int
    student_id: int
    consulted_on: date
    content: str
    follow_up: str | None
    author: Author | None


async def _student(session: AsyncSession, scope: Scope, student_id: int) -> Student:
    student = await session.scalar(visible_students(session, scope).where(Student.id == student_id))
    if student is None:
        # 다른 캠퍼스·담당 밖 학생의 존재를 드러내지 않는다(스코프 검사와 같은 403)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")
    return student


def _out(log: ConsultLog, author: AppUser | None) -> ConsultOut:
    return ConsultOut(
        id=log.id,
        student_id=log.student_id,
        consulted_on=log.consulted_on,
        content=log.content,
        follow_up=log.follow_up,
        author=Author(id=author.id, name=author.display_name) if author else None,
    )


@router.get("/students/{student_id}/consults")
async def list_consults(student_id: int, scope: CurrentScope, session: Db) -> list[ConsultOut]:
    student = await _student(session, scope, student_id)
    rows = await session.execute(
        select(ConsultLog, AppUser)
        .outerjoin(AppUser, AppUser.id == ConsultLog.author_id)
        .where(ConsultLog.student_id == student.id)
        .order_by(ConsultLog.consulted_on.desc(), ConsultLog.id.desc())
    )
    return [_out(log, author) for log, author in rows]


@router.post("/students/{student_id}/consults", status_code=status.HTTP_201_CREATED)
async def create_consult(
    student_id: int, payload: ConsultIn, scope: CurrentScope, session: Db
) -> ConsultOut:
    student = await _student(session, scope, student_id)
    log = ConsultLog(
        campus_id=student.campus_id, student_id=student.id, author_id=scope.user.id,
        **payload.model_dump(),
    )
    session.add(log)
    await session.commit()
    return _out(log, scope.user)


@router.patch("/students/{student_id}/consults/{consult_id}")
async def update_consult(
    student_id: int, consult_id: int, payload: ConsultIn, scope: CurrentScope, session: Db
) -> ConsultOut:
    student = await _student(session, scope, student_id)
    log = await session.get(ConsultLog, consult_id)
    if log is None or log.student_id != student.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "상담 기록을 찾을 수 없습니다.")
    # 강사는 자기가 쓴 기록만 고친다. 다른 사람의 상담 내용을 바꾸면 기록의 주인이 흐려진다
    if not scope.is_director and log.author_id != scope.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "직접 작성한 상담 기록만 수정할 수 있습니다.")
    for field, value in payload.model_dump().items():
        setattr(log, field, value)
    await session.commit()
    author = await session.get(AppUser, log.author_id) if log.author_id else None
    return _out(log, author)
