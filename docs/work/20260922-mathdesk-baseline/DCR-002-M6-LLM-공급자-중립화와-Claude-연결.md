# DCR-002: M6 LLM 공급자 중립화와 Claude 연결

> 문서 유형: `dcr`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `approved`
> 기준선: `v3`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-22`
> 관련 문서: [REQ-mathdesk: 요구사항](../../requirements.md), [DESIGN-mathdesk: 설계](../../design.md), [ADR-009: LLM 공급자 추상화와 Claude 연결](./ADR-009-LLM-공급자-추상화와-Claude-연결.md), [ADR-003: AI 작업 분리와 개인정보 경계](./ADR-003-AI-작업-분리와-개인정보-경계.md), [PLAN-mathdesk: 구현 계획](../../plan.md)

## 요약

- 목적: M6 시험지 분석의 LLM 공급자를 설정으로 교체 가능하게 만들고, Anthropic Claude를 기본 운영 공급자로 연결한다.
- 현재 결론 또는 상태: 2026-09-22 사용자 재승인으로 기준선 `v3`가 발행되었다. Claude 실호출 검증은 사용자 지시로 최종 단계(TASK-43)로 미뤘다.
- 다음 행동: 재승인 후 [TASK-23](../../plan.md#task-23-스키마-2차-시험omr상담파일)의 `llm_call_log` 컬럼을 반영하고 [TASK-31](../../plan.md#task-31-문항-분할llmadapter분석)에서 구현한다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-mathdesk: 요구사항](../../requirements.md) | NFR-15, AC-23, Q-05 | 변경 대상 요구사항 기준선 v2 |
| input | baseline | [DESIGN-mathdesk: 설계](../../design.md) | DES-14, 시스템 경계, 데이터 모델, 시험지 분석 흐름 | 변경 대상 설계 기준선 v2 |
| output | decision | [ADR-009: LLM 공급자 추상화와 Claude 연결](./ADR-009-LLM-공급자-추상화와-Claude-연결.md) | document | 이 변경의 핵심 결정 |
| input | related | [ADR-003: AI 작업 분리와 개인정보 경계](./ADR-003-AI-작업-분리와-개인정보-경계.md) | 결정 2 | 부분 대체 대상 |
| output | change | [PLAN-mathdesk: 구현 계획](../../plan.md) | TASK-23, TASK-31 | 변경을 반영할 작업 |

## 변경 사유와 증거

사용자가 "M6는 차후 가변으로 사용할 수 있게 해주고, 지금 사용 중인 Claude를 연결하는 것을 검토해 달라"고 요청했다. 승인된 기준선 `v2`는 `LlmAdapter`를 OpenAI 호환 `chat/completions` 클라이언트로 고정하고 있어 두 요청을 모두 수용할 수 없다.

확인한 사실은 다음과 같다.

| 사실 | 확인 방법 |
|---|---|
| ADR-003 결정 2가 어댑터를 "OpenAI 호환 `chat/completions`"로 고정한다 | [ADR-003 결정 2](./ADR-003-AI-작업-분리와-개인정보-경계.md#결정) |
| DES-14가 같은 문구로 설계에 반영되어 있다 | [design.md 컴포넌트와 책임](../../design.md#컴포넌트와-책임) |
| 시스템 경계 다이어그램이 외부 의존을 "OpenAI 호환 LLM API"로 표기한다 | [design.md 시스템 경계와 구조](../../design.md#시스템-경계와-구조) |
| Anthropic Messages API는 엔드포인트·인증 헤더·시스템 프롬프트 위치·응답 구조가 모두 OpenAI 호환과 다르다 | [ADR-009 배경](./ADR-009-LLM-공급자-추상화와-Claude-연결.md#배경)의 대조표 |
| 이 장비에 `ant` CLI가 없고 `ANTHROPIC_API_KEY`가 비어 있으며 `~/.config/anthropic` 프로필도 없다 | `command -v ant`, `env`, `ls ~/.config/anthropic` |
| Claude Code 구독 인증은 애플리케이션 서버가 재사용할 수 있는 API 자격증명이 아니다 | 위 확인 결과 + Anthropic 자격증명 해석 순서 |
| `llm_call_log`에 공급자와 캐시 토큰 컬럼이 없다 | [design.md 데이터 모델](../../design.md#데이터-모델) |
| TASK-23(스키마 2차)이 아직 착수 전이라 컬럼 추가에 별도 마이그레이션이 필요 없다 | [plan.md TASK-23](../../plan.md#task-23-스키마-2차-시험omr상담파일) 상태 `in-progress`, 리비전 미작성 |
| Q-05(공급자·예산 상한)가 미해결로 남아 있다 | [requirements.md 가정과 미해결 질문](../../requirements.md#가정과-미해결-질문) |

## 기존 기준선과 설계

- [DES-14](../../design.md#컴포넌트와-책임): "OpenAI 호환 `chat/completions` 클라이언트. 엔드포인트·모델·토큰 상한을 설정으로 주입, 호출 기록".
- [AC-23](../../requirements.md#인수-조건): "설정에서 LLM **엔드포인트**를 로컬 구현으로 바꾸면 코드 변경 없이 문항 분석이 그 엔드포인트를 호출한다" — 교체 단위를 엔드포인트로 전제한다.
- [NFR-15](../../requirements.md#비기능-요구사항): 토큰 상한과 호출 기록을 요구하지만 기본값이 미정이다.
- [데이터 모델](../../design.md#데이터-모델)의 `llm_call_log`: `purpose`, `model`, `prompt_tokens`, `completion_tokens`, `cost`.
- [Q-05](../../requirements.md#가정과-미해결-질문): 공급자와 예산 상한 미정.

## 제안 설계

`LlmAdapter`를 공급자 형식이 아니라 도메인 의미로 정의하고, 구현체를 설정으로 고른다.

```text
QuestionAnalyzer ──호출──▶ LlmAdapter (공급자 중립 계약)
  └ 전송 필드 화이트리스트      ├ TestModeLlm     (기본값, 외부 호출 0)
    (NFR-04 / AC-27 위치 불변)  ├ AnthropicLlm    (anthropic SDK, claude-opus-5)
                                └ OpenAICompatLlm (로컬 vLLM·Ollama 등 폴백)

선택: MATHDESK_LLM_PROVIDER / MATHDESK_LLM_MODEL (환경변수 우선)
      캠퍼스별 재정의는 integration_setting
```

1. 계약 입력은 문항 번호·문항 텍스트·문항 이미지, 출력은 단원·세부 유형·난이도·판단 근거·신뢰도와 사용량이다.
2. 화이트리스트는 어댑터가 아니라 `QuestionAnalyzer`에 남는다. 공급자를 바꿔도 개인정보 경계와 그 검증 위치가 바뀌지 않으며, 바뀌는 것은 나가는 호스트뿐이다.
3. Anthropic 구현은 공식 SDK를 쓰고 구조화 출력·프롬프트 캐싱을 사용하며 `stop_reason == "refusal"`을 문항 단위 실패로 분류한다.
4. 기본 공급자는 `test`다. API 키 없이 M6 구현과 전체 테스트가 진행된다.
5. 상세 근거와 대안 비교는 [ADR-009](./ADR-009-LLM-공급자-추상화와-Claude-연결.md)에 있다.

## 변경 항목

| 대상 | 변경 전 | 변경 후 | 이유 |
|---|---|---|---|
| [ADR-003](./ADR-003-AI-작업-분리와-개인정보-경계.md) 결정 2 | `LlmAdapter`를 OpenAI 호환 `chat/completions`로 고정 | ADR-009로 부분 대체. 결정 1·3·4·5는 유효 | Anthropic API가 OpenAI 호환이 아님 |
| [DES-14](../../design.md#컴포넌트와-책임) | "OpenAI 호환 `chat/completions` 클라이언트" | "공급자 중립 계약. 구현체 3종(test·anthropic·openai_compat)을 설정으로 선택. 공급자·모델·토큰 상한 주입, 사용량 기록" | 교체 가능성을 계약 수준으로 올림 |
| [시스템 경계 다이어그램](../../design.md#시스템-경계와-구조) | 외부 의존을 "OpenAI 호환 LLM API"로 표기 | "LLM API (Anthropic 기본 · OpenAI 호환 폴백 · 테스트 모드)" | 표기와 결정 일치 |
| [데이터 모델](../../design.md#데이터-모델) `llm_call_log` | `purpose`, `model`, `prompt_tokens`, `completion_tokens`, `cost` | + `provider`, `cache_read_tokens`, `cache_write_tokens` | 공급자가 가변이고 캐싱 후 실비용 재구성이 필요(NFR-15) |
| [AC-23](../../requirements.md#인수-조건) | "설정에서 LLM **엔드포인트**를 로컬 구현으로 바꾸면…" | "설정에서 LLM **공급자**를 바꾸면 코드 변경 없이 문항 분석이 그 공급자를 호출한다" | 교체 단위가 엔드포인트에서 공급자로 확장 |
| [NFR-15](../../requirements.md#비기능-요구사항) | 토큰 상한 기본값 미정 | + 기본값 시험지 1건당 입력 200,000·출력 30,000 토큰, 설정으로 조정 | Q-05 해소 |
| [Q-05](../../requirements.md#가정과-미해결-질문) | 미해결 — 공급자·예산 상한 | 해소 — 공급자 Anthropic(`claude-opus-5` 기본), 상한은 위 기본값 | 사용자 결정 |
| [시험지 분석 흐름](../../design.md#시험지-분석) 5번 | "LLM 호출 실패는 문항 단위로 재시도 2회" | + 안전 분류기 거부(`refusal`)도 실패로 분류 | Claude 고유 응답 상태 |
| [TASK-23](../../plan.md#task-23-스키마-2차-시험omr상담파일) | `llm_call_log` 기존 컬럼 | + 컬럼 3개 | 착수 전이라 추가 마이그레이션 불필요 |
| [TASK-31](../../plan.md#task-31-문항-분할llmadapter분석) | "OpenAI 호환 `LlmAdapter`" | 공급자 중립 계약 + 구현체 3종, 계약 테스트 공유 | 구현 경로 |

## 영향 범위

- 요구사항과 인수 조건: AC-23 문구 수정, NFR-15 기본값 확정, Q-05 해소. **신설 항목 없음.** FR은 변경 없음.
- 인터페이스와 데이터: REST 계약 변경 없음. `llm_call_log`에 컬럼 3개 추가. 미착수 테이블이라 데이터 마이그레이션이 없다.
- 보안과 개인정보: **경계 변경 없음.** 화이트리스트와 AC-27 테스트가 `QuestionAnalyzer`에 그대로 있다. 외부 호스트가 `api.anthropic.com`으로 추가된다.
- 비용: 새 종량제 비용이 생긴다. 기본 모델 `claude-opus-5` 기준 시험지 1건당 약 740원 추정.
- 진행 중인 구현: 없음. 사이클 1(MVP)은 완료·통합되었고 TASK-23은 리비전 작성 전이라 보류할 구현이 없다.
- 테스트와 문서: 계약 테스트 1건 추가. VER 항목 신설 없음(AC-23·AC-27이 기존 VER로 검증됨). README에 LLM 설정 항목 추가.

## 고려한 대안

대안 비교는 [ADR-009 고려한 대안](./ADR-009-LLM-공급자-추상화와-Claude-연결.md#고려한-대안)에 있다. 요약하면 공급자 중립 계약(선택), OpenAI 호환 shim 유지, Anthropic 전용 교체, 범용 추상화 라이브러리 도입의 4안을 비교했고, shim은 실익 상실로, 전용 교체는 "가변" 미충족으로, 라이브러리는 과한 의존성으로 기각했다.

## 구현된 코드의 처리

- 유지: 사이클 1(TASK-01~TASK-22, TASK-40~TASK-42)의 모든 구현과 검증 기록. 이 변경은 기존 동작을 바꾸지 않는다.
- 수정: 없음(M6 코드는 아직 존재하지 않는다).
- 되돌림: 없음.

## 마이그레이션과 롤백

- 데이터 마이그레이션 없음. `llm_call_log`는 TASK-23에서 처음 생성되므로 컬럼 3개가 최초 정의에 포함된다.
- 새 의존성: `anthropic` Python SDK(`uv add anthropic`). 기본 공급자가 `test`이므로 키 없이도 기동·테스트가 가능하다.
- 롤백: `MATHDESK_LLM_PROVIDER`를 `openai_compat` 또는 `test`로 되돌리면 Anthropic 경로가 즉시 비활성화된다. 코드 롤백이 필요 없다.
- API 키 유출 대응: `integration_setting` 암호화 저장(NFR-05)과 `.env` gitignore 유지. 키 교체는 설정 변경만으로 끝난다.

## 검증 방법

| 검증 | 대상 | 방법 |
|---|---|---|
| 계약 테스트 | NFR-12 | 3개 구현체가 동일한 `LlmAdapter` 계약 테스트를 통과 |
| VER(기존) | AC-23 | 설정에서 공급자를 바꾸면 해당 구현체가 호출되는지 확인(가짜 구현 카운터) |
| VER(기존) | AC-27 | 외부 호출 차단 환경에서 OMR·메시지 경로의 LLM 호출 카운터 0 |
| VER(기존) | AC-22 | 테스트 모드 어댑터로 30문항 초안 생성과 저신뢰 표시 |
| 비용 기록 | NFR-15 | 호출 후 `llm_call_log`에 `provider`·입출력·캐시 토큰·비용이 기록되고, 상한 초과 시 중단과 사용량 보고 |
| 실호출 | — | API 키 확보 후 실제 시험지 1건으로 품질·비용 실측(키 미확보 시 미검증으로 명시) |

## 남은 위험

| 위험 | 영향 | 완화 |
|---|---|---|
| Anthropic API 키가 아직 없다 | Claude 실호출 검증 불가 | 기본 공급자가 `test`라 구현·테스트는 진행 가능. 실호출 검증만 키 확보 시점으로 미룬다 |
| 시험지당 비용 추정이 실측과 다를 수 있다 | 운영비 예측 오차 | 토큰 상한이 stop-loss로 작동. 첫 실호출 후 실측으로 상한·모델 재조정 |
| 구조화 출력 스키마가 분석 결과 구조와 결합한다 | 결과 필드 변경 시 스키마 동시 수정 | 스키마를 분석 결과 모델에서 생성해 단일 소스로 유지 |
| 공급자 구현 2종의 동작이 갈라질 수 있다 | 교체 시 회귀 | 공유 계약 테스트로 강제 |
| 안전 분류기가 일부 문항을 거부할 수 있다 | 해당 문항 미분석 | `refusal`을 문항 단위 실패로 분류해 기존 재시도·부분 저장 경로를 탄다. 수학 문항에서 발생 가능성은 낮다 |

## 승인 기록

| 항목 | 내용 |
|---|---|
| 승인 대상 | 이 DCR 전체와 [ADR-009](./ADR-009-LLM-공급자-추상화와-Claude-연결.md) |
| 결과 | 승인 (Claude 실호출 검증을 최종 단계로 이동하는 조건 반영) |
| 결정자 | 사용자 |
| 결정 일시 | 2026-09-22 |
| 근거 | 2026-09-22 대화형 재승인 응답 "API키는 가장 마지막에 검증하는것으로 하자. 승인." |
| 유효 기준선 | `v3` (효력 시작 2026-09-22) |
| 후속 상태 변경 | [REQ-mathdesk](../../requirements.md)·[DESIGN-mathdesk](../../design.md) 기준선 `v3`, ADR-009 → `approved`, [TASK-43](../../plan.md#task-43-claude-실호출-검증) 신설 |

## 변경 이력

| 날짜 | 변경 | 근거 | 상태 또는 기준선 | 작성자·승인자 |
|---|---|---|---|---|
| 2026-09-22 | 최초 작성 — M6 공급자 중립화와 Claude 연결 제안 | 사용자 요청과 대화형 선택 2건(진행 승인, 기본 모델 `claude-opus-5`), 실행 환경 자격증명 조사 | → awaiting-approval, v2 → v3 제안 | Claude / 승인자 미정 |
| 2026-09-22 | 사용자 재승인 — 기준선 `v3` 발행. Claude 실호출 검증을 TASK-43으로 분리해 최종 단계에 배치 | 대화형 재승인 응답 | awaiting-approval → approved, 기준선 v2 → v3 | Claude / 사용자 |

## 인계

- 다음 단계 또는 워크플로우: wf-implement — TASK-23(컬럼 반영) → TASK-31(구현) → TASK-43(실호출 검증, 최종 단계)
- 시작 조건: 충족됨 — 이 DCR이 `approved`이고 기준선 `v3`가 2026-09-22에 발행되었다
- 입력 문서와 기준선: [REQ-mathdesk](../../requirements.md), [DESIGN-mathdesk](../../design.md), [ADR-009](./ADR-009-LLM-공급자-추상화와-Claude-연결.md)
- 완료된 항목: 현재 상태 조사, 자격증명 확인, 대안 비교, 변경 항목·영향·검증 정의, 재승인과 기준선 v3 발행, 요구사항·설계·계획 갱신
- 미완료 항목: TASK-23 컬럼 반영, TASK-31 구현, TASK-43 실호출 검증
- 차단 요인: 없음. Anthropic API 키는 TASK-43에서만 필요하며 그 앞 구현을 차단하지 않는다
- 다음 행동: TASK-23에서 `llm_call_log` 컬럼 3개를 반영한다
