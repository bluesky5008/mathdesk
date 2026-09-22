EXPECTED_TABLES = {
    "campus",
    "app_user",
    "app_user_campus",
    "student",
    "guardian",
    "class",
    "class_schedule",
    "enrollment",
    "class_session",
    "class_session_progress",
    "student_daily_record",
    "grade_comment",
    "message_template",
    "message_log",
    "integration_setting",
    "audit_log",
    "user_session",
}


def test_migration_roundtrip_creates_and_drops_every_table(
    empty_database, table_names, alembic
):
    alembic(empty_database, "upgrade", "head")
    assert EXPECTED_TABLES <= table_names()

    alembic(empty_database, "downgrade", "base")
    assert table_names() - {"alembic_version"} == set()
