"""NFR-01·NFR-02 측정: 반 10 · 학생 200 · 6개월 기록 규모에서 응답 시간을 잰다.

실행: cd apps/api && uv run python scripts/measure_perf.py
"""

import asyncio
import os
import statistics
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import asyncpg

API_DIR = Path(__file__).resolve().parents[1]
DB_NAME = "mathdesk_perf"
BASE = os.environ.get("MATHDESK_PERF_BASE", "postgresql://mathdesk:mathdesk@localhost:55432")
DATABASE_URL = f"postgresql+asyncpg://{urlsplit(BASE).netloc}/{DB_NAME}"

CLASSES = 10
STUDENTS_PER_CLASS = 20
WEEKS = 26
SESSIONS_PER_WEEK = 2
PASSWORD = "perf-password-1234"


async def build_dataset() -> None:
    admin = await asyncpg.connect(f"{BASE}/postgres")
    await admin.execute(f'DROP DATABASE IF EXISTS "{DB_NAME}" WITH (FORCE)')
    await admin.execute(f'CREATE DATABASE "{DB_NAME}"')
    await admin.close()

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=API_DIR,
        check=True,
        env={**os.environ, "DATABASE_URL": DATABASE_URL},
        stdout=subprocess.DEVNULL,
    )

    from mathdesk.security import hash_password

    connection = await asyncpg.connect(f"{BASE}/{DB_NAME}")
    campus_id = await connection.fetchval(
        "INSERT INTO campus (name, is_active) VALUES ('성능측정', true) RETURNING id"
    )
    user_id = await connection.fetchval(
        "INSERT INTO app_user (login_id, password_hash, display_name, role, is_active,"
        " failed_login_count) VALUES ('perf', $1, '원장', 'director', true, 0) RETURNING id",
        hash_password(PASSWORD),
    )
    await connection.execute(
        "INSERT INTO app_user_campus (user_id, campus_id) VALUES ($1, $2)", user_id, campus_id
    )

    start = date(2026, 3, 2)
    for class_index in range(CLASSES):
        class_id = await connection.fetchval(
            "INSERT INTO class (campus_id, name, grade, teacher_id, is_active)"
            " VALUES ($1, $2, '고2', $3, true) RETURNING id",
            campus_id,
            f"반{class_index + 1:02d}",
            user_id,
        )
        student_ids = []
        for seat in range(STUDENTS_PER_CLASS):
            number = class_index * STUDENTS_PER_CLASS + seat + 1
            student_id = await connection.fetchval(
                "INSERT INTO student (campus_id, name, school, grade, status, omr_number)"
                " VALUES ($1, $2, '한영고', '고2', 'enrolled', $3) RETURNING id",
                campus_id,
                f"학생{number:03d}",
                f"1000{number // 10 % 10}{number % 10}{number // 100 % 3}0",
            )
            student_ids.append(student_id)
            await connection.execute(
                "INSERT INTO enrollment (class_id, student_id, start_date) VALUES ($1, $2, $3)",
                class_id,
                student_id,
                start,
            )

        grades = ("A+", "A", "B", "C", "D", "F")
        for week in range(WEEKS):
            for slot in range(SESSIONS_PER_WEEK):
                session_date = start + timedelta(days=week * 7 + slot * 3)
                session_id = await connection.fetchval(
                    "INSERT INTO class_session (class_id, session_date, homework, test_name,"
                    " test_max_score) VALUES ($1, $2, '과제', '주간테스트', 100) RETURNING id",
                    class_id,
                    session_date,
                )
                await connection.executemany(
                    "INSERT INTO class_session_progress (session_id, period, content)"
                    " VALUES ($1, $2, $3)",
                    [(session_id, period, f"{period}교시 진도") for period in range(1, 5)],
                )
                await connection.executemany(
                    "INSERT INTO student_daily_record (session_id, student_id, attendance_status,"
                    " homework_grade, test_score_num) VALUES ($1, $2, 'present', $3, $4)",
                    [
                        (session_id, student_id, grades[(index + week) % len(grades)], 60 + index % 40)
                        for index, student_id in enumerate(student_ids)
                    ],
                )
    counts = await connection.fetchrow(
        "SELECT (SELECT count(*) FROM student) students, (SELECT count(*) FROM class) classes,"
        " (SELECT count(*) FROM class_session) sessions,"
        " (SELECT count(*) FROM student_daily_record) records"
    )
    await connection.close()
    print(f"데이터셋: 반 {counts['classes']} · 학생 {counts['students']} "
          f"· 수업 {counts['sessions']} · 기록 {counts['records']}")


def percentile(samples: list[float], ratio: float) -> float:
    ordered = sorted(samples)
    return ordered[min(len(ordered) - 1, int(len(ordered) * ratio))]


def measure() -> int:
    from fastapi.testclient import TestClient

    from mathdesk.main import app

    failures = 0
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"login_id": "perf", "password": PASSWORD})
        class_id = client.get("/api/classes").json()[0]["id"]
        probe = client.get("/api/daily", params={"class_id": class_id, "date": "2026-06-01"}).json()
        session_id = probe["session"]["id"]
        student_id = probe["records"][0]["student_id"]

        for label, call, budget in (
            (
                "NFR-01 대시보드 조회",
                lambda: client.get(
                    "/api/dashboard", params={"class_id": class_id, "date": "2026-06-01"}
                ),
                1.5,
            ),
            (
                "NFR-02 표 일괄 저장",
                lambda: client.put(
                    f"/api/daily/{session_id}/records",
                    json={"records": [{"student_id": student_id, "homework_grade": "A"}]},
                ),
                0.5,
            ),
        ):
            samples = []
            for _ in range(30):
                started = time.perf_counter()
                response = call()
                samples.append(time.perf_counter() - started)
                assert response.status_code == 200, response.text
            p50, p95 = percentile(samples, 0.5), percentile(samples, 0.95)
            verdict = "통과" if p95 <= budget else "미달"
            failures += verdict == "미달"
            print(
                f"{label}: p50 {p50 * 1000:.0f}ms · p95 {p95 * 1000:.0f}ms "
                f"· 최대 {max(samples) * 1000:.0f}ms (기준 {budget * 1000:.0f}ms) → {verdict}"
            )
    return failures


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = DATABASE_URL
    asyncio.run(build_dataset())
    sys.exit(measure())
