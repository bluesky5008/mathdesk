"""포털 계정 발급·재발급·상태(FR-48 상세, AC-50·AC-52, DES-26 상세, DCR-024).

로그인 ID는 전화번호 숫자열이고 초기 비밀번호는 로그인 ID와 같다. 발급된 계정은 최초 로그인에서
비밀번호를 바꾸기 전에는 아무 기능도 쓰지 못하고(`must_change_password`), 발급 유효기간이 지나면
로그인이 거부된다(`auth.issue_expired`). 한 번호는 계정 하나다 — 학부모 번호가 겹치면(형제) 같은
계정에 학생을 더 연결한다.
"""
import re
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import issue_expired
from .db import get_session
from .models import (
    PORTAL_ROLES,
    AppUser,
    AppUserCampus,
    AppUserStudent,
    AuditLog,
    Guardian,
    Student,
    UserSession,
)
from .scope import CurrentScope, Scope, ScopedRepository
from .security import hash_password

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["portal-accounts"])

Kind = Literal["student", "guardian"]
ACTIVE_STUDENT = ("enrolled", "paused")


class AccountOut(BaseModel):
    state: str  # none · pending · active · expired · inactive
    login_id: str | None = None
    user_id: int | None = None


class GuardianAccountOut(AccountOut):
    guardian_id: int


class AccountsOut(BaseModel):
    student: AccountOut
    guardians: list[GuardianAccountOut]


class IssueIn(BaseModel):
    kind: Kind
    guardian_id: int | None = None  # 비우면 대표 보호자


class IssuedOut(BaseModel):
    user_id: int
    login_id: str
    state: str
    linked: bool  # 기존 학부모 계정에 연결만 한 경우(형제)


def normalize_phone(phone: str | None) -> str | None:
    """숫자만 남긴 10~11자리. 그 밖은 None."""
    digits = re.sub(r"\D", "", phone or "")
    return digits if 10 <= len(digits) <= 11 else None


def account_state(user: AppUser | None, now: datetime | None = None) -> str:
    if user is None:
        return "none"
    if not user.is_active:
        return "inactive"
    if user.must_change_password:
        return "expired" if issue_expired(user, now or datetime.now(UTC)) else "pending"
    return "active"


def _links_of(student_id: int):
    return (
        select(AppUserStudent, AppUser)
        .join(AppUser, AppUser.id == AppUserStudent.user_id)
        .where(AppUserStudent.student_id == student_id)
    )


async def _linked(session: AsyncSession, student_id: int) -> list[tuple[AppUserStudent, AppUser]]:
    return [(link, user) for link, user in await session.execute(_links_of(student_id))]


async def portal_summary(session: AsyncSession, student_ids: list[int]) -> dict[int, dict[str, str]]:
    """학생 목록 열용 요약. 학부모 계정이 여럿이면 먼저 발급된 것을 보인다."""
    summary = {sid: {"student": "none", "guardian": "none"} for sid in student_ids}
    now = datetime.now(UTC)
    rows = await session.execute(
        select(AppUserStudent, AppUser)
        .join(AppUser, AppUser.id == AppUserStudent.user_id)
        .where(AppUserStudent.student_id.in_(student_ids))
        .order_by(AppUserStudent.created_at, AppUser.id)
    )
    for link, user in rows:
        entry = summary[link.student_id]
        if entry[user.role] == "none":
            entry[user.role] = account_state(user, now)
    return summary


async def _has_active_student(session: AsyncSession, user_id: int) -> bool:
    return bool(
        await session.scalar(
            select(func.count())
            .select_from(AppUserStudent)
            .join(Student, Student.id == AppUserStudent.student_id)
            .where(AppUserStudent.user_id == user_id, Student.status.in_(ACTIVE_STUDENT))
        )
    )


async def _set_active(session: AsyncSession, scope: Scope, user: AppUser, active: bool) -> None:
    if user.is_active == active:
        return
    user.is_active = active
    if not active:
        await session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.add(AuditLog(
        campus_id=scope.campus_id, actor_id=scope.user.id,
        action="portal.activate" if active else "portal.deactivate", target=f"app_user:{user.id}",
    ))


async def sync_portal_access(session: AsyncSession, scope: Scope, student_id: int) -> None:
    """학생 상태가 바뀐 뒤 — 재원·휴원 학생 연결이 하나도 없는 계정은 비활성, 있으면 활성(FR-48 상세)."""
    for _, user in await _linked(session, student_id):
        await _set_active(session, scope, user, await _has_active_student(session, user.id))


async def _delete_user(session: AsyncSession, user_id: int) -> None:
    """연결이 남지 않은 포털 계정을 세션·캠퍼스 연결과 함께 지운다. 감사 로그는 행위자만 비운다."""
    await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
    await session.execute(delete(AppUserCampus).where(AppUserCampus.user_id == user_id))
    await session.execute(update(AuditLog).where(AuditLog.actor_id == user_id).values(actor_id=None))
    await session.execute(delete(AppUser).where(AppUser.id == user_id))


async def _unlink(session: AsyncSession, link: AppUserStudent) -> bool:
    """연결을 끊고, 그 계정의 마지막 연결이었으면 계정도 지운다. 지웠으면 True."""
    user_id = link.user_id
    await session.delete(link)
    await session.flush()
    remaining = await session.scalar(
        select(func.count()).select_from(AppUserStudent).where(AppUserStudent.user_id == user_id)
    )
    if remaining:
        return False
    await _delete_user(session, user_id)
    return True


async def count_orphan_accounts(session: AsyncSession, student_id: int) -> int:
    """학생을 지우면 함께 사라질 포털 계정 수(삭제 미리보기)."""
    link_counts = (
        select(AppUserStudent.user_id, func.count().label("n"))
        .group_by(AppUserStudent.user_id)
        .subquery()
    )
    return await session.scalar(
        select(func.count())
        .select_from(AppUserStudent)
        .join(link_counts, link_counts.c.user_id == AppUserStudent.user_id)
        .where(AppUserStudent.student_id == student_id, link_counts.c.n == 1)
    )


async def remove_student_links(session: AsyncSession, student_id: int) -> None:
    """학생 삭제(DES-04 상세): 연결을 지우고 고아가 된 포털 계정을 지운다."""
    for link, _ in await _linked(session, student_id):
        await _unlink(session, link)


# ── REST ──────────────────────────────────────────────────────────────


async def _student(session: AsyncSession, scope: Scope, student_id: int) -> Student:
    return await ScopedRepository(session, scope).get(Student, student_id)


async def _guardians(session: AsyncSession, student_id: int) -> list[Guardian]:
    return list(
        await session.scalars(select(Guardian).where(Guardian.student_id == student_id).order_by(Guardian.id))
    )


@router.get("/students/{student_id}/portal-accounts")
async def read_accounts(student_id: int, scope: CurrentScope, session: Db) -> AccountsOut:
    """강사도 담당 반 학생의 발급 상태를 본다(버튼은 원장만)."""
    from .masterdata import visible_students

    if await session.scalar(visible_students(session, scope).where(Student.id == student_id)) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")
    now = datetime.now(UTC)
    linked = await _linked(session, student_id)
    student_user = next((u for l, u in linked if u.role == "student"), None)
    by_guardian = {l.guardian_id: u for l, u in linked if u.role == "guardian"}
    return AccountsOut(
        student=AccountOut(
            state=account_state(student_user, now),
            login_id=student_user.login_id if student_user else None,
            user_id=student_user.id if student_user else None,
        ),
        guardians=[
            GuardianAccountOut(
                guardian_id=g.id,
                state=account_state(by_guardian.get(g.id), now),
                login_id=by_guardian[g.id].login_id if g.id in by_guardian else None,
                user_id=by_guardian[g.id].id if g.id in by_guardian else None,
            )
            for g in await _guardians(session, student_id)
        ],
    )


def _audit(scope: Scope, action: str, user_id: int, student_id: int) -> AuditLog:
    # 전화번호는 쓰지 않는다(개인정보)
    return AuditLog(
        campus_id=scope.campus_id, actor_id=scope.user.id, action=action,
        target=f"app_user:{user_id}", detail=f"student={student_id}",
    )


@router.post("/students/{student_id}/portal-accounts", status_code=status.HTTP_201_CREATED)
async def issue_account(student_id: int, payload: IssueIn, scope: CurrentScope, session: Db) -> IssuedOut:
    scope.require_director()
    student = await _student(session, scope, student_id)

    guardian: Guardian | None = None
    if payload.kind == "student":
        raw = student.phone
        missing = "학생 연락처를 먼저 등록하세요."
    else:
        guardians = await _guardians(session, student_id)
        guardian = next((g for g in guardians if payload.guardian_id in (None, g.id)), None)
        raw = guardian.phone if guardian else None
        missing = "학부모 연락처를 먼저 등록하세요."
    if not raw:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, missing)
    login_id = normalize_phone(raw)
    if login_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "전화번호는 숫자 10~11자리여야 합니다.")

    # 같은 종류의 연결이 이미 있으면: 같은 번호면 거부, 번호가 바뀌었으면 옛 연결을 끊고 새로 발급(FR-48 상세)
    for link, user in await _linked(session, student_id):
        same_kind = user.role == payload.kind and (
            payload.kind == "student" or link.guardian_id in (None, guardian.id)
        )
        if not same_kind:
            continue
        if user.login_id == login_id:
            raise HTTPException(status.HTTP_409_CONFLICT, "이미 발급된 계정입니다.")
        await _unlink(session, link)

    existing = await session.scalar(select(AppUser).where(AppUser.login_id == login_id))
    now = datetime.now(UTC)
    if existing is not None:
        if not (payload.kind == "guardian" and existing.role == "guardian"):
            role = {"student": "학생", "guardian": "학부모", "director": "원장", "teacher": "강사"}[existing.role]
            raise HTTPException(status.HTTP_409_CONFLICT, f"이미 {role} 계정이 쓰는 번호입니다.")
        session.add(AppUserStudent(user_id=existing.id, student_id=student_id, guardian_id=guardian.id))
        await session.flush()
        await _set_active(session, scope, existing, await _has_active_student(session, existing.id))
        session.add(_audit(scope, "portal.link", existing.id, student_id))
        await session.commit()
        return IssuedOut(user_id=existing.id, login_id=login_id, state=account_state(existing, now), linked=True)

    user = AppUser(
        login_id=login_id,
        password_hash=hash_password(login_id),
        display_name=student.name if payload.kind == "student" else f"{student.name} 학부모",
        role=payload.kind,
        is_active=student.status in ACTIVE_STUDENT,
        must_change_password=True,
        issued_at=now,
    )
    session.add(user)
    await session.flush()
    session.add(AppUserCampus(user_id=user.id, campus_id=scope.campus_id))
    session.add(AppUserStudent(
        user_id=user.id, student_id=student_id, guardian_id=guardian.id if guardian else None
    ))
    session.add(_audit(scope, "portal.issue", user.id, student_id))
    await session.commit()
    return IssuedOut(user_id=user.id, login_id=login_id, state=account_state(user, now), linked=False)


@router.post("/students/{student_id}/portal-accounts/{user_id}/reissue", status_code=status.HTTP_204_NO_CONTENT)
async def reissue_account(student_id: int, user_id: int, scope: CurrentScope, session: Db) -> Response:
    """비밀번호를 로그인 ID로 되돌리고 변경 대기로. 그 계정의 로그인은 모두 끊는다."""
    scope.require_director()
    await _student(session, scope, student_id)
    user = next((u for l, u in await _linked(session, student_id) if u.id == user_id), None)
    if user is None or user.role not in PORTAL_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")

    user.password_hash = hash_password(user.login_id)
    user.must_change_password = True
    user.issued_at = datetime.now(UTC)
    user.failed_login_count = 0
    user.locked_until = None
    await session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.add(_audit(scope, "portal.reissue", user.id, student_id))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
