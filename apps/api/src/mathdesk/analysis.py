"""문항 분할(DES-12)과 분석(DES-13).

분석기가 **전송 필드 화이트리스트**를 소유한다(ADR-009 결정 4). 공급자를 바꿔도 이 경계는
그대로다. 외부로 나가는 것은 `QuestionInput`의 문항 번호·텍스트·이미지뿐이며, 학생 정보는
이 모듈에 들어오지 않는다(NFR-04).
"""
import os
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .ingest import NormalizedDocument, normalize
from .llm import AnalysisResult, LlmAdapter, LlmError, QuestionInput, Usage, cost, select_adapter
from .models import BackgroundTask, Exam, ExamQuestion, IntegrationSetting, LlmCallLog, StoredFile
from .storage import storage
from .tasks import task_handler

# 문항 번호: 블록 맨 앞의 "12." 또는 "12)". 원문자 선지(①)는 걸리지 않는다
QUESTION_NUMBER = re.compile(r"^\s*(\d{1,2})\s*[.)]\s*")

RETRIES = 2  # 문항 단위 재시도(설계 시험지 분석 흐름 5번)

# 모든 문항 호출에 똑같이 붙는 분류 체계. 캐시 대상이므로 문항마다 바뀌는 값을 넣지 않는다
TAXONOMY = """단원 분류 체계(고등학교 수학)
- 공통수학1: 다항식의 연산, 나머지정리, 인수분해, 복소수, 이차방정식, 이차방정식과 이차함수, 여러 가지 방정식, 여러 가지 부등식, 경우의 수, 행렬
- 공통수학2: 평면좌표, 직선의 방정식, 원의 방정식, 도형의 이동, 집합, 명제, 함수, 유리함수와 무리함수
- 대수: 지수와 로그, 지수함수와 로그함수, 삼각함수, 수열
- 미적분I: 함수의 극한과 연속, 미분, 적분
- 확률과 통계: 순열과 조합, 확률, 통계
- 미적분II: 수열의 극한, 여러 가지 미분법, 여러 가지 적분법
- 기하: 이차곡선, 평면벡터, 공간도형과 공간좌표"""


@dataclass(frozen=True)
class Segment:
    no: int
    text: str
    images: tuple[bytes, ...] = ()
    from_image: bool = False  # 텍스트가 없어 페이지 이미지로 대신한 문항


def segment(document: NormalizedDocument) -> list[Segment]:
    """문항 번호 기준으로 블록을 묶는다. 첫 문항 앞(시험지 제목 등)은 버린다.

    번호는 1씩 늘어날 때만 새 문항으로 본다. 본문 속 "3." 같은 줄을 문항 시작으로
    오인하지 않기 위해서다.
    """
    segments: list[list] = []  # [no, lines]
    for block in document.blocks:
        if block.kind not in ("text", "equation", "table") or not block.text:
            continue
        match = QUESTION_NUMBER.match(block.text) if block.kind == "text" else None
        expected = segments[-1][0] + 1 if segments else None
        if match and (expected is None or int(match.group(1)) == expected):
            segments.append([int(match.group(1)), [block.text]])
        elif segments:
            segments[-1][1].append(block.text)
    if segments:
        return [Segment(no, "\n".join(lines)) for no, lines in segments]

    # 텍스트로 문항을 찾지 못한 문서(스캔본)는 페이지 하나를 문항 하나로 보고 이미지로 넘긴다
    return [
        Segment(no=page, text="", images=(image,), from_image=True)
        for page, image in sorted(document.page_images.items())
    ]


@dataclass(frozen=True)
class AnalysisLimits:
    """시험지 1건당 상한(NFR-15, ADR-009 결정 7)."""

    max_input_tokens: int = 200_000
    max_output_tokens: int = 30_000
    review_threshold: float = 0.7

    @classmethod
    def from_env(cls) -> "AnalysisLimits":
        return cls(
            max_input_tokens=int(os.environ.get("MATHDESK_LLM_MAX_INPUT_TOKENS", 200_000)),
            max_output_tokens=int(os.environ.get("MATHDESK_LLM_MAX_OUTPUT_TOKENS", 30_000)),
            review_threshold=float(os.environ.get("MATHDESK_ANALYSIS_REVIEW_THRESHOLD", 0.7)),
        )


@dataclass
class QuestionOutcome:
    no: int
    result: AnalysisResult | None
    needs_review: bool


@dataclass
class TokenLimitExceeded(Exception):
    usage: Usage
    spent: object  # Decimal | None
    outcomes: list[QuestionOutcome] = field(default_factory=list)

    def __str__(self) -> str:
        spent = "알 수 없음" if self.spent is None else f"${self.spent:.4f}"
        return (
            f"시험지 1건의 토큰 상한을 넘어 분석을 멈췄습니다. 사용량: 입력 "
            f"{self.usage.input_tokens:,} · 출력 {self.usage.output_tokens:,} 토큰, 비용 {spent}"
        )


def _payload(item: Segment) -> QuestionInput:
    """화이트리스트. 외부로 나갈 값을 여기서만 고른다."""
    return QuestionInput(no=item.no, text=item.text, images=item.images)


async def analyze_segments(
    session: AsyncSession,
    campus_id: int,
    exam_id: int,
    segments: list[Segment],
    adapter: LlmAdapter,
    limits: AnalysisLimits,
    on_progress: Callable[[int], Awaitable[None]] | None = None,
) -> list[QuestionOutcome]:
    total = Usage()
    spent = cost(adapter.model, total)
    outcomes: list[QuestionOutcome] = []
    for index, item in enumerate(segments, start=1):
        result = None
        for _ in range(1 + RETRIES):
            usage, model = Usage(), adapter.model
            try:
                reply = await adapter.analyze(_payload(item), TAXONOMY)
                usage, model = reply.usage, reply.model
                # 거절(refusal)도 같은 실패 경로를 탄다(설계 시험지 분석 흐름 5번)
                result = None if reply.refused else reply.result
            except LlmError:
                result = None
            # 실패한 호출도 비용이 든다. 전부 기록한다(NFR-15)
            session.add(LlmCallLog(
                campus_id=campus_id, purpose="question_analysis", provider=adapter.provider,
                model=model, exam_id=exam_id, prompt_tokens=usage.input_tokens,
                completion_tokens=usage.output_tokens, cache_read_tokens=usage.cache_read_tokens,
                cache_write_tokens=usage.cache_write_tokens, cost=cost(model, usage),
            ))
            await session.commit()
            total = total + usage
            call_cost = cost(model, usage)
            spent = None if spent is None or call_cost is None else spent + call_cost
            if (total.input_tokens > limits.max_input_tokens
                    or total.output_tokens > limits.max_output_tokens):
                outcomes.append(QuestionOutcome(item.no, result, result is None))
                raise TokenLimitExceeded(usage=total, spent=spent, outcomes=outcomes)
            if result is not None:
                break  # 실패면 재시도한다. 끝내 실패하면 그 문항만 미분석으로 남긴다

        needs_review = (
            result is None or item.from_image or result.confidence < limits.review_threshold
        )
        outcomes.append(QuestionOutcome(item.no, result, needs_review))
        if on_progress is not None:
            await on_progress(round(index * 100 / len(segments)))
    return outcomes


async def _save(session: AsyncSession, exam: Exam, outcomes: list[QuestionOutcome]) -> None:
    """초안을 통째로 바꾼다. 재기동으로 작업이 처음부터 다시 돌아도 중복되지 않는다."""
    await session.execute(delete(ExamQuestion).where(ExamQuestion.exam_id == exam.id))
    for outcome in outcomes:
        result = outcome.result
        session.add(ExamQuestion(
            exam_id=exam.id,
            no=outcome.no,
            unit=result.unit if result else None,
            sub_type=result.sub_type if result else None,
            difficulty=result.difficulty if result else None,
            rationale=result.rationale if result else None,
            confidence=round(result.confidence, 3) if result else None,
            needs_review=outcome.needs_review,
        ))
    exam.question_count = len(outcomes)
    await session.commit()


async def _campus_settings(session: AsyncSession, campus_id: int) -> dict[str, str]:
    rows = await session.scalars(
        select(IntegrationSetting).where(
            IntegrationSetting.campus_id == campus_id,
            IntegrationSetting.key.in_(["llm_provider", "llm_model", "llm_base_url"]),
        )
    )
    return {row.key: row.value_encrypted for row in rows}


@task_handler("exam_analyze")
async def run_exam_analysis(session: AsyncSession, task: BackgroundTask) -> dict:
    exam = await session.scalar(
        select(Exam).where(Exam.id == task.payload["exam_id"], Exam.campus_id == task.campus_id)
    )
    if exam is None or exam.source_file_id is None:
        raise LookupError("분석할 시험지 파일이 없습니다.")
    stored = await session.get(StoredFile, exam.source_file_id)
    data = storage().get(stored.path)
    if data is None:
        raise LookupError("저장된 시험지 파일을 찾지 못했습니다.")

    # 파일 이름이 아니라 저장 키의 확장자로 형식을 정한다(키는 서버가 정했다)
    segments = segment(normalize(data, stored.path))
    if not segments:
        raise LookupError("시험지에서 문항을 찾지 못했습니다.")

    adapter = select_adapter(await _campus_settings(session, task.campus_id))

    async def progress(percent: int) -> None:
        task.progress = percent
        await session.commit()

    try:
        outcomes = await analyze_segments(
            session, task.campus_id, exam.id, segments, adapter, AnalysisLimits.from_env(),
            progress,
        )
    except TokenLimitExceeded as stopped:
        await _save(session, exam, stopped.outcomes)  # 이미 쓴 비용의 결과는 버리지 않는다
        raise
    await _save(session, exam, outcomes)
    return {
        "questions": len(outcomes),
        "needs_review": sum(1 for outcome in outcomes if outcome.needs_review),
        "provider": adapter.provider,
    }
