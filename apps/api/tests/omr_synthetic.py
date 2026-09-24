"""합성 OMR 답안지. [프로토타입 합성 테스트](../../../prototype/omr/test_omr.py)를 이식했다.

빈 양식(300dpi 렌더)에 마킹을 칠하고 휴대폰 촬영처럼 회전 3°·축소 0.6·원근 왜곡을 준다.
실제 학생 스캔본이 없어(Q-08) 임계값은 이 합성본 기준이다.
"""
import json
import random
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[3]
BLANK_FORM = REPO / "assets/omr/omr-template-ksat2027-math-300dpi.png"
TEMPLATE = REPO / "apps/api/src/mathdesk/omr_templates/ksat-2027-math.json"


def make_truth(seed: int = 7) -> dict:
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rnd = random.Random(seed)
    answers: dict[int, int | None] = {}
    for q in tpl["questions"]["multiple_choice"]:
        answers[q] = rnd.randint(1, 5)
    for q in tpl["questions"]["short_answer"]:
        answers[q] = rnd.choice([rnd.randint(1, 9), rnd.randint(10, 99), rnd.randint(100, 999)])
    answers[22] = None  # 일부러 비운다
    ranges = tpl["exam_number_ranges"]
    exam_number = "".join(str(rnd.randint(*ranges[str(i)])) for i in range(1, 9))
    return {"answers": answers, "exam_number": exam_number, "form": "odd", "double_mark": 3}


def paint(truth: dict, seed: int = 7) -> np.ndarray:
    """정답대로 칠한 정면 답안지. 마킹은 조금씩 어긋나고 덜 칠해져 있다."""
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    rnd = random.Random(seed)
    img = cv2.imread(str(BLANK_FORM))
    h, w = img.shape[:2]
    rx, ry = tpl["bubble_radius"]["rx"] * w, tpl["bubble_radius"]["ry"] * h
    answers = truth["answers"]

    def fill(b):
        cx = int(b["x"] * w + rnd.uniform(-3, 3))
        cy = int(b["y"] * h + rnd.uniform(-3, 3))
        cv2.ellipse(img, (cx, cy), (int(rx * 0.9), int(ry * 0.9)), 0, 0, 360, (20, 20, 20), -1)

    for f in tpl["fields"]:
        for b in f["bubbles"]:
            if f["kind"] == "multiple_choice":
                if answers[b["q"]] == b["choice"]:
                    fill(b)
                elif b["q"] == truth.get("double_mark") and b["choice"] == answers[b["q"]] % 5 + 1:
                    fill(b)
            elif f["kind"] == "short_answer":
                v = answers[b["q"]]
                if v is None or (b["place"] == "hundreds" and v < 100) or (b["place"] == "tens" and v < 10):
                    continue
                digit = {"hundreds": v // 100, "tens": v // 10 % 10, "ones": v % 10}[b["place"]]
                if digit == b["digit"]:
                    fill(b)
            elif f["kind"] == "digit_columns":
                if int(truth["exam_number"][b["col"] - 1]) == b["digit"]:
                    fill(b)
            elif f["name"] == f"form_{truth['form']}":
                fill(b)
    return img


def photograph(img: np.ndarray) -> np.ndarray:
    """회전 3°·축소 0.6·원근 왜곡, 회색 배경(AC-24)."""
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 3, 0.6)
    m[:, 2] += (80, 60)
    out = cv2.warpAffine(img, m, (w, h), borderValue=(120, 120, 120))
    src = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    dst = np.float32([[40, 30], [w - 10, 60], [20, h - 20], [w - 60, h - 70]])
    return cv2.warpPerspective(
        out, cv2.getPerspectiveTransform(src, dst), (w, h), borderValue=(120, 120, 120)
    )


def png(img: np.ndarray) -> bytes:
    return cv2.imencode(".png", img)[1].tobytes()


def pdf(images: list[np.ndarray]) -> bytes:
    """이미지마다 한 쪽인 PDF. 스캐너가 만드는 PDF와 같은 구조다."""
    import io

    from PIL import Image

    pages = [Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)) for img in images]
    out = io.BytesIO()
    pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:], resolution=300)
    return out.getvalue()
