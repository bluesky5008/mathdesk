"""TASK-27 — M9 상담일지(FR-39, DES-04).

권한은 설계의 권한 매트릭스를 따른다. 원장은 캠퍼스 전체, 강사는 담당 반 학생만.
강사는 자기가 쓴 기록만 고친다(매트릭스가 정하지 않은 부분, 작업 기록 참조).
"""
import pytest


@pytest.fixture
def taught(api, klass, world):
    """강사 A가 맡은 반(학생 셋)과 반에 속하지 않은 학생 하나."""
    api.patch(
        f"/api/classes/{klass['class_id']}",
        json={"name": "고2 윤B", "grade": "고2", "teacher_id": world["teacher_a"]},
    )
    outsider = api.post("/api/students", json={"name": "반 밖"}).json()["id"]
    return {**klass, "outsider": outsider}


def _consults(api, student_id):
    return api.get(f"/api/students/{student_id}/consults")


def _add(api, student_id, **body):
    payload = {"consulted_on": "2026-09-20", "content": "미적분 개념 복습 필요", **body}
    return api.post(f"/api/students/{student_id}/consults", json=payload)


def test_consults_are_recorded_listed_newest_first_and_edited(api, taught):
    student = taught["student_ids"][0]
    first = _add(api, student, consulted_on="2026-09-10", content="첫 상담")
    second = _add(api, student, consulted_on="2026-09-20", content="모의고사 결과 상담", follow_up="오답 노트 확인")
    assert first.status_code == 201, first.text

    listed = _consults(api, student).json()

    assert [c["content"] for c in listed] == ["모의고사 결과 상담", "첫 상담"]
    assert listed[0]["follow_up"] == "오답 노트 확인"
    assert listed[0]["author"] == {"id": api.ids["director_a"], "name": "director_a"}

    edited = api.patch(
        f"/api/students/{student}/consults/{second.json()['id']}",
        json={"consulted_on": "2026-09-21", "content": "모의고사 결과 상담", "follow_up": None},
    )
    assert edited.status_code == 200
    assert (edited.json()["consulted_on"], edited.json()["follow_up"]) == ("2026-09-21", None)


def test_content_is_required_and_bounded(api, taught):
    student = taught["student_ids"][0]

    assert _add(api, student, content="").status_code == 422
    assert _add(api, student, content="   ").status_code == 422
    assert _add(api, student, content="가" * 5001).status_code == 422
    assert _add(api, student, consulted_on="not-a-date").status_code == 422


def test_a_consult_is_reached_only_through_its_own_student(api, taught):
    first, other = taught["student_ids"][:2]
    consult = _add(api, first).json()["id"]

    response = api.patch(
        f"/api/students/{other}/consults/{consult}", json={"consulted_on": "2026-09-20", "content": "x"}
    )

    assert response.status_code == 404


def test_other_campus_cannot_see_or_write(api, taught):
    student = taught["student_ids"][0]
    _add(api, student)

    api.sign_in("director_b")

    assert _consults(api, student).status_code == 403
    assert _add(api, student).status_code == 403


def test_teacher_works_only_with_own_class_students_and_own_entries(api, taught):
    student = taught["student_ids"][0]
    by_director = _add(api, student, content="원장 상담").json()["id"]

    api.sign_in("teacher_a")
    own = _add(api, student, content="강사 상담")

    assert own.status_code == 201
    assert [c["content"] for c in _consults(api, student).json()] == ["강사 상담", "원장 상담"]
    assert _consults(api, taught["outsider"]).status_code == 403
    assert _add(api, taught["outsider"]).status_code == 403
    edit = {"consulted_on": "2026-09-20", "content": "고침"}
    assert api.patch(f"/api/students/{student}/consults/{own.json()['id']}", json=edit).status_code == 200
    assert api.patch(f"/api/students/{student}/consults/{by_director}", json=edit).status_code == 403
