# 결정 등록부 (Decision Registry)

> 문서 유형: `N/A — wf-design 결정 등록부(§6.2)이며 문서 유형 매핑 대상이 아님`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `in-progress`
> 기준선: `N/A — 등록부는 기준선을 발행하지 않음`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-22`
> 관련 문서: [REQ-mathdesk: 요구사항](./requirements.md), [DESIGN-mathdesk: 설계](./design.md)

## 요약

- 목적: 저장소 전역의 ADR·DCR을 한곳에서 조망하고 다음 일련번호를 발행할 기준을 제공한다.
- 현재 결론 또는 상태: ADR 12건과 DCR 5건이 모두 `approved`다. 유효 기준선은 `v6`이며 마지막 발행 번호는 ADR-012, DCR-005.
- 다음 행동: 없음. 새 ADR·DCR이 생기면 이 등록부를 같은 변경에서 갱신한다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-mathdesk: 요구사항](./requirements.md) | document | 결정이 적용되는 요구사항 기준선 |
| input | baseline | [DESIGN-mathdesk: 설계](./design.md) | DES-01~DES-22 | 결정이 적용되는 설계 |

## 등록부

| ID | 유형 | 제목 | 상태 | 날짜 | 위치 | 대체·관련 |
|---|---|---|---|---|---|---|
| ADR-001 | adr | 기술 스택과 실행 형태 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-001](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) | — |
| ADR-002 | adr | PostgreSQL 단일 저장소 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-002](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) | ADR-001 전제 |
| ADR-003 | adr | AI 작업 분리와 개인정보 경계 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-003](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) | ADR-006 관련 |
| ADR-004 | adr | 문서 입력 정규화 파이프라인 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-004](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) | — |
| ADR-005 | adr | 메시징 어댑터 단일화 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-005](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) | — |
| ADR-006 | adr | OMR 양식 고정과 템플릿 판독 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-006](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) | ADR-003 관련 |
| ADR-007 | adr | 인증·권한 모델 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-007](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) | — |
| ADR-008 | adr | 테스트 운영 노출 구성 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) | ADR-001 보완, DCR-001 |
| ADR-009 | adr | LLM 공급자 추상화와 Claude 연결 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/ADR-009](./work/20260922-mathdesk-baseline/ADR-009-LLM-공급자-추상화와-Claude-연결.md) | ADR-003 결정 2 부분 대체, DCR-002 |
| ADR-010 | adr | 웹 UI 디자인 시스템 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-010](./work/20260922-mathdesk-baseline/ADR-010-웹-UI-디자인-시스템.md) | ADR-011 관련, DCR-003 |
| ADR-011 | adr | 리포트 카드 HTML 렌더링 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-011](./work/20260922-mathdesk-baseline/ADR-011-리포트-카드-HTML-렌더링.md) | ADR-010 관련, DCR-003 |
| ADR-012 | adr | 테마 팔레트와 적용 방식 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/ADR-012](./work/20260922-mathdesk-baseline/ADR-012-테마-팔레트와-적용-방식.md) | ADR-010·ADR-011 관련, DCR-004 |
| DCR-001 | dcr | 테스트 운영 환경 노출 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) | ADR-008 |
| DCR-002 | dcr | M6 LLM 공급자 중립화와 Claude 연결 | approved | 2026-09-22 | [work/20260922-mathdesk-baseline/DCR-002](./work/20260922-mathdesk-baseline/DCR-002-M6-LLM-공급자-중립화와-Claude-연결.md) | ADR-009 |
| DCR-003 | dcr | 브랜드 자산으로서의 시각 설계 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-003](./work/20260922-mathdesk-baseline/DCR-003-브랜드-자산으로서의-시각-설계.md) | ADR-010, ADR-011 |
| DCR-004 | dcr | 웹 테마 선택과 브랜드 색의 역할 분리 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-004](./work/20260922-mathdesk-baseline/DCR-004-웹-테마-선택.md) | ADR-012 |
| DCR-005 | dcr | 화면별 차등 모바일 지원 | approved | 2026-09-23 | [work/20260922-mathdesk-baseline/DCR-005](./work/20260922-mathdesk-baseline/DCR-005-모바일-지원-범위.md) | ADR-010 관련 |
| DCR-006 | dcr | 퇴원·비활성 학생과 반의 삭제 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-006](./work/20260922-mathdesk-baseline/DCR-006-퇴원-비활성-학생과-반의-삭제.md) | — |
| DCR-007 | dcr | 시작 시각만 쓰는 반 시간표 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-007](./work/20260922-mathdesk-baseline/DCR-007-시작-시각만-쓰는-반-시간표.md) | — |
| DCR-008 | dcr | 주간 시간표 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-008](./work/20260922-mathdesk-baseline/DCR-008-주간-시간표.md) | DCR-007 관련 |
| DCR-009 | dcr | 비밀번호 변경과 재설정 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-009](./work/20260922-mathdesk-baseline/DCR-009-비밀번호-변경과-재설정.md) | ADR-007 관련 |
| DCR-010 | dcr | 수업 길이 기본값 4시간 | approved | 2026-09-24 | [work/20260922-mathdesk-baseline/DCR-010](./work/20260922-mathdesk-baseline/DCR-010-수업-길이-4시간.md) | DCR-008 기본값 대체 |

## 번호 발행 규칙

- ADR·DCR 번호는 저장소 전역 일련번호다. 새 번호는 이 등록부의 마지막 번호 다음 번호로 발행한다.
- 다음 ADR 번호: `ADR-013`. 다음 DCR 번호: `DCR-006`.
- 개별 ADR·DCR 파일이 정본이며 이 등록부는 목록이다. 불일치하면 파일에 맞춰 등록부를 수정한다.

## 아웃라인 결정 항목과의 대응

[SPEC-mathdesk-outline §7](./SPEC-mathdesk-outline.md)의 결정 항목 D1~D11이 ADR로 승격된 대응은 다음과 같다.

| 아웃라인 항목 | 처리 |
|---|---|
| D1 프론트엔드 스택, D2 백엔드 스택, D4 로컬 배포 형태 | [ADR-001](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) |
| D3 DB | [ADR-002](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) |
| D5 AI 모델 구성, D10 추론 하드웨어 전략 | [ADR-003](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) · [ADR-009](./work/20260922-mathdesk-baseline/ADR-009-LLM-공급자-추상화와-Claude-연결.md)(공급자 결정) |
| D6 시험지 입력 포맷 | [ADR-004](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) |
| D8 메시지 채널 | [ADR-005](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) |
| D11 OMR 답안지 양식 | [ADR-006](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) |
| D7 MVP 범위 | 요구사항 [범위](./requirements.md#범위)로 흡수. 사용자 결정으로 기준선 범위를 M0~M9 전체로 확대 |
| D9 워크플로우 단계 정의 | wf-implement 스킬 계획 수립 소유 항목이므로 ADR로 승격하지 않는다 |
| (신규) 인증·권한 모델 | [ADR-007](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) |
| (신규) 시각 설계·브랜드 | [ADR-010](./work/20260922-mathdesk-baseline/ADR-010-웹-UI-디자인-시스템.md) · [ADR-011](./work/20260922-mathdesk-baseline/ADR-011-리포트-카드-HTML-렌더링.md) · [DCR-003](./work/20260922-mathdesk-baseline/DCR-003-브랜드-자산으로서의-시각-설계.md) |
| (신규) 웹 테마 | [ADR-012](./work/20260922-mathdesk-baseline/ADR-012-테마-팔레트와-적용-방식.md) · [DCR-004](./work/20260922-mathdesk-baseline/DCR-004-웹-테마-선택.md) |
| (신규) 모바일 지원 범위 | [DCR-005](./work/20260922-mathdesk-baseline/DCR-005-모바일-지원-범위.md) (ADR 없음 — 지원 범위 조정이며 ADR-010의 구현 수단을 그대로 쓴다) |
| (신규) 테스트 운영 노출 | [ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) · [DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) |
