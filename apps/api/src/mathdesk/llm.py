"""LLM 어댑터(DES-14, ADR-009).

계약은 공급자 중립이다: 문항 입력 → 분석 결과·사용량. 특정 공급자의 요청·응답 형식을
계약에 드러내지 않는다. 구현체는 설정으로 고르며 기본은 외부 호출이 없는 테스트 모드다.

전송 필드 화이트리스트는 여기가 아니라 분석기가 소유한다(ADR-009 결정 4). 다만 계약 자체가
`QuestionInput`의 세 필드만 받으므로 어떤 구현체도 그 밖의 것을 보낼 수 없다.
"""
import base64
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError

DEFAULT_MODELS = {"test": "test-fixed", "anthropic": "claude-opus-5", "openai_compat": None}

# 공급자별 단가(달러/100만 토큰): 입력, 출력, 캐시 읽기, 캐시 쓰기. 없는 모델은 비용을 비워 둔다.
PRICES = {
    "claude-opus-5": (Decimal("5"), Decimal("25"), Decimal("0.5"), Decimal("6.25")),
    "claude-opus-4-8": (Decimal("5"), Decimal("25"), Decimal("0.5"), Decimal("6.25")),
}


class LlmError(Exception):
    """분석 한 번의 실패. 사용자에게 사유를 그대로 보여줄 수 있다."""


class AnalysisResult(BaseModel):
    """문항 분석 결과. 구조화 출력 스키마의 단일 소스다."""

    unit: str = Field(description="교육과정 단원")
    sub_type: str = Field(description="단원 안의 세부 유형")
    difficulty: Literal["low", "mid", "high", "top"] = Field(
        description="난이도: low=하, mid=중, high=상, top=최상"
    )
    rationale: str = Field(description="단원·유형·난이도를 그렇게 판단한 근거")
    confidence: float = Field(ge=0, le=1, description="판단 신뢰도 0~1")


def output_schema() -> dict:
    """구조화 출력용 JSON 스키마. 공급자가 받지 않는 키워드(범위 제약·제목)는 뺀다.
    범위는 응답을 받은 뒤 `AnalysisResult`가 다시 검사한다."""
    schema = AnalysisResult.model_json_schema()
    schema.pop("title", None)
    for spec in schema["properties"].values():
        for key in ("title", "minimum", "maximum"):
            spec.pop(key, None)
    schema["additionalProperties"] = False
    schema["required"] = list(schema["properties"])
    return schema


@dataclass(frozen=True)
class QuestionInput:
    """외부로 나갈 수 있는 유일한 형태(NFR-04). 문항 번호·텍스트·이미지뿐이다."""

    no: int
    text: str
    images: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens,
            self.output_tokens + other.output_tokens,
            self.cache_read_tokens + other.cache_read_tokens,
            self.cache_write_tokens + other.cache_write_tokens,
        )


def cost(model: str, usage: Usage) -> Decimal | None:
    if model.startswith("test"):
        return Decimal(0)
    prices = PRICES.get(model)
    if prices is None:
        return None
    counts = (usage.input_tokens, usage.output_tokens, usage.cache_read_tokens,
              usage.cache_write_tokens)
    return sum((price * count for price, count in zip(prices, counts)), Decimal(0)) / 1_000_000


@dataclass
class LlmReply:
    result: AnalysisResult | None
    usage: Usage
    model: str  # 실제로 응답한 모델. 폴백이 돌면 요청한 모델과 다를 수 있다
    refused: bool = False


class LlmAdapter(Protocol):
    provider: str
    model: str

    async def analyze(self, question: QuestionInput, taxonomy: str) -> LlmReply: ...


INSTRUCTION = (
    "고등학교 수학 시험 문항 하나를 분석한다. 주어진 단원 분류 체계에서 단원과 세부 유형을 고르고, "
    "난이도를 low(하)·mid(중)·high(상)·top(최상) 중 하나로 정한 뒤 판단 근거를 한두 문장으로 쓴다. "
    "확신이 없으면 confidence를 낮게 준다. 문항 속 수식은 한글 수식 스크립트일 수 있으며 원문 그대로 읽는다."
)


def _prompt(question: QuestionInput) -> str:
    return f"문항 {question.no}\n{question.text}"


def _parse(text: str) -> AnalysisResult:
    try:
        return AnalysisResult.model_validate_json(text)
    except ValidationError as error:
        raise LlmError(f"분석 결과 형식이 맞지 않습니다: {error.errors()[0]['msg']}") from error


class TestModeLlm:
    """외부 호출 0, 고정 응답(ADR-009 기본값). 번호에 따라 결정적으로 달라진다."""

    provider = "test"

    def __init__(self, model: str = "test-fixed") -> None:
        self.model = model

    async def analyze(self, question: QuestionInput, taxonomy: str) -> LlmReply:
        levels = ("low", "mid", "high", "top")
        return LlmReply(
            result=AnalysisResult(
                unit="테스트 단원",
                sub_type="테스트 유형",
                difficulty=levels[question.no % 4],
                rationale="테스트 모드 고정 응답이다. 실제 분석이 아니다.",
                # 일곱 번째마다 신뢰도를 낮춰 `확인 필요` 경로가 늘 함께 검사되게 한다
                confidence=0.5 if question.no % 7 == 0 else 0.9,
            ),
            usage=Usage(),
            model=self.model,
        )


class AnthropicLlm:
    """운영 구현. 공식 SDK만 쓴다(ADR-009 결정 5)."""

    provider = "anthropic"

    def __init__(self, model: str = "claude-opus-5", client=None, max_tokens: int = 2048) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = client

    def _get_client(self):
        # 키가 없어도 서버는 기동한다. 클라이언트는 첫 호출에서 만든다(DES-14)
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic()
        return self._client

    async def analyze(self, question: QuestionInput, taxonomy: str) -> LlmReply:
        import anthropic

        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(image).decode(),
                },
            }
            for image in question.images
        ]
        content.append({"type": "text", "text": _prompt(question)})
        try:
            response = await self._get_client().beta.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                # 지시와 분류 체계는 시험지 한 건의 모든 문항에서 같다. 캐시 대상이다
                system=[{"type": "text", "text": f"{INSTRUCTION}\n\n{taxonomy}",
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": content}],
                output_config={"format": {"type": "json_schema", "schema": output_schema()}},
                # 안전 분류기가 거절하면 서버가 거절 범주에 맞는 모델로 다시 돌린다
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as error:
            raise LlmError(
                "Anthropic 자격 증명이 없거나 올바르지 않습니다. ANTHROPIC_API_KEY를 확인하세요."
            ) from error
        except anthropic.APIStatusError as error:
            raise LlmError(f"Anthropic 호출 실패({error.status_code})") from error
        except anthropic.APIConnectionError as error:
            raise LlmError("Anthropic에 연결하지 못했습니다.") from error

        raw = response.usage
        usage = Usage(
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cache_read_tokens=raw.cache_read_input_tokens or 0,
            cache_write_tokens=raw.cache_creation_input_tokens or 0,
        )
        # 거절이면 본문을 읽지 않는다(DES-14). 문항 단위 실패로 넘긴다
        if response.stop_reason == "refusal":
            return LlmReply(result=None, usage=usage, model=response.model, refused=True)
        if response.stop_reason == "max_tokens":
            raise LlmError("응답이 길이 상한에서 잘렸습니다.")
        text = next((block.text for block in response.content if block.type == "text"), "")
        return LlmReply(result=_parse(text), usage=usage, model=response.model)


class OpenAICompatLlm:
    """로컬 폴백·타 공급자(vLLM·Ollama 등)의 `chat/completions`."""

    provider = "openai_compat"

    def __init__(
        self,
        model: str | None,
        base_url: str | None,
        api_key: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.model = model or ""
        self.base_url = base_url
        self.api_key = api_key
        self.transport = transport

    async def analyze(self, question: QuestionInput, taxonomy: str) -> LlmReply:
        if not self.base_url:
            raise LlmError("OpenAI 호환 엔드포인트가 설정되지 않았습니다(MATHDESK_LLM_BASE_URL).")
        if not self.model:
            raise LlmError("OpenAI 호환 모델이 설정되지 않았습니다(MATHDESK_LLM_MODEL).")

        parts: list[dict] = [{"type": "text", "text": _prompt(question)}]
        parts += [
            {"type": "image_url",
             "image_url": {"url": "data:image/png;base64," + base64.b64encode(image).decode()}}
            for image in question.images
        ]
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        async with httpx.AsyncClient(transport=self.transport, timeout=120) as client:
            try:
                response = await client.post(
                    f"{self.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": f"{INSTRUCTION}\n\n{taxonomy}"},
                            {"role": "user", "content": parts},
                        ],
                        "response_format": {
                            "type": "json_schema",
                            "json_schema": {"name": "question_analysis", "strict": True,
                                            "schema": output_schema()},
                        },
                    },
                )
                response.raise_for_status()
            except httpx.HTTPError as error:
                raise LlmError(f"OpenAI 호환 엔드포인트 호출 실패: {error}") from error

        body = response.json()
        choice = body["choices"][0]
        raw = body.get("usage") or {}
        usage = Usage(input_tokens=raw.get("prompt_tokens", 0),
                      output_tokens=raw.get("completion_tokens", 0))
        if choice.get("finish_reason") == "length":
            raise LlmError("응답이 길이 상한에서 잘렸습니다.")
        return LlmReply(
            result=_parse(choice["message"]["content"] or ""),
            usage=usage,
            model=body.get("model") or self.model,
        )


def select_adapter(settings: dict[str, str] | None = None) -> LlmAdapter:
    """환경변수가 캠퍼스 설정(`integration_setting`)보다 우선한다(DES-20)."""
    settings = settings or {}
    provider = os.environ.get("MATHDESK_LLM_PROVIDER") or settings.get("llm_provider") or "test"
    if provider not in DEFAULT_MODELS:
        raise LlmError(f"알 수 없는 LLM 공급자입니다: {provider}")
    model = (
        os.environ.get("MATHDESK_LLM_MODEL") or settings.get("llm_model") or DEFAULT_MODELS[provider]
    )
    if provider == "anthropic":
        return AnthropicLlm(model=model)
    if provider == "openai_compat":
        return OpenAICompatLlm(
            model=model,
            base_url=os.environ.get("MATHDESK_LLM_BASE_URL") or settings.get("llm_base_url"),
            api_key=os.environ.get("MATHDESK_LLM_API_KEY"),
        )
    return TestModeLlm(model=model)
