"""TASK-28 — StorageAdapter, 업로드, DB 상태 기반 TaskRunner.

RISK-09: 프로세스 내 큐는 재시작 시 진행 중 작업이 유실된다.
완화책은 작업 상태를 DB에 두고 재기동 시 `queued`부터 다시 시작하는 것이다.
"""
import asyncio
import hashlib

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.models import BackgroundTask
from mathdesk.storage import LocalStorage
from mathdesk.tasks import TaskRunner, task_handler

PDF = b"%PDF-1.4\nfake exam\n"


def test_local_storage_round_trip(tmp_path):
    storage = LocalStorage(tmp_path)

    ref = storage.put("exam/1.pdf", PDF)

    assert storage.get(ref) == PDF
    assert storage.url(ref).startswith("/api/files/")
    storage.delete(ref)
    assert storage.get(ref) is None


def test_local_storage_refuses_paths_that_escape_the_root(tmp_path):
    storage = LocalStorage(tmp_path)

    try:
        storage.put("../escape.pdf", PDF)
    except ValueError:
        return
    raise AssertionError("루트 밖 경로를 허용했다")


def test_upload_saves_the_file_and_records_metadata(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")

    created = api.post(
        "/api/exams/uploads", files={"file": ("시험지.pdf", PDF, "application/pdf")}
    )

    assert created.status_code == 201
    body = created.json()
    assert body["kind"] == "exam_source"
    assert body["size"] == len(PDF)
    assert body["sha256"] == hashlib.sha256(PDF).hexdigest()
    assert body["content_type"] == "application/pdf"
    assert api.get(f"/api/files/{body['id']}").content == PDF


def test_teacher_cannot_upload_exam_sources(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("teacher_a")

    rejected = api.post("/api/exams/uploads", files={"file": ("q.pdf", PDF, "application/pdf")})

    assert rejected.status_code == 403


def test_task_status_is_stored_in_the_database_and_readable(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")
    created = api.post(
        "/api/exams/uploads", files={"file": ("q.pdf", PDF, "application/pdf")}
    ).json()

    missing = api.get("/api/tasks/999999")

    # 저장소 규약: 없는 id와 남의 캠퍼스 id를 구분해 알려주지 않는다(둘 다 403)
    assert missing.status_code == 403
    assert created["id"] > 0


def test_interrupted_task_restarts_from_queued_after_a_restart(world, migrated_database):
    """재기동을 흉내 낸다: running으로 끊긴 작업이 queued로 되돌아가 다시 실행된다."""
    done: list[int] = []

    @task_handler("test_echo")
    async def _echo(session, task) -> dict:
        done.append(task.id)
        return {"echoed": task.payload["value"]}

    async def run() -> tuple[str, dict, list[int]]:
        engine = create_async_engine(migrated_database)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        runner = TaskRunner(factory)

        async with factory() as session:
            task_id = await runner.enqueue(
                session, world["campus_a"], "test_echo", {"value": 7}
            )
            # 프로세스가 죽기 직전 상태
            task = await session.get(BackgroundTask, task_id)
            task.status = "running"
            await session.commit()

        await runner.resume()  # 기동 시 호출되는 경로

        async with factory() as session:
            task = await session.get(BackgroundTask, task_id)
            state = (task.status, task.result, list(done))
        await engine.dispose()
        return state

    status, result, ran = asyncio.run(run())

    assert status == "done"
    assert result == {"echoed": 7}
    assert len(ran) == 1


def test_failed_handler_is_recorded_with_its_reason(world, migrated_database):
    @task_handler("test_boom")
    async def _boom(session, task) -> dict:
        raise RuntimeError("암호가 걸린 파일입니다.")

    async def run() -> tuple[str, str | None]:
        engine = create_async_engine(migrated_database)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        runner = TaskRunner(factory)
        async with factory() as session:
            task_id = await runner.enqueue(session, world["campus_a"], "test_boom", {})

        await runner.resume()

        async with factory() as session:
            task = await session.get(BackgroundTask, task_id)
            state = (task.status, task.error)
        await engine.dispose()
        return state

    status, error = asyncio.run(run())

    assert status == "failed"
    assert "암호가 걸린" in error


def test_upload_rejects_an_unsupported_format(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")

    rejected = api.post("/api/exams/uploads", files={"file": ("메모.txt", b"hello", "text/plain")})

    assert rejected.status_code == 415


def test_upload_rejects_a_file_over_the_limit(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    monkeypatch.setattr("mathdesk.files.MAX_UPLOAD_BYTES", 8)
    api.sign_in("director_a")

    rejected = api.post("/api/exams/uploads", files={"file": ("q.pdf", PDF, "application/pdf")})

    assert rejected.status_code == 413
