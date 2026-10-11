"""학생·학부모 포털 조회(FR-49 상세, AC-51, DES-26 상세, DCR-024·ADR-014).

`/api/portal` 아래의 모든 엔드포인트는 `current_portal_scope`만 쓴다. 응답 모델은 포털 전용으로
좁혀 다른 학생·보호자·연락처 정보를 담지 않는다. 계산은 기존 서비스의 내부 함수를 재사용한다.
"""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import AppUser, Enrollment, Klass, Student
from .scope import CurrentPortalScope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/portal", tags=["portal"])


class PortalClass(BaseModel):
    id: int
    name: str
    teacher_name: str | None


class PortalStudent(BaseModel):
    id: int
    name: str
    grade: str | None
    status: str
    classes: list[PortalClass]


async def _current_classes(session: AsyncSession, student_ids: tuple[int, ...]) -> dict[int, list[PortalClass]]:
    today = date.today()
    rows = await session.execute(
        select(Enrollment.student_id, Klass, AppUser.display_name)
        .join(Klass, Klass.id == Enrollment.class_id)
        .outerjoin(AppUser, AppUser.id == Klass.teacher_id)
        .where(
            Enrollment.student_id.in_(student_ids),
            Enrollment.start_date <= today,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= today),
            Klass.is_active,
        )
        .order_by(Klass.id)
    )
    classes: dict[int, list[PortalClass]] = {sid: [] for sid in student_ids}
    for student_id, klass, teacher in rows:
        classes[student_id].append(PortalClass(id=klass.id, name=klass.name, teacher_name=teacher))
    return classes


@router.get("/students")
async def list_students(scope: CurrentPortalScope, session: Db) -> list[PortalStudent]:
    """연결된 학생(재원·휴원). 학부모 계정은 자녀 여럿일 수 있다."""
    students = await session.scalars(
        select(Student).where(Student.id.in_(scope.student_ids)).order_by(Student.id)
    )
    classes = await _current_classes(session, scope.student_ids)
    return [
        PortalStudent(id=s.id, name=s.name, grade=s.grade, status=s.status, classes=classes[s.id])
        for s in students
    ]
