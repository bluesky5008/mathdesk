"""AC-40: 강사는 담당 반의 반명·학년·시간표만 바꾼다 (DCR-011)."""

import pytest


@pytest.fixture
def classes(api):
    api.sign_in("director_a")
    own = api.post(
        "/api/classes",
        json={
            "name": "고1 인A",
            "grade": "1",
            "teacher_id": api.ids["teacher_a"],
            "schedules": [{"weekday": 1, "start_time": "18:00"}],
        },
    ).json()["id"]
    other = api.post("/api/classes", json={"name": "고2 윤B", "grade": "고2"}).json()["id"]
    api.sign_in("teacher_a")
    return {"own": own, "other": other}


def _body(api, **changes):
    return {
        "name": "고1 인A",
        "grade": "1",
        "teacher_id": api.ids["teacher_a"],
        "is_active": True,
        "schedules": [{"weekday": 1, "start_time": "18:00"}],
        **changes,
    }


def _stored(api, class_id):
    api.sign_in("director_a")
    return next(c for c in api.get("/api/classes").json() if c["id"] == class_id)


def test_teacher_renames_and_reschedules_own_class(api, classes):
    response = api.patch(
        f"/api/classes/{classes['own']}",
        json=_body(api, name="인A", grade="고1", schedules=[{"weekday": 3, "start_time": "17:00"}]),
    )

    assert response.status_code == 200
    stored = _stored(api, classes["own"])
    assert (stored["name"], stored["grade"]) == ("인A", "고1")
    assert [(s["weekday"], s["start_time"]) for s in stored["schedules"]] == [(3, "17:00:00")]


def test_teacher_cannot_edit_a_class_they_do_not_teach(api, classes):
    response = api.patch(
        f"/api/classes/{classes['other']}",
        json={"name": "바뀐 이름", "grade": "고2", "teacher_id": None, "is_active": True},
    )

    assert response.status_code == 403
    assert _stored(api, classes["other"])["name"] == "고2 윤B"


@pytest.mark.parametrize("changes", [{"teacher_id": None}, {"is_active": False}])
def test_teacher_cannot_change_assignment_or_active_state(api, classes, changes):
    response = api.patch(f"/api/classes/{classes['own']}", json=_body(api, name="인A", **changes))

    assert response.status_code == 403
    stored = _stored(api, classes["own"])
    assert stored["name"] == "고1 인A"
    assert stored["teacher_id"] == api.ids["teacher_a"]
    assert stored["is_active"] is True


def test_teacher_still_cannot_create_or_delete_classes(api, classes):
    assert api.post("/api/classes", json={"name": "새 반"}).status_code == 403
    assert (
        api.request("DELETE", f"/api/classes/{classes['own']}", json={"confirm_name": "고1 인A"}).status_code
        == 403
    )


def test_teacher_edit_is_audited(api, classes, scalar):
    api.patch(f"/api/classes/{classes['own']}", json=_body(api, name="인A"))

    detail = scalar("SELECT detail FROM audit_log WHERE action = 'class.update'")
    assert detail == "name"
    assert scalar("SELECT target FROM audit_log WHERE action = 'class.update'") == f"class:{classes['own']}"
