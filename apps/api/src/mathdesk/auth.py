import hashlib
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import get_session
from .models import AppUser, UserSession
from .security import UNUSABLE_PASSWORD, hash_password, verify_password

SESSION_COOKIE = "mathdesk_session"
IDLE_TIMEOUT = timedelta(hours=12)

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
    user = await session.scalar(
        select(AppUser).where(AppUser.login_id == payload.login_id, AppUser.is_active)
    )
    # 계정이 없거나 비밀번호가 설정되지 않은 경우에도 같은 검증 비용을 치른다.
    usable_hash = (
        user.password_hash
        if user is not None and user.password_hash != UNUSABLE_PASSWORD
        else None
    )
    if not verify_password(usable_hash, payload.password) or user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "자격 증명이 올바르지 않습니다."
        )

    token = secrets.token_urlsafe(32)
    session.add(UserSession(token_hash=_token_hash(token), user_id=user.id))
    await session.commit()

    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=int(IDLE_TIMEOUT.total_seconds()),
    )
    return CurrentUser(
        id=user.id,
        login_id=user.login_id,
        display_name=user.display_name,
        role=user.role,
    )


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
    return CurrentUser(
        id=user.id,
        login_id=user.login_id,
        display_name=user.display_name,
        role=user.role,
    )


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
                )
            )
        elif user.password_hash == UNUSABLE_PASSWORD:
            user.password_hash = hash_password(password)
        else:
            return
        await session.commit()
