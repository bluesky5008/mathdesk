"""OMR 검수 서비스(DES-16) — 스캔 목록, 교정·학생 지정, 원본 대조 이미지(FR-34·FR-35).

교정한 판독값은 `label_correction`에 교정 전·후와 원본 크롭 참조로 남긴다(ADR-006 결정 6).
학생 지정은 답안지 판독값의 교정이 아니므로 기록하지 않는다.
"""
import asyncio
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .masterdata import validate_omr_number
from .models import Exam, LabelCorrection, OmrScan, StoredFile, Student
from .omr import TEMPLATE_ID, load_template, match_student, page_image, review_image, settle
from .scope import CurrentScope, Scope, ScopedRepository
from .storage import storage

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["omr"])


class StudentRef(BaseModel):
    id: int
    name: str


class ScanOut(BaseModel):
    id: int
    file_id: int | None
    page_no: int
    status: str
    student: StudentRef | None
    exam_number: str | None
    form: str | None
    answers: dict[str, int | None]
    flags: list[dict[str, str]]
    error: str | None


class ScanPatch(BaseModel):
    student_id: int | None = None
    exam_number: str | None = None
    form: Literal["odd", "even"] | None = None
    answers: dict[int, int | None] | None = None


def _out(scan: OmrScan, student: Student | None) -> ScanOut:
    payload = scan.read_payload or {}
    return ScanOut(
        id=scan.id,
        file_id=scan.file_id,
        page_no=scan.page_no,
        status=scan.status,
        student=StudentRef(id=student.id, name=student.name) if student else None,
        exam_number=payload.get("exam_number"),
        form=payload.get("form"),
        answers=payload.get("answers", {}),
        flags=scan.flags or [],
        error=payload.get("error"),
    )


async def _scan(session: AsyncSession, scope: Scope, exam_id: int, scan_id: int) -> OmrScan:
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    scan = await session.get(OmrScan, scan_id)
    if scan is None or scan.exam_id != exam.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "스캔을 찾을 수 없습니다.")
    return scan


@router.get("/exams/{exam_id}/omr/scans")
async def list_scans(exam_id: int, scope: CurrentScope, session: Db) -> list[ScanOut]:
    exam = await ScopedRepository(session, scope).get(Exam, exam_id)
    rows = await session.execute(
        select(OmrScan, Student)
        .outerjoin(Student, Student.id == OmrScan.matched_student_id)
        .where(OmrScan.exam_id == exam.id)
        .order_by(OmrScan.file_id, OmrScan.page_no)
    )
    return [_out(scan, student) for scan, student in rows]


def _check_answer(questions: dict, q: int, value: int | None) -> None:
    if q in questions["multiple_choice"]:
        low, high = 1, 5
    elif q in questions["short_answer"]:
        low, high = 0, 999
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{q}번 문항이 없습니다.")
    if value is not None and not low <= value <= high:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"{q}번은 {low}~{high}만 입력할 수 있습니다."
        )


@router.patch("/exams/{exam_id}/omr/scans/{scan_id}")
async def correct_scan(
    exam_id: int, scan_id: int, patch: ScanPatch, scope: CurrentScope, session: Db
) -> ScanOut:
    scope.require_director()
    scan = await _scan(session, scope, exam_id, scan_id)
    sent = patch.model_fields_set
    questions = load_template(TEMPLATE_ID)["questions"]
    # JSON 열은 제자리 변경을 감지하지 못한다. 새 객체로 바꿔 넣는다
    payload = dict(scan.read_payload or {})
    answers = dict(payload.get("answers", {}))
    flags = list(scan.flags or [])

    def resolve(field: str) -> None:
        flags[:] = [flag for flag in flags if flag["field"] != field]

    def record(field: str, before, after) -> None:
        # 판독값 그대로 확인한 경우는 교정이 아니다
        if before == after:
            return
        session.add(LabelCorrection(
            kind="omr",
            source_ref=f"omr_scan:{scan.id}:{field}",
            before_value=None if before is None else str(before),
            after_value=None if after is None else str(after),
            asset_ref=f"/api/exams/{exam_id}/omr/scans/{scan.id}/image?field={field}",
            corrected_by=scope.user.id,
        ))

    if patch.answers is not None:
        for q, value in patch.answers.items():
            _check_answer(questions, q, value)
        for q, value in sorted(patch.answers.items()):
            record(str(q), answers.get(str(q)), value)
            answers[str(q)] = value
            resolve(str(q))
        payload["answers"] = answers

    if "form" in sent:
        record("form", payload.get("form"), patch.form)
        payload["form"] = patch.form
        resolve("form")

    if "exam_number" in sent:
        number = patch.exam_number or ""
        if reason := validate_omr_number(number):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, reason)
        record("exam_number", payload.get("exam_number"), number)
        payload["exam_number"] = number
        resolve("exam_number")
        student = await match_student(session, scope.campus_id, number)
        scan.matched_student_id = student.id if student else None
        if student:
            resolve("student")
        elif not any(flag["field"] == "student" for flag in flags):
            flags.append({"field": "student", "code": "unmatched"})

    if patch.student_id is not None:
        student = await ScopedRepository(session, scope).get(Student, patch.student_id)
        scan.matched_student_id = student.id
        resolve("student")

    # 정합하지 못한 쪽은 문형과 30문항을 모두 입력해야 판독 실패가 풀린다
    every = questions["multiple_choice"] + questions["short_answer"]
    if payload.get("form") and all(str(q) in answers for q in every):
        resolve("sheet")

    scan.read_payload, scan.flags = payload, flags
    settle(scan)
    await session.commit()
    student = await session.get(Student, scan.matched_student_id) if scan.matched_student_id else None
    return _out(scan, student)


@router.get("/exams/{exam_id}/omr/scans/{scan_id}/image")
async def scan_image(
    exam_id: int,
    scan_id: int,
    scope: CurrentScope,
    session: Db,
    field: Annotated[str | None, Query(pattern=r"^(\d{1,2}|exam_number|form|student|sheet)$")] = None,
) -> Response:
    scan = await _scan(session, scope, exam_id, scan_id)
    stored = await session.get(StoredFile, scan.file_id) if scan.file_id else None
    data = storage().get(stored.path) if stored else None
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "저장된 OMR 파일이 없습니다.")
    suffix = Path(stored.path).suffix

    def render() -> bytes:
        return review_image(page_image(data, suffix, scan.page_no - 1), TEMPLATE_ID, field)

    # 스캔 이미지는 학생 답안이다. 로컬에서만 처리하고(NFR-04) 캐시하지 않는다(API 전역 no-store)
    return Response(content=await asyncio.to_thread(render), media_type="image/png")
