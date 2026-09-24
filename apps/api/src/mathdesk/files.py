"""업로드와 파일 제공.

파일 바이트는 `StorageAdapter`가, 메타데이터는 `stored_file`이 맡는다(DES-10).
업로드 경로는 신뢰 경계라 크기·확장자·저장 키를 서버가 정한다.
"""
import hashlib
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import StoredFile
from .scope import CurrentScope, ScopedRepository
from .storage import storage

Db = Annotated[AsyncSession, Depends(get_session)]

router = APIRouter(prefix="/api", tags=["files"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
EXAM_SOURCE_SUFFIXES = {".pdf", ".hwp", ".hwpx", ".png", ".jpg", ".jpeg"}


class StoredFileOut(BaseModel):
    id: int
    kind: str
    content_type: str | None
    size: int | None
    sha256: str | None
    url: str


async def save_upload(
    session: AsyncSession,
    campus_id: int,
    kind: str,
    upload: UploadFile,
    suffixes: set[str],
    *,
    max_bytes: int | None = None,
    validate: Callable[[bytes, str], None] | None = None,
) -> StoredFile:
    """`validate`는 저장 전에 내용을 검사하고 거절하려면 HTTPException을 던진다."""
    max_bytes = max_bytes or MAX_UPLOAD_BYTES  # 기본값을 호출 시점에 읽는다
    suffix = PurePosixPath(upload.filename or "").suffix.lower()
    if suffix not in suffixes:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"지원하지 않는 형식입니다: {suffix or '확장자 없음'}",
        )
    # 읽기 전에 막는다. 다 읽고 나서 재면 큰 파일이 이미 메모리에 올라온 뒤다.
    if upload.size is not None and upload.size > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "파일이 너무 큽니다.")
    data = await upload.read()
    if len(data) > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "파일이 너무 큽니다.")
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "빈 파일입니다.")
    if validate is not None:
        validate(data, suffix)

    digest = hashlib.sha256(data).hexdigest()
    # 저장 키를 서버가 정한다. 업로드 파일명을 경로에 쓰면 루트를 벗어나거나 서로 덮어쓴다.
    key = f"{campus_id}/{kind}/{digest}{suffix}"
    storage().put(key, data)

    stored = StoredFile(
        campus_id=campus_id,
        kind=kind,
        path=key,
        content_type=upload.content_type,
        size=len(data),
        sha256=digest,
    )
    session.add(stored)
    await session.commit()
    return stored


def _out(stored: StoredFile) -> StoredFileOut:
    return StoredFileOut(
        id=stored.id,
        kind=stored.kind,
        content_type=stored.content_type,
        size=stored.size,
        sha256=stored.sha256,
        url=f"/api/files/{stored.id}",
    )


@router.post("/exams/uploads", status_code=status.HTTP_201_CREATED)
async def upload_exam_source(
    scope: CurrentScope, session: Db, file: Annotated[UploadFile, File()]
) -> StoredFileOut:
    scope.require_director()
    return _out(await save_upload(session, scope.campus_id, "exam_source", file, EXAM_SOURCE_SUFFIXES))


@router.get("/files/{file_id}")
async def read_file(file_id: int, scope: CurrentScope, session: Db) -> Response:
    stored = await ScopedRepository(session, scope).get(StoredFile, file_id)
    data = storage().get(stored.path)
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "저장된 파일이 없습니다.")
    return Response(content=data, media_type=stored.content_type or "application/octet-stream")
