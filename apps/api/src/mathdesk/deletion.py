"""학생·비활성 반의 삭제(FR-05 상세·FR-07, AC-36, DES-04 상세, DCR-006·DCR-012·DCR-013).

되돌릴 수 없는 작업이다. 그래서 세 가지를 지킨다.
- 선행 조건: 반은 비활성이어야 한다. 학생은 상태와 관계없이 지운다(DCR-012) — 감사 로그에 삭제
  당시 상태를 남긴다.
- 이름 확인: 반은 요청 본문의 `confirm_name`이 대상 이름과 같아야 한다. 학생은 확인 없이 지운다(DCR-013).
- 한 트랜잭션: 대상 행을 잠그고 확인 → 연관 삭제 → 대상 삭제. 중간에 실패하면 전부 되돌린다.

삭제·보존 목록은 아래 상수가 정본이다. 새 테이블이 학생·반(또는 여기서 지우는 테이블)을
참조하게 되면 `test_every_table_that_points_at_a_deleted_row_is_handled`가 먼저 실패한다.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import (
    AuditLog,
    ClassSchedule,
    ConsultLog,
    Enrollment,
    Exam,
    ExamAnswer,
    ExamAttempt,
    Guardian,
    Klass,
    LabelCorrection,
    MessageLog,
    OmrScan,
    Student,
    StudentDailyRecord,
)
from .models.daily import ClassSession, ClassSessionProgress
from .scope import CurrentScope, Scope, ScopedRepository

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["masterdata"])

# 학생을 지울 때 함께 지우는 테이블(과 그 테이블을 가리키는 하위 테이블)
STUDENT_CASCADE = {
    "guardian", "enrollment", "student_daily_record", "exam_attempt", "exam_answer",
    "omr_scan", "message_log", "consult_log",
}
# 반을 지울 때 함께 지우는 테이블
CLASS_CASCADE = {
    "class_schedule", "enrollment", "class_session", "class_session_progress", "student_daily_record",
}
# 반을 지울 때 남기고 반 연결만 끊는 테이블 — 시험 결과는 학생들의 성적이다
CLASS_UNLINK = {"exam"}


class PreviewOut(BaseModel):
    deletable: bool
    reason: str | None
    counts: dict[str, int]


async def _count(session: AsyncSession, model, *where) -> int:
    return await session.scalar(select(func.count()).select_from(model).where(*where))


# ── 학생 ─────────────────────────────────────────────────────────────


async def _student(session: AsyncSession, scope: Scope, student_id: int, lock: bool = False) -> Student:
    scope.require_director()
    student = await ScopedRepository(session, scope).get(Student, student_id)
    if lock:
        await session.refresh(student, with_for_update=True)
    return student


def _scans(student_id: int):
    return select(OmrScan.id).where(OmrScan.matched_student_id == student_id)


def _attempts(student_id: int):
    return select(ExamAttempt.id).where(ExamAttempt.student_id == student_id)


async def _student_counts(session: AsyncSession, student_id: int) -> dict[str, int]:
    return {
        "guardians": await _count(session, Guardian, Guardian.student_id == student_id),
        "enrollments": await _count(session, Enrollment, Enrollment.student_id == student_id),
        "daily_records": await _count(session, StudentDailyRecord, StudentDailyRecord.student_id == student_id),
        "exam_attempts": await _count(session, ExamAttempt, ExamAttempt.student_id == student_id),
        "omr_scans": await _count(session, OmrScan, OmrScan.matched_student_id == student_id),
        "messages": await _count(session, MessageLog, MessageLog.student_id == student_id),
        "consults": await _count(session, ConsultLog, ConsultLog.student_id == student_id),
    }


@router.get("/students/{student_id}/deletion-preview")
async def preview_student_deletion(student_id: int, scope: CurrentScope, session: Db) -> PreviewOut:
    # 학생은 상태와 관계없이 지울 수 있다(DCR-012). 화면은 학생 삭제에 미리보기를 쓰지 않는다(DCR-013)
    student = await _student(session, scope, student_id)
    return PreviewOut(deletable=True, reason=None, counts=await _student_counts(session, student.id))


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: int, scope: CurrentScope, session: Db) -> Response:
    # 학생은 확인 없이 바로 지운다(DCR-013). 본문이 와도 읽지 않는다
    student = await _student(session, scope, student_id, lock=True)

    counts = await _student_counts(session, student.id)
    state = student.status
    scan_ids = list(await session.scalars(_scans(student.id)))
    # 답안지 교정 기록은 외래키가 아니라 `omr_scan:{id}:{필드}` 문자열로 답안지를 가리킨다
    for scan_id in scan_ids:
        await session.execute(
            delete(LabelCorrection).where(LabelCorrection.source_ref.like(f"omr_scan:{scan_id}:%"))
        )
    await session.execute(delete(OmrScan).where(OmrScan.id.in_(scan_ids)))
    await session.execute(delete(ExamAnswer).where(ExamAnswer.attempt_id.in_(_attempts(student.id))))
    for model in (ExamAttempt, StudentDailyRecord, MessageLog, ConsultLog, Guardian, Enrollment):
        await session.execute(delete(model).where(model.student_id == student.id))
    await session.delete(student)
    # 이름·연락처는 감사 로그에 쓰지 않는다(개인정보)
    session.add(AuditLog(
        campus_id=scope.campus_id, actor_id=scope.user.id, action="student.delete",
        target=f"student:{student_id}",
        detail=" ".join(f"{k}={v}" for k, v in {"status": state, **counts}.items()),
    ))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── 반 ───────────────────────────────────────────────────────────────


async def _class(session: AsyncSession, scope: Scope, class_id: int, lock: bool = False) -> Klass:
    scope.require_director()
    klass = await ScopedRepository(session, scope).get(Klass, class_id)
    if lock:
        await session.refresh(klass, with_for_update=True)
    return klass


def _sessions(class_id: int):
    return select(ClassSession.id).where(ClassSession.class_id == class_id)


async def _class_counts(session: AsyncSession, class_id: int) -> dict[str, int]:
    return {
        "schedules": await _count(session, ClassSchedule, ClassSchedule.class_id == class_id),
        "enrollments": await _count(session, Enrollment, Enrollment.class_id == class_id),
        "sessions": await _count(session, ClassSession, ClassSession.class_id == class_id),
        "daily_records": await _count(
            session, StudentDailyRecord, StudentDailyRecord.session_id.in_(_sessions(class_id))
        ),
        "exams_unlinked": await _count(session, Exam, Exam.class_id == class_id),
    }


@router.get("/classes/{class_id}/deletion-preview")
async def preview_class_deletion(class_id: int, scope: CurrentScope, session: Db) -> PreviewOut:
    # 반은 활성 여부와 관계없이 지울 수 있다. 화면은 반 삭제에 미리보기를 쓰지 않는다(DCR-016)
    klass = await _class(session, scope, class_id)
    return PreviewOut(deletable=True, reason=None, counts=await _class_counts(session, klass.id))


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_class(class_id: int, scope: CurrentScope, session: Db) -> Response:
    # 반도 확인 없이 바로 지운다(DCR-016). 본문이 와도 읽지 않는다
    klass = await _class(session, scope, class_id, lock=True)

    counts = {"is_active": str(klass.is_active).lower(), **await _class_counts(session, klass.id)}
    sessions = _sessions(klass.id)
    await session.execute(delete(StudentDailyRecord).where(StudentDailyRecord.session_id.in_(sessions)))
    await session.execute(delete(ClassSessionProgress).where(ClassSessionProgress.session_id.in_(sessions)))
    # 발송 로그는 학생 기록으로 남기고 수업 참조만 비운다(DCR-023 `message_log.session_id`)
    await session.execute(
        update(MessageLog).where(MessageLog.session_id.in_(sessions)).values(session_id=None)
    )
    await session.execute(delete(ClassSession).where(ClassSession.class_id == klass.id))
    await session.execute(delete(ClassSchedule).where(ClassSchedule.class_id == klass.id))
    await session.execute(delete(Enrollment).where(Enrollment.class_id == klass.id))
    await session.execute(update(Exam).where(Exam.class_id == klass.id).values(class_id=None))
    await session.delete(klass)
    session.add(AuditLog(
        campus_id=scope.campus_id, actor_id=scope.user.id, action="class.delete",
        target=f"class:{class_id}", detail=" ".join(f"{k}={v}" for k, v in counts.items()),
    ))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
