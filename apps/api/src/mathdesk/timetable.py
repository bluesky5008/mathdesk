"""주간 시간표 — FR-42, DCR-008.

종료 시각은 저장하지 않는다(DCR-007). 캠퍼스에 하나인 수업 길이로 계산한다.
강사 이름을 서버가 붙이므로 강사가 원장 전용인 `/users`를 부를 필요가 없다.
"""

from datetime import datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .masterdata import _visible_classes
from .models import AppUser, ClassSchedule, IntegrationSetting, Klass
from .scope import CurrentScope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["timetable"])

CLASS_MINUTES_KEY = "class_minutes"
DEFAULT_CLASS_MINUTES = 240  # 수업 한 번 4시간(사용자 확인 2026-09-24)


class Teacher(BaseModel):
    id: int
    name: str


class UnscheduledClass(BaseModel):
    class_id: int
    class_name: str
    grade: str | None
    teacher: Teacher | None


class Slot(UnscheduledClass):
    weekday: int
    start_time: time
    end_time: time


class Timetable(BaseModel):
    class_minutes: int
    slots: list[Slot]
    unscheduled: list[UnscheduledClass]


class ClassMinutesIn(BaseModel):
    class_minutes: int = Field(ge=30, le=480)


async def _class_minutes(session: AsyncSession, campus_id: int) -> int:
    stored = await session.get(IntegrationSetting, (campus_id, CLASS_MINUTES_KEY))
    return int(stored.value_encrypted) if stored else DEFAULT_CLASS_MINUTES


@router.get("/timetable")
async def read_timetable(scope: CurrentScope, session: Db) -> Timetable:
    minutes = await _class_minutes(session, scope.campus_id)
    classes = list(await session.scalars(_visible_classes(scope).where(Klass.is_active)))
    teacher_ids = {klass.teacher_id for klass in classes if klass.teacher_id}
    teachers = {
        user.id: Teacher(id=user.id, name=user.display_name)
        for user in await session.scalars(select(AppUser).where(AppUser.id.in_(teacher_ids)))
    }
    schedules = list(
        await session.scalars(
            select(ClassSchedule).where(ClassSchedule.class_id.in_([k.id for k in classes]))
        )
    )

    def base(klass: Klass) -> dict:
        return {
            "class_id": klass.id,
            "class_name": klass.name,
            "grade": klass.grade,
            "teacher": teachers.get(klass.teacher_id),
        }

    by_id = {klass.id: klass for klass in classes}
    length = timedelta(minutes=minutes)
    slots = [
        Slot(
            **base(by_id[s.class_id]),
            weekday=s.weekday,
            start_time=s.start_time,
            # 자정을 넘기면 다음 날 시각으로 돌아간다
            end_time=(datetime.combine(datetime.min, s.start_time) + length).time(),
        )
        for s in schedules
    ]
    slots.sort(key=lambda slot: (slot.weekday, slot.start_time, slot.class_id))
    scheduled = {s.class_id for s in schedules}
    unscheduled = [UnscheduledClass(**base(k)) for k in classes if k.id not in scheduled]
    return Timetable(class_minutes=minutes, slots=slots, unscheduled=unscheduled)


@router.put("/settings/class-minutes")
async def write_class_minutes(
    payload: ClassMinutesIn, scope: CurrentScope, session: Db
) -> ClassMinutesIn:
    scope.require_director()
    value = str(payload.class_minutes)
    stored = await session.get(IntegrationSetting, (scope.campus_id, CLASS_MINUTES_KEY))
    if stored is None:
        session.add(
            IntegrationSetting(
                campus_id=scope.campus_id, key=CLASS_MINUTES_KEY, value_encrypted=value
            )
        )
    else:
        stored.value_encrypted = value
    await session.commit()
    return payload
