"""FR-24~FR-26 / AC-19·AC-20 — 학생·반 통계와 엑셀 내보내기."""

WEEKS = ["2026-09-04", "2026-09-11", "2026-09-18"]  # 3주 연속 금요일


def _write(api, class_id, on, records, notes=None):
    session_id = api.get(
        "/api/daily", params={"class_id": class_id, "date": on}
    ).json()["session"]["id"]
    if notes:
        api.put(f"/api/daily/{session_id}/notes", json=notes)
    api.put(f"/api/daily/{session_id}/records", json={"records": records})


def _history(api, klass):
    """3주간 학생1은 85·90·95점 A/A/B, 학생2는 65·70·75점 B/C/C. 학생3은 마지막 주 결석."""
    first, second, third = klass["student_ids"]
    scores = {first: [85, 90, 95], second: [65, 70, 75], third: [50, 55, None]}
    grades = {first: ["A", "A", "B"], second: ["B", "C", "C"], third: ["C", "D", None]}
    for index, on in enumerate(WEEKS):
        records = []
        for student_id in (first, second, third):
            score = scores[student_id][index]
            records.append(
                {
                    "student_id": student_id,
                    "attendance_status": "present" if score is not None else "absent",
                    "homework_grade": grades[student_id][index],
                    "test_score_num": score,
                }
            )
        _write(api, klass["class_id"], on, records, {"test_name": "주간", "test_max_score": 100})


def test_student_history_gives_eight_weeks_with_the_class_average(api, klass):
    _history(api, klass)
    student_id = klass["student_ids"][0]

    body = api.get(
        f"/api/stats/students/{student_id}", params={"to": WEEKS[-1], "weeks": 8}
    ).json()

    assert body["student"]["name"] == "김나윤"
    assert len(body["weeks"]) == 8
    assert [week["week_start"] for week in body["weeks"][-3:]] == [
        "2026-08-31",
        "2026-09-07",
        "2026-09-14",
    ]
    assert [week["test_average"] for week in body["weeks"][-3:]] == [85.0, 90.0, 95.0]
    # 마지막 주 반 평균은 95·75 두 명(학생3은 결석으로 점수 없음)
    assert body["weeks"][-1]["class_test_average"] == 85.0
    assert [week["homework_grades"] for week in body["weeks"][-3:]] == [["A"], ["A"], ["B"]]
    assert body["weeks"][-1]["attendance_rate"] == 100.0
    assert body["weeks"][0]["test_average"] is None


def test_class_stats_gives_rows_distribution_and_a_period_comparison(api, klass):
    _history(api, klass)

    body = api.get(
        f"/api/stats/classes/{klass['class_id']}",
        params={
            "start": WEEKS[1],
            "end": WEEKS[2],
            "compare_start": WEEKS[0],
            "compare_end": WEEKS[0],
        },
    ).json()

    rows = {row["name"]: row for row in body["period"]["students"]}
    assert rows["김나윤"]["test_average"] == 92.5
    assert rows["김나윤"]["attendance_rate"] == 100.0
    assert rows["김나윤"]["homework_completion"] == 100.0
    assert rows["김태호"]["attendance_rate"] == 50.0
    assert rows["김정현"]["homework_completion"] == 0.0  # C·C는 기준(B) 미만
    assert body["period"]["test"]["average"] == 77.0  # 90·70·55·95·75
    assert body["period"]["test"]["distribution"] == [
        {"bucket": "50~59", "count": 1},
        {"bucket": "70~79", "count": 2},
        {"bucket": "90~100", "count": 2},
    ]
    assert body["period"]["homework"]["distribution"] == {"A": 1, "B": 1, "C": 2, "D": 1}
    assert body["compare"]["test"]["average"] == 66.7  # 85·65·50
    assert body["compare"]["start"] == WEEKS[0]


def test_export_contains_the_same_rows_as_the_class_stats_screen(api, klass):
    from io import BytesIO
    from openpyxl import load_workbook

    _history(api, klass)
    params = {"class_id": klass["class_id"], "start": WEEKS[0], "end": WEEKS[2]}
    shown = api.get(f"/api/stats/classes/{klass['class_id']}", params={
        "start": WEEKS[0], "end": WEEKS[2]
    }).json()["period"]["students"]

    exported = api.get("/api/stats/export", params=params)

    assert exported.status_code == 200
    assert "spreadsheetml" in exported.headers["content-type"]
    sheet = load_workbook(BytesIO(exported.content)).active
    header, *rows = [[cell.value for cell in row] for row in sheet.iter_rows()]
    assert header == ["학생", "테스트 평균", "과제 완수율", "출결률"]
    assert rows == [
        [row["name"], row["test_average"], row["homework_completion"], row["attendance_rate"]]
        for row in shown
    ]


def test_teacher_cannot_read_history_of_a_student_outside_their_classes(api, klass):
    """설계의 권한 표: 통계는 원장이 캠퍼스 전체, 강사는 담당 반 한정이다."""
    outsider = klass["student_ids"][0]
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")  # 담당 반이 없는 강사

    assert api.get(f"/api/stats/students/{outsider}").status_code == 403
