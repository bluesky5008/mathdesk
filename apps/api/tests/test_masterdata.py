import pytest

from mathdesk.masterdata import validate_omr_number


@pytest.mark.parametrize(
    "value,valid",
    [
        ("90000001", True),
        ("12345601", True),
        ("00000001", False),  # 1열은 1~9
        ("18600001", False),  # 3열은 0~5
        ("10000091", False),  # 7열은 0~2
        ("1000001", False),  # 8자리가 아님
        ("1000000a", False),
    ],
)
def test_omr_number_range_per_digit(value, valid):
    assert (validate_omr_number(value) is None) is valid


def _student(api, **overrides):
    payload = {"name": "김나윤", "school": "한영고", "grade": "고2", "omr_number": "90000001"}
    return api.post("/api/students", json=payload | overrides)


def test_student_is_created_and_listed(api):
    api.sign_in("director_a")

    created = _student(api)

    assert created.status_code == 201
    assert created.json()["omr_number"] == "90000001"
    assert [s["name"] for s in api.get("/api/students").json()] == ["김나윤"]


def test_student_with_out_of_range_omr_number_is_rejected(api):
    api.sign_in("director_a")

    assert _student(api, omr_number="00000001").status_code == 422
    assert _student(api, omr_number="18600001").status_code == 422
    assert api.get("/api/students").json() == []


def test_duplicate_omr_number_in_same_campus_is_rejected(api):
    api.sign_in("director_a")
    _student(api)

    duplicated = _student(api, name="다른 학생")

    assert duplicated.status_code == 409


def test_enrollment_resolves_class_membership_on_a_date(api):
    api.sign_in("director_a")
    student_id = _student(api).json()["id"]
    class_id = api.post(
        "/api/classes",
        json={
            "name": "고2 윤B",
            "grade": "고2",
            "schedules": [{"weekday": 4, "start_time": "18:00", "end_time": "22:00"}],
        },
    ).json()["id"]

    api.post(
        f"/api/classes/{class_id}/enrollments",
        json={"student_id": student_id, "start_date": "2026-03-02", "end_date": "2026-06-30"},
    )

    on_term = api.get(f"/api/classes/{class_id}/enrollments", params={"on": "2026-04-01"})
    after_term = api.get(f"/api/classes/{class_id}/enrollments", params={"on": "2026-07-01"})

    assert [row["student_id"] for row in on_term.json()] == [student_id]
    assert after_term.json() == []


def test_teacher_cannot_read_a_class_they_do_not_teach(api):
    api.sign_in("director_a")
    class_id = api.post("/api/classes", json={"name": "고3 윤A", "grade": "고3"}).json()["id"]

    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert api.get(f"/api/classes/{class_id}/enrollments").status_code == 403
    assert api.get("/api/classes").json() == []


def test_teacher_reads_own_class_and_its_students(api):
    api.sign_in("director_a")
    student_id = _student(api).json()["id"]
    class_id = api.post(
        "/api/classes",
        json={"name": "고2 윤B", "grade": "고2", "teacher_id": api.ids["teacher_a"]},
    ).json()["id"]
    api.post(
        f"/api/classes/{class_id}/enrollments",
        json={"student_id": student_id, "start_date": "2026-03-02"},
    )

    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert [row["id"] for row in api.get("/api/classes").json()] == [class_id]
    assert [s["id"] for s in api.get("/api/students").json()] == [student_id]


def test_withdrawn_student_leaves_the_enrolled_list_but_keeps_past_records(api, klass):
    """FR-05: 퇴원은 상태 전이이며 과거 기록을 지우지 않는다."""
    student_id = klass["student_ids"][0]
    params = {"class_id": klass["class_id"], "date": "2026-09-18"}
    session_id = api.get("/api/daily", params=params).json()["session"]["id"]
    api.put(
        f"/api/daily/{session_id}/records",
        json={"records": [{"student_id": student_id, "homework_grade": "A"}]},
    )

    updated = api.patch(
        f"/api/students/{student_id}",
        json={"name": "김나윤", "omr_number": "10000100", "status": "withdrawn"},
    )

    assert updated.status_code == 200
    assert updated.json()["status"] == "withdrawn"
    enrolled = api.get("/api/students", params={"status": "enrolled"}).json()
    assert [student["id"] for student in enrolled] == klass["student_ids"][1:]
    records = api.get("/api/daily", params=params).json()["records"]
    kept = next(record for record in records if record["student_id"] == student_id)
    assert kept["homework_grade"] == "A"
