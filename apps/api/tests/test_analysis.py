"""TASK-31 — 문항 분할·LlmAdapter·분석(FR-28·FR-29, AC-22·AC-23, NFR-04·NFR-15, ADR-009).

외부 호출은 전부 가짜 전송 계층으로 막는다. Anthropic 실호출은 TASK-43에서 검증한다.
"""
import asyncio
import json
import time
from dataclasses import fields
from pathlib import Path

import httpx
import httpx2
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from mathdesk.analysis import AnalysisLimits, TokenLimitExceeded, analyze_segments, segment
from mathdesk.ingest import Block, NormalizedDocument
from mathdesk.llm import (
    AnalysisResult,
    AnthropicLlm,
    LlmError,
    LlmReply,
    OpenAICompatLlm,
    QuestionInput,
    TestModeLlm,
    Usage,
    select_adapter,
)
from mathdesk.models import Exam, ExamQuestion, LlmCallLog

FIXTURES = Path(__file__).parent / "fixtures"

ANSWER = {
    "unit": "이차방정식",
    "sub_type": "근과 계수의 관계",
    "difficulty": "mid",
    "rationale": "두 근의 합과 곱을 이용하는 전형 문항",
    "confidence": 0.82,
}

QUESTION = QuestionInput(no=3, text="3. x^2-5x+6=0의 두 근의 합은?")


# ── 분할(DES-12) ──────────────────────────────────────────────────────


def test_segmenter_splits_on_question_numbers_and_drops_the_header():
    document = NormalizedDocument(
        format="pdf",
        page_count=1,
        blocks=[
            Block(1, "text", "2026학년도 모의고사"),
            Block(1, "text", "1. 첫 문항 본문"),
            Block(1, "text", "① 1 ② 2 ③ 3"),
            Block(1, "equation", "x over 2"),
            Block(1, "text", "2) 둘째 문항"),
        ],
    )

    segments = segment(document)

    assert [s.no for s in segments] == [1, 2]
    assert segments[0].text == "1. 첫 문항 본문\n① 1 ② 2 ③ 3\nx over 2"


def test_segmenter_falls_back_to_one_segment_per_page_image():
    document = NormalizedDocument(
        format="image", page_count=1, blocks=[Block(1, "image")],
        page_images={1: b"\x89PNG..."}, image_fallback=True,
    )

    segments = segment(document)

    assert [(s.no, s.images) for s in segments] == [(1, (b"\x89PNG...",))]
    assert segments[0].from_image is True


# ── 어댑터 계약(DES-14) — 구현체 3종이 같은 계약을 통과한다 ──────────


def _anthropic(handler) -> AnthropicLlm:
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key="test-key",
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler)),
        max_retries=0,
    )
    return AnthropicLlm(model="claude-opus-5", client=client)


def _anthropic_ok(request):
    body = json.loads(request.content)
    assert body["output_config"]["format"]["type"] == "json_schema"
    assert body["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert body["fallbacks"] == "default"
    return httpx2.Response(200, json={
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5",
        "content": [{"type": "text", "text": json.dumps(ANSWER)}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 120, "output_tokens": 40,
                  "cache_read_input_tokens": 900, "cache_creation_input_tokens": 0},
    })


def _openai_compat(handler) -> OpenAICompatLlm:
    return OpenAICompatLlm(
        model="local-model", base_url="http://llm.local/v1",
        transport=httpx.MockTransport(handler),
    )


def _openai_ok(request):
    body = json.loads(request.content)
    assert body["response_format"]["type"] == "json_schema"
    return httpx.Response(200, json={
        "model": "local-model",
        "choices": [{"message": {"content": json.dumps(ANSWER)}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 40},
    })


@pytest.mark.parametrize(
    "make",
    [
        lambda: TestModeLlm(),
        lambda: _anthropic(_anthropic_ok),
        lambda: _openai_compat(_openai_ok),
    ],
    ids=["test", "anthropic", "openai_compat"],
)
def test_every_adapter_honours_the_same_contract(make):
    adapter = make()

    reply = asyncio.run(adapter.analyze(QUESTION, "단원 분류 체계"))

    assert isinstance(reply, LlmReply)
    assert isinstance(reply.result, AnalysisResult)
    assert reply.result.difficulty in ("low", "mid", "high", "top")
    assert 0 <= reply.result.confidence <= 1
    assert reply.usage.input_tokens >= 0 and reply.usage.output_tokens >= 0
    assert reply.model
    assert adapter.provider in ("test", "anthropic", "openai_compat")


def test_anthropic_reports_cache_tokens():
    reply = asyncio.run(_anthropic(_anthropic_ok).analyze(QUESTION, "체계"))

    assert reply.usage == Usage(input_tokens=120, output_tokens=40,
                                cache_read_tokens=900, cache_write_tokens=0)


def test_anthropic_refusal_is_a_failure_and_the_body_is_not_read():
    def refuse(request):
        return httpx2.Response(200, json={
            "id": "msg_2", "type": "message", "role": "assistant", "model": "claude-opus-5",
            "content": [{"type": "text", "text": "not json at all"}],
            "stop_reason": "refusal", "stop_sequence": None,
            "stop_details": {"type": "refusal", "category": None, "explanation": None},
            "usage": {"input_tokens": 10, "output_tokens": 0},
        })

    reply = asyncio.run(_anthropic(refuse).analyze(QUESTION, "체계"))

    assert reply.refused is True
    assert reply.result is None


def test_missing_credentials_surface_at_the_first_call_not_at_startup():
    def unauthorized(request):
        return httpx2.Response(401, json={
            "type": "error", "error": {"type": "authentication_error", "message": "bad key"},
        })

    adapter = _anthropic(unauthorized)  # 생성은 성공한다

    with pytest.raises(LlmError) as raised:
        asyncio.run(adapter.analyze(QUESTION, "체계"))
    assert "자격 증명" in str(raised.value)


def test_openai_compat_without_an_endpoint_fails_at_the_first_call():
    adapter = OpenAICompatLlm(model="m", base_url=None)

    with pytest.raises(LlmError) as raised:
        asyncio.run(adapter.analyze(QUESTION, "체계"))
    assert "엔드포인트" in str(raised.value)


# ── 공급자 선택(AC-23) ────────────────────────────────────────────────


def test_provider_is_chosen_by_configuration_not_code(monkeypatch):
    monkeypatch.delenv("MATHDESK_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("MATHDESK_LLM_MODEL", raising=False)

    assert isinstance(select_adapter(), TestModeLlm)
    assert isinstance(select_adapter({"llm_provider": "anthropic"}), AnthropicLlm)
    assert select_adapter({"llm_provider": "anthropic"}).model == "claude-opus-5"

    monkeypatch.setenv("MATHDESK_LLM_PROVIDER", "openai_compat")
    monkeypatch.setenv("MATHDESK_LLM_MODEL", "qwen")
    # 환경변수가 캠퍼스 설정보다 우선한다(DES-20)
    chosen = select_adapter({"llm_provider": "anthropic"})
    assert isinstance(chosen, OpenAICompatLlm)
    assert chosen.model == "qwen"


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("MATHDESK_LLM_PROVIDER", "gpt")

    with pytest.raises(LlmError):
        select_adapter()


# ── 분석기(DES-13) — 화이트리스트·재시도·상한·기록 ────────────────────


def test_only_whitelisted_fields_can_leave_the_server():
    """NFR-04: 외부로 나가는 것은 문항 번호·텍스트·이미지뿐이다. 구조로 강제한다."""
    assert {f.name for f in fields(QuestionInput)} == {"no", "text", "images"}


class SpyLlm:
    """호출을 기록하고 지정한 순서대로 응답한다."""

    provider = "test"
    model = "spy"

    def __init__(self, replies=None, usage=Usage(input_tokens=10, output_tokens=5)):
        self.replies = list(replies or [])
        self.usage = usage
        self.sent: list[QuestionInput] = []

    async def analyze(self, question, taxonomy):
        self.sent.append(question)
        outcome = self.replies.pop(0) if self.replies else "ok"
        if outcome == "error":
            raise LlmError("일시 오류")
        if outcome == "refusal":
            return LlmReply(result=None, usage=self.usage, model=self.model, refused=True)
        return LlmReply(result=AnalysisResult(**ANSWER), usage=self.usage, model=self.model)


def _segments(count):
    document = NormalizedDocument(
        format="pdf", page_count=1,
        blocks=[Block(1, "text", f"{n}. 문항 {n}") for n in range(1, count + 1)],
    )
    return segment(document)


def _with_exam(world, migrated_database, body):
    async def run():
        engine = create_async_engine(migrated_database)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            exam = Exam(campus_id=world["campus_a"], name="모의고사")
            session.add(exam)
            await session.commit()
            try:
                return await body(session, exam)
            finally:
                await engine.dispose()

    return asyncio.run(run())


def test_a_question_is_retried_twice_then_left_for_review(world, migrated_database):
    spy = SpyLlm(replies=["error", "refusal", "ok",       # 1번: 세 번째에 성공
                          "error", "error", "error"])      # 2번: 끝내 실패

    async def body(session, exam):
        outcomes = await analyze_segments(
            session, world["campus_a"], exam.id, _segments(2), spy, AnalysisLimits()
        )
        logs = (await session.scalars(select(LlmCallLog))).all()
        return outcomes, len(logs)

    outcomes, logged = _with_exam(world, migrated_database, body)

    assert outcomes[0].result is not None and outcomes[0].needs_review is False
    assert outcomes[1].result is None and outcomes[1].needs_review is True
    assert len(spy.sent) == 6
    assert logged == 6  # 실패한 호출도 기록한다(NFR-15)


def test_low_confidence_is_flagged_for_review(world, migrated_database):
    low = SpyLlm()

    async def body(session, exam):
        return await analyze_segments(
            session, world["campus_a"], exam.id, _segments(1), low,
            AnalysisLimits(review_threshold=0.9),
        )

    outcomes = _with_exam(world, migrated_database, body)

    assert outcomes[0].result is not None
    assert outcomes[0].needs_review is True  # 신뢰도 0.82 < 0.9


def test_token_limit_stops_the_analysis_and_reports_usage(world, migrated_database):
    heavy = SpyLlm(usage=Usage(input_tokens=600, output_tokens=10))

    async def body(session, exam):
        with pytest.raises(TokenLimitExceeded) as raised:
            await analyze_segments(
                session, world["campus_a"], exam.id, _segments(5), heavy,
                AnalysisLimits(max_input_tokens=1000),
            )
        return raised.value

    stopped = _with_exam(world, migrated_database, body)

    assert stopped.usage.input_tokens == 1200  # 2번째 호출에서 상한을 넘겼다
    assert len(heavy.sent) == 2
    assert "토큰" in str(stopped)


# ── 업로드 → 분석 작업 → 초안(AC-22) ──────────────────────────────────


def _wait(api, task_id, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        task = api.get(f"/api/tasks/{task_id}").json()
        if task["status"] in ("done", "failed"):
            return task
        time.sleep(0.1)
    raise AssertionError(f"작업이 끝나지 않았다: {task}")


def test_thirty_question_exam_produces_thirty_draft_questions(
    api, tmp_path, monkeypatch
):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    monkeypatch.delenv("MATHDESK_LLM_PROVIDER", raising=False)
    api.sign_in("director_a")
    upload = api.post(
        "/api/exams/uploads",
        files={"file": ("모의고사.pdf", (FIXTURES / "exam-30.pdf").read_bytes(), "application/pdf")},
    ).json()
    exam = api.post("/api/exams", json={"name": "3월 모의고사", "source_file_id": upload["id"]}).json()

    started = api.post(f"/api/exams/{exam['id']}/analyze")
    task = _wait(api, started.json()["task_id"])

    assert started.status_code == 202
    assert task["status"] == "done", task["error"]
    questions = api.get(f"/api/exams/{exam['id']}/questions").json()
    assert [q["no"] for q in questions] == list(range(1, 31))
    assert all(q["unit"] and q["sub_type"] and q["difficulty"] and q["rationale"] for q in questions)
    flagged = [q["no"] for q in questions if q["needs_review"]]
    assert flagged and len(flagged) < 30  # 저신뢰 문항만 `확인 필요`


def test_analysis_can_run_twice_without_duplicating_questions(api, tmp_path, monkeypatch):
    """재기동 시 작업이 처음부터 다시 돈다(TASK-28). 핸들러는 멱등이어야 한다."""
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")
    upload = api.post(
        "/api/exams/uploads",
        files={"file": ("e.pdf", (FIXTURES / "exam-text.pdf").read_bytes(), "application/pdf")},
    ).json()
    exam = api.post("/api/exams", json={"name": "주간", "source_file_id": upload["id"]}).json()

    for _ in range(2):
        _wait(api, api.post(f"/api/exams/{exam['id']}/analyze").json()["task_id"])

    assert [q["no"] for q in api.get(f"/api/exams/{exam['id']}/questions").json()] == [1, 2, 3]


def test_teacher_cannot_start_an_analysis(api, tmp_path, monkeypatch):
    monkeypatch.setenv("MATHDESK_STORAGE_ROOT", str(tmp_path))
    api.sign_in("director_a")
    upload = api.post(
        "/api/exams/uploads",
        files={"file": ("e.pdf", (FIXTURES / "exam-text.pdf").read_bytes(), "application/pdf")},
    ).json()
    exam = api.post("/api/exams", json={"name": "주간", "source_file_id": upload["id"]}).json()
    api.post("/api/auth/logout")
    api.sign_in("teacher_a")

    assert api.post(f"/api/exams/{exam['id']}/analyze").status_code == 403
