"""리포트 카드 이미지 렌더.

설계는 서버 렌더를 규정한다([DES-08]). 헤드리스 브라우저 대신 이미지 라이브러리로
직접 그려서 컨테이너 크기와 실행 환경 요구를 낮췄다(Q-10 해소).
"""

import io
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .messaging import MessageContext, WEEKDAYS, render_daily_message

WIDTH = 760
MARGIN = 40
CARD_BG = (255, 255, 255)
PAGE_BG = (241, 243, 249)
ACCENT = (79, 70, 229)
TEXT = (30, 32, 46)
MUTED = (110, 116, 140)

# 한글 글리프가 있는 글꼴이 필요하다. 굵은 글꼴은 파일을 따로 고른다 —
# 같은 파일의 face index로 굵게 잡으면 한글이 없는 face가 걸려 네모로 깨진다.
REGULAR_FONTS = (
    os.environ.get("MATHDESK_REPORT_FONT", ""),
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
)
BOLD_FONTS = (
    os.environ.get("MATHDESK_REPORT_FONT_BOLD", ""),
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in (BOLD_FONTS + REGULAR_FONTS) if bold else REGULAR_FONTS:
        if candidate and Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, limit: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            if draw.textlength(current + char, font=font) > limit:
                lines.append(current)
                current = char
            else:
                current += char
        lines.append(current)
    return lines


def render_report_png(context: MessageContext) -> bytes:
    body = render_daily_message(context)
    title_font, heading_font, text_font = _font(30, True), _font(19, True), _font(17)

    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    inner = WIDTH - MARGIN * 2 - 48

    day = context.session_date
    header = (
        f"{context.campus_name} · {day.year}-{day.month:02d}-{day.day:02d}"
        f"({WEEKDAYS[day.weekday()]}) · {context.teacher_name}T"
    )

    blocks: list[tuple[str, list[str]]] = []
    for raw in body.split("\n\n")[1:]:
        head, _, rest = raw.partition("\n")
        blocks.append((head, _wrap(measure, rest, text_font, inner) if rest else []))

    height = 200 + sum(46 + len(lines) * 26 for _, lines in blocks) + MARGIN
    image = Image.new("RGB", (WIDTH, height), PAGE_BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (MARGIN, MARGIN, WIDTH - MARGIN, height - MARGIN), radius=18, fill=CARD_BG
    )
    draw.rounded_rectangle((MARGIN, MARGIN, WIDTH - MARGIN, MARGIN + 8), radius=4, fill=ACCENT)

    x, y = MARGIN + 24, MARGIN + 40
    draw.text((x, y), f"{context.student_name} 학습피드백", font=title_font, fill=TEXT)
    y += 44
    draw.text((x, y), header, font=text_font, fill=MUTED)
    y += 46

    for head, lines in blocks:
        draw.text((x, y), head, font=heading_font, fill=ACCENT)
        y += 30
        for line in lines:
            draw.text((x, y), line, font=text_font, fill=TEXT)
            y += 26
        y += 16

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
