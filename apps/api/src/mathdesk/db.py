import os
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


def create_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(database_url or os.environ["DATABASE_URL"])


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session
