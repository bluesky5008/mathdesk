import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import async_sessionmaker

from .auth import ensure_initial_director, router as auth_router
from .consult import router as consult_router
from .branding import router as branding_router
from .daily import router as daily_router
from .db import create_engine
from .exams import router as exams_router
from .files import router as files_router
from .masterdata import router as masterdata_router
from .messaging import router as messaging_router
from .omr import router as omr_router
from .omr_review import router as omr_review_router
from .omr_scoring import router as omr_scoring_router
from .stats import router as stats_router
from .tasks import TaskRunner, router as tasks_router
from .users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_engine()
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    await ensure_initial_director(app.state.session_factory)

    # 브라우저 콜드 스타트는 수 초다. 요청 경로에서 빼기 위해 여기서 warm으로 올린다(NFR-19).
    from .report import ReportRenderer

    app.state.report_renderer = ReportRenderer()
    await app.state.report_renderer.start()

    # 지난 프로세스가 실행 중에 끊겼으면 그 작업을 queued로 되돌려 다시 시작한다(RISK-09).
    app.state.task_runner = TaskRunner(app.state.session_factory)
    app.state.background = set()  # 실행 중인 작업 루프가 GC로 사라지지 않게 붙잡는다
    resume = asyncio.create_task(app.state.task_runner.resume())
    try:
        yield
    finally:
        resume.cancel()
        await app.state.report_renderer.stop()
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

    @app.middleware("http")
    async def no_store_api_responses(request: Request, call_next):
        """API 응답은 캐시하지 않는다. CDN이 인증된 응답을 엣지에 보관하면
        URL만으로 열람할 수 있게 된다(실제로 발생했다)."""
        response = await call_next(request)
        if request.url.path.startswith("/api"):
            response.headers["Cache-Control"] = "no-store, private"
        return response

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(branding_router)
    app.include_router(masterdata_router)
    app.include_router(consult_router)
    app.include_router(daily_router)
    app.include_router(stats_router)
    app.include_router(messaging_router)
    app.include_router(files_router)
    app.include_router(exams_router)
    app.include_router(omr_router)
    app.include_router(omr_review_router)
    app.include_router(omr_scoring_router)
    app.include_router(tasks_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    dist = Path(web_dist or os.environ.get("MATHDESK_WEB_DIST", ""))
    if dist.name and dist.is_dir():
        _mount_web(app, dist)
    return app


app = create_app()
