"""백그라운드 작업 실행기(DES-18).

별도 워커 프로세스를 두지 않고 FastAPI 프로세스 안에서 실행한다(Q-09 가정).
대신 **상태를 DB에 둔다**. 프로세스가 죽으면 메모리의 큐는 사라지지만 행은 남아
기동 시 `queued`부터 다시 시작한다(RISK-09 완화책).
"""
import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import get_session
from .models import BackgroundTask
from .scope import CurrentScope, ScopedRepository

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["tasks"])

Handler = Callable[[AsyncSession, BackgroundTask], Awaitable[dict | None]]

HANDLERS: dict[str, Handler] = {}


def task_handler(kind: str) -> Callable[[Handler], Handler]:
    """작업 종류별 실행 함수를 등록한다."""

    def register(function: Handler) -> Handler:
        HANDLERS[kind] = function
        return function

    return register


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TaskOut(BaseModel):
    id: int
    kind: str
    status: str
    progress: int
    result: dict | None
    error: str | None


class TaskRunner:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def enqueue(
        self, session: AsyncSession, campus_id: int, kind: str, payload: dict
    ) -> int:
        task = BackgroundTask(campus_id=campus_id, kind=kind, payload=payload)
        session.add(task)
        await session.commit()
        return task.id

    async def resume(self) -> int:
        """기동 시 호출한다. 끊긴 `running`을 `queued`로 되돌리고 대기열을 비운다."""
        async with self.session_factory() as session:
            await session.execute(
                update(BackgroundTask)
                .where(BackgroundTask.status == "running")
                .values(status="queued", started_at=None)
            )
            await session.commit()
        return await self.run_pending()

    async def run_pending(self) -> int:
        """대기 중인 작업을 순서대로 끝까지 실행하고 실행한 건수를 돌려준다."""
        count = 0
        while (task_id := await self._claim()) is not None:
            await self._run(task_id)
            count += 1
        return count

    async def _claim(self) -> int | None:
        async with self.session_factory() as session:
            task = await session.scalar(
                select(BackgroundTask)
                .where(BackgroundTask.status == "queued")
                .order_by(BackgroundTask.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if task is None:
                return None
            task.status, task.started_at = "running", _now()
            await session.commit()
            return task.id

    async def _run(self, task_id: int) -> None:
        async with self.session_factory() as session:
            task = await session.get(BackgroundTask, task_id)
            handler = HANDLERS.get(task.kind)
            try:
                if handler is None:
                    raise LookupError(f"등록되지 않은 작업 종류입니다: {task.kind}")
                task.result = await handler(session, task)
                task.status, task.progress = "done", 100
            except Exception as error:  # 작업 실패는 서버 오류가 아니라 작업의 결과다
                task.status, task.error = "failed", str(error)
            task.finished_at = _now()
            await session.commit()


@router.get("/tasks/{task_id}")
async def read_task(task_id: int, scope: CurrentScope, session: Db) -> TaskOut:
    task = await ScopedRepository(session, scope).get(BackgroundTask, task_id)
    return TaskOut.model_validate(task, from_attributes=True)
