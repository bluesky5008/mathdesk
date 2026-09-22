import asyncio

from mathdesk.seed import seed


def test_seed_creates_four_classes_and_47_students(empty_database, scalar, alembic):
    alembic(empty_database, "upgrade", "head")

    asyncio.run(seed(empty_database))

    assert scalar('SELECT count(*) FROM "class"') == 4
    assert scalar("SELECT count(*) FROM student") == 47
    assert scalar("SELECT count(*) FROM enrollment") == 47
    assert scalar("SELECT count(*) FROM student WHERE omr_number IS NULL") == 0
