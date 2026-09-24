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

/* 브랜드 색 헤더. 카톡 목록의 섬네일만 봐도 어느 학원인지 읽히게 한다 */
.hero { background: var(--md-color-brand); padding: var(--md-space-6); }
.hero.ink-light { color: var(--md-color-brand-fg); }
.hero.ink-dark { color: var(--md-color-fg); }

.hero .academy {
  display: flex;
  align-items: center;
  gap: var(--md-space-2);
  font-size: var(--md-text-sm);
  font-weight: 600;
  opacity: 0.85;
}
.hero .academy img { height: 22px; width: auto; display: block; }

.hero h1 {
  margin-top: var(--md-space-2);
  font-size: var(--md-text-3xl);
  font-weight: 700;
  line-height: var(--md-leading-tight);
  letter-spacing: -0.02em;
}

.hero .when { margin-top: var(--md-space-1); font-size: var(--md-text-xs); opacity: 0.8; }

.facts {
  display: grid;
  grid-template-columns: repeat(%(facts)s, 1fr);
  gap: var(--md-space-3);
  padding: var(--md-space-5) var(--md-space-6);
}

.fact { background: var(--md-color-accent); border-radius: var(--md-radius-md); padding: var(--md-space-4); }
.fact .k { font-size: var(--md-text-xs); color: var(--md-color-muted-fg); }
.fact .v { margin-top: var(--md-space-1); font-size: var(--md-text-xl); font-weight: 700; }
.fact .s { margin-top: 2px; font-size: var(--md-text-xs); color: var(--md-color-muted-fg); }

.empty {
  margin: var(--md-space-5) var(--md-space-6);
  padding: var(--md-space-5);
  background: var(--md-color-accent);
  border-radius: var(--md-radius-md);
  font-size: var(--md-text-sm);
  color: var(--md-color-muted-fg);
  text-align: center;
}

.body { padding: 0 var(--md-space-6) var(--md-space-6); }

.row { padding: var(--md-space-4) 0; border-top: 1px solid var(--md-color-border); }
.row h2 {
  font-size: var(--md-text-xs);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--md-color-brand);
  margin-bottom: var(--md-space-1);
}
.row p { font-size: var(--md-text-base); white-space: pre-wrap; word-break: break-word; }
"""  # noqa: E501


def header_ink(colour: str) -> str:
    """브랜드 색 배경 위 글자를 밝게 쓸지 어둡게 쓸지 정한다.

    시그니처 색은 원장이 자유롭게 고른다(FR-40). 밝은 색에 흰 글씨를 얹으면 읽히지 않으므로
    WCAG 상대 휘도로 뒤집는다.
    """
    value = colour.lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    channels = []
    for part in (value[0:2], value[2:4], value[4:6]):
        c = int(part, 16) / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    return "dark" if luminance > 0.4 else "light"


def _facts(context: MessageContext) -> list[tuple[str, str, str | None]]:
    """학부모가 카드를 열자마자 보는 값이다. 본문 순서대로 두면 점수가 아래로 묻힌다."""
    facts: list[tuple[str, str, str | None]] = []

    attendance = ATTENDANCE_LABEL.get(context.attendance or "")
    if attendance:
        facts.append(("출결", attendance, None))

    if context.homework_grade:
        facts.append(("과제", context.homework_grade, context.grade_comment))

    if context.test_score is not None:
        note = None
        if context.class_average is not None:
            try:
                gap = float(context.test_score) - context.class_average
                note = f"반평균 {context.class_average:g}점 · {'+' if gap >= 0 else ''}{gap:g}"
            except ValueError:
                note = f"반평균 {context.class_average:g}점"
        facts.append(("테스트", f"{context.test_score}점", note))

    return facts


def _details(context: MessageContext) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = []
    progress = "\n".join(
        f"[{period}교시] {content}" for period, content in context.progress if content
    )
    if progress:
        details.append(("수업 진도", progress))
    if context.homework:
        details.append(("오늘의 과제", context.homework))
    if context.video_url:
        details.append(("수업 영상", context.video_url))
    return details


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


def render_report_html(
    context: MessageContext,
    brand_colour: str | None = None,
    logo_data_url: str | None = None,
) -> str:
    """카드 HTML. 레이아웃은 시안 B(컬러 헤더형) 확정안이다.

    본문 순서를 그대로 따르면 학부모가 가장 먼저 보고 싶은 점수가 아래로 묻힌다.
    출결·과제·테스트를 헤더 바로 아래 요약으로 올리고 나머지를 상세로 내린다.
    """
    day = context.session_date
    when = f"{day.year}-{day.month:02d}-{day.day:02d}({WEEKDAYS[day.weekday()]}) · {context.teacher_name}T"

    if brand_colour and not HEX_COLOUR.match(brand_colour):
        raise ValueError(f"브랜드 색은 #RGB 또는 #RRGGBB 형식이어야 한다: {brand_colour!r}")
    brand = f"\n:root {{ --md-color-brand: {brand_colour}; }}" if brand_colour else ""
    ink = header_ink(brand_colour) if brand_colour else "light"

    # 로고가 없으면 학원명 텍스트로 대체한다(FR-40)
    mark = (
        f'<img src="{escape(logo_data_url)}" alt="{escape(context.campus_name)}">'
        if logo_data_url
        else ""
    )

    facts = _facts(context)
    if facts:
        cells = "".join(
            f'<div class="fact"><div class="k">{escape(key)}</div>'
            f'<div class="v">{escape(value)}</div>'
            + (f'<div class="s">{escape(note)}</div>' if note else "")
            + "</div>"
            for key, value, note in facts
        )
        summary = f'<div class="facts">{cells}</div>'
    else:
        summary = '<div class="empty">오늘 기록된 내용이 없습니다</div>'

    rows = "".join(
        f'<div class="row"><h2>{escape(head)}</h2><p>{escape(text)}</p></div>'
        for head, text in _details(context)
    )

    css = CARD_CSS % {"width": CARD_WIDTH, "facts": max(len(facts), 1)}
    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><style>
{TOKENS_CSS}{brand}
{css}
</style></head>
<body>
  <div class="card">
    <div class="hero ink-{ink}">
      <div class="academy">{mark}<span>{escape(context.campus_name)}</span></div>
      <h1>{escape(context.student_name)} 학습 피드백</h1>
      <div class="when">{escape(when)}</div>
    </div>
    {summary}
    {f'<div class="body">{rows}</div>' if rows else ''}
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
        self,
        context: MessageContext,
        brand_colour: str | None = None,
        logo_data_url: str | None = None,
    ) -> bytes:
        return await self.render_html(render_report_html(context, brand_colour, logo_data_url))

    async def render_html(self, html: str) -> bytes:
        """이 저장소가 조립한 카드 HTML을 촬영한다. 외부 입력을 렌더하지 않는다(DES-08)."""
        if self._browser is None:
            raise RuntimeError("렌더러가 시작되지 않았다. lifespan에서 start()를 호출한다.")
        page = await self._browser.new_page(
            viewport={"width": CARD_WIDTH, "height": 600}, device_scale_factor=SCALE
        )
        try:
            await page.set_content(html)
            # full_page는 뷰포트 높이를 하한으로 잡아 짧은 카드 아래에 빈 배경이 붙는다.
            # body 요소만 촬영하면 이미지 높이가 내용 높이와 정확히 같아진다.
            return await page.locator("body").screenshot(type="png")
        finally:
            await page.close()


DIFFICULTY_LABELS = (("low", "하"), ("mid", "중"), ("high", "상"), ("top", "최상"))

DIFFICULTY_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { width: %(width)spx; padding: var(--md-space-5); background: var(--md-color-bg);
       font-family: var(--md-font-sans); color: var(--md-color-fg);
       line-height: var(--md-leading-normal); }
.card { background: var(--md-color-surface); border-radius: var(--md-radius-lg);
        box-shadow: var(--md-shadow-md); overflow: hidden;
        border-top: 6px solid var(--md-color-brand); padding: var(--md-space-6); }
.eyebrow { font-size: var(--md-text-xs); font-weight: 600; letter-spacing: 0.06em;
           color: var(--md-color-brand); }
h1 { font-size: var(--md-text-2xl); line-height: var(--md-leading-tight);
     margin-top: var(--md-space-2); }
.exam { font-size: var(--md-text-lg); font-weight: 600; margin-top: var(--md-space-1); }
.meta { font-size: var(--md-text-sm); color: var(--md-color-muted-fg); margin-top: var(--md-space-1); }
.levels { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--md-space-3);
          margin-top: var(--md-space-5); }
.level { border-radius: var(--md-radius-md); padding: var(--md-space-3) var(--md-space-4);
         background: var(--md-color-accent); }
.level .k { font-size: var(--md-text-sm); font-weight: 600; color: var(--md-color-muted-fg); }
.level .v { font-size: var(--md-text-2xl); font-weight: 700; margin-top: var(--md-space-1);
            font-variant-numeric: tabular-nums; }
.note { font-size: var(--md-text-xs); color: var(--md-color-muted-fg); margin-top: var(--md-space-4); }
"""


def render_difficulty_html(
    campus_name: str,
    exam_name: str,
    meta: str,
    counts: dict[str, int],
    brand_colour: str | None = None,
) -> str:
    """난이도 분석표 카드(FR-30). 리포트 카드와 같은 렌더러·토큰을 쓰고 템플릿만 다르다(DES-08)."""
    if brand_colour and not HEX_COLOUR.match(brand_colour):
        raise ValueError(f"브랜드 색은 #RGB 또는 #RRGGBB 형식이어야 한다: {brand_colour!r}")
    brand = f"\n:root {{ --md-color-brand: {brand_colour}; }}" if brand_colour else ""
    levels = "".join(
        f'<div class="level"><div class="k">{label}</div>'
        f'<div class="v">{counts.get(key, 0)}문항</div></div>'
        for key, label in DIFFICULTY_LABELS
    )
    return f"""<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><style>
{TOKENS_CSS}{brand}
{DIFFICULTY_CSS % {"width": CARD_WIDTH}}
</style></head>
<body>
  <div class="card">
    <div class="eyebrow">{escape(campus_name)} · EXAM ANALYSIS</div>
    <h1>문항별 난이도 분석표</h1>
    <div class="exam">{escape(exam_name)}</div>
    <div class="meta">{escape(meta)}</div>
    <div class="levels">{levels}</div>
    <div class="note">AI 추정 난이도 · 실제 정답률과 별개입니다</div>
  </div>
</body>
</html>"""
