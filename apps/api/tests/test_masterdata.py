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


def test_inactive_class_leaves_the_default_list_and_the_active_count(api, klass):
    """FR-07: 반은 지우지 않고 비활성으로 내린다. 과거 기록은 그대로 열린다."""
    class_id = klass["class_id"]
    params = {"class_id": class_id, "date": "2026-09-18"}

    updated = api.patch(
        f"/api/classes/{class_id}",
        json={"name": "고2 윤B", "grade": "고2", "is_active": False},
    )

    assert updated.status_code == 200
    assert updated.json()["is_active"] is False
    assert api.get("/api/classes").json() == []
    listed = api.get("/api/classes", params={"include_inactive": True}).json()
    assert [klass_out["id"] for klass_out in listed] == [class_id]
    assert api.get("/api/dashboard", params=params).json()["campus"]["active_classes"] == 0
    assert api.get("/api/daily", params=params).status_code == 200


def test_released_enrollment_leaves_the_roster_but_past_sessions_stay(api, klass):
    """FR-08: 해제는 배정 기간을 끝내는 것이며 그 이전 수업일의 명단은 그대로다."""
    class_id, student_id = klass["class_id"], klass["student_ids"][0]
    enrollment_id = api.get(f"/api/classes/{class_id}/enrollments").json()[0]["id"]

    released = api.patch(
        f"/api/classes/{class_id}/enrollments/{enrollment_id}",
        json={"end_date": "2026-09-17"},
    )

    assert released.status_code == 200
    assert released.json()["end_date"] == "2026-09-17"
    current = api.get(f"/api/classes/{class_id}/enrollments", params={"on": "2026-09-18"}).json()
    assert student_id not in [row["student_id"] for row in current]
    after = api.get("/api/daily", params={"class_id": class_id, "date": "2026-09-18"}).json()
    assert student_id not in [record["student_id"] for record in after["records"]]
    before = api.get("/api/daily", params={"class_id": class_id, "date": "2026-09-11"}).json()
    assert student_id in [record["student_id"] for record in before["records"]]


def test_enrollment_cannot_end_before_it_starts(api, klass):
    class_id = klass["class_id"]
    enrollment_id = api.get(f"/api/classes/{class_id}/enrollments").json()[0]["id"]

    rejected = api.patch(
        f"/api/classes/{class_id}/enrollments/{enrollment_id}",
        json={"end_date": "2026-03-01"},
    )

    assert rejected.status_code == 422


def test_enrollment_cannot_overlap_an_existing_period(api, klass):
    """TASK-71: 배정 시작일을 고를 수 있게 되며 같은 반에 기간이 겹치는 배정이 생기면 일일 명단에 두 번 나온다."""
    class_id, student_id = klass["class_id"], klass["student_ids"][0]
    enrollment_id = api.get(f"/api/classes/{class_id}/enrollments").json()[0]["id"]
    api.patch(f"/api/classes/{class_id}/enrollments/{enrollment_id}", json={"end_date": "2026-09-17"})

    overlapping = api.post(
        f"/api/classes/{class_id}/enrollments",
        json={"student_id": student_id, "start_date": "2026-09-10"},
    )
    earlier_open = api.post(
        f"/api/classes/{class_id}/enrollments",
        json={"student_id": klass["student_ids"][1], "start_date": "2026-01-05"},
    )
    after_end = api.post(
        f"/api/classes/{class_id}/enrollments",
        json={"student_id": student_id, "start_date": "2026-09-18"},
    )

    assert overlapping.status_code == 422
    assert earlier_open.status_code == 422
    assert after_end.status_code == 201
    daily = api.get("/api/daily", params={"class_id": class_id, "date": "2026-09-11"}).json()
    assert [record["student_id"] for record in daily["records"]].count(student_id) == 1


# ── DCR-014: 학부모 연락처(대표 보호자)와 성적 칸 — AC-41 ──────────────────


def _guardians(api, student_id):
    return [
        {k: g[k] for k in ("relation", "name", "phone", "is_notify_target")}
        for g in api.get(f"/api/students/{student_id}/guardians").json()
    ]


def _patch(api, student, **changes):
    body = {k: student[k] for k in ("name", "school", "grade", "phone", "omr_number", "status")}
    return api.patch(f"/api/students/{student['id']}", json=body | changes)


def test_guardian_phone_and_score_note_are_saved_and_listed(api):
    api.sign_in("director_a")

    created = _student(api, guardian_phone="010-2222-3333", score_note="중간고사 85, 서술형 약함")

    assert created.status_code == 201, created.text
    [listed] = api.get("/api/students").json()
    assert listed["guardian_phone"] == "010-2222-3333"
    assert listed["score_note"] == "중간고사 85, 서술형 약함"
    assert _guardians(api, listed["id"]) == [
        {"relation": "학부모", "name": "", "phone": "010-2222-3333", "is_notify_target": True}
    ]


def test_editing_guardian_phone_keeps_the_existing_relation_and_name(api):
    api.sign_in("director_a")
    student = _student(api).json()
    api.post(f"/api/students/{student['id']}/guardians", json={"relation": "모", "name": "박영희", "phone": "010-1111-1111"})

    response = _patch(api, student, guardian_phone="010-9999-9999")

    assert response.status_code == 200
    assert response.json()["guardian_phone"] == "010-9999-9999"
    assert _guardians(api, student["id"]) == [
        {"relation": "모", "name": "박영희", "phone": "010-9999-9999", "is_notify_target": True}
    ]


def test_clearing_guardian_phone_removes_the_guardian(api):
    api.sign_in("director_a")
    student = _student(api, guardian_phone="010-2222-3333").json()

    _patch(api, student, guardian_phone=None)

    assert _guardians(api, student["id"]) == []
    assert api.get("/api/students").json()[0]["guardian_phone"] is None


def test_omitting_the_new_fields_leaves_guardian_and_score_note_alone(api):
    api.sign_in("director_a")
    student = _student(api, guardian_phone="010-2222-3333", score_note="기말 90").json()

    _patch(api, student, status="paused")

    [listed] = api.get("/api/students").json()
    assert (listed["status"], listed["guardian_phone"], listed["score_note"]) == ("paused", "010-2222-3333", "기말 90")


def test_score_note_over_500_characters_is_rejected(api):
    api.sign_in("director_a")

    assert _student(api, score_note="가" * 501).status_code == 422
    assert _student(api, score_note="가" * 500).status_code == 201


# DCR-026 (AC-53): 같은 학부모 번호를 가진 다른 학생이 있으면 안내한다(저장은 막지 않는다)
def test_students_sharing_a_guardian_phone_are_named_for_each_other(api):
    api.sign_in("director_a")
    first = api.post("/api/students", json={"name": "김나윤", "guardian_phone": "010-9876-5432"})
    assert first.json()["guardian_phone_shared_with"] == []

    second = api.post("/api/students", json={"name": "김정현", "guardian_phone": "010 9876 5432"})
    assert second.status_code == 201
    assert second.json()["guardian_phone_shared_with"] == ["김나윤"]

    other = api.post("/api/students", json={"name": "박서준", "guardian_phone": "010-1111-2222"})
    assert other.json()["guardian_phone_shared_with"] == []
    none = api.post("/api/students", json={"name": "이하준"})
    assert none.json()["guardian_phone_shared_with"] == []

    listed = {s["name"]: s["guardian_phone_shared_with"] for s in api.get("/api/students").json()}
    assert listed == {"김나윤": ["김정현"], "김정현": ["김나윤"], "박서준": [], "이하준": []}

    edited = api.patch(f"/api/students/{other.json()['id']}", json={"name": "박서준", "guardian_phone": "01098765432"})
    assert edited.json()["guardian_phone_shared_with"] == ["김나윤", "김정현"]
