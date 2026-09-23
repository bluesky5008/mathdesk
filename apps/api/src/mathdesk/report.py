"""리포트 카드 렌더 — HTML 템플릿 + 헤드리스 Chromium 스크린샷.

[ADR-011]이 Pillow 직접 그리기를 대체했다. 카드는 학부모에게 도달하는 브랜드 자산이라
레이아웃·타이포의 상한이 이미지 라이브러리로는 낮았고, HTML/CSS로 가면 웹과 같은
디자인 토큰을 그대로 쓸 수 있다(NFR-18 / AC-31).

[ADR-012] 결정 7에 따라 카드는 웹 테마를 따르지 않는다. `data-theme`를 지정하지 않아
`:root` 라이트 팔레트를 쓰고, 학원 시그니처 색(FR-40)만 `--md-color-brand`로 덮어쓴다.
"""

import os
import re
from html import escape
from pathlib import Path

from playwright.async_api import Browser, async_playwright

from .messaging import ATTENDANCE_LABEL, MessageContext, WEEKDAYS

# 레이아웃은 CSS 픽셀 760에 맞추고 2배로 촬영한다. 카톡으로 받은 카드를 폰에서
# 확대해 보는 일이 흔해 1배는 흐리다.
CARD_WIDTH = 760
SCALE = 2

# 브랜드 색(FR-40)은 CSS 선언 안으로 들어간다. HTML 이스케이프는 CSS 주입을 막지 못하므로
# (`red; } body { display:none`) 형식 자체를 강제한다.
HEX_COLOUR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _find_tokens_css() -> Path:
    """웹과 같은 토큰 파일을 찾는다([DES-24]가 경로를 단일 소스로 규정한다).

    컨테이너에서는 이미지 빌드 시 복사된 경로를, 저장소에서 직접 실행할 때는
    `apps/web/...` 상대 경로를 쓴다. 값을 베껴 오지 않고 파일 자체를 읽는다.
    """
    candidates = [
        os.environ.get("MATHDESK_TOKENS_CSS", ""),
        "/app/web/tokens.css",
        str(Path(__file__).resolve().parents[3] / "web/src/styles/tokens.css"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise RuntimeError(f"디자인 토큰 파일을 찾지 못했다. 확인한 경로: {candidates}")


TOKENS_CSS = _find_tokens_css().read_text(encoding="utf-8")

CARD_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  width: %(width)spx;
  /* 여백을 .card의 margin이 아니라 body의 padding으로 둔다. margin이면 body와 상쇄되어
     body 요소의 높이가 실제 내용과 어긋나고, 그 높이로 촬영하면 카드가 잘린다. */
  padding: var(--md-space-5);
  background: var(--md-color-bg);
  font-family: var(--md-font-sans);
  color: var(--md-color-fg);
  line-height: var(--md-leading-normal);
  -webkit-font-smoothing: antialiased;
}

.card {
  background: var(--md-color-surface);
  border-radius: var(--md-radius-lg);
  overflow: hidden;
  box-shadow: var(--md-shadow-md);
}

.bar { height: 6px; background: var(--md-color-brand); }

.head {
  padding: var(--md-space-6) var(--md-space-6) var(--md-space-5);
  border-bottom: 1px solid var(--md-color-border);
}

.head h1 {
  font-size: var(--md-text-3xl);
  line-height: var(--md-leading-tight);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.head p {
  margin-top: var(--md-space-2);
  font-size: var(--md-text-sm);
  color: var(--md-color-muted-fg);
}

.body { padding: var(--md-space-5) var(--md-space-6) var(--md-space-6); }

section + section { margin-top: var(--md-space-5); }

section h2 {
  font-size: var(--md-text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--md-color-brand);
  margin-bottom: var(--md-space-2);
}

section p {
  font-size: var(--md-text-base);
  white-space: pre-wrap;
  word-break: break-word;
}

.foot {
  padding: var(--md-space-4) var(--md-space-6);
  border-top: 1px solid var(--md-color-border);
  font-size: var(--md-text-xs);
  color: var(--md-color-muted-fg);
}
""" % {"width": CARD_WIDTH}


def _sections(context: MessageContext) -> list[tuple[str, str]]:
    """본문과 같은 순서·같은 내용을 쓴다. 문자와 카드가 갈라지면 AC-16이 깨진다."""
    sections: list[tuple[str, str]] = []

    attendance = ATTENDANCE_LABEL.get(context.attendance or "")
    if attendance:
        sections.append(("출결", attendance))

    progress = "\n".join(
        f"[{period}교시] {content}" for period, content in context.progress if content
    )
    if progress:
        sections.append(("수업진도", progress))

    if context.homework_grade:
        feedback = context.homework_grade
        if context.grade_comment:
            feedback += f"\n{context.grade_comment}"
        sections.append(("과제피드백", feedback))

    if context.test_name and context.test_score is not None:
        test = f"{context.test_name}\n학생점수: {context.test_score}점"
        if context.class_average is not None:
            test += f"\n반평균: {context.class_average}점"
        sections.append(("테스트", test))

    if context.homework:
        sections.append(("오늘의 과제", context.homework))

    if context.video_url:
        sections.append(("수업 영상 링크", context.video_url))

    return sections


def render_report_html(context: MessageContext, brand_colour: str | None = None) -> str:
    day = context.session_date
    subtitle = (
        f"{context.campus_name} · {day.year}-{day.month:02d}-{day.day:02d}"
        f"({WEEKDAYS[day.weekday()]}) · {context.teacher_name}T"
    )
    # 학생 이름·과제 내용은 사용자 입력이다. 반드시 이스케이프한다.
    blocks = "\n".join(
        f"<section><h2>{escape(head)}</h2><p>{escape(text)}</p></section>"
        for head, text in _sections(context)
    )
    brand = ""
    if brand_colour:
        if not HEX_COLOUR.match(brand_colour):
            raise ValueError(f"브랜드 색은 #RGB 또는 #RRGGBB 형식이어야 한다: {brand_colour!r}")
        brand = f"\n:root {{ --md-color-brand: {brand_colour}; }}"

    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><style>
{TOKENS_CSS}{brand}
{CARD_CSS}
</style></head>
<body>
  <div class="card">
    <div class="bar"></div>
    <div class="head">
      <h1>{escape(context.student_name)} 학습피드백</h1>
      <p>{escape(subtitle)}</p>
    </div>
    <div class="body">
{blocks}
    </div>
    <div class="foot">{escape(context.campus_name)}</div>
  </div>
</body>
</html>"""


class ReportRenderer:
    """Chromium을 lifespan 동안 warm으로 유지한다.

    콜드 스타트(수 초)를 요청 경로에서 빼기 위해서다(NFR-19). 요청마다 페이지만 연다.
    """

    def __init__(self) -> None:
        self._playwright = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        # 컨테이너가 root로 실행되어 샌드박스를 쓸 수 없다. 렌더 대상은 이 저장소가 만든
        # HTML뿐이고 외부 페이지를 열지 않으므로 수용한다.
        self._browser = await self._playwright.chromium.launch(args=["--no-sandbox"])

    async def stop(self) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        self._browser = self._playwright = None

    async def render_png(
        self, context: MessageContext, brand_colour: str | None = None
    ) -> bytes:
        if self._browser is None:
            raise RuntimeError("렌더러가 시작되지 않았다. lifespan에서 start()를 호출한다.")
        page = await self._browser.new_page(
            viewport={"width": CARD_WIDTH, "height": 600}, device_scale_factor=SCALE
        )
        try:
            await page.set_content(render_report_html(context, brand_colour))
            # full_page는 뷰포트 높이를 하한으로 잡아 짧은 카드 아래에 빈 배경이 붙는다.
            # body 요소만 촬영하면 이미지 높이가 내용 높이와 정확히 같아진다.
            return await page.locator("body").screenshot(type="png")
        finally:
            await page.close()
