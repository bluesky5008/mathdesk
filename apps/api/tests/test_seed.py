import asyncio

from mathdesk.seed import seed


def test_seed_creates_four_classes_and_47_students(empty_database, scalar, alembic):
    alembic(empty_database, "upgrade", "head")

    asyncio.run(seed(empty_database))

    assert scalar('SELECT count(*) FROM "class"') == 4
    assert scalar("SELECT count(*) FROM student") == 47
    assert scalar("SELECT count(*) FROM enrollment") == 47
    assert scalar("SELECT count(*) FROM student WHERE omr_number IS NULL") == 0


def test_seed_reuses_an_already_created_director_account(empty_database, scalar, alembic):
    """초기 원장 계정이 먼저 만들어진 DB(테스트 운영 기동 직후)에서도 시드가 동작해야 한다."""
    alembic(empty_database, "upgrade", "head")
    asyncio.run(_create_director(empty_database))

    asyncio.run(seed(empty_database))

    assert scalar("SELECT count(*) FROM app_user WHERE login_id = 'director'") == 1
    assert scalar('SELECT count(*) FROM "class"') == 4


def test_seed_reuses_the_campus_made_for_the_initial_director(
    empty_database, scalar, alembic, monkeypatch
):
    """기동 시 초기 원장에게 캠퍼스가 만들어진 뒤(테스트 운영 기동 직후)에도 시드가 동작해야 한다."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from mathdesk.auth import ensure_initial_director

    alembic(empty_database, "upgrade", "head")
    monkeypatch.setenv("MATHDESK_INITIAL_ADMIN_ID", "director")
    monkeypatch.setenv("MATHDESK_INITIAL_ADMIN_PASSWORD", "temp-pass-1234")

    async def boot():
        engine = create_async_engine(empty_database)
        await ensure_initial_director(async_sessionmaker(engine))
        await engine.dispose()

    asyncio.run(boot())

    asyncio.run(seed(empty_database))

    assert scalar("SELECT count(*) FROM campus") == 1
    assert scalar("SELECT name FROM campus") == "전병훈 수학학원 고등관"
    assert scalar("SELECT count(*) FROM app_user_campus") == 1
    assert scalar('SELECT count(*) FROM "class"') == 4


async def _create_director(database_url: str) -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from mathdesk.models import AppUser

    engine = create_async_engine(database_url)
    async with async_sessionmaker(engine)() as session:
        session.add(
            AppUser(
                login_id="director",
                password_hash="x",
                display_name="원장",
                role="director",
            )
        )
        await session.commit()
    await engine.dispose()
