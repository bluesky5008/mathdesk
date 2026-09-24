import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import get_session
from .models import AppUser, AuditLog, UserSession
from .security import UNUSABLE_PASSWORD, hash_password, verify_password

SESSION_COOKIE = "mathdesk_session"
IDLE_TIMEOUT = timedelta(hours=12)


def _max_attempts() -> int:
    """연속 실패 임계. 호출 시점에 읽어 설정 변경과 테스트가 바로 반영되게 한다."""
    return int(os.environ.get("MATHDESK_LOGIN_MAX_ATTEMPTS", "10"))


def _lockout() -> timedelta:
    return timedelta(seconds=int(os.environ.get("MATHDESK_LOGIN_LOCKOUT_SECONDS", "180")))


def _cookie_secure() -> bool:
    """HTTPS로 노출되는 구성에서만 켠다. 로컬 HTTP 개발에서 켜면 쿠키가 저장되지 않는다."""
    return os.environ.get("MATHDESK_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}

router = APIRouter(prefix="/api/auth", tags=["auth"])

SessionToken = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
Db = Annotated[AsyncSession, Depends(get_session)]


class LoginRequest(BaseModel):
    login_id: str
    password: str


class CurrentUser(BaseModel):
    id: int
    login_id: str
    display_name: str
    role: str
    must_change_password: bool


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


def _current_user_out(user: AppUser) -> CurrentUser:
    return CurrentUser.model_validate(user, from_attributes=True)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _unauthorized() -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, "인증이 필요합니다.")


async def current_user(session: Db, token: SessionToken = None) -> AppUser:
    if not token:
        raise _unauthorized()

    stored = await session.scalar(
        select(UserSession).where(UserSession.token_hash == _token_hash(token))
    )
    if stored is None:
        raise _unauthorized()

    now = datetime.now(UTC)
    if now - stored.last_seen_at > IDLE_TIMEOUT:
        await session.delete(stored)
        await session.commit()
        raise _unauthorized()

    user = await session.get(AppUser, stored.user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    stored.last_seen_at = now
    await session.commit()
    return user


CurrentAppUser = Annotated[AppUser, Depends(current_user)]


@router.post("/login")
async def login(payload: LoginRequest, response: Response, session: Db) -> CurrentUser:
    now = datetime.now(UTC)
    user = await session.scalar(
        select(AppUser).where(AppUser.login_id == payload.login_id, AppUser.is_active)
    )
    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "연속 로그인 실패로 계정이 잠겼습니다. 잠시 후 다시 시도하세요.",
        )
    # 계정이 없거나 비밀번호가 설정되지 않은 경우에도 같은 검증 비용을 치른다.
    usable_hash = (
        user.password_hash
        if user is not None and user.password_hash != UNUSABLE_PASSWORD
        else None
    )
    if not verify_password(usable_hash, payload.password) or user is None:
        if user is not None:
            await _record_failure(session, user, now)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "자격 증명이 올바르지 않습니다."
        )

    user.failed_login_count = 0
    user.locked_until = None
    token = secrets.token_urlsafe(32)
    session.add(UserSession(token_hash=_token_hash(token), user_id=user.id))
    await session.commit()

    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=int(IDLE_TIMEOUT.total_seconds()),
    )
    return _current_user_out(user)


async def _record_failure(session: AsyncSession, user: AppUser, now: datetime) -> None:
    user.failed_login_count += 1
    if user.failed_login_count >= _max_attempts():
        user.locked_until = now + _lockout()
        user.failed_login_count = 0
        session.add(
            AuditLog(
                actor_id=user.id,
                action="auth.lockout",
                target=f"app_user:{user.id}",
                detail=f"연속 실패 {_max_attempts()}회, {_lockout().seconds}초 잠금",
            )
        )
    await session.commit()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, session: Db, token: SessionToken = None) -> None:
    if token:
        await session.execute(
            delete(UserSession).where(UserSession.token_hash == _token_hash(token))
        )
        await session.commit()
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
async def me(user: CurrentAppUser) -> CurrentUser:
    return _current_user_out(user)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange, user: CurrentAppUser, session: Db, token: SessionToken = None
) -> None:
    """본인 변경. 이 세션만 남기고 다른 기기의 로그인은 끊는다."""
    if not verify_password(user.password_hash, payload.current_password):
        await _record_failure(session, user, datetime.now(UTC))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "현재 비밀번호가 올바르지 않습니다.")
    if payload.new_password == payload.current_password:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "새 비밀번호는 현재 비밀번호와 달라야 합니다."
        )

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    await session.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id, UserSession.token_hash != _token_hash(token or "")
        )
    )
    session.add(AuditLog(actor_id=user.id, action="password.change", target=f"app_user:{user.id}"))
    await session.commit()


async def ensure_initial_director(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """최초 기동 시 환경변수로 원장 계정을 준비한다. 사용 중인 비밀번호는 덮어쓰지 않는다."""
    login_id = os.environ.get("MATHDESK_INITIAL_ADMIN_ID")
    password = os.environ.get("MATHDESK_INITIAL_ADMIN_PASSWORD")
    if not login_id or not password:
        return

    async with session_factory() as session:
        user = await session.scalar(select(AppUser).where(AppUser.login_id == login_id))
        if user is None:
            session.add(
                AppUser(
                    login_id=login_id,
                    password_hash=hash_password(password),
                    display_name="원장",
                    role="director",
                    must_change_password=True,
                )
            )
        elif user.password_hash == UNUSABLE_PASSWORD:
            user.password_hash = hash_password(password)
        else:
            return
        await session.commit()
