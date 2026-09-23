"""시각 회귀 — [DES-08 상세]가 규정한 기준 이미지 비교.

카드는 학부모에게 도달하는 브랜드 자산이라 레이아웃이 조용히 틀어지면 안 된다.
**기준 이미지는 컨테이너에서 만든 것만 쓴다.** 글꼴이 호스트(Apple SD Gothic Neo)와
컨테이너(NanumGothic)에서 달라 호스트 기준 이미지는 컨테이너에서 항상 실패한다.
따라서 이 테스트는 기준 이미지가 있을 때만 돈다.

기준 이미지 갱신:
    docker compose exec -w /app -e PYTHONPATH=/app/src api python -m tests.make_baseline
"""

import asyncio
import io
import os

import pytest
from PIL import Image, ImageChops

from make_baseline import BASELINE, render_sample


@pytest.mark.skipif(
    not (BASELINE / "card.png").is_file(),
    reason="기준 이미지가 없다. 컨테이너에서 tests.make_baseline으로 만든다",
)
@pytest.mark.skipif(
    not os.environ.get("MATHDESK_TOKENS_CSS"),
    reason="컨테이너 밖이다. 글꼴이 달라 기준 이미지와 어긋난다",
)
def test_card_matches_the_visual_baseline():
    actual = Image.open(io.BytesIO(asyncio.run(render_sample()))).convert("RGB")
    expected = Image.open(BASELINE / "card.png").convert("RGB")

    assert actual.size == expected.size, f"카드 크기가 바뀌었다: {expected.size} → {actual.size}"
    diff = ImageChops.difference(actual, expected).convert("L")
    total = actual.width * actual.height
    changed = total - diff.histogram()[0]
    ratio = changed / total
    assert ratio < 0.001, f"카드 그림이 {ratio:.2%} 달라졌다. 의도한 변경이면 기준 이미지를 갱신한다"
