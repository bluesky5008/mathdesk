"""NFR-03 측정: 30쪽 OMR PDF 판독 시간(기준 5분 이내).

합성 답안지 30장(학생마다 다른 답)을 PDF로 묶고, 작업 핸들러와 같은 경로
(`page_image` → `TemplateOmrReader.read`)로 한 쪽씩 판독한다. DB 기록 시간은 제외한다.

실행: cd apps/api && uv run python scripts/measure_omr.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from omr_synthetic import make_truth, paint, pdf, photograph  # noqa: E402

from mathdesk.omr import TEMPLATE_ID, TemplateOmrReader, page_count, page_image  # noqa: E402

PAGES = 30

truths = [make_truth(seed) for seed in range(PAGES)]
data = pdf([photograph(paint(truth, seed)) for seed, truth in enumerate(truths)])
print(f"PDF {PAGES}쪽, {len(data) / 1024 / 1024:.1f}MB")

reader = TemplateOmrReader()
started = time.perf_counter()
wrong = 0
for index in range(page_count(data, ".pdf")):
    result = reader.read(page_image(data, ".pdf", index), TEMPLATE_ID)
    truth = truths[index]
    wrong += result.exam_number != truth["exam_number"]
    wrong += sum(result.answers[q] != truth["answers"][q] for q in range(1, 31) if q != 3)
elapsed = time.perf_counter() - started
print(f"판독 {elapsed:.1f}초 (쪽당 {elapsed / PAGES:.2f}초), 불일치 {wrong}건, 기준 300초")
sys.exit(0 if elapsed < 300 and wrong == 0 else 1)
