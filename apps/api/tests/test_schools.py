"""DCR-015: 학교 관리와 학교 드롭다운 — FR-43, AC-42."""

import asyncio

import asyncpg

from conftest import TEST_DATABASE_URL, _dsn


def _school(api, name):
    return api.post("/api/schools", json={"name": name})


def _student(api, **fields):
    return api.post("/api/students", json={"name": "김나윤"} | fields).json()


def _patch(api, student, **changes):
    body = {k: student[k] for k in ("name", "grade", "phone", "omr_number", "status")}
    return api.patch(f"/api/students/{student['id']}", json=body | changes)


def test_schools_are_listed_by_name_with_their_student_count(api):
    api.sign_in("director_a")
    hanyoung = _school(api, " 한영고 ").json()
    _school(api, "대명고")
    _student(api, school_id=hanyoung["id"])
    _student(api, school_id=hanyoung["id"], status="withdrawn")

    listed = api.get("/api/schools").json()

    assert hanyoung["name"] == "한영고"
    assert [(s["name"], s["student_count"]) for s in listed] == [("대명고", 0), ("한영고", 2)]


def test_duplicate_or_blank_school_name_is_rejected(api):
    api.sign_in("director_a")
    _school(api, "한영고")

    assert _school(api, "  한영고").status_code == 409
    assert _school(api, "   ").status_code == 422
    assert _school(api, "가" * 101).status_code == 422


def test_the_same_school_name_may_exist_in_another_campus(api):
    api.sign_in("director_a")
    _school(api, "한영고")
    api.sign_in("director_b")

    assert _school(api, "한영고").status_code == 201
    assert [s["name"] for s in api.get("/api/schools").json()] == ["한영고"]


def test_a_student_picks_a_school_and_lists_its_name(api):
    api.sign_in("director_a")
    school = _school(api, "한영고").json()

    created = api.post("/api/students", json={"name": "김나윤", "school_id": school["id"]})

    assert created.status_code == 201, created.text
    [listed] = api.get("/api/students").json()
    assert (listed["school_id"], listed["school"]) == (school["id"], "한영고")


def test_a_school_of_another_campus_or_a_missing_one_cannot_be_picked(api):
    api.sign_in("director_b")
    other = _school(api, "중앙중").json()
    api.sign_in("director_a")
    student = _student(api)

    assert api.post("/api/students", json={"name": "김정현", "school_id": other["id"]}).status_code == 422
    assert _patch(api, student, school_id=999999).status_code == 422


def test_omitting_school_id_on_edit_leaves_the_school_alone(api):
    api.sign_in("director_a")
    school = _school(api, "한영고").json()
    student = _student(api, school_id=school["id"])

    _patch(api, student, status="paused")
    assert api.get("/api/students").json()[0]["school"] == "한영고"

    _patch(api, student, school_id=None)
    assert api.get("/api/students").json()[0]["school"] is None


def test_renaming_a_school_shows_the_new_name_on_its_students(api):
    api.sign_in("director_a")
    school = _school(api, "고1학교").json()
    _school(api, "대명고")
    _student(api, school_id=school["id"])

    renamed = api.patch(f"/api/schools/{school['id']}", json={"name": "한영고"})
    taken = api.patch(f"/api/schools/{school['id']}", json={"name": "대명고"})

    assert renamed.status_code == 200
    assert taken.status_code == 409
    assert api.get("/api/students").json()[0]["school"] == "한영고"


def test_deleting_a_school_clears_only_its_students_school(api, scalar):
    api.sign_in("director_a")
    school = _school(api, "한영고").json()
    kept = _school(api, "대명고").json()
    student = _student(api, school_id=school["id"], grade="고2", score_note="기말 90")
    _student(api, school_id=kept["id"])

    response = api.delete(f"/api/schools/{school['id']}")

    assert response.status_code == 204
    students = {s["id"]: s for s in api.get("/api/students").json()}
    cleared = students.pop(student["id"])
    assert (cleared["school_id"], cleared["school"], cleared["grade"], cleared["score_note"]) == (None, None, "고2", "기말 90")
    assert [s["school"] for s in students.values()] == ["대명고"]
    assert [s["name"] for s in api.get("/api/schools").json()] == ["대명고"]
    assert scalar("SELECT detail FROM audit_log WHERE action = 'school.delete'") == "한영고, 학생 1명"


def test_a_school_of_another_campus_cannot_be_renamed_or_deleted(api):
    api.sign_in("director_b")
    other = _school(api, "중앙중").json()
    api.sign_in("director_a")

    assert api.patch(f"/api/schools/{other['id']}", json={"name": "바꿈"}).status_code == 403
    assert api.delete(f"/api/schools/{other['id']}").status_code == 403


def test_a_teacher_cannot_use_the_school_api(api):
    api.sign_in("director_a")
    school = _school(api, "한영고").json()
    api.sign_in("teacher_a")

    assert api.get("/api/schools").status_code == 403
    assert _school(api, "대명고").status_code == 403
    assert api.patch(f"/api/schools/{school['id']}", json={"name": "바꿈"}).status_code == 403
    assert api.delete(f"/api/schools/{school['id']}").status_code == 403


# ── 마이그레이션: 학생의 학교 텍스트 ↔ 학교 연결 ─────────────────────────────


async def _sql(*statements):
    connection = await asyncpg.connect(_dsn(TEST_DATABASE_URL))
    try:
        results = []
        for statement in statements:
            results.append([tuple(r) for r in await connection.fetch(statement)])
        return results
    finally:
        await connection.close()


def test_migration_links_existing_school_text_and_restores_it_on_downgrade(empty_database, alembic):
    alembic(empty_database, "upgrade", "c4a8e2f6b1d3")
    asyncio.run(_sql(
        "INSERT INTO campus (id, name, is_active) VALUES (1, '고등관', true), (2, '중등관', true)",
        "INSERT INTO student (campus_id, name, school, status) VALUES "
        "(1, '가', ' 한영고 ', 'enrolled'), (1, '나', '한영고', 'enrolled'), (1, '다', '', 'enrolled'), "
        "(1, '라', NULL, 'enrolled'), (2, '마', '한영고', 'enrolled')",
    ))

    alembic(empty_database, "upgrade", "head")
    schools, students = asyncio.run(_sql(
        "SELECT campus_id, name FROM school ORDER BY campus_id",
        "SELECT s.name, sc.name FROM student s LEFT JOIN school sc ON sc.id = s.school_id ORDER BY s.name",
    ))
    assert schools == [(1, "한영고"), (2, "한영고")]
    assert students == [("가", "한영고"), ("나", "한영고"), ("다", None), ("라", None), ("마", "한영고")]

    alembic(empty_database, "downgrade", "c4a8e2f6b1d3")
    [restored] = asyncio.run(_sql("SELECT name, school FROM student ORDER BY name"))
    assert restored == [("가", "한영고"), ("나", "한영고"), ("다", None), ("라", None), ("마", "한영고")]
