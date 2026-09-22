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


@pytest.fixture
def empty_database() -> str:
    database = urlsplit(TEST_DATABASE_URL).path.lstrip("/")
    asyncio.run(_recreate(database))
    return TEST_DATABASE_URL


@pytest.fixture
def table_names():
    return lambda: asyncio.run(_table_names())


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
