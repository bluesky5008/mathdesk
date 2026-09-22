from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from .auth import ensure_initial_director, router as auth_router
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


app = FastAPI(title="mathdesk API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(masterdata_router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
