"""개발용 시드 데이터: 캠퍼스 1개, 반 4개, 학생 47명.

실행: DATABASE_URL=... uv run python -m mathdesk.seed
"""

import asyncio
import os
from datetime import date, time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .models import (
    AppUser,
    AppUserCampus,
    Campus,
    ClassSchedule,
    Enrollment,
    Guardian,
    Klass,
    Student,
)

CAMPUS_NAME = "전병훈 수학학원 고등관"
# (반 이름, 학년, 요일, 시작, 종료, 인원)
CLASS_SPECS = [
    ("고3 윤A", "고3", 1, time(18, 0), time(22, 0), 8),
    ("고2 윤B", "고2", 4, time(18, 0), time(22, 0), 13),
    ("고2 윤C", "고2", 2, time(18, 0), time(22, 0), 13),
    ("고1 윤D", "고1", 3, time(18, 0), time(22, 0), 13),
]
ENROLLED_SINCE = date(2026, 3, 2)


def omr_number(sequence: int) -> str:
    """자리별 허용 범위(1열 1-9, 3열 0-5, 7열 0-2)를 지키는 8자리 번호."""
    return f"1000{sequence // 10}{sequence % 10}00"


async def seed(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            if await session.scalar(select(Campus.id).limit(1)) is not None:
                raise RuntimeError("이미 시드된 데이터베이스다. 먼저 비우고 실행하라.")

            campus = Campus(name=CAMPUS_NAME)
            session.add(campus)
            await session.flush()

            director = AppUser(
                login_id="director",
                password_hash="!",  # 로그인 불가 표시. 실제 해시는 TASK-04에서 설정한다.
                display_name="원장",
                role="director",
            )
            session.add(director)
            await session.flush()
            session.add(AppUserCampus(user_id=director.id, campus_id=campus.id))

            sequence = 0
            for name, grade, weekday, start, end, size in CLASS_SPECS:
                klass = Klass(
                    campus_id=campus.id, name=name, grade=grade, teacher_id=director.id
                )
                session.add(klass)
                await session.flush()
                session.add(
                    ClassSchedule(
                        class_id=klass.id, weekday=weekday, start_time=start, end_time=end
                    )
                )

                for _ in range(size):
                    sequence += 1
                    student = Student(
                        campus_id=campus.id,
                        name=f"학생{sequence:02d}",
                        school=f"{grade[:2]}학교",
                        grade=grade,
                        omr_number=omr_number(sequence),
                    )
                    session.add(student)
                    await session.flush()
                    session.add(
                        Guardian(
                            student_id=student.id,
                            relation="모",
                            name=f"학부모{sequence:02d}",
                            phone=f"010-0000-{sequence:04d}",
                        )
                    )
                    session.add(
                        Enrollment(
                            class_id=klass.id,
                            student_id=student.id,
                            start_date=ENROLLED_SINCE,
                        )
                    )

            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed(os.environ["DATABASE_URL"]))
