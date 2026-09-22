import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker

from .auth import ensure_initial_director, router as auth_router
from .daily import router as daily_router
from .db import create_engine
from .masterdata import router as masterdata_router
from .users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine()
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await ensure_initial_director(app.state.session_factory)
    yield
    await engine.dispose()


def _mount_web(app: FastAPI, dist: Path) -> None:
    """웹 정적 빌드를 같은 오리진에서 서빙한다. API 경로는 절대 가로채지 않는다."""
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "없는 경로입니다.")
        candidate = dist / path
        if path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


def create_app(web_dist: Path | str | None = None) -> FastAPI:
    app = FastAPI(title="mathdesk API", lifespan=lifespan)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(masterdata_router)
    app.include_router(daily_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    dist = Path(web_dist or os.environ.get("MATHDESK_WEB_DIST", ""))
    if dist.name and dist.is_dir():
        _mount_web(app, dist)
    return app


app = create_app()
