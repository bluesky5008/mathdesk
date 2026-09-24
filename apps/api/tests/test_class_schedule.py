"""TASK-63 — 반 시간표는 요일·시작 시각(FR-07, AC-37, DCR-007)."""


def _create(api, schedules):
    api.sign_in("director_a")
    return api.post("/api/classes", json={"name": "고1 인A", "grade": "고1", "schedules": schedules})


def test_a_schedule_needs_only_weekday_and_start_time(api):
    created = _create(api, [{"weekday": 1, "start_time": "18:00"}, {"weekday": 5, "start_time": "10:00"}])

    assert created.status_code == 201, created.text
    [klass] = [c for c in api.get("/api/classes").json() if c["id"] == created.json()["id"]]
    assert klass["schedules"] == [
        {"weekday": 1, "start_time": "18:00:00", "end_time": None},
        {"weekday": 5, "start_time": "10:00:00", "end_time": None},
    ]


def test_an_end_time_is_still_accepted(api):
    created = _create(api, [{"weekday": 1, "start_time": "18:00", "end_time": "22:00"}])

    assert created.status_code == 201
    assert created.json()["schedules"][0]["end_time"] == "22:00:00"


def test_editing_replaces_the_schedule(api):
    class_id = _create(api, [{"weekday": 1, "start_time": "18:00"}]).json()["id"]

    response = api.patch(f"/api/classes/{class_id}", json={
        "name": "고1 인A", "grade": "고1", "teacher_id": None, "is_active": True,
        "schedules": [{"weekday": 3, "start_time": "19:30"}],
    })

    assert response.status_code == 200
    assert response.json()["schedules"] == [{"weekday": 3, "start_time": "19:30:00", "end_time": None}]


def test_the_same_weekday_and_start_time_twice_is_rejected(api):
    twice = [{"weekday": 1, "start_time": "18:00"}, {"weekday": 1, "start_time": "18:00"}]

    assert _create(api, twice).status_code == 422
    class_id = _create(api, []).json()["id"]
    response = api.patch(f"/api/classes/{class_id}", json={
        "name": "고1 인A", "grade": "고1", "teacher_id": None, "is_active": True, "schedules": twice,
    })
    assert response.status_code == 422
