"""시각 회귀 기준 이미지와 그 샘플 정의.

기준 이미지는 **컨테이너에서만 만든다**. 글꼴이 호스트(Apple SD Gothic Neo)와
컨테이너(NanumGothic)에서 달라 호스트 기준 이미지는 컨테이너에서 항상 어긋난다.

    docker compose exec -w /app -e PYTHONPATH=/app/src api python /app/tests/make_baseline.py

pytest를 임포트하지 않는다. 운영 이미지에는 개발 의존성이 없다.
"""

import asyncio
from datetime import date
from pathlib import Path

from mathdesk.messaging import MessageContext
from mathdesk.report import ReportRenderer

BASELINE = Path(__file__).parent / "baseline"
PINK = "#C3457F"


def sample_context() -> MessageContext:
    return MessageContext(
        student_name="김나윤", campus_name="전병훈 수학학원 고등관", teacher_name="원장",
        session_date=date(2026, 9, 23), attendance="present",
        progress=[(1, "2024 광문고 기출 시행"), (2, "삼각함수 그래프 개형")],
        homework_grade="B", grade_comment="풀이 과정을 더 꼼꼼히 적어봅시다.",
        test_name="4차연합고사", test_score="78", class_average=72.5,
        homework="기출 문제집 p.114~120 풀어오기", video_url="https://han.video/0923",
    )


async def render_sample() -> bytes:
    renderer = ReportRenderer()
    await renderer.start()
    try:
        return await renderer.render_png(sample_context(), brand_colour=PINK)
    finally:
        await renderer.stop()


if __name__ == "__main__":
    BASELINE.mkdir(exist_ok=True)
    png = asyncio.run(render_sample())
    (BASELINE / "card.png").write_bytes(png)
    print(f"기준 이미지 갱신: {BASELINE / 'card.png'} ({len(png)} bytes)")
