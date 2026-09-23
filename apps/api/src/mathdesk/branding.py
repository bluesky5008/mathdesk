"""학원 브랜드 설정 — FR-40.

학원명은 `campus.name`을 단일 소스로 쓴다. `integration_setting`에 또 두면 같은 사실이
두 곳에 생겨 갈라진다. 로고와 시그니처 색만 설정 테이블에 둔다.

로고·색은 민감값이 아니므로 평문으로 저장한다. [DES-20]은 민감값만 암호화하도록 규정하며,
실제 시크릿(알리고 키 등)이 들어오는 시점에 암호화 계층이 필요하다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import Campus, IntegrationSetting
from .scope import CurrentScope

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api/settings", tags=["settings"])

LOGO_KEY = "brand.logo"
COLOUR_KEY = "brand.colour"
HEX_PATTERN = r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$"


class BrandIn(BaseModel):
    campus_name: str = Field(min_length=1, max_length=100)
    # 이 값은 카드의 CSS 선언 안으로 들어간다. 형식을 강제하지 않으면 CSS 주입이 된다.
    brand_colour: str | None = Field(default=None, pattern=HEX_PATTERN)
    logo_data_url: str | None = Field(default=None, max_length=500_000)


class BrandOut(BaseModel):
    campus_name: str
    brand_colour: str | None
    logo_data_url: str | None


async def _settings(session: AsyncSession, campus_id: int) -> dict[str, str]:
    rows = await session.scalars(
        select(IntegrationSetting).where(
            IntegrationSetting.campus_id == campus_id,
            IntegrationSetting.key.in_([LOGO_KEY, COLOUR_KEY]),
        )
    )
    return {row.key: row.value_encrypted for row in rows}


async def load_brand(session: AsyncSession, campus_id: int) -> tuple[str | None, str | None]:
    """카드 렌더러가 쓰는 조회 경로. (시그니처 색, 로고 data URL)"""
    values = await _settings(session, campus_id)
    return values.get(COLOUR_KEY), values.get(LOGO_KEY)


async def _store(session: AsyncSession, campus_id: int, key: str, value: str | None) -> None:
    existing = await session.get(IntegrationSetting, (campus_id, key))
    if value is None:
        if existing is not None:
            await session.delete(existing)
        return
    if existing is None:
        session.add(IntegrationSetting(campus_id=campus_id, key=key, value_encrypted=value))
    else:
        existing.value_encrypted = value


@router.get("/brand")
async def read_brand(scope: CurrentScope, session: Db) -> BrandOut:
    campus = await session.get(Campus, scope.campus_id)
    colour, logo = await load_brand(session, scope.campus_id)
    return BrandOut(campus_name=campus.name, brand_colour=colour, logo_data_url=logo)


@router.put("/brand")
async def write_brand(payload: BrandIn, scope: CurrentScope, session: Db) -> BrandOut:
    scope.require_director()
    campus = await session.get(Campus, scope.campus_id)
    campus.name = payload.campus_name
    await _store(session, scope.campus_id, COLOUR_KEY, payload.brand_colour)
    await _store(session, scope.campus_id, LOGO_KEY, payload.logo_data_url)
    await session.commit()
    return BrandOut(
        campus_name=campus.name,
        brand_colour=payload.brand_colour,
        logo_data_url=payload.logo_data_url,
    )
