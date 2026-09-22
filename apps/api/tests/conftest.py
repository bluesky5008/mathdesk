import asyncio
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg
import pytest

API_DIR = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.environ.get(
    "MATHDESK_TEST_DATABASE_URL",
    "postgresql+asyncpg://mathdesk:mathdesk@localhost:55432/mathdesk_test",
)


def _dsn(url: str, database: str | None = None) -> str:
    parts = urlsplit(url.replace("postgresql+asyncpg://", "postgresql://"))
    name = database if database is not None else parts.path.lstrip("/")
    return f"postgresql://{parts.netloc}/{name}"


async def _recreate(database: str) -> None:
    connection = await asyncpg.connect(_dsn(TEST_DATABASE_URL, "postgres"))
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{database}"')
    finally:
        await connection.close()


async def _table_names() -> set[str]:
    connection = await asyncpg.connect(_dsn(TEST_DATABASE_URL))
    try:
        rows = await connection.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        )
    finally:
        await connection.close()
    return {row["tablename"] for row in rows}


os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)


@pytest.fixture
def empty_database() -> str:
    database = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
    asyncio.run(_recreate(database))
    return TEST_DATABASE_URL


@pytest.fixture
def table_names():
    return lambda: asyncio.run(_table_names())


async def _column_names(table: str) -> set[str]:
    connection = await asyncpg.connect(_dsn(TEST_DATABASE_URL))
    try:
        rows = await connection.fetch(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1",
            table,
        )
    finally:
        await connection.close()
    return {row["column_name"] for row in rows}


@pytest.fixture
def column_names():
    return lambda table: asyncio.run(_column_names(table))


async def _scalar(query: str) -> int:
    connection = await asyncpg.connect(_dsn(TEST_DATABASE_URL))
    try:
        return await connection.fetchval(query)
    finally:
        await connection.close()


@pytest.fixture
def scalar():
    return lambda query: asyncio.run(_scalar(query))


@pytest.fixture
def alembic():
    def run(database_url: str, *args: str) -> None:
        subprocess.run(
            ["alembic", *args],
            cwd=API_DIR,
            check=True,
            env={**os.environ, "DATABASE_URL": database_url},
        )

    return run


@pytest.fixture
def migrated_database(empty_database, alembic):
    alembic(empty_database, "upgrade", "head")
    os.environ["DATABASE_URL"] = empty_database
    return empty_database


PASSWORD = "sup3r-secret-pw"


async def _create_world(database_url: str) -> dict[str, int]:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from mathdesk.models import AppUser, AppUserCampus, Campus
    from mathdesk.security import hash_password

    engine = create_async_engine(database_url)
    ids: dict[str, int] = {}
    async with async_sessionmaker(engine, expire_on_commit=False)() as session:
        for key, name in (("campus_a", "고등관"), ("campus_b", "중등관")):
            campus = Campus(name=name)
            session.add(campus)
            await session.flush()
            ids[key] = campus.id

        for login_id, role, campus_key in (
            ("director_a", "director", "campus_a"),
            ("teacher_a", "teacher", "campus_a"),
            ("director_b", "director", "campus_b"),
        ):
            user = AppUser(
                login_id=login_id,
                password_hash=hash_password(PASSWORD),
                display_name=login_id,
                role=role,
            )
            session.add(user)
            await session.flush()
            session.add(AppUserCampus(user_id=user.id, campus_id=ids[campus_key]))
            ids[login_id] = user.id
        await session.commit()
    await engine.dispose()
    return ids


@pytest.fixture
def world(migrated_database) -> dict[str, int]:
    return asyncio.run(_create_world(migrated_database))


@pytest.fixture
def api(world):
    from fastapi.testclient import TestClient

    from mathdesk.main import app

    with TestClient(app) as client:

        def sign_in(login_id: str) -> None:
            response = client.post(
                "/api/auth/login", json={"login_id": login_id, "password": PASSWORD}
            )
            assert response.status_code == 200

        client.sign_in = sign_in  # type: ignore[attr-defined]
        client.ids = world  # type: ignore[attr-defined]
        yield client


@pytest.fixture
def klass(api):
    api.sign_in("director_a")
    class_id = api.post("/api/classes", json={"name": "고2 윤B", "grade": "고2"}).json()["id"]
    student_ids = []
    for index, name in enumerate(["김나윤", "김정현", "김태호"], start=1):
        student_id = api.post(
            "/api/students", json={"name": name, "omr_number": f"1000{index:02d}00"}
        ).json()["id"]
        api.post(
            f"/api/classes/{class_id}/enrollments",
            json={"student_id": student_id, "start_date": "2026-03-02"},
        )
        student_ids.append(student_id)
    return {"class_id": class_id, "student_ids": student_ids}




@pytest.fixture
def password() -> str:
    return PASSWORD
