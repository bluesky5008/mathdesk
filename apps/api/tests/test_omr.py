"""TASK-34 — OmrReader 제품 이식(FR-32·FR-33, AC-24, AC-27, NFR-03·NFR-16, ADR-006).

실제 학생 스캔본이 없어(Q-08) 합성 답안지로만 검증한다. 현장 정확도는 미검증이다.
"""
import asyncio
import time

import numpy as np
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.models import BackgroundTask, OmrScan
from mathdesk.omr import OmrRegistrationError, OmrThresholds, TemplateOmrReader
from mathdesk.tasks import TaskRunner

from omr_synthetic import make_truth, paint, pdf, photograph, png

TEMPLATE_ID = "ksat-2027-math"


@pytest.fixture(scope="module")
def truth():
    return make_truth()


@pytest.fixture(scope="module")
def photo(truth):
    return photograph(paint(truth))


def _flags(result) -> dict[str, str]:
    return {flag["field"]: flag["code"] for flag in result.flags}


# ── 판독(DES-15) ──────────────────────────────────────────────────────


def test_distorted_sheet_reads_every_field_and_flags_the_deliberate_errors(truth, photo):
    """AC-24: 회전 3°·축소 0.6·원근 왜곡에도 30문항·수험번호·문형이 일치하고
    의도한 복수마킹(3번)·무마킹(22번)이 플래그로 분류된다."""
    result = TemplateOmrReader().read(png(photo), TEMPLATE_ID)

    assert result.exam_number == truth["exam_number"]
    assert result.form == "odd"
    for q in range(1, 31):
        if q == 3:
            continue
        assert result.answers[q] == truth["answers"][q], q
    assert _flags(result) == {"3": "multi", "22": "blank"}


def test_thresholds_come_from_settings(photo, monkeypatch):
    """RISK-01: 실스캔으로 보정할 수 있게 임계값을 설정값으로 노출한다."""
    monkeypatch.setenv("MATHDESK_OMR_ABS_TH", "250")

    result = TemplateOmrReader(OmrThresholds.from_env()).read(png(photo), TEMPLATE_ID)

    assert all(result.answers[q] is None for q in range(1, 31))
    assert _flags(result)["exam_number"] == "blank"
    assert _flags(result)["form"] == "blank"


def test_sheet_without_corner_marks_is_a_registration_error():
    blank = np.full((2480, 3508, 3), 255, np.uint8)

    with pytest.raises(OmrRegistrationError):
        TemplateOmrReader().read(png(blank), TEMPLATE_ID)


def test_unknown_template_is_rejected(photo):
    with pytest.raises(LookupError):
        TemplateOmrReader().read(png(photo), "other-form")


# ── 업로드 → 페이지 분리 → 판독(DES-15·DES-18) ─────────────────────────


def _wait(api, task_id, timeout=60.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("done", "failed"):
            return task
        time.sleep(0.2)
    raise AssertionError(f"작업이 끝나지 않았다: {task}")


def _scans(database_url: str, exam_id: int) -> list[OmrScan]:
    async def run():
        engine = create_async_engine(database_url)
        try:
            async with engine.connect() as connection:
                rows = await connection.execute(
                    select(OmrScan).where(OmrScan.exam_id == exam_id).order_by(OmrScan.page_no)
                )
                return list(rows)
        finally:
            await engine.dispose()

    return asyncio.run(run())


@pytest.fixture
def exam(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")
    return api.post("/api/exams", json={"name": "9월 모의"}).json()


def _upload(api, exam_id, name, data, content_type="application/pdf"):
    return api.post(
        f"/api/exams/{exam_id}/omr/uploads", files={"file": (name, data, content_type)}
    )


@pytest.fixture
def no_llm(monkeypatch):
    """AC-27: 외부 HTTP를 막고 모든 LLM 어댑터 호출을 기록한다."""
    import httpx

    from mathdesk import llm

    async def explode(*args, **kwargs):
        raise AssertionError("OMR 경로에서 외부 호출이 발생했다")

    monkeypatch.setattr(httpx.AsyncClient, "post", explode)
    monkeypatch.setattr(httpx.AsyncClient, "get", explode)
    calls = []

    async def spy(self, question, taxonomy):
        calls.append(type(self).__name__)
        raise AssertionError("OMR 경로에서 LLM이 호출되었다")

    for adapter in (llm.TestModeLlm, llm.AnthropicLlm, llm.OpenAICompatLlm):
        monkeypatch.setattr(adapter, "analyze", spy)
    return calls


def test_pdf_pages_are_read_into_scans_and_a_bad_page_does_not_stop_the_rest(
    api, exam, truth, photo, migrated_database, no_llm
):
    """설계 OMR 흐름 1·6: 페이지마다 판독해 `omr_scan`에 남기고, 정합 실패 페이지만 실패로 표시한다.
    AC-27(OMR 경로): 이 전체 경로에서 LLM 어댑터 호출은 0이다."""
    blank = np.full((2480, 3508, 3), 255, np.uint8)
    started = _upload(api, exam["id"], "9월.pdf", pdf([photo, blank]))
    assert started.status_code == 202

    task = _wait(api, started.json()["task_id"])

    assert task["status"] == "done", task
    assert task["result"] == {"pages": 2, "failed": 1}
    first, second = _scans(migrated_database, exam["id"])
    assert (first.page_no, second.page_no) == (1, 2)
    assert first.read_payload["exam_number"] == truth["exam_number"]
    assert first.read_payload["answers"]["30"] == truth["answers"][30]
    assert {f["field"]: f["code"] for f in first.flags} == {"3": "multi", "22": "blank"}
    assert second.read_payload["error"]
    assert second.flags == [{"field": "sheet", "code": "low_confidence"}]
    assert no_llm == []


def test_rerunning_the_read_replaces_scans_instead_of_adding(api, exam, photo, migrated_database):
    """핸들러는 멱등이어야 한다. 재기동 재개(TaskRunner.resume)가 처음부터 다시 돌린다."""
    task_id = _upload(api, exam["id"], "a.png", png(photo), "image/png").json()["task_id"]
    _wait(api, task_id)

    async def rerun():
        engine = create_async_engine(migrated_database)
        try:
            async with engine.begin() as connection:
                await connection.execute(
                    update(BackgroundTask).where(BackgroundTask.id == task_id).values(status="queued")
                )
            return await TaskRunner(async_sessionmaker(engine, expire_on_commit=False)).run_pending()
        finally:
            await engine.dispose()

    assert asyncio.run(rerun()) == 1
    assert len(_scans(migrated_database, exam["id"])) == 1


def test_upload_limits_follow_fr32(api, exam):
    """FR-32: PDF 1개 최대 20MB·30쪽."""
    too_many = pdf([np.full((100, 140, 3), 255, np.uint8)] * 31)
    assert _upload(api, exam["id"], "많음.pdf", too_many).status_code == 422
    assert _upload(api, exam["id"], "큼.pdf", b"%PDF" + b"0" * (20 * 1024 * 1024)).status_code == 413
    assert _upload(api, exam["id"], "문서.hwp", b"x", "application/octet-stream").status_code == 415


def test_teacher_cannot_upload_omr(api, exam):
    api.sign_in("teacher_a")
    assert _upload(api, exam["id"], "a.pdf", b"%PDF").status_code == 403


def test_an_oversized_pdf_page_is_rendered_within_a_bounded_size():
    """업로드한 PDF의 쪽 크기가 비정상적으로 커도 렌더 크기는 상한 안에 머문다."""
    import io

    import cv2
    import pypdfium2 as pdfium

    from mathdesk.omr import MAX_RENDER_SIDE, page_image

    document = pdfium.PdfDocument.new()
    document.new_page(14400, 14400)  # 200in × 200in — 300dpi면 6만 px
    out = io.BytesIO()
    document.save(out)

    image = cv2.imdecode(np.frombuffer(page_image(out.getvalue(), ".pdf", 0), np.uint8), cv2.IMREAD_COLOR)

    assert max(image.shape[:2]) <= MAX_RENDER_SIDE
