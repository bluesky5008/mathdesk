from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, StringConstraints, field_validator
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import AppUser, AppUserCampus, AuditLog, ClassSchedule, Enrollment, Guardian, Klass, School, Student
from .portal_accounts import portal_summary, sync_portal_access
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
    # DCR-015: 등록된 학교 중에서 고른다. 보내지 않으면 수정 시 그대로 둔다
    school_id: int | None = None
    grade: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=20)
    status: str = Field(default="enrolled", pattern="^(enrolled|paused|withdrawn)$")
    omr_number: str | None = None
    # DCR-014: 대표 보호자 번호와 성적·비고. 보내지 않으면 수정 시 그대로 둔다(빈 값과 구분)
    guardian_phone: str | None = Field(default=None, max_length=20)
    score_note: str | None = Field(default=None, max_length=500)


class StudentOut(BaseModel):
    id: int
    name: str
    school_id: int | None
    school: str | None = None  # 학교 이름(읽기 전용)
    grade: str | None
    phone: str | None
    status: str
    omr_number: str | None
    guardian_phone: str | None = None
    score_note: str | None = None
    # 포털 계정 상태 요약(FR-48 상세): {"student": state, "guardian": state}
    portal: dict[str, str] | None = None


class ScheduleIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time | None = None  # 선택 항목(DCR-007)


class ClassIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    grade: str | None = Field(default=None, max_length=20)
    teacher_id: int | None = None
    is_active: bool = True
    schedules: list[ScheduleIn] = Field(default_factory=list)

    @field_validator("schedules")
    @classmethod
    def no_duplicate_slots(cls, schedules: list[ScheduleIn]) -> list[ScheduleIn]:
        slots = [(s.weekday, s.start_time) for s in schedules]
        if len(slots) != len(set(slots)):
            raise ValueError("같은 요일·시작 시각이 두 번 들어 있습니다.")
        return schedules


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


class EnrollmentUpdate(BaseModel):
    end_date: date | None = None


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


def visible_students(session: AsyncSession, scope: Scope):
    """캠퍼스의 학생. 강사는 담당 반에 배정된 적이 있는 학생만 본다(권한 매트릭스)."""
    statement = _repo(session, scope).select(Student)
    if not scope.is_director:
        statement = statement.where(
            Student.id.in_(
                select(Enrollment.student_id).where(
                    Enrollment.class_id.in_(select(Klass.id).where(Klass.teacher_id == scope.user.id))
                )
            )
        )
    return statement


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


async def _guardian_phones(session: AsyncSession, student_ids: list[int]) -> dict[int, str]:
    """학생마다 대표 보호자(가장 먼저 등록된 보호자)의 번호(DCR-014). 한 번의 조회로 읽는다."""
    rows = await session.execute(
        select(Guardian.student_id, Guardian.phone)
        .where(Guardian.student_id.in_(student_ids))
        .order_by(Guardian.id)
    )
    phones: dict[int, str] = {}
    for student_id, phone in rows:
        phones.setdefault(student_id, phone)
    return phones


def _student_out(student: Student, guardian_phone: str | None, school: str | None) -> StudentOut:
    out = StudentOut.model_validate(student, from_attributes=True)
    return out.model_copy(update={"guardian_phone": guardian_phone, "school": school})


async def _school_name(session: AsyncSession, scope: Scope, school_id: int | None) -> str | None:
    """학생이 고른 학교의 이름. 같은 캠퍼스의 학교가 아니면 422(DCR-015)."""
    if school_id is None:
        return None
    name = await session.scalar(
        select(School.name).where(School.id == school_id, School.campus_id == scope.campus_id)
    )
    if name is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "학교를 찾을 수 없습니다.")
    return name


async def _sync_guardian(session: AsyncSession, student_id: int, phone: str | None) -> None:
    """대표 보호자를 화면의 학부모 연락처에 맞춘다. 관계·이름은 기존 값을 지킨다(DCR-014)."""
    guardian = await session.scalar(
        select(Guardian).where(Guardian.student_id == student_id).order_by(Guardian.id).limit(1)
    )
    if phone:
        if guardian is None:
            session.add(Guardian(student_id=student_id, relation="학부모", name="", phone=phone))
        else:
            guardian.phone = phone
    elif guardian is not None:
        await session.delete(guardian)


@router.get("/students")
async def list_students(
    scope: CurrentScope,
    session: Db,
    q: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[StudentOut]:
    statement = (
        visible_students(session, scope)
        .add_columns(School.name)
        .outerjoin(School, School.id == Student.school_id)
        .order_by(Student.id)
    )
    if q:
        statement = statement.where(Student.name.ilike(f"%{q}%"))
    if status_filter:
        statement = statement.where(Student.status == status_filter)
    rows = (await session.execute(statement)).all()
    student_ids = [student.id for student, _ in rows]
    phones = await _guardian_phones(session, student_ids)
    portal = await portal_summary(session, student_ids)
    return [
        _student_out(student, phones.get(student.id), school).model_copy(update={"portal": portal[student.id]})
        for student, school in rows
    ]


@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student(payload: StudentIn, scope: CurrentScope, session: Db) -> StudentOut:
    scope.require_director()
    omr_number = await _validated_omr_number(session, scope, payload.omr_number)
    school = await _school_name(session, scope, payload.school_id)
    student = Student(
        **payload.model_dump(exclude={"omr_number", "guardian_phone"}),
        omr_number=omr_number,
        campus_id=scope.campus_id,
    )
    session.add(student)
    await session.flush()
    await _sync_guardian(session, student.id, payload.guardian_phone)
    await session.commit()
    return _student_out(student, payload.guardian_phone or None, school)


@router.patch("/students/{student_id}")
async def update_student(
    student_id: int, payload: StudentIn, scope: CurrentScope, session: Db
) -> StudentOut:
    scope.require_director()
    student = await _repo(session, scope).get(Student, student_id)
    student.omr_number = await _validated_omr_number(
        session, scope, payload.omr_number, exclude_id=student_id
    )
    fields = payload.model_dump(exclude={"omr_number", "guardian_phone"})
    for optional in ("score_note", "school_id"):
        if optional not in payload.model_fields_set:
            del fields[optional]
    if "school_id" in fields:
        await _school_name(session, scope, payload.school_id)
    status_before = student.status
    for field, value in fields.items():
        setattr(student, field, value)
    if "guardian_phone" in payload.model_fields_set:
        await _sync_guardian(session, student_id, payload.guardian_phone)
    if student.status != status_before:
        # 퇴원이면 이 학생만 연결된 포털 계정을 비활성화하고, 복귀하면 되살린다(FR-48 상세)
        await sync_portal_access(session, scope, student_id)
    await session.commit()
    phones = await _guardian_phones(session, [student_id])
    return _student_out(student, phones.get(student_id), await _school_name(session, scope, student.school_id))


# ── 학교(FR-43, DCR-015) — 원장 전용 ─────────────────────────────────────

SchoolName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class SchoolIn(BaseModel):
    name: SchoolName


class SchoolOut(BaseModel):
    id: int
    name: str
    student_count: int = 0


async def _check_school_name(session: AsyncSession, scope: Scope, name: str, exclude_id: int | None = None) -> None:
    statement = select(School.id).where(School.campus_id == scope.campus_id, School.name == name)
    if exclude_id is not None:
        statement = statement.where(School.id != exclude_id)
    if await session.scalar(statement):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 등록된 학교입니다.")


@router.get("/schools")
async def list_schools(scope: CurrentScope, session: Db) -> list[SchoolOut]:
    scope.require_director()
    rows = await session.execute(
        select(School.id, School.name, func.count(Student.id))
        .outerjoin(Student, Student.school_id == School.id)
        .where(School.campus_id == scope.campus_id)
        .group_by(School.id)
        .order_by(School.name)
    )
    return [SchoolOut(id=id, name=name, student_count=count) for id, name, count in rows]


@router.post("/schools", status_code=status.HTTP_201_CREATED)
async def create_school(payload: SchoolIn, scope: CurrentScope, session: Db) -> SchoolOut:
    scope.require_director()
    await _check_school_name(session, scope, payload.name)
    school = School(campus_id=scope.campus_id, name=payload.name)
    session.add(school)
    await session.commit()
    return SchoolOut(id=school.id, name=school.name)


@router.patch("/schools/{school_id}")
async def update_school(school_id: int, payload: SchoolIn, scope: CurrentScope, session: Db) -> SchoolOut:
    scope.require_director()
    school = await _repo(session, scope).get(School, school_id)
    await _check_school_name(session, scope, payload.name, exclude_id=school_id)
    school.name = payload.name
    await session.commit()
    return SchoolOut(id=school.id, name=school.name)


@router.delete("/schools/{school_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_school(school_id: int, scope: CurrentScope, session: Db) -> None:
    """확인 없이 지우고 그 학교 학생들의 학교를 비운다(사용자 결정). 학생은 지우지 않는다."""
    scope.require_director()
    school = await _repo(session, scope).get(School, school_id)
    cleared = await session.execute(
        update(Student).where(Student.school_id == school_id).values(school_id=None)
    )
    session.add(
        AuditLog(
            campus_id=scope.campus_id,
            actor_id=scope.user.id,
            action="school.delete",
            target=f"school:{school_id}",
            detail=f"{school.name}, 학생 {cleared.rowcount}명",
        )
    )
    await session.delete(school)
    await session.commit()


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


async def _check_teacher(
    session: AsyncSession, scope: Scope, teacher_id: int | None, current: int | None = None
) -> None:
    """새로 지정하는 담당 강사는 같은 캠퍼스의 활성 강사여야 한다.
    이미 지정된 강사는 나중에 비활성이 되어도 반을 고칠 때 그대로 둘 수 있다(PATCH가 전치환이다)."""
    if teacher_id is None or teacher_id == current:
        return
    valid = await session.scalar(
        select(AppUser.id)
        .join(AppUserCampus, AppUserCampus.user_id == AppUser.id)
        .where(
            AppUser.id == teacher_id,
            AppUserCampus.campus_id == scope.campus_id,
            AppUser.role == "teacher",
            AppUser.is_active,
        )
    )
    if valid is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "담당 강사는 이 캠퍼스의 사용 중인 강사 계정이어야 합니다."
        )


@router.post("/classes", status_code=status.HTTP_201_CREATED)
async def create_class(payload: ClassIn, scope: CurrentScope, session: Db) -> ClassOut:
    scope.require_director()
    await _check_teacher(session, scope, payload.teacher_id)
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
    # 강사는 담당 반의 반명·학년·시간표만 바꾼다. 담당 지정·활성 여부는 원장만(DCR-011)
    klass = await _visible_class(session, scope, class_id)
    existing = list(
        await session.scalars(select(ClassSchedule).where(ClassSchedule.class_id == class_id))
    )
    if not scope.is_director:
        if payload.teacher_id != klass.teacher_id or payload.is_active != klass.is_active:
            raise _forbidden()
        changed = [
            field
            for field, before, after in (
                ("name", klass.name, payload.name),
                ("grade", klass.grade, payload.grade),
                (
                    "schedules",
                    {(s.weekday, s.start_time) for s in existing},
                    {(s.weekday, s.start_time) for s in payload.schedules},
                ),
            )
            if before != after
        ]
        session.add(
            AuditLog(
                campus_id=scope.campus_id,
                actor_id=scope.user.id,
                action="class.update",
                target=f"class:{class_id}",
                detail=", ".join(changed),
            )
        )
    await _check_teacher(session, scope, payload.teacher_id, current=klass.teacher_id)
    klass.name, klass.grade, klass.teacher_id = payload.name, payload.grade, payload.teacher_id
    klass.is_active = payload.is_active
    for schedule in existing:
        await session.delete(schedule)
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
    # 같은 반에 기간이 겹치는 배정이 둘이면 그 날짜의 명단에 학생이 두 번 나온다
    overlap = await session.scalar(
        select(Enrollment.id).where(
            Enrollment.class_id == class_id,
            Enrollment.student_id == payload.student_id,
            or_(Enrollment.end_date.is_(None), Enrollment.end_date >= payload.start_date),
            *([Enrollment.start_date <= payload.end_date] if payload.end_date else []),
        )
    )
    if overlap is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "이 반에 기간이 겹치는 배정이 이미 있습니다."
        )
    enrollment = Enrollment(class_id=class_id, **payload.model_dump())
    session.add(enrollment)
    await session.commit()
    return EnrollmentOut.model_validate(enrollment, from_attributes=True)


async def _enrollment(
    session: AsyncSession, scope: Scope, class_id: int, enrollment_id: int
) -> Enrollment:
    await _visible_class(session, scope, class_id)
    enrollment = await session.scalar(
        select(Enrollment).where(
            Enrollment.id == enrollment_id, Enrollment.class_id == class_id
        )
    )
    if enrollment is None:
        raise _forbidden()
    return enrollment


@router.patch("/classes/{class_id}/enrollments/{enrollment_id}")
async def update_enrollment(
    class_id: int,
    enrollment_id: int,
    payload: EnrollmentUpdate,
    scope: CurrentScope,
    session: Db,
) -> EnrollmentOut:
    """해제는 삭제가 아니라 배정 기간의 종료다. 과거 수업일의 명단은 기간으로 재현한다."""
    scope.require_director()
    enrollment = await _enrollment(session, scope, class_id, enrollment_id)
    if payload.end_date is not None and payload.end_date < enrollment.start_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "종료일은 배정 시작일보다 빠를 수 없습니다."
        )
    enrollment.end_date = payload.end_date
    await session.commit()
    return EnrollmentOut.model_validate(enrollment, from_attributes=True)


@router.delete("/classes/{class_id}/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    class_id: int, enrollment_id: int, scope: CurrentScope, session: Db
) -> None:
    """오등록 취소 전용이다. 수강을 끝내는 것은 PATCH의 종료일이다."""
    scope.require_director()
    enrollment = await _enrollment(session, scope, class_id, enrollment_id)
    await session.delete(enrollment)
    await session.commit()
