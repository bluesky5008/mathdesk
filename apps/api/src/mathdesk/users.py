from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import AppUser, AppUserCampus, AuditLog, Campus, UserSession
from .scope import CurrentScope
from .security import hash_password

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["users"])


class CampusOut(BaseModel):
    id: int
    name: str


class UserOut(BaseModel):
    id: int
    login_id: str
    display_name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    login_id: str = Field(min_length=3, max_length=50)
    display_name: str = Field(min_length=1, max_length=50)
    role: str = Field(pattern="^(director|teacher)$")
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    role: str | None = Field(default=None, pattern="^(director|teacher)$")
    is_active: bool | None = None


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


@router.get("/campuses")
async def list_campuses(scope: CurrentScope, session: Db) -> list[CampusOut]:
    campuses = await session.scalars(
        select(Campus)
        .join(AppUserCampus, AppUserCampus.campus_id == Campus.id)
        .where(AppUserCampus.user_id == scope.user.id)
        .order_by(Campus.id)
    )
    return [CampusOut(id=campus.id, name=campus.name) for campus in campuses]


def _users_in_campus(campus_id: int):
    return (
        select(AppUser)
        .join(AppUserCampus, AppUserCampus.user_id == AppUser.id)
        .where(AppUserCampus.campus_id == campus_id)
        .order_by(AppUser.id)
    )


@router.get("/users")
async def list_users(scope: CurrentScope, session: Db) -> list[UserOut]:
    scope.require_director()
    users = await session.scalars(_users_in_campus(scope.campus_id))
    return [UserOut.model_validate(user, from_attributes=True) for user in users]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, scope: CurrentScope, session: Db) -> UserOut:
    scope.require_director()
    if await session.scalar(select(AppUser.id).where(AppUser.login_id == payload.login_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "이미 사용 중인 아이디입니다.")

    user = AppUser(
        login_id=payload.login_id,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role=payload.role,
        must_change_password=True,
    )
    session.add(user)
    await session.flush()
    session.add(AppUserCampus(user_id=user.id, campus_id=scope.campus_id))
    await session.commit()
    return UserOut.model_validate(user, from_attributes=True)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int, payload: UserUpdate, scope: CurrentScope, session: Db
) -> UserOut:
    scope.require_director()
    user = await _user_in_campus(session, scope.campus_id, user_id)

    changes = payload.model_dump(exclude_none=True)
    stays_director = changes.get("role", user.role) == "director" and changes.get(
        "is_active", user.is_active
    )
    if user.role == "director" and user.is_active and not stays_director:
        other_directors = await session.scalar(
            select(func.count(AppUser.id))
            .join(AppUserCampus, AppUserCampus.user_id == AppUser.id)
            .where(
                AppUserCampus.campus_id == scope.campus_id,
                AppUser.role == "director",
                AppUser.is_active,
                AppUser.id != user.id,
            )
        )
        if not other_directors:
            raise HTTPException(status.HTTP_409_CONFLICT, "원장 계정이 최소 한 개는 있어야 합니다.")

    for field, value in changes.items():
        setattr(user, field, value)
    await session.commit()
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/users/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: int, payload: PasswordReset, scope: CurrentScope, session: Db
) -> None:
    """원장이 임시 비밀번호를 정한다. 본인은 다음 로그인에서 새 비밀번호를 정해야 한다."""
    scope.require_director()
    user = await _user_in_campus(session, scope.campus_id, user_id)
    if user.id == scope.user.id:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "본인 비밀번호는 비밀번호 변경에서 바꿉니다."
        )

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = True
    user.failed_login_count = 0
    user.locked_until = None
    await session.execute(delete(UserSession).where(UserSession.user_id == user.id))
    session.add(
        AuditLog(
            campus_id=scope.campus_id,
            actor_id=scope.user.id,
            action="password.reset",
            target=f"app_user:{user.id}",
        )
    )
    await session.commit()


async def _user_in_campus(session: AsyncSession, campus_id: int, user_id: int) -> AppUser:
    user = await session.scalar(_users_in_campus(campus_id).where(AppUser.id == user_id))
    if user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")
    return user
