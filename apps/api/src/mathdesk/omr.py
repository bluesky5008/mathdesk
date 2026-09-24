"""OMR 판독(DES-15)과 업로드 → 페이지 분리 → 판독 작업(FR-32·FR-33, ADR-006).

[프로토타입](../../../../prototype/omr/omr_reader.py)을 이식했다.
정합(모서리 마크 호모그래피) → R채널 드롭아웃 → 버블 농도 → 필드 판정·플래그.
전부 로컬 CPU에서 돈다. 이 모듈에는 외부 네트워크 호출이 없어야 한다(NFR-04, AC-27).
학생 매칭·`needs_review` 전이·검수는 DES-16(TASK-35)이 맡는다.
"""
import asyncio
import io
import json
import os
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Annotated, Protocol

import cv2
import numpy as np
import pypdfium2 as pdfium
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .files import save_upload
from .models import BackgroundTask, Exam, OmrScan, StoredFile
from .scope import CurrentScope, ScopedRepository
from .storage import storage
from .tasks import task_handler

TEMPLATES = Path(__file__).parent / "omr_templates"
TEMPLATE_ID = "ksat-2027-math"
CANVAS_W, CANVAS_H = 3508, 2480  # 기준 캔버스(A4 가로 300dpi)
RENDER_SCALE = 300 / 72  # PDF 1pt = 1/72in → 300dpi
MAX_RENDER_SIDE = 5000  # px. A4 300dpi의 긴 변(3508)에 여유를 둔 값

MAX_OMR_BYTES = 20 * 1024 * 1024  # FR-32
MAX_OMR_PAGES = 30
OMR_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}

# 필드 하나에 여러 판정이 겹치면 더 심각한 것 하나만 남긴다
SEVERITY = ("multi", "blank", "low_confidence")


class OmrRegistrationError(Exception):
    """페이지를 기준 캔버스에 맞추지 못했다. 그 페이지만 실패로 남긴다(설계 OMR 흐름 6)."""


@dataclass(frozen=True)
class OmrThresholds:
    """판정 임계값. 실스캔 보정 전까지 합성 기준값이다(RISK-01, Q-08)."""

    abs_th: float = 70.0  # 이 농도 이상이어야 마킹으로 본다(0=흰색, 255=검정)
    rel: float = 0.5  # 같은 행 최댓값 대비 이 비율 이상이어야 마킹으로 본다
    margin: float = 25.0  # 1·2위 농도 차가 이보다 작으면 저신뢰

    @classmethod
    def from_env(cls) -> "OmrThresholds":
        return cls(
            abs_th=float(os.environ.get("MATHDESK_OMR_ABS_TH", 70.0)),
            rel=float(os.environ.get("MATHDESK_OMR_REL", 0.5)),
            margin=float(os.environ.get("MATHDESK_OMR_MARGIN", 25.0)),
        )


@dataclass
class OmrReadResult:
    template_id: str
    exam_number: str | None = None  # 읽지 못한 자리는 `?`
    form: str | None = None  # `odd`·`even`
    absent: bool = False
    answers: dict[int, int | None] = field(default_factory=dict)
    flags: list[dict[str, str]] = field(default_factory=list)  # {"field", "code"}

    def payload(self) -> dict:
        return {
            "template_id": self.template_id,
            "exam_number": self.exam_number,
            "form": self.form,
            "absent": self.absent,
            "answers": {str(q): v for q, v in self.answers.items()},
        }


class OmrReader(Protocol):
    def read(self, page_image: bytes, template_id: str) -> OmrReadResult: ...


@cache
def load_template(template_id: str) -> dict:
    # 요청 값으로 경로를 만들지 않는다. 제품에 들어 있는 템플릿 중에서만 고른다
    known = {path.stem: path for path in TEMPLATES.glob("*.json")}
    if template_id not in known:
        raise LookupError(f"알 수 없는 OMR 템플릿입니다: {template_id}")
    return json.loads(known[template_id].read_text(encoding="utf-8"))


def _corner_marks(img: np.ndarray) -> np.ndarray:
    """검정 모서리 마크 4개(TL, TR, BL, BR)의 중심."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    black = (gray < 90).astype(np.uint8) * 255
    black = cv2.morphologyEx(black, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    scale = gray.shape[1] / CANVAS_W
    blobs = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < 120 * scale * scale or w > 200 * scale or h > 200 * scale:
            continue
        if cv2.contourArea(contour) / area < 0.6:
            continue
        blobs.append((x + w / 2, y + h / 2))
    if len(blobs) < 4:
        raise OmrRegistrationError("모서리 마크를 찾지 못했습니다.")
    # 모서리 마크는 가장 바깥의 검정 덩어리다. 두 대각선 방향의 극값을 고른다
    # (사진 속에서 용지가 축소·회전되어 있어도 성립한다)
    points = np.array(blobs)
    s, d = points[:, 0] + points[:, 1], points[:, 0] - points[:, 1]
    return np.float32([points[s.argmin()], points[d.argmax()], points[d.argmin()], points[s.argmax()]])


def _register(img: np.ndarray, tpl: dict) -> np.ndarray:
    corners = tpl["timing_marks"]["corners"]
    target = np.float32([
        [corners[k]["x"] * CANVAS_W, corners[k]["y"] * CANVAS_H]
        for k in ("top_left", "top_right", "bottom_left", "bottom_right")
    ])
    matrix = cv2.getPerspectiveTransform(_corner_marks(img), target)
    return cv2.warpPerspective(img, matrix, (CANVAS_W, CANVAS_H), borderValue=(255, 255, 255))


class TemplateOmrReader:
    """템플릿 좌표 판독기(ADR-006). 학습 모델 판독기로 바꿔 끼울 수 있게 `OmrReader` 뒤에 둔다."""

    def __init__(self, thresholds: OmrThresholds | None = None) -> None:
        self.th = thresholds or OmrThresholds()

    def read(self, page_image: bytes, template_id: str) -> OmrReadResult:
        tpl = load_template(template_id)
        img = cv2.imdecode(np.frombuffer(page_image, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise OmrRegistrationError("이미지를 읽을 수 없습니다.")
        # 분홍 인쇄는 R 채널에서 사라지고 검정 펜 마킹만 남는다
        dark = 255 - _register(img, tpl)[:, :, 2]
        rx = tpl["bubble_radius"]["rx"] * CANVAS_W
        ry = tpl["bubble_radius"]["ry"] * CANVAS_H

        def level(bubble: dict) -> float:
            cx, cy = int(bubble["x"] * CANVAS_W), int(bubble["y"] * CANVAS_H)
            ax, ay = max(1, int(rx * 0.8)), max(1, int(ry * 0.8))
            # 캔버스 전체가 아니라 버블 주변만 잘라 평균을 낸다(버블 437개 × 캔버스는 느리다)
            patch = dark[cy - ay:cy + ay + 1, cx - ax:cx + ax + 1]
            mask = np.zeros(patch.shape, np.uint8)
            cv2.ellipse(mask, (ax, ay), (ax, ay), 0, 0, 360, 255, -1)
            return float(patch[mask == 255].mean())

        result = OmrReadResult(template_id=template_id)

        def flag(name: str, codes: list[str]) -> None:
            for code in SEVERITY:
                if code in codes:
                    result.flags.append({"field": name, "code": code})
                    return

        for f in tpl["fields"]:
            kind = f["kind"]
            if kind == "multiple_choice":
                by_question: dict[int, list] = {}
                for b in f["bubbles"]:
                    by_question.setdefault(b["q"], []).append((b["choice"], level(b)))
                for q, values in by_question.items():
                    marked, code = self._decide(values)
                    result.answers[q] = marked[0] if code in ("ok", "low_confidence") else None
                    flag(str(q), [code])
            elif kind == "short_answer":
                q = f["bubbles"][0]["q"]
                columns: dict[str, list] = {}
                for b in f["bubbles"]:
                    columns.setdefault(b["place"], []).append((b["digit"], level(b)))
                digits, codes = {}, []
                for place in ("hundreds", "tens", "ones"):
                    marked, code = self._decide(columns[place])
                    digits[place] = marked[0] if len(marked) == 1 else None
                    # 백·십의 자리 무마킹은 정상이다(두 자리·한 자리 답)
                    if code != "blank" or place == "ones":
                        codes.append(code)
                if "multi" in codes or digits["ones"] is None:
                    result.answers[q] = None
                else:
                    result.answers[q] = (
                        (digits["hundreds"] or 0) * 100 + (digits["tens"] or 0) * 10 + digits["ones"]
                    )
                flag(str(q), codes)
            elif kind == "digit_columns":
                columns = {}
                for b in f["bubbles"]:
                    columns.setdefault(b["col"], []).append((b["digit"], level(b)))
                number, codes = "", []
                for col in sorted(columns):
                    marked, code = self._decide(columns[col])
                    number += str(marked[0]) if code in ("ok", "low_confidence") else "?"
                    codes.append(code)
                result.exam_number = number
                flag("exam_number", codes)
            elif kind == "single":
                on = level(f["bubbles"][0]) >= self.th.abs_th
                if f["name"] == "absent":
                    result.absent = on
                elif on:
                    result.form = "multi" if result.form else f["name"].removeprefix("form_")

        if result.form == "multi":
            result.form = None
            flag("form", ["multi"])
        elif result.form is None:
            flag("form", ["blank"])
        return result

    def _decide(self, values: list[tuple[int, float]]) -> tuple[list[int], str]:
        """한 행(또는 열)의 판정. 절대 임계값과 행 내 상대 비교를 함께 쓴다."""
        top = max(v for _, v in values)
        marked = [label for label, v in values if v >= self.th.abs_th and v >= self.th.rel * top]
        if not marked:
            return [], "blank"
        if len(marked) > 1:
            return marked, "multi"
        runner_up = max((v for label, v in values if label != marked[0]), default=0.0)
        if top - runner_up < self.th.margin:
            return marked, "low_confidence"
        return marked, "ok"


# ── 페이지 분리 ─────────────────────────────────────────────────────


def page_count(data: bytes, suffix: str) -> int:
    if suffix != ".pdf":
        return 1
    try:
        document = pdfium.PdfDocument(io.BytesIO(data))
    except pdfium.PdfiumError as error:
        raise ValueError("PDF를 열 수 없습니다.") from error
    try:
        return len(document)
    finally:
        document.close()


def page_image(data: bytes, suffix: str, index: int) -> bytes:
    """`index`번째 쪽의 이미지 바이트. 한 번에 한 쪽만 메모리에 올린다(설계 자원 제약)."""
    if suffix != ".pdf":
        return data
    document = pdfium.PdfDocument(io.BytesIO(data))
    try:
        page = document[index]
        # 페이지 크기는 업로드한 사람이 정한다. 거대한 쪽이 메모리를 다 쓰지 않게 긴 변을 제한한다
        scale = min(RENDER_SCALE, MAX_RENDER_SIDE / max(page.get_size()))
        bitmap = page.render(scale=scale)
        # BMP는 압축이 없어 인코딩·디코딩이 빠르다. 디스크에 남기지 않는다
        return cv2.imencode(".bmp", cv2.cvtColor(bitmap.to_numpy(), cv2.COLOR_RGB2BGR))[1].tobytes()
    finally:
        document.close()


def _read_page(reader: OmrReader, data: bytes, suffix: str, index: int) -> tuple[dict, list]:
    try:
        result = reader.read(page_image(data, suffix, index), TEMPLATE_ID)
    except OmrRegistrationError as error:
        return {"template_id": TEMPLATE_ID, "error": str(error)}, [
            {"field": "sheet", "code": "low_confidence"}
        ]
    return result.payload(), result.flags


@task_handler("omr_read")
async def run_omr_read(session: AsyncSession, task: BackgroundTask) -> dict:
    exam_id, file_id = task.payload["exam_id"], task.payload["file_id"]
    stored = await session.scalar(
        select(StoredFile).where(StoredFile.id == file_id, StoredFile.campus_id == task.campus_id)
    )
    data = storage().get(stored.path) if stored else None
    if data is None:
        raise LookupError("저장된 OMR 파일을 찾지 못했습니다.")
    suffix = Path(stored.path).suffix

    # 멱등: 재기동 재개는 이 작업을 처음부터 다시 돌리므로 같은 파일의 이전 판독을 지운다
    await session.execute(
        delete(OmrScan).where(OmrScan.exam_id == exam_id, OmrScan.file_id == file_id)
    )
    reader = TemplateOmrReader(OmrThresholds.from_env())
    total, failed = page_count(data, suffix), 0
    for index in range(total):
        # CPU 작업이 이벤트 루프를 붙잡지 않게 스레드에서 돌린다
        payload, flags = await asyncio.to_thread(_read_page, reader, data, suffix, index)
        failed += "error" in payload
        session.add(OmrScan(
            exam_id=exam_id, file_id=file_id, page_no=index + 1, read_payload=payload, flags=flags
        ))
        task.progress = (index + 1) * 100 // total
        await session.commit()
    return {"pages": total, "failed": failed}


# ── 업로드(REST 계약의 OMR 절) ──────────────────────────────────────

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["omr"])


def _check_pages(data: bytes, suffix: str) -> None:
    try:
        pages = page_count(data, suffix)
    except ValueError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    if pages > MAX_OMR_PAGES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"한 번에 {MAX_OMR_PAGES}쪽까지 올릴 수 있습니다({pages}쪽).",
        )


@router.post("/exams/{exam_id}/omr/uploads", status_code=status.HTTP_202_ACCEPTED)
async def upload_omr(
    exam_id: int,
    request: Request,
    scope: CurrentScope,
    session: Db,
    file: Annotated[UploadFile, File()],
) -> dict[str, int]:
    scope.require_director()
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    stored = await save_upload(
        session, scope.campus_id, "omr_scan", file, OMR_SUFFIXES,
        max_bytes=MAX_OMR_BYTES, validate=_check_pages,
    )
    runner = request.app.state.task_runner
    task_id = await runner.enqueue(
        session, scope.campus_id, "omr_read", {"exam_id": exam.id, "file_id": stored.id}
    )
    # 요청을 붙잡지 않는다. 진행 상태는 GET /tasks/{task_id}로 폴링한다(DES-18)
    running = asyncio.create_task(runner.run_pending())
    request.app.state.background.add(running)
    running.add_done_callback(request.app.state.background.discard)
    return {"file_id": stored.id, "task_id": task_id}
