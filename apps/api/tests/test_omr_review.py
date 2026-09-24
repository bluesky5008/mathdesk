"""TASK-35 — 학생 매칭·검수·라벨 교정(FR-34·FR-35, AC-25 전반부, DES-16).

AC-25 전반부 중 "검수 전 채점에 반영되지 않음"은 여기서 상태(`needs_review`)로 고정하고,
반영 단계에서 그 상태를 거르는 검사는 채점(TASK-36)에서 한다.
"""
import asyncio
import time

import numpy as np
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from mathdesk.models import LabelCorrection

from omr_synthetic import make_truth, paint, pdf, photograph

# 1쪽: 3번 복수마킹·22번 무마킹 / 2쪽: 깨끗한 답안 / 3쪽: 등록되지 않은 번호 / 4쪽: 정합 실패
FLAGGED = make_truth(7)
CLEAN = {**make_truth(8), "double_mark": None}
CLEAN["answers"][22] = 15
STRANGER = {**make_truth(9), "double_mark": None}
STRANGER["answers"][22] = 15
LATE = "19000100"  # 3쪽 학생이 원래 칠했어야 할 번호


@pytest.fixture(scope="module")
def sheets() -> bytes:
    blank = np.full((2480, 3508, 3), 255, np.uint8)
    return pdf([photograph(paint(t)) for t in (FLAGGED, CLEAN, STRANGER)] + [blank])


def _wait(api, task_id, timeout=60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("done", "failed"):
            return task
        time.sleep(0.2)
    raise AssertionError(f"작업이 끝나지 않았다: {task}")


@pytest.fixture
def read(api, sheets, tmp_path, monkeypatch):
    """네 쪽을 판독한 시험. 학생 셋의 수험번호가 등록되어 있다(3쪽 번호는 없다)."""
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")
    students = {
        key: api.post("/api/students", json={"name": name, "omr_number": number}).json()["id"]
        for key, name, number in (
            ("flagged", "김하나", FLAGGED["exam_number"]),
            ("clean", "이두리", CLEAN["exam_number"]),
            ("late", "박세찬", LATE),
        )
    }
    exam = api.post("/api/exams", json={"name": "9월 모의"}).json()
    started = api.post(
        f"/api/exams/{exam['id']}/omr/uploads",
        files={"file": ("9월.pdf", sheets, "application/pdf")},
    )
    assert _wait(api, started.json()["task_id"])["status"] == "done"
    scans = api.get(f"/api/exams/{exam['id']}/omr/scans").json()
    return {"exam_id": exam["id"], "students": students, "scans": scans}


def _codes(scan) -> dict[str, str]:
    return {flag["field"]: flag["code"] for flag in scan["flags"]}


def _corrections(database_url: str) -> list[LabelCorrection]:
    async def run():
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                rows = await connection.execute(select(LabelCorrection).order_by(LabelCorrection.id))
                return list(rows)
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _patch(api, read, page, body):
    scan = read["scans"][page - 1]
    return api.patch(f"/api/exams/{read['exam_id']}/omr/scans/{scan['id']}", json=body)


# ── 매칭과 검수 대기(FR-34, AC-25 전반부) ──────────────────────────────


def test_scans_are_matched_by_exam_number_and_only_clean_sheets_skip_review(read):
    flagged, clean, stranger, broken = read["scans"]

    assert [s["page_no"] for s in read["scans"]] == [1, 2, 3, 4]
    assert flagged["student"]["id"] == read["students"]["flagged"]
    assert flagged["status"] == "needs_review"
    assert _codes(flagged) == {"3": "multi", "22": "blank"}

    assert clean["student"] == {"id": read["students"]["clean"], "name": "이두리"}
    assert clean["status"] == "read"
    assert clean["flags"] == []
    assert clean["answers"]["22"] == 15

    assert stranger["student"] is None
    assert stranger["status"] == "needs_review"
    assert _codes(stranger) == {"student": "unmatched"}

    assert broken["status"] == "needs_review"
    assert broken["error"]
    assert _codes(broken) == {"sheet": "low_confidence", "student": "unmatched"}


# ── 교정과 라벨 교정 기록(FR-35) ───────────────────────────────────────


def test_correcting_every_flag_readies_the_scan_and_records_each_change(api, read, migrated_database):
    response = _patch(api, read, 1, {"answers": {"3": 4, "22": 15}})

    assert response.status_code == 200, response.text
    scan = response.json()
    assert scan["status"] == "read"
    assert scan["flags"] == []
    assert scan["answers"]["3"] == 4 and scan["answers"]["22"] == 15
    corrections = _corrections(migrated_database)
    assert [(c.source_ref, c.before_value, c.after_value) for c in corrections] == [
        (f"omr_scan:{scan['id']}:3", None, "4"),
        (f"omr_scan:{scan['id']}:22", None, "15"),
    ]
    assert all(c.kind == "omr" and c.corrected_by for c in corrections)
    assert corrections[0].asset_ref.endswith(f"/omr/scans/{scan['id']}/image?field=3")


def test_confirming_a_value_as_read_clears_the_flag_without_a_correction(api, read, migrated_database):
    """고칠 것이 없으면 판독값 그대로 보내 확인한다(문항 확인 화면과 같은 규칙)."""
    response = _patch(api, read, 1, {"answers": {"3": None, "22": None}})

    assert response.json()["status"] == "read"
    assert _corrections(migrated_database) == []


def test_partial_review_keeps_the_scan_waiting(api, read):
    scan = _patch(api, read, 1, {"answers": {"3": 4}}).json()

    assert scan["status"] == "needs_review"
    assert _codes(scan) == {"22": "blank"}


def test_unmatched_sheet_can_be_assigned_by_hand(api, read, migrated_database):
    scan = _patch(api, read, 3, {"student_id": read["students"]["late"]}).json()

    assert scan["student"]["id"] == read["students"]["late"]
    assert scan["status"] == "read"
    # 학생 지정은 답안지 판독값의 교정이 아니다
    assert _corrections(migrated_database) == []


def test_correcting_the_exam_number_rematches_the_student(api, read, migrated_database):
    scan = _patch(api, read, 3, {"exam_number": LATE}).json()

    assert scan["exam_number"] == LATE
    assert scan["student"]["id"] == read["students"]["late"]
    assert scan["status"] == "read"
    [correction] = _corrections(migrated_database)
    assert (correction.before_value, correction.after_value) == (STRANGER["exam_number"], LATE)


def test_an_unreadable_page_is_cleared_only_by_entering_the_whole_sheet(api, read):
    answers = {str(q): 1 for q in range(1, 31)}
    partial = _patch(api, read, 4, {"student_id": read["students"]["late"], "form": "odd"}).json()
    assert _codes(partial) == {"sheet": "low_confidence"}

    scan = _patch(api, read, 4, {"answers": answers}).json()

    assert scan["status"] == "read"
    assert scan["form"] == "odd"
    assert scan["answers"] == answers


def test_corrections_are_validated(api, read, world):
    assert _patch(api, read, 1, {"answers": {"3": 6}}).status_code == 422  # 객관식은 1~5
    assert _patch(api, read, 1, {"answers": {"16": 1000}}).status_code == 422  # 단답형은 0~999
    assert _patch(api, read, 1, {"answers": {"31": 1}}).status_code == 422
    assert _patch(api, read, 1, {"exam_number": "12345"}).status_code == 422
    assert _patch(api, read, 1, {"form": "both"}).status_code == 422

    api.sign_in("director_b")
    other = api.post("/api/students", json={"name": "다른 관"}).json()["id"]
    api.sign_in("director_a")
    assert _patch(api, read, 3, {"student_id": other}).status_code == 403


def test_teachers_can_see_scans_but_not_correct_them(api, read):
    api.sign_in("teacher_a")

    assert api.get(f"/api/exams/{read['exam_id']}/omr/scans").status_code == 200
    assert _patch(api, read, 1, {"answers": {"3": 4}}).status_code == 403


# ── 원본 대조 이미지(FR-35) ─────────────────────────────────────────────


def test_review_images_are_crops_of_the_aligned_page(api, read):
    base = f"/api/exams/{read['exam_id']}/omr/scans"
    flagged, broken = read["scans"][0], read["scans"][3]

    crop = api.get(f"{base}/{flagged['id']}/image", params={"field": "3"})
    page = api.get(f"{base}/{flagged['id']}/image")
    raw = api.get(f"{base}/{broken['id']}/image", params={"field": "3"})

    assert crop.headers["content-type"] == "image/png"
    assert "no-store" in crop.headers["cache-control"]
    assert 0 < len(crop.content) < len(page.content)
    assert raw.status_code == 200  # 정합하지 못한 쪽은 원본 전체를 준다
    assert api.get(f"{base}/{flagged['id']}/image", params={"field": "../x"}).status_code == 422


# ── 판독 → 검수 → 반영 한 흐름(TASK-36 연결) ────────────────────────────


def test_uploaded_sheets_reach_scores_only_after_review(api, read):
    """실제 판독 결과(`read_payload`)가 채점 엔진에 그대로 들어가는지 본다."""
    key = [CLEAN["answers"][q] for q in range(1, 31)]
    api.patch(f"/api/exams/{read['exam_id']}", json={"question_count": 30, "answer_key_odd": key})
    base = f"/api/exams/{read['exam_id']}"

    first = api.post(f"{base}/omr/apply").json()
    assert (first["applied"], first["waiting"]) == (1, 3)
    scores = {row["student"]["name"]: row["score"] for row in api.get(f"{base}/results").json()["students"]}
    assert scores == {"이두리": 100}

    _patch(api, read, 1, {"answers": {"3": key[2], "22": key[21]}})
    second = api.post(f"{base}/omr/apply").json()

    assert (second["applied"], second["waiting"]) == (2, 2)
    names = {row["student"]["name"] for row in api.get(f"{base}/results").json()["students"]}
    assert names == {"이두리", "김하나"}
