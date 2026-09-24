"""TASK-62 — 퇴원 학생·비활성 반의 삭제(FR-05 상세·FR-07, AC-36, DES-04 상세, DCR-006)."""
import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk import deletion
from mathdesk.models import (
    AuditLog,
    Base,
    ConsultLog,
    Enrollment,
    Exam,
    ExamAnswer,
    ExamAttempt,
    Guardian,
    LabelCorrection,
    MessageLog,
    OmrScan,
    Student,
    StudentDailyRecord,
)
from mathdesk.models.daily import ClassSession

from test_message_send import DATE, prepared  # noqa: F401 — 픽스처 재사용


def _db(database_url, body):
    async def run():
        engine = create_async_engine(database_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                return await body(session)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _count(database_url, model, *where):
    return _db(database_url, lambda s: s.scalar(select(func.count()).select_from(model).where(*where)))


@pytest.fixture
def history(api, klass, prepared, migrated_database):
    """김나윤(첫 학생)에게 모든 종류의 기록을, 김정현(둘째)에게 비교용 기록을 만든다."""
    target, other = klass["student_ids"][:2]
    session_id = prepared["session_id"]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": other, "attendance_status": "present"}]},
    )
    assert api.post("/api/messages/send", json={
        "session_id": session_id, "student_id": target, "recipients": ["guardian"],
    }).status_code == 200
    api.post(f"/api/students/{target}/consults", json={"consulted_on": DATE, "content": "상담"})
    exam = api.post("/api/exams", json={"name": "9월 모의", "class_id": klass["class_id"]}).json()

    async def body(session):
        for student_id in (target, other):
            attempt = ExamAttempt(exam_id=exam["id"], student_id=student_id, form_type="odd",
                                  score=90, source="omr")
            session.add(attempt)
            await session.flush()
            session.add(ExamAnswer(attempt_id=attempt.id, question_no=1, raw_value="3", is_correct=True))
            scan = OmrScan(exam_id=exam["id"], page_no=1, status="applied",
                           matched_student_id=student_id, read_payload={}, flags=[])
            session.add(scan)
            await session.flush()
            session.add(LabelCorrection(kind="omr", source_ref=f"omr_scan:{scan.id}:3",
                                        before_value=None, after_value="3"))
        await session.commit()

    _db(migrated_database, body)
    return {"target": target, "other": other, "exam_id": exam["id"], "class_id": klass["class_id"],
            "session_id": session_id}


def _withdraw(api, student_id):
    student = api.get("/api/students").json()
    row = next(s for s in student if s["id"] == student_id)
    body = {k: row[k] for k in ("name", "school", "grade", "phone", "omr_number")} | {"status": "withdrawn"}
    assert api.patch(f"/api/students/{student_id}", json=body).status_code == 200
    return row


def _delete(api, path, name):
    return api.request("DELETE", path, json={"confirm_name": name})


def _student_rows(db, student_id):
    return {
        "student": _count(db, Student, Student.id == student_id),
        "guardians": _count(db, Guardian, Guardian.student_id == student_id),
        "enrollments": _count(db, Enrollment, Enrollment.student_id == student_id),
        "daily_records": _count(db, StudentDailyRecord, StudentDailyRecord.student_id == student_id),
        "exam_attempts": _count(db, ExamAttempt, ExamAttempt.student_id == student_id),
        "omr_scans": _count(db, OmrScan, OmrScan.matched_student_id == student_id),
        "messages": _count(db, MessageLog, MessageLog.student_id == student_id),
        "consults": _count(db, ConsultLog, ConsultLog.student_id == student_id),
    }


# ── 학생(AC-36 ①②④) ────────────────────────────────────────────────


def test_an_enrolled_student_cannot_be_deleted(api, history, migrated_database):
    before = _student_rows(migrated_database, history["target"])

    preview = api.get(f"/api/students/{history['target']}/deletion-preview").json()
    response = _delete(api, f"/api/students/{history['target']}", "김나윤")

    assert preview["deletable"] is False and "퇴원" in preview["reason"]
    assert response.status_code == 409
    assert _student_rows(migrated_database, history["target"]) == before


def test_preview_counts_what_will_be_deleted(api, history):
    _withdraw(api, history["target"])

    preview = api.get(f"/api/students/{history['target']}/deletion-preview").json()

    assert preview["deletable"] is True
    assert preview["counts"] == {
        "guardians": 1, "enrollments": 1, "daily_records": 1, "exam_attempts": 1,
        "omr_scans": 1, "messages": 1, "consults": 1,
    }


def test_a_wrong_confirmation_name_changes_nothing(api, history, migrated_database):
    _withdraw(api, history["target"])
    before = _student_rows(migrated_database, history["target"])

    response = _delete(api, f"/api/students/{history['target']}", "김나운")

    assert response.status_code == 422
    assert _student_rows(migrated_database, history["target"]) == before


def test_deleting_a_withdrawn_student_removes_all_their_records_and_only_theirs(
    api, history, migrated_database
):
    row = _withdraw(api, history["target"])
    other_before = _student_rows(migrated_database, history["other"])

    response = _delete(api, f"/api/students/{history['target']}", "김나윤")

    assert response.status_code == 204, response.text
    assert set(_student_rows(migrated_database, history["target"]).values()) == {0}
    assert _count(migrated_database, LabelCorrection, LabelCorrection.source_ref.like("omr_scan:%")) == 1
    assert _student_rows(migrated_database, history["other"]) == other_before
    # 반 평균 같은 수치는 남은 학생 기준으로 다시 계산된다
    results = api.get(f"/api/exams/{history['exam_id']}/results").json()
    assert [r["student"]["id"] for r in results["students"]] == [history["other"]]
    # 수험번호를 다시 쓸 수 있다
    reuse = api.post("/api/students", json={"name": "새 학생", "omr_number": row["omr_number"]})
    assert reuse.status_code == 201


def test_student_deletion_is_audited_without_the_name(api, history, migrated_database):
    _withdraw(api, history["target"])
    _delete(api, f"/api/students/{history['target']}", "김나윤")

    logs = _db(migrated_database, lambda s: s.scalars(select(AuditLog).where(AuditLog.action == "student.delete")))
    [log] = list(logs)
    assert log.target == f"student:{history['target']}"
    assert "김나윤" not in (log.detail or "") and "010" not in (log.detail or "")
    assert "daily_records=1" in log.detail


# ── 반(AC-36 ①③④) ─────────────────────────────────────────────────


def _deactivate(api, class_id):
    klass = next(c for c in api.get("/api/classes", params={"include_inactive": "true"}).json() if c["id"] == class_id)
    body = {k: klass[k] for k in ("name", "grade", "teacher_id", "schedules")} | {"is_active": False}
    assert api.patch(f"/api/classes/{class_id}", json=body).status_code == 200


def test_an_active_class_cannot_be_deleted(api, history, migrated_database):
    response = _delete(api, f"/api/classes/{history['class_id']}", "고2 윤B")

    assert response.status_code == 409
    assert _count(migrated_database, ClassSession, ClassSession.class_id == history["class_id"]) == 1


def test_deleting_an_inactive_class_removes_its_lessons_but_keeps_its_exams(api, history, migrated_database):
    _deactivate(api, history["class_id"])
    preview = api.get(f"/api/classes/{history['class_id']}/deletion-preview").json()
    assert preview["deletable"] is True
    assert preview["counts"] == {
        "schedules": 0, "enrollments": 3, "sessions": 1, "daily_records": 2, "exams_unlinked": 1,
    }

    response = _delete(api, f"/api/classes/{history['class_id']}", "고2 윤B")

    assert response.status_code == 204, response.text
    assert _count(migrated_database, ClassSession, ClassSession.class_id == history["class_id"]) == 0
    assert _count(migrated_database, StudentDailyRecord) == 0
    assert _count(migrated_database, Enrollment) == 0
    exam = _db(migrated_database, lambda s: s.get(Exam, history["exam_id"]))
    assert exam.class_id is None
    assert _count(migrated_database, ExamAttempt) == 2  # 학생 성적은 남는다
    assert _count(migrated_database, Student) == 3  # 학생은 반과 별개다


# ── 권한 ──────────────────────────────────────────────────────────


def test_only_directors_of_the_campus_can_delete(api, history):
    _withdraw(api, history["target"])

    api.sign_in("teacher_a")
    assert _delete(api, f"/api/students/{history['target']}", "김나윤").status_code == 403
    assert api.get(f"/api/students/{history['target']}/deletion-preview").status_code == 403

    api.sign_in("director_b")
    assert _delete(api, f"/api/students/{history['target']}", "김나윤").status_code == 403


# ── 삭제 규칙의 누락 방지(DES-04 상세) ─────────────────────────────


def test_every_table_that_points_at_a_deleted_row_is_handled():
    """학생·반과, 삭제되는 행을 가리키는 모든 외래키가 삭제 규칙에 분류되어 있어야 한다.
    새 테이블이 학생·반을 참조하게 되면 이 테스트가 먼저 실패한다."""
    tables = Base.metadata.tables
    handled = deletion.STUDENT_CASCADE | deletion.CLASS_CASCADE | deletion.CLASS_UNLINK
    deleted = {"student", "class"} | deletion.STUDENT_CASCADE | deletion.CLASS_CASCADE
    # 삭제되지 않고 이력으로 남아도 되는 참조(삭제 대상 행을 가리키지 않음)
    for table in tables.values():
        for fk in table.foreign_keys:
            if fk.column.table.name in deleted and table.name not in deleted:
                assert table.name in handled, f"{table.name}.{fk.parent.name} → {fk.column.table.name}"
