"""AC-38: 주간 시간표 (FR-42, DCR-008)."""


def _class(api, name, teacher=None, schedules=(), is_active=True):
    response = api.post(
        "/api/classes",
        json={
            "name": name,
            "grade": "고2",
            "teacher_id": api.ids[teacher] if teacher else None,
            "is_active": is_active,
            "schedules": [{"weekday": w, "start_time": t} for w, t in schedules],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def _names(slots):
    return [(s["class_name"], s["weekday"], s["start_time"]) for s in slots]


def test_director_sees_every_active_class_with_teacher_names(api):
    api.sign_in("director_a")
    _class(api, "고2 윤B", "teacher_a", [(4, "18:00"), (1, "18:00")])
    _class(api, "고3 윤A", None, [(1, "10:00")])

    body = api.get("/api/timetable").json()

    assert body["class_minutes"] == 120
    # 요일 → 시작 시각 순
    assert _names(body["slots"]) == [
        ("고3 윤A", 1, "10:00:00"),
        ("고2 윤B", 1, "18:00:00"),
        ("고2 윤B", 4, "18:00:00"),
    ]
    teacher_slot = body["slots"][1]
    assert teacher_slot["teacher"] == {"id": api.ids["teacher_a"], "name": "teacher_a"}
    assert teacher_slot["end_time"] == "20:00:00"
    assert body["slots"][0]["teacher"] is None


def test_teacher_sees_only_own_classes(api):
    api.sign_in("director_a")
    _class(api, "고2 윤B", "teacher_a", [(4, "18:00")])
    _class(api, "고3 윤A", None, [(1, "10:00")])
    _class(api, "고1 윤D", "teacher_a")

    api.sign_in("teacher_a")
    body = api.get("/api/timetable").json()

    assert _names(body["slots"]) == [("고2 윤B", 4, "18:00:00")]
    assert [c["class_name"] for c in body["unscheduled"]] == ["고1 윤D"]


def test_other_campus_classes_never_appear(api):
    api.sign_in("director_b")
    _class(api, "중2 A", None, [(2, "17:00")])

    api.sign_in("director_a")
    body = api.get("/api/timetable").json()

    assert body["slots"] == [] and body["unscheduled"] == []


def test_unscheduled_and_inactive_classes(api):
    api.sign_in("director_a")
    _class(api, "고1 윤D")
    _class(api, "고3 종강반", None, [(5, "10:00")], is_active=False)
    _class(api, "고3 종강반2", None, [], is_active=False)

    body = api.get("/api/timetable").json()

    assert body["slots"] == []
    assert body["unscheduled"] == [
        {"class_id": body["unscheduled"][0]["class_id"], "class_name": "고1 윤D", "grade": "고2",
         "teacher": None}
    ]


def test_changing_the_class_length_moves_end_times(api):
    api.sign_in("director_a")
    _class(api, "고2 윤B", None, [(6, "23:00")])

    assert api.put("/api/settings/class-minutes", json={"class_minutes": 90}).status_code == 200

    body = api.get("/api/timetable").json()
    assert body["class_minutes"] == 90
    # 자정을 넘기면 다음 날 시각으로 돌아간다
    assert body["slots"][0]["end_time"] == "00:30:00"


def test_class_length_is_director_only_and_bounded(api):
    api.sign_in("director_a")
    for minutes in (29, 481):
        assert api.put("/api/settings/class-minutes", json={"class_minutes": minutes}).status_code == 422

    api.sign_in("teacher_a")
    assert api.put("/api/settings/class-minutes", json={"class_minutes": 60}).status_code == 403


def test_class_length_is_per_campus(api):
    api.sign_in("director_b")
    api.put("/api/settings/class-minutes", json={"class_minutes": 60})

    api.sign_in("director_a")
    assert api.get("/api/timetable").json()["class_minutes"] == 120
