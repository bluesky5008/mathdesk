"""FR-07 담당 강사 — 같은 캠퍼스의 활성 강사만 새로 지정할 수 있다 (TASK-65)."""


def _create(api, teacher_id):
    return api.post("/api/classes", json={"name": "고2 윤B", "grade": "고2", "teacher_id": teacher_id})


def test_a_campus_teacher_can_be_assigned(api):
    api.sign_in("director_a")

    created = _create(api, api.ids["teacher_a"])

    assert created.status_code == 201
    assert created.json()["teacher_id"] == api.ids["teacher_a"]
    api.sign_in("teacher_a")
    assert [c["name"] for c in api.get("/api/classes").json()] == ["고2 윤B"]


def test_only_an_active_teacher_of_the_same_campus_can_be_assigned(api):
    api.sign_in("director_a")

    for teacher_id in (api.ids["director_b"], api.ids["director_a"], 99999):
        response = _create(api, teacher_id)
        assert response.status_code == 422, teacher_id
        assert "중등관" not in response.text

    api.patch(f"/api/users/{api.ids['teacher_a']}", json={"is_active": False})
    assert _create(api, api.ids["teacher_a"]).status_code == 422


def test_editing_a_class_keeps_a_teacher_who_was_later_deactivated(api):
    api.sign_in("director_a")
    klass = _create(api, api.ids["teacher_a"]).json()
    api.patch(f"/api/users/{api.ids['teacher_a']}", json={"is_active": False})

    renamed = api.patch(
        f"/api/classes/{klass['id']}",
        json={"name": "고2 윤C", "grade": "고2", "teacher_id": api.ids["teacher_a"]},
    )

    assert renamed.status_code == 200
    assert renamed.json()["teacher_id"] == api.ids["teacher_a"]


def test_a_class_can_be_updated_to_another_campus_teacher_only_if_valid(api):
    api.sign_in("director_a")
    klass = _create(api, None).json()

    response = api.patch(
        f"/api/classes/{klass['id']}",
        json={"name": "고2 윤B", "grade": "고2", "teacher_id": api.ids["director_b"]},
    )

    assert response.status_code == 422
