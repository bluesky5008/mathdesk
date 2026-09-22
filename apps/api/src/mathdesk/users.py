from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import AppUser, AppUserCampus, Campus
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
    user = await session.scalar(
        _users_in_campus(scope.campus_id).where(AppUser.id == user_id)
    )
    if user is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await session.commit()
    return UserOut.model_validate(user, from_attributes=True)
