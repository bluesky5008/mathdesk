from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import CurrentAppUser
from .db import get_session
from .models import AppUser, AppUserCampus

Db = Annotated[AsyncSession, Depends(get_session)]


@dataclass(frozen=True)
class Scope:
    """모든 도메인 조회·변경이 통과하는 단일 검사 지점."""

    user: AppUser
    campus_id: int

    @property
    def is_director(self) -> bool:
        return self.user.role == "director"

    def require_director(self) -> None:
        if not self.is_director:
            raise _forbidden()


def _forbidden() -> HTTPException:
    # 자원 존재 여부를 노출하지 않기 위해 404가 아니라 403으로 통일한다.
    return HTTPException(status.HTTP_403_FORBIDDEN, "접근 권한이 없습니다.")


async def current_scope(
    user: CurrentAppUser,
    session: Db,
    campus_id: Annotated[int | None, Header(alias="X-Campus-Id")] = None,
) -> Scope:
    # 원장이 정한 비밀번호로 들어온 사용자는 본인 비밀번호를 정하기 전까지 아무 기능도 쓰지 못한다.
    if user.must_change_password:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "비밀번호를 먼저 바꿔 주세요.")
    accessible = list(
        await session.scalars(
            select(AppUserCampus.campus_id).where(AppUserCampus.user_id == user.id)
        )
    )
    if not accessible:
        raise _forbidden()

    if campus_id is None:
        campus_id = accessible[0]
    elif campus_id not in accessible:
        raise _forbidden()

    return Scope(user=user, campus_id=campus_id)


CurrentScope = Annotated[Scope, Depends(current_scope)]


class ScopedRepository:
    """캠퍼스 필터를 빠뜨릴 수 없게 만드는 기반 클래스."""

    def __init__(self, session: AsyncSession, scope: Scope) -> None:
        self.session = session
        self.scope = scope

    def select(self, model: type) -> Select:
        return select(model).where(model.campus_id == self.scope.campus_id)

    async def get(self, model: type, entity_id: int):
        entity = await self.session.scalar(
            self.select(model).where(model.id == entity_id)
        )
        if entity is None:
            raise _forbidden()
        return entity
