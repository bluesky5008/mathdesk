from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import ClassSchedule, Enrollment, Guardian, Klass, Student
from .scope import CurrentScope, Scope, ScopedRepository

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["masterdata"])

# 2027학년도 수능 수학영역 답안지의 수험번호 자리별 마킹 가능 범위.
OMR_DIGIT_RANGES = ((1, 9), (0, 9), (0, 5), (0, 9), (0, 9), (0, 9), (0, 2), (0, 9))


def validate_omr_number(value: str) -> str | None:
    """오류 사유를 반환한다. 유효하면 None."""
    if len(value) != len(OMR_DIGIT_RANGES) or not value.isdigit():
        return "수험번호는 8자리 숫자여야 합니다."
    for position, (digit, (low, high)) in enumerate(zip(value, OMR_DIGIT_RANGES), start=1):
        if not low <= int(digit) <= high:
            return f"{position}열은 {low}~{high}만 마킹할 수 있습니다."
    return None


class GuardianIn(BaseModel):
    relation: str = Field(max_length=20)
    name: str = Field(max_length=50)
    phone: str = Field(max_length=20)
    is_notify_target: bool = True


class GuardianOut(GuardianIn):
    id: int


class StudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    school: str | None = Field(default=None, max_length=100)
    grade: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=20)
    status: str = Field(default="enrolled", pattern="^(enrolled|paused|withdrawn)$")
    omr_number: str | None = None


class StudentOut(BaseModel):
    id: int
    name: str
    school: str | None
    grade: str | None
    phone: str | None
    status: str
    omr_number: str | None


class ScheduleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    grade: str | None = Field(default=None, max_length=20)
    teacher_id: int | None = None
    is_active: bool = True
    schedules: list[ScheduleIn] = Field(default_factory=list)


class ClassOut(BaseModel):
    id: int
    name: str
    grade: str | None
    teacher_id: int | None
    is_active: bool
    schedules: list[ScheduleIn]


class EnrollmentIn(BaseModel):
    student_id: int
    start_date: date
    end_date: date | None = None


class EnrollmentOut(EnrollmentIn):
    id: int


def _forbidden() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")


def _repo(session: AsyncSession, scope: Scope) -> ScopedRepository:
    return ScopedRepository(session, scope)


def _visible_classes(scope: Scope):
    """강사는 담당 반만 본다."""
    statement = select(Klass).where(Klass.campus_id == scope.campus_id)
    if not scope.is_director:
        statement = statement.where(Klass.teacher_id == scope.user.id)
    return statement.order_by(Klass.id)


async def _visible_class(session: AsyncSession, scope: Scope, class_id: int) -> Klass:
    klass = await session.scalar(_visible_classes(scope).where(Klass.id == class_id))
    if klass is None:
        raise _forbidden()
    return klass


async def _validated_omr_number(
    session: AsyncSession, scope: Scope, value: str | None, exclude_id: int | None = None
) -> str | None:
    if value is None:
        return None
    reason = validate_omr_number(value)
    if reason:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)

    statement = _repo(session, scope).select(Student).where(Student.omr_number == value)
    if exclude_id is not None:
        statement = statement.where(Student.id != exclude_id)
    if await session.scalar(statement):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 수험번호입니다.")
    return value


@router.get("/students")
async def list_students(
    scope: CurrentScope,
    session: Db,
    q: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[StudentOut]:
    statement = _repo(session, scope).select(Student).order_by(Student.id)
    if q:
        statement = statement.where(Student.name.ilike(f"%{q}%"))
    if status_filter:
        statement = statement.where(Student.status == status_filter)
    if not scope.is_director:
        statement = statement.where(
            Student.id.in_(
                select(Enrollment.student_id).where(
                    Enrollment.class_id.in_(select(Klass.id).where(Klass.teacher_id == scope.user.id))
                )
            )
        )
    students = await session.scalars(statement)
    return [StudentOut.model_validate(student, from_attributes=True) for student in students]


@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(payload: StudentIn, scope: CurrentScope, session: Db) -> StudentOut:
    scope.require_director()
    omr_number = await _validated_omr_number(session, scope, payload.omr_number)
    student = Student(
        **payload.model_dump(exclude={"omr_number"}),
        omr_number=omr_number,
        campus_id=scope.campus_id,
    )
    session.add(student)
    await session.commit()
    return StudentOut.model_validate(student, from_attributes=True)


@router.patch("/students/{student_id}")
async def update_student(
    student_id: int, payload: StudentIn, scope: CurrentScope, session: Db
) -> StudentOut:
    scope.require_director()
    student = await _repo(session, scope).get(Student, student_id)
    student.omr_number = await _validated_omr_number(
        session, scope, payload.omr_number, exclude_id=student_id
    )
    for field, value in payload.model_dump(exclude={"omr_number"}).items():
        setattr(student, field, value)
    await session.commit()
    return StudentOut.model_validate(student, from_attributes=True)


@router.get("/students/{student_id}/guardians")
async def list_guardians(student_id: int, scope: CurrentScope, session: Db) -> list[GuardianOut]:
    await _repo(session, scope).get(Student, student_id)
    guardians = await session.scalars(
        select(Guardian).where(Guardian.student_id == student_id).order_by(Guardian.id)
    )
    return [GuardianOut.model_validate(g, from_attributes=True) for g in guardians]


@router.post("/students/{student_id}/guardians", status_code=status.HTTP_201_CREATED)
async def create_guardian(
    student_id: int, payload: GuardianIn, scope: CurrentScope, session: Db
) -> GuardianOut:
    scope.require_director()
    await _repo(session, scope).get(Student, student_id)
    guardian = Guardian(student_id=student_id, **payload.model_dump())
    session.add(guardian)
    await session.commit()
    return GuardianOut.model_validate(guardian, from_attributes=True)


async def _class_out(session: AsyncSession, klass: Klass) -> ClassOut:
    schedules = await session.scalars(
        select(ClassSchedule).where(ClassSchedule.class_id == klass.id).order_by(ClassSchedule.id)
    )
    return ClassOut(
        id=klass.id,
        name=klass.name,
        grade=klass.grade,
        teacher_id=klass.teacher_id,
        is_active=klass.is_active,
        schedules=[ScheduleIn.model_validate(s, from_attributes=True) for s in schedules],
    )


@router.get("/classes")
async def list_classes(
    scope: CurrentScope, session: Db, include_inactive: bool = False
) -> list[ClassOut]:
    # 비활성 반은 반 선택 목록에서 빠져야 한다. 과거 기록 조회는 반 단건 경로를 쓰므로 영향이 없다.
    statement = _visible_classes(scope)
    if not include_inactive:
        statement = statement.where(Klass.is_active)
    classes = list(await session.scalars(statement))
    return [await _class_out(session, klass) for klass in classes]


@router.post("/classes", status_code=status.HTTP_201_CREATED)
async def create_class(payload: ClassIn, scope: CurrentScope, session: Db) -> ClassOut:
    scope.require_director()
    klass = Klass(
        campus_id=scope.campus_id,
        name=payload.name,
        grade=payload.grade,
        teacher_id=payload.teacher_id,
        is_active=payload.is_active,
    )
    session.add(klass)
    await session.flush()
    for schedule in payload.schedules:
        session.add(ClassSchedule(class_id=klass.id, **schedule.model_dump()))
    await session.commit()
    return await _class_out(session, klass)


@router.patch("/classes/{class_id}")
async def update_class(
    class_id: int, payload: ClassIn, scope: CurrentScope, session: Db
) -> ClassOut:
    scope.require_director()
    klass = await _repo(session, scope).get(Klass, class_id)
    klass.name, klass.grade, klass.teacher_id = payload.name, payload.grade, payload.teacher_id
    klass.is_active = payload.is_active
    for existing in await session.scalars(
        select(ClassSchedule).where(ClassSchedule.class_id == class_id)
    ):
        await session.delete(existing)
    for schedule in payload.schedules:
        session.add(ClassSchedule(class_id=class_id, **schedule.model_dump()))
    await session.commit()
    return await _class_out(session, klass)


@router.get("/classes/{class_id}/enrollments")
async def list_enrollments(
    class_id: int, scope: CurrentScope, session: Db, on: date | None = None
) -> list[EnrollmentOut]:
    await _visible_class(session, scope, class_id)
    statement = select(Enrollment).where(Enrollment.class_id == class_id)
    if on is not None:
        statement = statement.where(
            Enrollment.start_date <= on,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= on),
        )
    rows = await session.scalars(statement.order_by(Enrollment.id))
    return [EnrollmentOut.model_validate(row, from_attributes=True) for row in rows]


@router.post("/classes/{class_id}/enrollments", status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    class_id: int, payload: EnrollmentIn, scope: CurrentScope, session: Db
) -> EnrollmentOut:
    scope.require_director()
    await _visible_class(session, scope, class_id)
    await _repo(session, scope).get(Student, payload.student_id)
    enrollment = Enrollment(class_id=class_id, **payload.model_dump())
    session.add(enrollment)
    await session.commit()
    return EnrollmentOut.model_validate(enrollment, from_attributes=True)


@router.delete("/classes/{class_id}/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    class_id: int, enrollment_id: int, scope: CurrentScope, session: Db
) -> None:
    scope.require_director()
    await _visible_class(session, scope, class_id)
    enrollment = await session.scalar(
        select(Enrollment).where(
            Enrollment.id == enrollment_id, Enrollment.class_id == class_id
        )
    )
    if enrollment is None:
        raise _forbidden()
    await session.delete(enrollment)
    await session.commit()
