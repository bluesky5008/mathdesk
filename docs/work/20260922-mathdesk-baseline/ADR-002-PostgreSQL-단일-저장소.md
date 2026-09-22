# ADR-002: PostgreSQL 단일 저장소

> 문서 유형: `adr`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `approved`
> 기준선: `N/A — ADR은 기준선 번호를 발행하지 않음`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-22`
> 관련 문서: [REQ-mathdesk: 요구사항](../../requirements.md), [DESIGN-mathdesk: 설계](../../design.md), [결정 등록부](../../decisions.md)

## 요약

- 결정: Phase A와 Phase B 모두 PostgreSQL을 유일한 데이터베이스로 사용하고 SQLite를 대안으로 두지 않는다.
- 핵심 이유: 로컬과 운영의 DB가 같으면 쿼리·타입·마이그레이션을 한 번만 검증하면 된다.
- 주요 단점: 로컬 실행에 Postgres 컨테이너가 필요해 단일 실행파일 배포가 어려워진다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-mathdesk: 요구사항](../../requirements.md) | NFR-08, NFR-09 | 이식성·스키마 관리 |
| output | decision | [DESIGN-mathdesk: 설계](../../design.md) | DES-21 | 마이그레이션 설계 |
| output | related | [결정 등록부](../../decisions.md) | ADR-002 | 등록부 등재 |

## 배경

Phase A는 로컬 단독 사용이라 파일 기반 SQLite가 배포상 매력적이다. 그러나 Phase B는 다중 학원·동시 접속을 전제하므로 PostgreSQL이 필요하다. 두 DB를 함께 지원하면 SQL 방언, JSON 타입, 동시성 동작이 갈린다.

## 영향을 받는 요구사항과 제약

- [NFR-09 스키마 관리](../../requirements.md#비기능-요구사항): 마이그레이션이 빈 DB에서 재현 가능해야 한다.
- [NFR-01 대시보드 응답](../../requirements.md#비기능-요구사항): 집계 쿼리 성능이 DB 엔진에 의존한다.
- [ADR-001](./ADR-001-기술-스택과-실행-형태.md)에서 `docker compose` 실행을 채택해 컨테이너 추가 비용이 낮다.

## 고려한 대안

| 대안 | 장점 | 단점·위험 | 전환 비용 |
|---|---|---|---|
| A. PostgreSQL 단일 (선택) | 로컬·운영 동일, JSONB·집계 기능 활용, 검증 1회 | 로컬에 컨테이너 필요 | — |
| B. SQLite(로컬) + PostgreSQL(운영) | 로컬 배포 간단 | 방언 차이로 이중 검증, 전환 시 버그 위험 | 높음 |
| C. SQLite 단일 | 가장 단순 | Phase B 다중 사용자 요구를 만족하지 못함 | 매우 높음 |

## 결정

PostgreSQL을 단일 저장소로 고정한다. 로컬에서도 Docker Postgres 컨테이너를 사용한다. ORM은 SQLAlchemy 2.0 async, 스키마 변경은 Alembic 리비전으로만 수행한다.

## 이유

1. 두 DB를 지원하면 모든 쿼리와 마이그레이션을 두 번 검증해야 하며, 이 비용이 로컬 배포 편의보다 크다.
2. JSONB(OMR 판독 페이로드, 정답표)와 집계 함수 활용이 설계 단순화에 직접 기여한다.
3. `docker compose` 실행을 이미 채택했으므로 컨테이너 1개 추가의 한계 비용이 작다.

## 결과와 감수할 단점

- 순수 단일 실행파일 배포는 불가능하다. 설치 패키지가 필요해지면 내장 Postgres 번들링을 별도로 결정한다.
- 사용자 PC에 Docker가 없으면 사용할 수 없다. 설치 안내와 기동 스크립트로 완화한다.

## 후속 작업

- `docker compose`에 Postgres 볼륨·백업 스크립트 포함(NFR-11)

## 대체 관계

- 대체 대상 ADR: 없음
- 대체 ADR: 없음

## 승인 기록

- 결과: 승인 (2026-09-22, 결정자 `사용자`)
- 근거: [DESIGN-mathdesk 승인 기록](../../design.md#승인-기록)의 기준선 `v1` 승인에 포함됨

## 변경 이력

| 날짜 | 변경 | 근거 | 상태 또는 기준선 | 작성자·승인자 |
|---|---|---|---|---|
| 2026-09-22 | 최초 작성 | [SPEC-mathdesk-outline](../../SPEC-mathdesk-outline.md) D3 | → proposed | Claude |
| 2026-09-22 | 사용자 승인 | [DESIGN-mathdesk 승인 기록](../../design.md#승인-기록) | proposed → approved | Claude / 사용자 |
