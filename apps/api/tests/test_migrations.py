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
    "stored_file",
    "exam",
    "exam_question",
    "exam_attempt",
    "exam_answer",
    "omr_scan",
    "label_correction",
    "llm_call_log",
    "consult_log",
}

# 기준선 v3 (DCR-002): 공급자가 가변이고 캐싱 후 실비용을 재구성할 수 있어야 한다(NFR-15).
LLM_CALL_LOG_COLUMNS = {
    "id",
    "campus_id",
    "purpose",
    "provider",
    "model",
    "exam_id",
    "prompt_tokens",
    "completion_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "cost",
    "created_at",
}


def test_migration_roundtrip_creates_and_drops_every_table(
    empty_database, table_names, alembic
):
    alembic(empty_database, "upgrade", "head")
    assert EXPECTED_TABLES <= table_names()

    alembic(empty_database, "downgrade", "base")
    assert table_names() - {"alembic_version"} == set()


def test_llm_call_log_records_provider_and_cache_tokens(
    empty_database, column_names, alembic
):
    alembic(empty_database, "upgrade", "head")
    assert column_names("llm_call_log") == LLM_CALL_LOG_COLUMNS
