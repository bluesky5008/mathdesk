# WORK-20260922-mathdesk-baseline: 작업 기록

> 문서 유형: `work-log`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `in-progress`
> 기준선: `v1`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-24`
> 관련 문서: [PLAN-mathdesk: 구현 계획](../../plan.md), [REQ-mathdesk: 요구사항](../../requirements.md), [DESIGN-mathdesk: 설계](../../design.md), [결정 등록부](../../decisions.md)

## 요약

- 목적: 기준선 `v1`의 구현 진행 상태, 결정, 검증 결과와 재개 지점을 기록한다.
- 현재 결론 또는 상태: **사이클 1(MVP)이 사용자 승인으로 완료**되었다. AC-01~AC-18 전항 성공, NFR-01(p95 21ms)·NFR-02(p95 8ms) 통과. 사이클 2(M5~M9)를 시작한다.
- 다음 행동: [TASK-49 마스터 데이터 수정 기능 보완](../../plan.md#task-49-마스터-데이터-수정-기능-보완) — 하위 TASK-50(학생 수정·퇴원) → TASK-51(반 수정·활성 여부, API 보완 포함) → TASK-52(수강 배정·해제). 사용자가 지정한 순서는 모바일 → 마스터 데이터 수정 → 사이클 2 재개다. 모바일 대응은 [TASK-53](../../plan.md#task-53-화면별-차등-모바일-대응)으로 등록되었고 사용자 지시로 **후순위**(카드 작업 뒤)다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | implementation | [PLAN-mathdesk: 구현 계획](../../plan.md) | TASK-01~TASK-39 | 이 기록이 수행하는 계획 |
| input | baseline | [REQ-mathdesk: 요구사항](../../requirements.md) | AC-01~AC-27 | 검증 대상 인수 조건 |
| input | baseline | [DESIGN-mathdesk: 설계](../../design.md) | DES-01~DES-22 | 적용 설계 기준선 |
| input | decision | [결정 등록부](../../decisions.md) | ADR-001~ADR-007 | 적용 결정 |

## 기준선과 현재 계획

- 적용 기준선: [REQ-mathdesk](../../requirements.md) `v6`, [DESIGN-mathdesk](../../design.md) `v6` (2026-09-23 재승인)
- 현재 계획: [PLAN-mathdesk](../../plan.md) — 작업 47건, 사이클 1(MVP M0~M4, TASK-01~22 + TASK-40~42) / 사이클 2(확장 M5~M9, TASK-23~39, TASK-43)
- 발생한 DCR: [DCR-001](./DCR-001-테스트-운영-환경-노출.md) (v2), [DCR-002](./DCR-002-M6-LLM-공급자-중립화와-Claude-연결.md) (v3), [DCR-003](./DCR-003-브랜드-자산으로서의-시각-설계.md) (v4), [DCR-004](./DCR-004-웹-테마-선택.md) (v5), [DCR-005](./DCR-005-모바일-지원-범위.md) (v6) — 모두 `approved`

## 현재 상태

- 진행 중인 작업: [TASK-29 M6 시험지 분석](../../plan.md#task-29-m6-시험지-분석) — TASK-30·31 완료, TASK-32 남음
- 마지막 완료 작업: [TASK-31 문항 분할·LlmAdapter·분석](../../plan.md#task-31-문항-분할llmadapter분석) (2026-09-24 03:30)
- 차단 요인: 없음. Anthropic API 키는 [TASK-43](../../plan.md#task-43-claude-실호출-검증)에서만 필요하며 그 앞 구현을 차단하지 않는다. 구 경로(`/api/messages/report.png`)의 Cloudflare 엣지 캐시 퍼지는 사용자가 보류했다(TTL 만료로 자연 해소)

## 계획 트리

<!-- snapshot: 2026-09-22 완료 시점 — 사이클 1(MVP) 서브트리. 재생성하지 않는다. -->

```text
├─ [✓] 사이클 1 — MVP (M0~M4) ....................... completed (23/23) 2026-09-22 20:05
│  ├─ [▶] TASK-01 M0 기반 (분해 5, 4/5)
│  │   ├─ [✓] TASK-02 모노레포 스캐폴딩과 실행 환경 ... 2026-09-22 09:58
│  │   ├─ [✓] TASK-03 스키마 1차·마이그레이션·시드 .... 2026-09-22 10:26
│  │   ├─ [✓] TASK-04 인증과 세션 .................... 2026-09-22 10:53
│  │   ├─ [✓] TASK-05 권한·캠퍼스 스코프 강제 ........ 2026-09-22 11:14
│  │   └─ [✓] TASK-40 로그인 시도 제한 ............... 2026-09-22 14:31
│  ├─ [✓] TASK-06 M1 학생/반 관리 (분해 2, 2/2) ...... 2026-09-22 12:34
│  │   ├─ [✓] TASK-07 마스터 데이터 API .............. 2026-09-22 11:36
│  │   └─ [✓] TASK-08 마스터 데이터 화면 ............. 2026-09-22 12:34
│  ├─ [✓] TASK-09 M2 일일 수업 입력 (분해 3, 3/3) .... 2026-09-22 13:58
│  │   ├─ [✓] TASK-10 일일 기록 API (3 저장 단위) .... 2026-09-22 13:02
│  │   ├─ [✓] TASK-11 출결 확정·재검사 판정 .......... 2026-09-22 13:29
│  │   └─ [✓] TASK-12 일일 입력 2패널 화면 ........... 2026-09-22 13:58
│  ├─ [✓] TASK-13 M3 대시보드 (분해 2, 2/2) .......... 2026-09-22 16:31
│  │   ├─ [✓] TASK-14 KPI 집계 API ................... 2026-09-22 16:02
│  │   └─ [✓] TASK-15 대시보드 화면 .................. 2026-09-22 16:31
│  ├─ [✓] TASK-16 M4 메시지 (분해 4, 4/4) ............ 2026-09-22 19:12
│  │   ├─ [✓] TASK-17 메시지 렌더러와 등급 문구 ...... 2026-09-22 17:03
│  │   ├─ [✓] TASK-18 리포트 이미지와 복사 ........... 2026-09-22 18:05
│  │   ├─ [✓] TASK-19 MessagingAdapter·발송 로그 ..... 2026-09-22 18:41
│  │   └─ [✓] TASK-20 메시지 화면 .................... 2026-09-22 19:12
│  ├─ [✓] TASK-21 MVP 통합·인수 검증 ................. 2026-09-22 19:48
│  └─ [✓] TASK-22 ★ MVP 사이클 완료 승인 ............. 2026-09-22 20:05
```

```mermaid
flowchart TD
    C1["사이클 1 — MVP (M0~M4)"]:::done
    C1 --> T01["TASK-01 M0 기반"]:::active
    T01 --> T02["TASK-02 스캐폴딩"]:::done
    T01 --> T03["TASK-03 스키마 1차·마이그레이션"]:::done
    T01 --> T04["TASK-04 인증·세션"]:::done
    T01 --> T05["TASK-05 권한·캠퍼스 스코프"]:::done
    T01 --> T40["TASK-40 로그인 시도 제한"]:::todo
    C1 --> T06["TASK-06 M1 학생/반 관리"]:::done
    T06 --> T07["TASK-07 마스터 데이터 API"]:::done
    T06 --> T08["TASK-08 마스터 데이터 화면"]:::done
    C1 --> T09["TASK-09 M2 일일 수업 입력"]:::done
    T09 --> T10["TASK-10 일일 기록 API (3 저장 단위)"]:::done
    T09 --> T11["TASK-11 출결 확정·재검사 판정"]:::done
    T09 --> T12["TASK-12 일일 입력 2패널 화면"]:::done
    C1 --> T13["TASK-13 M3 대시보드"]:::done
    T13 --> T14["TASK-14 KPI 집계 API"]:::done
    T13 --> T15["TASK-15 대시보드 화면"]:::done
    C1 --> T16["TASK-16 M4 메시지"]:::done
    T16 --> T17["TASK-17 메시지 렌더러·등급 문구"]:::done
    T16 --> T18["TASK-18 리포트 이미지·복사"]:::done
    T16 --> T19["TASK-19 MessagingAdapter·발송 로그"]:::done
    T16 --> T20["TASK-20 메시지 화면"]:::done
    C1 --> T21["TASK-21 MVP 통합·인수 검증"]:::done
    C1 --> T22[["★ TASK-22 MVP 사이클 완료 승인"]]:::done
    T02 -. depends .-> T03
    T03 -. depends .-> T04
    T04 -. depends .-> T05
    T05 -. depends .-> T07
    T07 -. depends .-> T10
    T10 -. depends .-> T14
    T10 -. depends .-> T17
    T21 -. depends .-> T22
    classDef done fill:#c8e6c9,stroke:#2e7d32
    classDef active fill:#fff9c4,stroke:#f9a825
    classDef todo fill:#eceff1,stroke:#90a4ae
    classDef gate fill:#ffcdd2,stroke:#c62828
```

## 수행 기록

### 2026-09-22 — 기준선 승인과 계획 수립

- 수행 내용
  - wf-design으로 [요구사항](../../requirements.md)(FR 39·NFR 16·AC 27)과 [설계](../../design.md)(DES 22·테이블 24·REST 계약)를 작성하고 사용자 승인으로 기준선 `v1`을 발행했다.
  - ADR-001~007을 작성하고 `approved`로 전이했다.
  - wf-implement로 [구현 계획](../../plan.md)을 수립했다. 작업 39건을 두 사이클로 분할하고 계획 트리(ASCII + mermaid 2종)와 검증 계획 VER-01~24를 작성했다.
- 변경 파일: `docs/requirements.md`, `docs/design.md`, `docs/decisions.md`, `docs/plan.md`, `docs/work/20260922-mathdesk-baseline/ADR-001~007`, `README.md`, `docs/SPEC-mathdesk-outline.md`
- 발견 사항
  - 저장소에 제품 코드가 없다. `prototype/omr`(판독기·템플릿·합성 테스트)과 `prototype/notice-generator.html`만 존재하며 둘 다 참조 구현이다.
  - `prototype/omr/test_omr.py`의 합성 왜곡 테스트가 AC-24의 검증 방법과 그대로 대응하므로 TASK-34에서 제품 테스트로 이식하기로 계획했다.
- 결정과 이유
  - 포트폴리오(`docs/status.md`) 계층을 두지 않고 단일 작업 ID의 `plan.md` 하나로 관리한다. 기준선이 작업 ID를 하나만 발행했고, 사이클 축약 규칙으로 문서 비대화를 처리할 수 있다.
  - 사이클 2 작업(TASK-23~39)은 목표·의존성·완료 조건까지만 확정하고 변경 대상 파일 수준의 상세는 사이클 1 완료 시점에 구체화한다. 지금 상세화하면 사이클 1 결과에 따라 낡는다.
  - 릴리스 관문 TASK-22·TASK-39를 별도 작업으로 두었다. push는 설계 승인으로 대체되지 않는 외부·비가역 작업이다.
- 실행한 검증
  - 문서 링크·앵커 전수 검사(로컬 링크 전부 해석 성공), 식별자 중복 검사(FR 39 / NFR 16 / AC 27 / DES 22 / Q 11 / RISK 10, 중복 0).
  - 코드 검증은 없음 — 구현 미착수.
- 결과: 계획 수립 완료. 구현 미착수.

### 2026-09-22 — TASK-02 모노레포 스캐폴딩과 실행 환경

- 수행 내용
  - TDD Red: `apps/api/tests/test_health.py`에 `GET /api/health` → 200 `{"status":"ok"}`를 기대하는 통합 테스트를 먼저 작성하고 실행해 `ModuleNotFoundError: No module named 'mathdesk.main'`로 의도한 실패를 확인했다.
  - Green: `apps/api/src/mathdesk/main.py`에 FastAPI 앱과 헬스 엔드포인트만 구현했다.
  - `apps/web`에 React 19 + Vite + TypeScript 최소 SPA를 손으로 구성했다(API 상태 표시 1화면).
  - `compose.yaml`과 api·web Dockerfile로 api + web + postgres 3개 서비스를 구성했다.
- 변경 파일: `apps/api/{pyproject.toml,uv.lock,Dockerfile,.dockerignore,src/mathdesk/{__init__,main}.py,tests/test_health.py}`, `apps/web/{package.json,package-lock.json,tsconfig.json,vite.config.ts,index.html,Dockerfile,.dockerignore,src/{main,App}.tsx}`, `compose.yaml`, `README.md`, `.gitignore`
- 발견 사항
  - 호스트의 8000 포트를 다른 Docker 컨테이너가 이미 점유하고 있어 api 컨테이너 기동이 실패했다. 호스트 포트를 `API_PORT`(기본 8080)·`WEB_PORT`(기본 5173) 환경변수로 노출해 해소했다.
  - Vite 설정에서 `process.env`를 쓰려면 `@types/node`가 필요해 devDependency 1건을 추가했다.
  - 시스템 Python이 3.9라 `uv`로 3.12 가상환경을 만들어 사용한다. 저장소는 `uv.lock`으로 버전을 고정한다.
- 결정과 이유
  - Vite 공식 템플릿 생성기 대신 최소 파일만 손으로 작성했다. 템플릿은 로고·데모 카운터·린트 설정 등 기준선이 요구하지 않는 보일러플레이트를 포함한다(결정 사다리 1단계).
  - 이 작업에서는 DB 연결 설정(`DATABASE_URL`)을 추가하지 않았다. 사용처가 TASK-03에서 처음 생기므로 지금 넣으면 미사용 설정이 된다. postgres 서비스 자체는 완료 조건이 요구하므로 포함했다.
  - 라우팅(React Router)과 서버 상태(TanStack Query)는 화면이 생기는 TASK-08부터 도입한다.
  - `POSTGRES_PASSWORD`는 로컬 기동성을 위해 기본값을 두되 5432를 호스트에 게시하지 않고 README에 `.env` 재정의를 안내했다.
- 실행한 검증
  - `uv run pytest -q` — 최초 실행 `1 error`(의도한 Red, 모듈 없음) → 구현 후 `1 passed`.
  - `npm run build` — `tsc -b && vite build` 성공(28 modules, dist 생성). 최초 실행은 `process` 타입 누락으로 실패 후 `@types/node` 추가로 통과.
  - `docker compose up -d --build` → `docker compose ps`에서 api·postgres·web 3개 `running`.
  - `curl http://localhost:8080/api/health` → `{"status":"ok"}`, `curl http://localhost:5173/api/health`(웹 개발 서버 프록시 경유) → `{"status":"ok"}`.
- 결과: TASK-02 완료. 완료 조건(3개 컨테이너 기동 + API 테스트 1회 성공 + 웹 빌드 1회 성공) 전항 충족.

### 2026-09-22 — TASK-03 스키마 1차·마이그레이션·시드

- 수행 내용
  - TDD Red: `tests/test_migrations.py`에 빈 DB → `upgrade head` → 16개 테이블 존재 확인 → `downgrade base` → 테이블 소거를 검증하는 테스트를 먼저 작성해 `No 'script_location' key found`로 의도한 실패를 확인했다.
  - Green: SQLAlchemy 2.0 선언형 모델 16개(`models/{base,masterdata,daily,messaging,system}.py`)와 alembic 비동기 환경(`migrations/env.py`)을 만들고 초기 리비전 `5b67d2c537eb`을 autogenerate했다.
  - TDD Red → Green: 시드 스크립트 테스트(반 4 · 학생 47 · 수강 47 · 수험번호 누락 0)를 먼저 작성하고 `src/mathdesk/seed.py`를 구현했다.
  - `compose.yaml`에 postgres 호스트 포트 게시(`POSTGRES_PORT`, 기본 55432)와 api의 `DATABASE_URL`을 추가했다.
- 변경 파일: `apps/api/{alembic.ini,migrations/,src/mathdesk/models/,src/mathdesk/seed.py,tests/{conftest,test_migrations,test_seed}.py,pyproject.toml,uv.lock}`, `compose.yaml`, `README.md`
- 발견 사항
  - SQLAlchemy 비동기 엔진이 `greenlet`을 요구해 의존성 1건을 추가했다.
  - 호스트 5432는 로컬 postgres가 점유 중이라 컨테이너 postgres를 55432로 게시했다.
- 결정과 이유
  - 열거값은 네이티브 Postgres enum 대신 `native_enum=False`(VARCHAR + CHECK)로 만들었다. 네이티브 enum은 downgrade에서 타입 삭제가 따로 필요해 왕복 마이그레이션이 복잡해진다.
  - `MetaData`에 명명 규칙을 두어 제약·인덱스 이름을 결정적으로 만들었다. 이름 없는 제약은 downgrade에서 삭제 대상을 특정하기 어렵다.
  - 테스트 DB를 `mathdesk_test`로 분리하고 픽스처가 매번 다시 만든다. 개발 DB에 직접 `downgrade base`를 걸면 시드 데이터가 사라진다.
  - 시드의 원장 계정 `password_hash`는 로그인 불가 표시 `!`로 두었다. 실제 해시는 TASK-04에서 설정하며, 지금 임시 비밀번호를 심으면 약한 자격 증명이 저장소에 남는다.
  - `db.py`(엔진·세션 팩토리) 도입을 미뤘다. 현재 사용처는 시드 하나뿐이며 앱 배선이 생기는 TASK-04에서 만든다.
  - 시드는 이미 캠퍼스가 있으면 예외로 중단한다. 재실행 시 학생이 94명으로 불어나는 사고를 막는다.
- 실행한 검증
  - `uv run pytest -q` — 마이그레이션 테스트 최초 `1 failed`(의도한 Red), 시드 테스트 최초 `ModuleNotFoundError`(의도한 Red) → 구현 후 전체 `3 passed`.
  - 개발 DB에 `alembic upgrade head` + `python -m mathdesk.seed` 실행 → class 4 / student 47 / enrollment 47 / guardian 47, 수험번호 `10000100`~`10004700`(자리별 범위 준수).
  - `docker compose ps` — postgres가 55432로 게시된 상태로 재기동 확인.
- 결과: TASK-03 완료. 완료 조건(왕복 마이그레이션 통과, 시드로 반 4개·학생 47명 투입) 전항 충족. VER-23(NFR-09)의 마이그레이션 왕복 근거가 확보되었다.

### 2026-09-22 — TASK-04 인증과 세션

- 수행 내용
  - TDD Red: `tests/test_auth.py`에 AC-01 흐름(로그인 → `/me` → 로그아웃 → `/me` 401), 오답 거부, 평문 미저장·미노출, 쿠키 속성 4개 테스트를 먼저 작성해 `ModuleNotFoundError: mathdesk.security`로 의도한 실패를 확인했다.
  - Green: `security.py`(Argon2id), `db.py`(엔진·세션 의존성), `models/auth.py`(`user_session`), `auth.py`(로그인·로그아웃·`/me`·`current_user` 의존성·초기 원장 계정), `main.py` lifespan 배선을 구현했다.
  - 웹에 로그인 화면(`LoginForm.tsx`)과 인증 상태 분기(`App.tsx`), API 클라이언트(`api.ts`)를 추가했다.
  - alembic 리비전 `977a7bf03a58`(user_session)을 추가했다.
- 변경 파일: `apps/api/src/mathdesk/{security,db,auth,main}.py`, `apps/api/src/mathdesk/models/{auth.py,__init__.py}`, `apps/api/migrations/versions/977a7bf03a58_user_session.py`, `apps/api/tests/{conftest,test_auth,test_migrations}.py`, `apps/web/src/{api.ts,LoginForm.tsx,App.tsx}`, `compose.yaml`, `README.md`
- 발견 사항
  - 시드가 만든 원장 계정의 `password_hash`가 `!`(사용 불가)였고, 초기 계정 준비 로직이 이를 실제 해시로 교체해 로그인이 가능해졌다. 이미 사용 중인 비밀번호는 덮어쓰지 않는다.
- 결정과 이유
  - 세션 토큰은 SHA-256 해시로만 저장한다. DB 덤프가 곧 세션 탈취가 되지 않도록.
  - 계정이 없거나 비밀번호가 미설정이어도 더미 해시로 동일한 검증 비용을 치른다. 응답 시간으로 계정 존재를 알아내는 것을 막는다.
  - 초기 원장 계정 환경변수는 compose에 기본값을 두지 않았다. 기본 비밀번호를 저장소에 남기지 않기 위해서다. 비우면 계정을 만들지 않는다.
  - React Router·TanStack Query는 아직 도입하지 않았다. 화면이 2개(로그인·빈 대시보드)뿐이라 필요가 없다. TASK-08에서 도입한다.
- 실행한 검증
  - `uv run pytest -q` — 인증 테스트 최초 `ModuleNotFoundError`(의도한 Red) → 구현 후 전체 `7 passed`.
  - `npm run build` 성공.
  - 실행 스택 e2e(`curl`): 비로그인 `/api/auth/me` 401 → 오답 로그인 401 → 정상 로그인 200(쿠키 `HttpOnly`) → `/me` 200 → 로그아웃 204 → `/me` 401.
- 결과: TASK-04 완료. AC-01(VER-01) 통과, 완료 조건(평문 미저장 확인 포함) 충족.

### 2026-09-22 — TASK-05 권한·캠퍼스 스코프 강제

- 수행 내용
  - TDD Red: `tests/test_scope.py`에 엔드포인트 순회 회귀 테스트, 캠퍼스 목록 필터링(AC-03), 타 캠퍼스 헤더 거부(AC-03), 강사의 사용자 관리 거부(AC-02 역할 부분), 원장의 사용자 생성·조회를 먼저 작성해 `ModuleNotFoundError: mathdesk.scope`로 의도한 실패를 확인했다.
  - Green: `scope.py`(`Scope`·`current_scope`·`ScopedRepository`)와 `users.py`(캠퍼스 목록, 사용자 CRUD)를 구현하고 `main.py`에 배선했다.
  - `ScopedRepository`의 캠퍼스 필터를 검증하는 테스트를 추가하고, 필터를 제거하는 변이를 넣어 테스트가 실제로 실패하는지 확인했다(제거 시 `1 failed`, 복원 시 통과).
- 변경 파일: `apps/api/src/mathdesk/{scope,users,main}.py`, `apps/api/tests/{conftest,test_scope}.py`
- 발견 사항
  - 엔드포인트 순회 테스트는 FastAPI의 `route.dependant`를 재귀 탐색해 `current_scope` 의존 여부를 판정한다. 인증·헬스 4개 경로만 예외 목록으로 두었으므로, 이후 스코프를 빠뜨린 엔드포인트가 추가되면 즉시 실패한다([RISK-08](../../design.md#위험) 완화).
- 결정과 이유
  - 권한 없음은 404가 아니라 403으로 통일했다(설계 REST 계약). 자원 존재 여부를 응답으로 알아낼 수 없게 하기 위해서다.
  - `X-Campus-Id`를 생략하면 접근 가능한 첫 캠퍼스를 사용한다. Phase A 단일 캠퍼스에서 헤더를 매 요청에 붙이지 않아도 되게 하되, 지정한 캠퍼스가 접근 불가면 403이다.
  - `ScopedRepository`는 현재 엔드포인트에서 쓰이지 않지만 유지했다. 계획이 요구하는 산출물이고, 변이 테스트로 실효성을 확인했으며 TASK-07에서 바로 사용한다.
  - 사용자 목록·수정은 현재 캠퍼스에 속한 사용자로 제한한다. 다른 캠퍼스 사용자 조회·수정 시도는 403이다.
- 실행한 검증
  - `uv run pytest -q` — 스코프 테스트 최초 `ModuleNotFoundError`(의도한 Red) → 구현 후 전체 `13 passed`.
  - 변이 테스트: `ScopedRepository.select`의 캠퍼스 필터 제거 → `1 failed`, 복원 → `13 passed`.
  - 실행 스택 e2e(`curl`): 로그인 후 `/api/campuses` → 접근 가능한 1개만 반환, `/api/users` → 캠퍼스 내 사용자만, `X-Campus-Id: 999` → 403.
- 결과: TASK-05 완료. AC-03(VER-02 일부) 통과, AC-02는 역할 기반 거부만 통과. 반 소유권 기반 거부는 학생 기록 API가 생기는 TASK-07·TASK-10에서 재검증한다.

### 2026-09-22 — TASK-07 마스터 데이터 API

- 수행 내용
  - TDD Red: `tests/test_masterdata.py`에 수험번호 자리별 범위(AC-04) 파라미터 테스트, 학생 생성·목록, 범위 위반 422, 중복 409, 수강 등록의 날짜 기준 소속 판정, 강사의 비담당 반 접근 403, 강사의 담당 반·소속 학생 조회를 먼저 작성해 `ModuleNotFoundError: mathdesk.masterdata`로 의도한 실패를 확인했다.
  - Green: `masterdata.py`에 `validate_omr_number`와 학생·보호자·반·시간표·수강 등록 엔드포인트를 구현하고 `main.py`에 배선했다.
- 변경 파일: `apps/api/src/mathdesk/{masterdata,main}.py`, `apps/api/tests/test_masterdata.py`
- 발견 사항
  - 엔드포인트를 11개 추가했는데 [TASK-05](../../plan.md#task-05-권한캠퍼스-스코프-강제)의 순회 회귀 테스트가 그대로 통과했다. 스코프 누락 없이 추가되었다는 자동 근거다.
- 결정과 이유
  - 시간표를 별도 엔드포인트로 두지 않고 반 생성·수정 페이로드에 포함했다. 설계의 REST 계약에 시간표 엔드포인트가 없고, 반과 분리해 관리할 요구가 없다.
  - 강사 가시성은 쿼리 자체에 반영했다. 반은 `teacher_id`로, 학생은 담당 반의 수강 등록으로 좁힌다. 조회 후 필터링하면 누락 시 노출로 이어진다.
  - 수험번호 중복 검사는 캠퍼스 범위로 한정했다(스키마의 `uq_student_campus_id_omr_number`와 일치). DB 제약과 API 검사를 모두 두어 409를 사용자 메시지로 돌려준다.
  - 수강 등록 조회에 `on=<date>` 파라미터를 두어 특정 날짜의 소속을 재현한다(FR-08).
- 실행한 검증
  - `uv run pytest -q` — 마스터 데이터 테스트 최초 `ModuleNotFoundError`(의도한 Red) → 구현 후 전체 `26 passed`.
  - 시드된 개발 DB e2e(`curl`): 학생 47명, 반 4개(각 시간표 1건), 범위 위반 수험번호 `18600001` → 422, `2026-04-01` 기준 1반 수강생 8명.
- 결과: TASK-07 완료. AC-04(VER-03) 통과, 완료 조건의 날짜 기준 소속 조회 통과. AC-02의 반 소유권 차원이 이 작업에서 검증되었고, 일일 학생 기록 API 대상 검증은 TASK-10에 남는다.

### 2026-09-22 — TASK-08 마스터 데이터 화면 (TASK-06 완료)

- 수행 내용
  - 웹 테스트 하네스를 붙였다(vitest + jsdom + Testing Library, `npm test`).
  - TDD Red: `StudentsPage.test.tsx`에 목록 렌더와 "수험번호 범위 위반 시 서버 메시지 표시"를 먼저 작성해 `Failed to resolve import "./StudentsPage"`로 의도한 실패를 확인했다.
  - Green: `api.ts`를 서버 오류 메시지를 예외로 전달하는 클라이언트로 확장하고 `StudentsPage`·`ClassesPage`를 구현했다. React Router와 TanStack Query를 이 시점에 도입했다.
  - AC-05 렌더 테스트(`Roster.test.tsx`)와 시간표 문자열 포맷 테스트를 추가했다.
- 변경 파일: `apps/web/{package.json,package-lock.json,vite.config.ts,tsconfig.json}`, `apps/web/src/{api.ts,App.tsx,main.tsx}`, `apps/web/src/pages/{StudentsPage,ClassesPage}.tsx`, `apps/web/src/pages/*.test.tsx`, `apps/web/src/test/setup.ts`
- 발견 사항
  - `vite.config.ts`에 `test` 블록을 두려면 `defineConfig`를 `vitest/config`에서 가져와야 한다. `vite`에서 가져오면 타입 오류로 빌드가 실패한다.
- 결정과 이유
  - 서버의 `detail` 문구를 그대로 화면에 표시한다. 수험번호 자리별 범위 같은 규칙을 클라이언트에 복제하면 서버와 어긋날 수 있고, 서버 메시지가 이미 사용자용 한국어다.
  - 학생과 반 화면을 한 라우트(`/students`)에 함께 두었다. 참조 화면의 메뉴가 "학생/반 관리" 하나이고, 지금 분리할 이유가 없다.
  - AC-05는 47명·4반 응답을 주입한 렌더 테스트로 검증했다. 실제 브라우저 육안 확인은 계획의 자동화 제외 항목으로 남긴다.
- 실행한 검증
  - `npm test` — 컴포넌트 테스트 최초 import 실패(의도한 Red) → 구현 후 `3 files, 5 tests passed`.
  - `npm run build` — `defineConfig` 출처 수정 후 성공.
  - `uv run pytest -q` — `26 passed` (회귀 없음).
  - 실행 스택: `http://localhost:5173/students` 200, 개발 서버 프록시 경유 `/api/students`가 시드 47명 반환.
- 결과: TASK-08 완료, 이로써 TASK-06(M1 학생/반 관리)도 완료. AC-05(VER-04) 통과.

### 2026-09-22 — TASK-10 일일 기록 API (3 저장 단위)

- 수행 내용
  - TDD Red: `tests/test_daily.py`에 수업일 기준 수강생 목록, 저장 단위 독립(AC-11), 재검사 즉시 저장, 반 평균(AC-12), 등원 집계, 강사의 타 반 접근 거부를 먼저 작성해 `6 failed`로 의도한 실패를 확인했다.
  - Green: `daily.py`에 `GET /api/daily`와 메모·표 일괄·재검사 3개 저장 엔드포인트를 구현했다.
- 변경 파일: `apps/api/src/mathdesk/{daily,main}.py`, `apps/api/tests/test_daily.py`
- 결정과 이유
  - 세 저장 엔드포인트 모두 `model_dump(exclude_unset=True)`로 **보낸 필드만** 갱신한다. 이것이 AC-11(저장 단위 독립)을 만족시키는 핵심이다. 전체 객체를 덮어쓰면 다른 단위의 값이 사라진다.
  - 수업 세션은 `GET /api/daily`에서 없으면 만든다. 설계 REST 계약에 세션 생성 엔드포인트가 없고 [DES-05](../../design.md#des-05-상세)가 "첫 입력 시 생성"이라 조회 시점이 유일한 생성 지점이다. 생성되는 행은 `class_id`+`session_date`뿐이라 비용이 낮다.
  - 학생 목록은 수업일 기준 수강 등록으로 정한다([TASK-07](../../plan.md#task-07-마스터-데이터-api)의 `on=<date>` 판정과 같은 규칙). 과거 수업일을 열어도 그날의 명단이 재현된다.
  - 표 일괄 저장은 그날 수강 등록이 없는 학생 ID를 403으로 거부한다. 다른 반 학생 ID를 섞어 보내는 경로를 막는다.
  - 등원 인원은 `출석+지각+조퇴`로 계산한다(FR-09).
- 실행한 검증
  - `uv run pytest -q` — 일일 기록 테스트 최초 `6 failed`(의도한 Red) → 구현 후 전체 `32 passed`.
  - 시드 DB e2e(`curl`): 세션 생성 → 진도·과제·시험명 메모 저장 → 학생 3명 점수 78·72·65와 출결 저장 → 재조회에서 진도·과제 보존, `{'enrolled': 8, 'attending': 2, 'test_average': 71.7, 'test_count': 3}`.
- 결과: TASK-10 완료. AC-11(VER-08)·AC-12(VER-09) 통과. AC-02의 일일 기록 API 대상 검증도 이 작업에서 통과했다(강사의 타 반 `GET`·`PUT` 모두 403).

### 2026-09-22 — TASK-11 출결 확정·재검사 판정

- 수행 내용
  - TDD Red: `tests/test_attendance.py`에 출결 토글 해제(AC-06), 확정 후 잠금과 해제, 잠금 중 등급 수정 허용, 확정·해제 감사 기록, 직전 수업 등급 기반 재검사 판정(AC-09), 재검사 즉시 저장(AC-10)을 먼저 작성해 `4 failed`로 의도한 실패를 확인했다.
  - Green: `daily.py`에 `attendance/confirm`·`attendance/unlock` 엔드포인트, 잠금 중 출결 필드 409 거부, 직전 세션 등급 조회와 재검사 판정을 구현했다.
  - `klass` 픽스처를 `conftest.py`로 옮겨 일일 기록·출결 테스트가 공유하게 했다.
- 변경 파일: `apps/api/src/mathdesk/daily.py`, `apps/api/tests/{conftest,test_daily,test_attendance}.py`
- 결정과 이유
  - 재검사 대상은 저장하지 않고 조회할 때마다 계산한다. 기준 등급이 설정값이라 저장하면 설정 변경 즉시 낡는다([FR-12 상세](../../requirements.md#fr-12-상세)).
  - 기준 등급은 환경변수 `MATHDESK_RECHECK_THRESHOLD_GRADE`(기본 `B`)로 노출했다. 설정값 요구를 만족하면서 새 테이블을 만들지 않는 가장 작은 방법이다.
  - 잠금은 출결 필드(`attendance_status`·`attendance_reason`)에만 적용한다. 설계가 "학생 출결 필드 변경 요청은 409"라고 한정했고, 과제 등급·점수는 출결 확정과 무관하게 계속 입력한다.
  - `RecordOut.recheck_result`(평면)를 설계 예시의 `recheck` 중첩 객체(`target`·`prev_grade`·`prev_date`·`result`)로 바꿨다. TASK-10에서 평면으로 낸 것이 설계와 어긋났고, 화면(TASK-12)이 판단 근거를 함께 표시해야 한다.
  - 확정·해제는 `audit_log`에 `attendance.confirm`·`attendance.unlock`으로 남긴다(FR-09 상세의 "확정·해제 시각과 수행자").
- 실행한 검증
  - `uv run pytest -q` — 출결 테스트 최초 `4 failed`(의도한 Red) → 구현 후 전체 `38 passed`.
  - 시드 DB e2e(`curl`): 직전 수업 등급 B/A → 재검사 판정 `{target: true, prev_grade: 'B', prev_date: '2026-09-16'}` / `{target: false}`, 확정 200 → 출결 변경 409 → 과제 등급 변경 200 → 해제 200 → 출결 변경 200.
- 결과: TASK-11 완료. AC-06(VER-05 일부)·AC-09·AC-10 통과.

### 2026-09-22 — TASK-12 일일 입력 2패널 화면 (TASK-09 완료)

- 수행 내용
  - TDD Red: `DailyPage.test.tsx`에 "메모 편집 중 표 저장 시 메모 유지"(AC-11 UI), 등원 현황 표시(AC-07 UI), 출결 토글 해제(AC-06 UI), 재검사 즉시 저장 호출 경로를 먼저 작성해 import 실패로 의도한 실패를 확인했다.
  - Green: `api.ts`에 일일 기록 클라이언트를 추가하고 `DailyPage.tsx`(좌측 명단 그리드 + 우측 진도·과제·영상·첨언 패널)를 구현한 뒤 `/daily` 라우트에 연결했다.
- 변경 파일: `apps/web/src/api.ts`, `apps/web/src/pages/DailyPage.tsx`, `apps/web/src/pages/DailyPage.test.tsx`, `apps/web/src/App.tsx`
- 발견 사항
  - 등원 현황을 `등원 현황 {a} / {b}명 ...` 한 문단에 쓰면 React가 텍스트 노드를 쪼개 `4 / 13명`으로 조회되지 않는다. KPI 값을 자체 요소로 분리해 해결했다(마크업상으로도 이쪽이 맞다).
- 결정과 이유
  - 표 편집과 메모 편집을 **별도 상태**(`drafts`, `notes`)로 두고, 초기화는 반·날짜가 바뀔 때만 한다. 서버 응답이 올 때마다 메모 상태를 다시 세우면 표 저장 직후 미저장 메모가 사라진다 — AC-11이 UI에서 깨지는 지점이 정확히 여기다.
  - 재검사 합/불은 `drafts`를 거치지 않고 즉시 뮤테이션을 호출한다(FR-14의 즉시 저장 단위).
  - 출결 확정 중에는 출결 버튼·사유만 비활성화하고 등급·점수 입력은 열어 둔다(TASK-11의 서버 규칙과 일치).
  - 미저장 입력이 있는 상태에서 반·날짜를 바꾸면 확인을 받는다(FR-14 상세).
- 실행한 검증
  - `npm test` — 최초 import 실패(의도한 Red) → 구현 후 `4 files, 9 tests passed`.
  - `npm run build` 성공, `uv run pytest -q` `38 passed`(백엔드 회귀 없음).
  - 실행 스택: `http://localhost:5173/daily` 200.
- 결과: TASK-12 완료, 이로써 TASK-09(M2 일일 수업 입력)도 완료. AC-07·AC-08의 화면 측면과 AC-11의 UI 측면이 통과했다. 실제 브라우저 육안 확인은 자동화 제외 항목으로 남는다.

### 2026-09-22 — TASK-40·41 그리고 TASK-42(부분): 테스트 운영 노출

- 수행 내용
  - TASK-40 TDD Red: `tests/test_login_lockout.py`에 잠금 중 올바른 비밀번호 거부, 잠금 만료 후 허용, 성공 시 카운트 초기화를 먼저 작성해 `2 failed`로 의도한 실패를 확인했다. Green: `app_user`에 `failed_login_count`·`locked_until`을 추가(리비전 `9c040c3bb194`)하고 잠금 로직과 `auth.lockout` 감사 기록을 구현했다.
  - TASK-41 TDD Red: `tests/test_serving.py`에 SPA fallback이 `/api/*`를 가로채지 않음, 클라이언트 라우트에 `index.html` 반환, `Secure` 쿠키 설정을 먼저 작성해 import 실패로 확인했다. Green: `main.py`를 `create_app(web_dist=…)` 형태로 바꾸고 정적 서빙과 `MATHDESK_COOKIE_SECURE`를 구현했다. `Dockerfile.testops`(웹 빌드 → API 이미지)와 `compose.testops.yaml`(별도 프로젝트, 호스트 포트 게시 없음)을 추가했다.
  - TASK-42: 전용 터널 `mathdesk`(`4724c8d8-…`) 생성, DNS 라우트, `cloudflared` compose 서비스 추가, 공개 도메인 검증. `ops/README.md`에 기동·재생성·롤백 절차를 남겼다.
- 변경 파일: `apps/api/src/mathdesk/{auth,main,seed}.py`, `apps/api/src/mathdesk/models/masterdata.py`, `apps/api/migrations/versions/9c040c3bb194_…`, `apps/api/tests/{conftest,test_login_lockout,test_serving,test_seed}.py`, `Dockerfile.testops`, `compose.testops.yaml`, `.env.example`, `.gitignore`, `ops/`
- 발견 사항
  - **시드가 초기 원장 계정과 충돌했다.** 테스트 운영 기동 시 환경변수로 `director`가 먼저 생성되는데 시드가 같은 `login_id`를 다시 만들어 `UniqueViolationError`가 났다. 재현 테스트를 먼저 추가한 뒤 기존 계정을 재사용하도록 고쳤다.
  - **`cloudflared tunnel route dns`가 엉뚱한 터널로 라우팅했다.** `~/.cloudflared/config.yml`의 `tunnel:` 값이 인자를 덮어써 `mathdesk.yongs-wiki.com`이 `homewiki` 터널에 연결됐다. 빈 설정을 `--config`로 지정하고 `--overwrite-dns`로 재라우팅해 바로잡았다. 이 함정을 `ops/README.md`에 남겼다.
  - `Secure` 쿠키 때문에 컨테이너 내부 HTTP 호출로는 인증 흐름을 검증할 수 없다(쿠키가 재전송되지 않음). 의도된 동작이며 검증은 HTTPS 경로에서 수행했다.
  - Docker Desktop `AutoStart`가 꺼져 있어 재부팅 후 자동 기동이 성립하지 않는다.
- 결정과 이유
  - cloudflared를 launchd 대신 **compose 서비스**로 운용했다. 컨테이너 네트워크로 `app:8000`에 직접 닿으므로 호스트 포트를 하나도 게시하지 않아 NFR-17을 문자 그대로 만족한다. 계획의 `변경 대상`도 이에 맞춰 수정했다.
  - 테스트 운영을 별도 compose 프로젝트로 분리했다. 개발 스택과 DB·볼륨·수명주기가 섞이지 않는다.
  - 마이그레이션은 컨테이너 기동 시 `alembic upgrade head`로 적용한다. 단일 노드 테스트 운영에서 별도 배포 단계를 두지 않는 가장 단순한 방법이다.
  - 잠금 임계·시간은 호출 시점에 환경변수를 읽는다. 모듈 로드 시 고정하면 설정 변경과 테스트가 반영되지 않는다.
- 실행한 검증
  - `uv run pytest -q` — 잠금 테스트 최초 `2 failed`, 서빙 테스트 최초 import 실패, 시드 회귀 테스트 최초 `1 failed`(모두 의도한 Red) → 구현 후 전체 `46 passed`.
  - 테스트 운영 스택: `docker compose -f compose.testops.yaml ps`에서 3개 서비스 `running`, 호스트 게시 포트 0개(`Publishers`의 PublishedPort 모두 0) → VER-27 충족.
  - 공개 도메인(VER-25/AC-28): `/` 200, `/api/health` `{"status":"ok"}`, 비로그인 `/api/auth/me` 401, 로그인 200 + `Set-Cookie … HttpOnly … SameSite=lax; Secure`, 인증 후 학생 47명, 로그아웃 204 → `/me` 401, SPA 딥링크 `/daily` 200.
  - 기존 서비스 영향 없음: `https://yongs-wiki.com/` 200.
  - VER-26(AC-29)는 잠금 테스트 3건으로 충족.
- 결과: TASK-40·TASK-41 완료. TASK-42는 노출과 검증이 끝났으나 **재부팅 자동 기동 조건이 미충족**이라 `in-progress`로 남긴다.

### 2026-09-22 — TASK-42 자동 기동과 환경 분리

- 수행 내용
  - 사용자 지시로 Docker Desktop `AutoStart`를 켰다(설정 파일 직접 수정, 백업 `/tmp/docker-settings-backup.json`).
  - `restart: unless-stopped`만으로는 복구되지 않는 것을 실측하고 launchd 에이전트(`ops/com.mathdesk.testops.plist` + `ops/start-testops.sh`)를 추가했다. 엔진이 준비될 때까지 최대 5분 대기 후 `compose up -d`를 실행한다.
  - 사용자 지시로 초기 원장 비밀번호를 `director`로 교체했다(DB 해시 직접 교체, `.env` 동기화).
- 변경 파일: `ops/{start-testops.sh,com.mathdesk.testops.plist,README.md}`, `compose.yaml`, `docs/plan.md`
- 발견 사항
  - **`restart: unless-stopped`가 이 환경에서 동작하지 않는다.** Docker Desktop을 재시작하면 정책이 있어도 컨테이너가 복구되지 않았다(`docker desktop restart` 후 `docker ps` 비어 있음). launchd 보완이 필수다.
  - **저장소 루트 `.env`가 개발 스택까지 오염시켰다.** 테스트 운영용으로 만든 `POSTGRES_PASSWORD`를 개발 `compose.yaml`이 `${POSTGRES_PASSWORD:-mathdesk}`로 읽어, 기존 볼륨의 비밀번호와 어긋나 개발 API가 `InvalidPasswordError`로 기동 실패했다. 개발 compose의 DB 비밀번호를 고정값으로 바꿔 결합을 끊었다.
  - Docker Desktop 재시작 과정에서 다른 프로젝트 컨테이너(`herongs-backend`)도 함께 내려갔다. 확인 후 복구했다.
- 결정과 이유
  - 자동 기동을 launchd로 처리했다. compose 재시작 정책이 실제로 동작하지 않는 것을 확인했고, 기존 home-wiki 운영도 같은 방식이라 일관된다.
  - 개발 compose는 비밀번호를 변수로 받지 않는다. 로컬 전용 스택이 노출 환경의 비밀 설정에 결합될 이유가 없다.
  - 자격 증명 `director`/`director`는 사용자 지시에 따른 **의도된 선택**이다. 배포 이관 단계에서 교체하기로 합의했고 현재는 합성 데이터만 보관한다.
- 실행한 검증
  - launchd 에이전트: 스택을 `stop`한 뒤 `launchctl kickstart`로 3개 서비스가 모두 `running`으로 복구되고 공개 도메인 `/api/health` 200.
  - 개발 스택 복구: `docker compose ps` 3개 `running`, `http://localhost:8080/api/health` 200.
  - 비밀번호 교체: 공개 도메인에서 새 비밀번호 200, 이전 비밀번호 401, 인증 후 학생 47명.
  - 다른 서비스 무영향: `https://yongs-wiki.com/` 200, `herongs-backend` 복구 확인.
- 결과: TASK-42 완료. 실제 재부팅 검증은 수행하지 않았다(사용자 장비 재부팅을 임의로 하지 않음). 에이전트 동작은 kickstart로 대체 검증했다.

### 2026-09-22 — TASK-14 대시보드 KPI 집계 API

- 수행 내용
  - TDD Red: `tests/test_dashboard.py`에 캠퍼스 집계, 등원 현황(AC-07), 금주 완수율과 전주 대비(AC-13), 재검사 대상 인원, 주간 테스트 N·MAX·MIN, 표본 없음 처리, 지난 수업 요약을 먼저 작성해 `7 failed`로 의도한 실패를 확인했다.
  - Green: `stats.py`에 `GET /api/dashboard`를 구현하고 `main.py`에 배선했다.
- 변경 파일: `apps/api/src/mathdesk/{stats,main}.py`, `apps/api/tests/test_dashboard.py`
- 발견 사항
  - 개발 스택 DB에 `9c040c3bb194`(로그인 잠금 컬럼) 리비전이 적용되지 않아 개발 API가 기동 실패했다. 테스트 운영 이미지는 기동 시 `alembic upgrade head`를 돌리지만 개발용 이미지는 돌리지 않는다. 수동 적용으로 해소했고 README에 절차가 이미 있다.
- 결정과 이유
  - 주간 범위는 월요일 시작으로 계산한다(`date - weekday()` ~ +6일).
  - 완수 기준 등급은 `MATHDESK_HOMEWORK_PASS_GRADE`(기본 `B`)로 노출했다. [Q-07](../../requirements.md#가정과-미해결-질문)이 설정값을 전제한다.
  - **미제출은 등급 `F`로 해석했다.** 요구사항은 "미제출 건수"만 말하고 데이터 모델에 별도 필드가 없다. 6단계 등급의 최하위인 `F`를 미제출로 보는 것이 가장 자연스럽다. 2026-09-22 사용자 승인으로 확정되어 [FR-15 상세](../../requirements.md#fr-15-상세)에 명확화로 반영했다.
  - 재검사 대상 인원은 금주 각 세션에 대해 조회 시 계산을 반복하고 학생 단위로 중복을 제거한다. 저장하지 않는 원칙([TASK-11](../../plan.md#task-11-출결-확정재검사-판정))을 유지했다.
  - 표본이 없으면 0이 아니라 `null`을 반환한다(FR-15 상세의 `—` 표기).
  - 지난 수업 요약(FR-17)을 같은 응답에 담았다. 화면 하나가 쓰는 데이터를 한 번에 주는 편이 왕복을 줄인다.
- 실행한 검증
  - `uv run pytest -q` — 대시보드 테스트 최초 `7 failed`(의도한 Red) → 구현 후 전체 `53 passed`.
  - 시드 DB e2e: 재원생 47·활성 4반, 등원 1/8, 완수율 100%·재검사 대상 1명, 테스트 평균 71.7(N=3, MAX 78, MIN 65), 지난 수업 2026-09-16.
- 결과: TASK-14 완료. AC-07(VER-06)·AC-13(VER-10) 통과.

### 2026-09-22 — TASK-15 대시보드 화면 (TASK-13 완료)

- 수행 내용
  - TDD Red: `DashboardPage.test.tsx`에 KPI 카드 4개 렌더, 지난 수업 진도·과제 표시, 출결 확정 후 버튼 잠금과 편집 해제를 먼저 작성해 import 실패로 확인했다.
  - Green: `api.ts`에 `fetchDashboard`를 추가하고 `DashboardPage.tsx`를 구현해 `/` 라우트에 연결했다.
  - 출결 4버튼 토글을 `components/AttendanceButtons.tsx`로 추출해 일일 입력 화면과 공유했다.
- 변경 파일: `apps/web/src/api.ts`, `apps/web/src/components/AttendanceButtons.tsx`, `apps/web/src/pages/{DashboardPage.tsx,DashboardPage.test.tsx,DailyPage.tsx}`, `apps/web/src/App.tsx`
- 결정과 이유
  - 출결 버튼을 공용 컴포넌트로 추출했다. 대시보드 위젯과 일일 입력이 같은 토글 규칙(같은 값을 다시 누르면 해제)을 쓰므로 두 벌로 두면 어긋난다. 기존 일일 입력 테스트가 회귀를 잡아 준다.
  - 대시보드 출결 위젯은 KPI와 명단을 각각 `/api/dashboard`와 `/api/daily`에서 가져온다. 저장 후 두 쿼리를 함께 무효화해 카드와 표가 동시에 갱신된다.
  - 확정 상태에서는 위젯의 저장 버튼도 비활성화한다. 출결만 다루는 위젯이라 잠금 중에는 저장할 것이 없다.
- 실행한 검증
  - `npm test` — 최초 import 실패(의도한 Red) → 구현 후 `5 files, 12 tests passed`.
  - `npm run build` 성공.
  - 테스트 운영 재배포 후 `https://mathdesk.yongs-wiki.com/` 200, 대시보드 API가 재원생 47·활성 4반·등원 0/8 반환.
- 결과: TASK-15 완료, 이로써 TASK-13(M3 대시보드)도 완료. 화면 ①의 구성 요소가 모두 표시된다.

### 2026-09-22 — TASK-17 메시지 렌더러와 등급 문구

- 수행 내용
  - TDD Red: `tests/test_message_render.py`(7구획 포함, 데이터 없는 구획 생략, 한국어 라벨, 교시 표기, 점수·반평균, 문구 없는 등급, 미확인 출결 생략)와 `tests/test_messages_api.py`(세션·기록 병합, 등급 문구 수정 반영, 강사 권한)를 먼저 작성해 import 실패로 확인했다.
  - Green: `messaging.py`에 순수 함수 `render_daily_message`와 `GET /api/messages/preview`, `GET/PUT /api/messages/grade-comments`를 구현하고 `main.py`에 배선했다.
- 변경 파일: `apps/api/src/mathdesk/{messaging,main}.py`, `apps/api/tests/{test_message_render,test_messages_api}.py`
- 결정과 이유
  - 본문 구성은 렌더러 안에 고정하고 **등급 문구만 설정값**(`grade_comment` 테이블)으로 뒀다. 참조 화면의 구획 구성이 고정이고, AC가 요구하는 가변 요소는 등급 문구다. `message_template` 테이블은 아직 쓰지 않는다 — 템플릿 편집 요구가 생길 때 연결한다.
  - 렌더러를 순수 함수로 분리해 DB 없이 단위 테스트한다. 본문 규칙 회귀를 가장 싸게 잡는 지점이다.
  - 출결이 `unchecked`면 출결 구획을 생략한다. "미확인"을 학부모에게 보낼 이유가 없다.
  - 반평균은 같은 세션의 저장된 점수로 계산한다([TASK-10](../../plan.md#task-10-일일-기록-api-3-저장-단위)의 요약과 같은 규칙).
  - 인사말의 학원명은 캠퍼스명, 강사명은 반 담당 강사의 표시 이름을 쓴다. 담당이 없으면 "담당"으로 대체한다.
- 실행한 검증
  - `uv run pytest -q` — 메시지 테스트 최초 import 실패(의도한 Red) → 구현 후 전체 `64 passed`.
  - 시드 DB e2e: 등급 문구 저장 후 미리보기가 제목·인사말·수업일(`9월 18일(금)`)·출결·교시별 진도·등급과 문구·테스트(학생점수 78점, 반평균 71.7점)·오늘의 과제를 참조 화면과 같은 형식으로 반환했다.
- 결과: TASK-17 완료. AC-14·AC-15(VER-11) 통과.

### 2026-09-22 — TASK-18 리포트 이미지와 복사 (CDN 캐시 노출 사고 포함)

- 수행 내용
  - TDD Red: PNG 반환·내용 변경 시 이미지 변화·스코프 거부를 먼저 작성해 `3 failed`로 확인했다. Green: `report.py`에 Pillow 기반 카드 렌더러와 이미지 엔드포인트를 구현했다.
  - 웹 클립보드 유틸(`clipboard.ts`: 텍스트 복사·이미지 복사·이미지 저장)을 TDD로 추가했다.
  - 컨테이너 이미지에 한글 글꼴(`fonts-nanum`)을 넣었다.
- 변경 파일: `apps/api/src/mathdesk/{report,messaging,main}.py`, `apps/api/tests/test_report_image.py`, `apps/web/src/clipboard.{ts,test.ts}`, `apps/api/Dockerfile`, `Dockerfile.testops`
- 발견 사항
  - **CDN이 인증된 리포트 이미지를 캐시해 무인증 열람이 가능했다.** 엔드포인트 경로가 `/api/messages/report.png`로 끝나 Cloudflare의 확장자 기반 캐시 규칙에 걸렸고, 응답에 `cf-cache-status: HIT`·`cache-control: max-age=14400`이 붙어 **쿠키 없이 200으로 학생 리포트가 내려왔다.** 경로에서 확장자를 없애고(`/api/messages/report-image`) 모든 `/api` 응답에 `Cache-Control: no-store, private`를 붙여 막았다. 확인: 새 경로는 `cf-cache-status: DYNAMIC`, 무인증 요청 401.
  - **컨테이너에서 굵은 글꼴이 한글을 렌더하지 못했다.** 같은 TTF의 face index로 굵게 잡은 것이 원인이며, 제목·소제목이 네모로 깨졌다. 굵은 글꼴 파일을 따로 고르도록 고쳤다. 글리프 커버리지 검사 테스트를 추가했다(로컬 macOS에서는 통과하던 환경 의존 결함이라, 컨테이너에서 직접 확인했다).
  - `npm test`만 돌리고 `npm run build`를 확인하지 않아 타입 오류가 있는 테스트가 Docker 빌드를 깨뜨렸다. 이후 두 명령을 함께 돌린다.
  - `docker compose up -d --build`는 빌드 실패 시에도 기존 이미지로 컨테이너를 올리고 0을 반환했다. 빌드 출력을 확인하지 않으면 옛 코드가 도는 것을 놓친다.
- 결정과 이유
  - **Q-10 해소:** 리포트 이미지는 설계대로 서버에서 생성하되 헤드리스 브라우저 대신 Pillow로 직접 그린다. 설계상 위치(서버)를 바꾸지 않으므로 DCR 없이 진행했고, RISK-10(브라우저 의존으로 인한 이미지 비대)도 함께 해소됐다. 이미지에 추가된 것은 한글 글꼴 패키지뿐이다.
  - 이미지 클립보드 복사는 브라우저 API로만 가능하므로 웹에 유틸을 두고, 서버는 PNG만 제공한다.
  - API 경로에 정적 파일 확장자를 쓰지 않는다. 이번 사고의 근본 원인이다.
- 실행한 검증
  - `uv run pytest -q` — 최초 `3 failed`(의도한 Red) → 캐시·인증 회귀 테스트 추가 후 전체 `71 passed`.
  - `npm test` `15 passed`, `npm run build` 성공.
  - 공개 도메인: 새 경로 200(`cache-control: no-store, private`, `cf-cache-status: DYNAMIC`), 무인증 401, 렌더된 카드에서 한글 제목·소제목 정상.
  - 오리진에서 구 경로는 404다. 남아 있는 200 응답은 Cloudflare 엣지의 잔여 캐시다.
- 결과: TASK-18 완료. AC-16(VER-12) 통과. 잔여 위험: 구 경로의 엣지 캐시 — 사용자 퍼지 또는 TTL 만료(최대 4시간) 필요.

### 2026-09-22 — TASK-19 MessagingAdapter와 발송 로그

- 수행 내용
  - TDD Red: 테스트 모드 무통신 발송, 로그 스냅샷 불변(AC-18), 장문 LMS 전환, 학생·학부모 동시 수신, 연락처 없음 422, 잔여량 조회를 먼저 작성해 `6 failed`로 확인했다.
  - Green: `messaging_adapter.py`(`MessagingAdapter` 계약, `TestModeMessaging`, `AligoMessaging`, 채널 선택)와 `POST /api/messages/send`·`GET /api/messages/logs`·`GET /api/messages/balance`를 구현했다.
- 변경 파일: `apps/api/src/mathdesk/{messaging_adapter,messaging}.py`, `apps/api/tests/test_message_send.py`
- 결정과 이유
  - **테스트 모드가 기본값**이고 실발송은 `MATHDESK_MESSAGING_MODE=live`와 알리고 자격 증명 3개가 모두 있을 때만 선택된다. 설정이 빠진 채 실발송으로 넘어가 과금되는 사고를 막는다.
  - 외부 미통신을 **HTTP 호출 자체를 막고 검증**한다. `httpx.AsyncClient.post/get`을 예외로 바꿔 두고 테스트 모드 발송이 성공하는지 본다. 어댑터 구현을 믿는 대신 경계를 직접 확인하는 방식이다(AC-17).
  - 채널은 본문을 EUC-KR로 인코딩한 바이트 길이 90을 기준으로 SMS/LMS를 고른다(알리고 기준). 첨부가 있으면 MMS다.
  - 본문 스냅샷은 발송 시점 렌더 결과를 그대로 저장한다. 이후 수업 기록이 바뀌어도 로그는 변하지 않는다(AC-18).
  - 알림톡→SMS 폴백은 [TASK-37](../../plan.md#task-37-m8-카카오-알림톡)의 몫이라 여기서는 문자 채널만 다뤘다.
- 실행한 검증
  - `uv run pytest -q` — 발송 테스트 최초 `6 failed`(의도한 Red) → 구현 후 전체 `77 passed`.
  - 공개 도메인 e2e: 테스트 모드 발송이 `channel=lms`, `status=test`로 응답하고 로그에 수신자·채널·상태·스냅샷이 남았다. 잔여량은 `mode=test`로 반환된다.
  - 실발송 경로는 [Q-02](../../requirements.md#가정과-미해결-질문)(알리고 계정·발신번호) 미해소로 **미검증**이다.
- 결과: TASK-19 완료. AC-17·AC-18(VER-13) 통과. 실발송 미검증은 그대로 남는다.

### 2026-09-22 — TASK-20 메시지 화면 (TASK-16 완료, MVP 구현 완료)

- 수행 내용
  - TDD Red: 병합 본문 표시, 수신 대상 미선택 시 발송 비활성, 선택한 대상으로 발송, 리포트 탭 이미지, 문자 복사를 먼저 작성해 import 실패로 확인했다.
  - Green: `api.ts`에 미리보기·발송·로그·리포트 URL을 추가하고 `MessagesPage.tsx`(문자/리포트 탭, 수신 대상 체크박스, 복사·저장·발송, 발송 내역)를 구현해 `/messages` 라우트에 연결했다.
- 변경 파일: `apps/web/src/api.ts`, `apps/web/src/pages/{MessagesPage.tsx,MessagesPage.test.tsx}`, `apps/web/src/App.tsx`
- 발견 사항
  - 학생 선택 `<select>`의 라벨과 수신 대상 체크박스 라벨이 모두 "학생"이라 접근성 조회가 모호해졌다. 선택 라벨을 "학생 선택"으로 바꿔 해소했다 — 화면에서도 이쪽이 명확하다.
  - 미리보기가 도착하기 전에는 복사 버튼이 비활성이라, 테스트가 본문 도착을 기다리도록 고쳤다(제품 결함이 아니라 테스트 타이밍 문제).
- 결정과 이유
  - 탭은 `role="tablist"`/`role="tab"`으로 노출했다. 접근성 조회가 버튼과 구분된다.
  - 발송 버튼은 수신 대상이 하나도 없으면 비활성이다. 빈 발송 요청을 서버에서 422로 막고 있지만 화면에서 먼저 거른다.
  - 리포트 이미지는 `<img src>`로 직접 참조한다. 쿠키가 함께 나가므로 별도 처리 없이 인증된 이미지가 표시된다.
- 실행한 검증
  - `npm test` — 최초 import 실패(의도한 Red) → 구현 후 `7 files, 20 tests passed`.
  - `npm run build` 성공, `uv run pytest -q` `77 passed`(회귀 없음).
  - 테스트 운영 재배포 후 `https://mathdesk.yongs-wiki.com/messages` 200.
- 결과: TASK-20 완료, 이로써 TASK-16(M4 메시지)과 **MVP(M0~M4) 구현 전체**가 끝났다. 남은 것은 통합 검증과 완료 승인이다.

### 2026-09-22 — TASK-21 MVP 통합·인수 검증

- 수행 내용
  - 백엔드·프론트 전체 테스트를 실행하고 인수 조건 AC-01~AC-18을 근거 테스트에 매핑해 판정했다.
  - NFR-01·NFR-02를 측정하기 위해 `scripts/measure_perf.py`를 만들어 반 10 · 학생 200 · 수업 520 · 학생 기록 10,400건 규모의 데이터셋을 별도 DB(`mathdesk_perf`)에 만들고 응답 시간을 30회씩 측정했다.
- 변경 파일: `apps/api/scripts/measure_perf.py`
- 실행한 검증
  - `uv run pytest -q` → **77 passed**
  - `npm test` → **20 passed** (7 files)
  - `npm run build` → 성공
  - `uv run python scripts/measure_perf.py` → 아래 성능 결과

| 검증 | 대상 | 방법과 근거 | 결과 |
|---|---|---|---|
| VER-01 | AC-01 | `test_auth.py::test_login_then_me_then_logout_blocks_protected_access` | 성공 |
| VER-02 | AC-02 | `test_scope.py::test_teacher_cannot_manage_users`, `test_masterdata.py::test_teacher_cannot_read_a_class_they_do_not_teach`, `test_daily.py::test_teacher_cannot_touch_daily_records_of_another_class`, 엔드포인트 순회 회귀 | 성공 |
| VER-02 | AC-03 | `test_scope.py::test_campus_list_only_returns_accessible_campuses`, `::test_request_for_another_campus_is_forbidden` | 성공 |
| VER-03 | AC-04 | `test_masterdata.py::test_omr_number_range_per_digit`(7케이스), `::test_student_with_out_of_range_omr_number_is_rejected` | 성공 |
| VER-04 | AC-05 | 웹 `Roster.test.tsx`(학생 47·반 4 렌더) + 시드 DB e2e(학생 47·반 4) | 성공 (브라우저 육안 확인은 미수행) |
| VER-05 | AC-06 | `test_attendance.py::test_attendance_toggles_back_to_unchecked`, `::test_confirmed_attendance_is_locked_until_unlocked`, 웹 `DailyPage.test.tsx` 토글 | 성공 |
| VER-06 | AC-07 | `test_dashboard.py::test_attendance_shows_attending_over_enrolled`, 웹 `DashboardPage.test.tsx` KPI | 성공 |
| VER-07 | AC-08 | `test_daily.py::test_saving_records_keeps_unsaved_notes_and_the_reverse`(진도·과제 재조회) | 성공 |
| VER-05 | AC-09 | `test_attendance.py::test_recheck_target_comes_from_the_previous_session_grade` | 성공 |
| VER-05 | AC-10 | `test_attendance.py::test_recheck_result_is_saved_immediately` | 성공 |
| VER-08 | AC-11 | `test_daily.py::test_saving_records_keeps_unsaved_notes_and_the_reverse` + 웹 `DailyPage.test.tsx::keeps unsaved notes` | 성공 |
| VER-09 | AC-12 | `test_daily.py::test_class_test_average_is_computed_from_saved_scores`(78·72·65 → 71.7) | 성공 |
| VER-10 | AC-13 | `test_dashboard.py::test_weekly_homework_rate_and_delta_against_last_week` | 성공 |
| VER-11 | AC-14 | `test_message_render.py` 7건(구획 포함·생략·라벨·교시·점수·문구 없음·미확인) | 성공 |
| VER-11 | AC-15 | `test_messages_api.py::test_editing_a_grade_comment_changes_the_preview` | 성공 |
| VER-12 | AC-16 | `test_report_image.py` 6건(PNG 생성·내용 반영·캐시 금지·무인증 401·스코프·글리프) | 성공 |
| VER-13 | AC-17 | `test_message_send.py::test_test_mode_sends_without_calling_the_provider`(HTTP 호출 차단 상태에서 성공) | 성공 |
| VER-13 | AC-18 | `test_message_send.py::test_send_writes_a_log_with_an_immutable_body_snapshot` | 성공 |
| VER-21 | NFR-01 | 반 10·학생 200·수업 520·기록 10,400 규모에서 대시보드 30회: p50 8ms · **p95 21ms** · 최대 24ms (기준 1500ms) | 성공 |
| VER-21 | NFR-02 | 같은 규모에서 표 일괄 저장 30회: p50 6ms · **p95 8ms** · 최대 8ms (기준 500ms) | 성공 |
| VER-23 | NFR-09 | `test_migrations.py::test_migration_roundtrip_creates_and_drops_every_table` | 성공 |
| VER-25 | AC-28 | 공개 도메인 로그인 쿠키 `Secure`·`HttpOnly`, 로그아웃 후 401 | 성공 |
| VER-26 | AC-29 | `test_login_lockout.py` 3건 | 성공 |
| VER-27 | NFR-17 | 테스트 운영 스택 호스트 게시 포트 0개, 기본 비밀번호 미사용 | 성공(단, 현재 자격 증명은 사용자 지시로 `director`/`director`) |

- 미수행·미검증으로 남는 항목
  - AC-05의 **실제 브라우저 육안 확인**: 계획의 자동화 제외 항목. 사용자 확인 필요.
  - **알리고 실발송**: [Q-02](../../requirements.md#가정과-미해결-질문) 미해소로 테스트 모드까지만 검증했다.
  - AC-19~AC-27: 사이클 2(M5~M9) 범위라 이번 검증 대상이 아니다.
  - 구 경로 `/api/messages/report.png`의 Cloudflare 엣지 캐시 잔존(퍼지 대기).
- 결과: TASK-21 완료. **MVP 인수 조건 AC-01~AC-18 전항 성공**, NFR-01·NFR-02 기준 대비 큰 여유로 통과. 남은 제한은 위에 명시했다.

### 2026-09-22 — TASK-22 MVP 사이클 완료 승인

- 수행 내용: [TASK-21 검증 결과](#2026-09-22--task-21-mvp-통합인수-검증)와 미수행 항목을 사용자에게 제시하고 응답을 받았다.
- 승인 기록
  - 결과: **승인** (2026-09-22, 결정자 `사용자`, 응답 "승인")
  - 승인 범위: 사이클 1(MVP, M0~M4) 완료 확정과 사이클 2(M5~M9) 착수
  - 제시한 미수행 항목: AC-05 브라우저 육안 확인, 알리고 실발송(Q-02), AC-19~AC-27(사이클 2 범위), 구 경로 엣지 캐시 퍼지
- 결과: TASK-22 완료. 사이클 1 23건이 모두 `completed`가 되었고 완료 시점 트리 스냅숏을 위 [계획 트리](#계획-트리)에 동결했다. 사이클 2는 TASK-23부터 시작한다.

### 2026-09-22 — 기준선 `v3` 발행 (DCR-002 / ADR-009)

- 계기: 사용자 요청 — "M6는 차후 가변으로 사용할 수 있게 해주고, 지금 사용 중인 Claude를 연결하는 것을 검토해 달라".
- 감지한 차이: [ADR-003](./ADR-003-AI-작업-분리와-개인정보-경계.md) 결정 2가 `LlmAdapter`를 OpenAI 호환 `chat/completions`로 고정하고 있어, Anthropic Messages API(엔드포인트·인증 헤더·시스템 프롬프트 위치·응답 구조가 모두 다름)를 붙일 수 없었다. 중대한 변경으로 판단해 wf-design DCR 절차로 반환했다.
- 확인한 사실: 이 장비에 `ant` CLI 미설치, `ANTHROPIC_API_KEY` 미설정, `~/.config/anthropic` 프로필 없음. **Claude Code 구독 인증은 애플리케이션 서버가 재사용할 수 있는 API 자격증명이 아니다.**
- 사용자 결정 2건: 진행 승인(DCR-002/ADR-009 작성), 기본 모델 `claude-opus-5`.
- 결정: `LlmAdapter`를 공급자 중립 계약으로 정의하고 구현체 3종(`test`·`anthropic`·`openai_compat`)을 설정으로 선택. 화이트리스트는 `QuestionAnalyzer`에 유지해 NFR-04·AC-27 경계와 검증 위치 불변. 상세는 [ADR-009](./ADR-009-LLM-공급자-추상화와-Claude-연결.md).
- 기각한 대안: OpenAI 호환 shim(구조화 출력·캐싱·사용량 기록 상실), Anthropic 전용 교체(가변성 상실), 범용 추상화 라이브러리(과한 의존성).
- 기준선 변경: AC-23 문구(엔드포인트 → 공급자), NFR-15 기본 상한 확정(입력 200,000·출력 30,000 토큰), Q-05 해소, DES-14 공급자 중립화와 DES-14 상세 신설, `llm_call_log` 컬럼 3개 추가, 시험지 분석 흐름에 `refusal` 처리 추가. **신설 AC·NFR 없음.**
- 계획 변경: TASK-23(컬럼 구성), TASK-31(구현체 3종·계약 테스트) 갱신, [TASK-43 Claude 실호출 검증](../../plan.md#task-43-claude-실호출-검증) 신설.
- 사용자 지시: "API키는 가장 마지막에 검증하는것으로 하자" → 실호출 검증을 TASK-43으로 분리해 TASK-38 뒤, 최종 승인 관문(TASK-39) 앞에 배치했다. 기본 공급자가 `test`이므로 키 없이 TASK-31까지 완료할 수 있다.
- 재승인: 2026-09-22 사용자 응답 "API키는 가장 마지막에 검증하는것으로 하자. 승인." → 기준선 `v3` 발행, ADR-009 `approved`.
- 검증: 이 변경은 문서 변경만이며 코드 변경이 없다. 링크 검증만 수행했다.

### 2026-09-22 — TASK-23 스키마 2차 (시험·OMR·상담·파일) 완료

- TDD Red: `tests/test_migrations.py`의 `EXPECTED_TABLES`에 신규 9건을 추가하고, 기준선 `v3`가 요구하는 `llm_call_log` 컬럼 구성을 고정하는 `test_llm_call_log_records_provider_and_cache_tokens`를 먼저 작성했다. 두 테스트 모두 의도한 이유(테이블 부재)로 실패했다.
- Green: 모델 `exam.py`(Exam·ExamQuestion·ExamAttempt·ExamAnswer·OmrScan·LabelCorrection), `consult.py`(ConsultLog), `system.py`(StoredFile·LlmCallLog)를 추가하고 Alembic 리비전 `6f28fe0c3cac`를 autogenerate했다.
- `llm_call_log`는 `provider`(`test`·`anthropic`·`openai_compat`)와 `cache_read_tokens`·`cache_write_tokens`를 **최초 정의에 포함**했다. TASK-23이 착수 전이었기 때문에 [DCR-002](./DCR-002-M6-LLM-공급자-중립화와-Claude-연결.md)의 컬럼 추가에 별도 마이그레이션이 들지 않았다.
- 설계에 명시되지 않았으나 추가한 제약(되돌릴 수 있는 구현 세부사항): `exam_question(exam_id, no)`, `exam_attempt(exam_id, student_id)`, `exam_answer(attempt_id, question_no)` 유일 제약. 근거는 [시험지 분석·OMR 채점 흐름](../../design.md#omr-채점)의 "이미 반영된 스캔을 다시 적용하면 기존 시도를 대체한다".
- 검증: 왕복 마이그레이션 통과(`upgrade head` → `downgrade base` 후 잔여 테이블 0), API 전체 78건 통과(직전 77건 + 신규 1건).
- 통합: 개발 DB와 테스트 운영 DB 모두 `6f28fe0c3cac` 적용 완료. 테스트 운영 재빌드 후 `https://mathdesk.yongs-wiki.com/` HTTP 200 확인.
- 발견: API 컨테이너에는 `migrations/`·`alembic.ini`가 없어 개발 DB 마이그레이션은 호스트에서 `DATABASE_URL`을 지정해 실행해야 한다(테스트 운영 이미지는 기동 시 자동 적용).

### 2026-09-23 — 기준선 `v4` 발행 (DCR-003 / ADR-010 / ADR-011)

- 계기: 사용자 질문("UI 꾸미기는 언제 하나, 지금은 예쁘지 않다")과 이어진 목표 진술 — "이 뷰를 학생과 학부모에게 보여줌으로써 매출 확대를 도모한다".
- 감지한 차이: **기준선에 디자인·미관 요구사항이 아예 없었다.** UI 관련 항목은 NFR-13(조작 효율)·NFR-14(해상도)뿐이고 설계에 CSS·디자인 언급이 0건이었다. 실측 결과 웹은 CSS 파일 0개, `className`·`style` 0회로 완전 무스타일이었다. 의도적 제외가 아니라 요구사항 도출 단계의 누락이다.
- **우선순위를 뒤집은 근거:** 요구사항을 확인하니 [대상과 시나리오](../../requirements.md#대상과-시나리오)가 수신자를 "시스템에 로그인하지 않음"으로 규정하고 [범위 · 제외](../../requirements.md#제외)가 학부모 포털을 명시적으로 뺐다. 즉 **학부모는 웹 UI에 도달하지 않으며, 도달하는 시각물은 리포트 카드(FR-20)와 난이도 분석표 카드(FR-30)뿐이다.** 매출 목표 기준으로 심미 투자 1순위는 웹 UI가 아니라 카드다. 사용자도 도달 경로를 "카톡·문자 리포트 카드"로 한정 확인했다.
- 사용자 결정 4건: 범위 "지금 기반 + 화면별 다듬기까지", 방식 "가장 좋고 이쁜 솔루션 추천 위임", 도달 경로 "리포트 카드", 렌더러 "HTML/CSS 전환".
- 결정: [ADR-010](./ADR-010-웹-UI-디자인-시스템.md) 웹은 Tailwind v4 + shadcn/ui 패턴(Radix) + Recharts, 토큰은 순수 CSS 변수 단일 소스. [ADR-011](./ADR-011-리포트-카드-HTML-렌더링.md) 카드는 Pillow → HTML/CSS + 헤드리스 Chromium.
- 기각한 대안: 컴포넌트 라이브러리(MUI·Mantine) — NFR-13의 표 기반 키보드 입력이 라이브러리 API 밖 요구라 싸워야 한다. WeasyPrint — CSS grid 미지원으로 토큰 공유 이점이 무너진다. Pillow 유지 — 사용자가 지정한 판단 기준(미관 최우선)에 미달.
- **Q-10 재개:** 2026-09-22 해소 당시 판단 기준은 의존성 무게였고, 매출 목표가 제시되며 기준이 심미적 상한으로 바뀌었다. 설계 DES-08 원안("카드형 HTML로 구성해 이미지로 변환")으로 돌아가는 것이기도 하다.
- 재작성 위험 평가: 웹 테스트 20건의 쿼리가 전부 의미 기반(`getByRole` 15·`getByLabelText` 5·`getByText` 10, `getByTestId`·`querySelector`·`container` 각 0)이라 역할·레이블을 유지하면 마크업 전면 교체가 안전하다. 이 사실이 "변경 범위가 커도 된다"는 판단의 근거가 되었다.
- 기준선 변경: FR-40(브랜드)·NFR-18(토큰 일관성)·NFR-19(카드 3초)·AC-30~32 신설, NFR-13 보강, DES-08 전환·DES-08 상세 신설, DES-24 신설, Q-10 재해소. 스키마 변경 없음(브랜드는 기존 `integration_setting` 사용).
- 계획 변경: TASK-44~47 신설. **기존 화면 재작성(TASK-47)을 마지막에 두어** 학부모에게 닿는 자산을 먼저 완성한다. M5~M9 기능 작업은 그 뒤에 재개한다.
- 함께 보정: 요구사항 외부 연동 표가 v3(DCR-002) 반영에서 누락되어 "OpenAI 호환 LLM API"로 남아 있었다. 공급자 중립 표기로 고쳤다(의미 변경 없음).
- 재승인: 2026-09-23 사용자 응답 `승인` → 기준선 `v4` 발행, ADR-010·ADR-011 `approved`.
- 검증: 문서 변경만이며 코드 변경이 없다. 링크·앵커 전수 검증만 수행했다.

### 2026-09-23 — TASK-44 디자인 토큰과 공통 컴포넌트 기반 완료

- TDD Red: `apps/web/src/styles/tokens.test.ts`를 먼저 작성했다(VER-30 웹 측). 네 가지 계약을 고정한다 — (1) 토큰 파일에 프레임워크 전처리 지시어가 없다, (2) 색·타이포·간격·라운드·그림자 토큰이 정의된다, (3) 참조하는 변수를 모두 자기 파일 안에서 정의한다, (4) 웹 스타일시트가 같은 토큰 파일을 참조한다. `tokens.css` 부재로 의도한 이유로 실패했다.
- (3)이 이 테스트의 핵심이다. [ADR-011](./ADR-011-리포트-카드-HTML-렌더링.md)의 카드 렌더러가 이 파일을 `<style>`에 **그대로 인라인**하므로, 외부 파일을 참조하는 순간 카드에서만 조용히 깨진다. 테스트가 그 회귀를 웹 측에서 미리 막는다.
- Green: `tokens.css`에 순수 CSS 변수 38개를 단일 정의하고, `app.css`가 `@theme inline`으로 이를 Tailwind 이름에 연결한다. `inline`을 쓴 이유는 유틸리티가 `var(--md-*)`를 그대로 참조하게 해 다크 모드 덮어쓰기와 브랜드 색 런타임 교체(FR-40)가 살아 있게 하기 위해서다.
- 간격은 개별 유틸리티를 나열하지 않고 `--spacing: var(--md-space-1)` 하나만 연결했다. Tailwind v4가 이 값에서 전체 수치 스케일을 파생하므로 `p-3`·`gap-4`까지 토큰의 4px 리듬에서 나온다(빌드 산출물에서 `padding-inline:calc(var(--md-space-1) * 3)` 확인).
- 공통 컴포넌트: `button`(cva 4변형×3크기)·`input`·`card`·`table`·`dialog`(Radix)와 `lib/utils.ts`의 `cn`, 레이아웃 셸 `components/AppShell.tsx`. 로그인 화면과 앱 셸에 적용해 동작을 확인했다.
- **`table`은 데이터 API 없는 얇은 스타일 래퍼로 두었다.** 소비하는 화면이 아직 없는 상태에서 API를 설계하면 추측이 된다. 스타일만 입히면 역할·레이블이 보존되어 TASK-47에서 모양을 정해도 위험이 없다. NFR-13의 키보드 이동은 계획대로 TASK-47이 소유한다.
- `CardTitle`에 `as` prop을 두었다. 로그인 화면은 카드가 페이지 전체라 제목이 `h1`이어야 하는데 기본값 `h2`로는 `h1` 없는 문서가 된다. 접근성은 최소화 대상이 아니므로(스킬 §2.4) 한 줄로 해결했다.
- 미룬 의존성: Recharts와 lucide-react는 [ADR-010](./ADR-010-웹-UI-디자인-시스템.md) 결정 4·3을 유지하되 설치하지 않았다. ADR은 **무엇을 쓸지**를 정한 것이고 설치 시점은 정하지 않았다. 실제 사용처가 생기는 TASK-26(차트)·TASK-47(아이콘)에서 넣는다.
- 발견과 수정: 루트에 `.dockerignore`가 없어 `Dockerfile.testops`가 `apps/web/dist/`를 빌드 컨텍스트에 함께 담고 있었다. Tailwind가 그 이전 빌드 산출물까지 스캔해 컨테이너 CSS가 28,230바이트로 부풀었다(호스트 13,480바이트). 루트 `.dockerignore`를 추가하자 호스트와 컨테이너의 자산 해시가 완전히 일치했다(`index-Nn7GXW20.css` 13,480 / `index-CYTfd47o.js` 355,959). 같은 누락으로 호스트 `node_modules/`와 `.env`도 컨텍스트에 들어가고 있었고 함께 제외했다.
- 검증: 웹 테스트 24건 통과(기존 20건 + 토큰 4건, 기존 테스트 수정 0). `npm run build` 통과. 빌드 산출 CSS에서 `--md-*` 정의 38건과 유틸리티의 토큰 참조를 확인했다. 개발 컨테이너 재빌드 후 dev 서버가 Tailwind로 `app.css`를 컴파일함을 확인(`bg-brand`·`text-muted-fg`·`rounded-lg` 생성). 테스트 운영 이미지 빌드 통과 후 검증용 이미지는 제거했다.
- 번들 영향: JS 324.18 → 355.96 kB(gzip 100.72 → 110.58), CSS 신규 13.48 kB(gzip 3.64). [ADR-010 후속 작업](./ADR-010-웹-UI-디자인-시스템.md#후속-작업)의 번들 측정 항목을 이 수치로 채운다.
- 미수행: 브라우저 육안 확인. 헤드리스 브라우저가 설치되어 있지 않다(TASK-45에서 Chromium을 넣는다). 사용자가 `http://localhost:5173`에서 확인할 수 있다.

### 2026-09-23 — 작업 순서 변경 (TASK-47을 TASK-45·46보다 앞으로)

- 계기: 사용자가 테스트 운영 주소에서 TASK-44 결과를 직접 확인한 뒤 "47 먼저 하자. 45 46은 그다음"으로 지시했다.
- 분류: **DCR 아님.** wf-implement의 역할 경계상 작업 순서는 구현 계획의 소유이며, 기준선 항목(FR-40·NFR-18·NFR-19·AC-30~32·DES-08·DES-24)과 각 작업의 내용·완료 조건은 하나도 바뀌지 않는다. [DCR-003](./DCR-003-브랜드-자산으로서의-시각-설계.md)이 적어 둔 "카드 먼저" 우선순위를 뒤집는 것이므로 계획과 이 기록에 이유를 남긴다.
- 선행 조건: TASK-47의 의존성은 TASK-44뿐이고 이미 완료되어 있다. 순서를 바꿔도 의존 관계가 깨지지 않는다.
- 기술적 평가: 화면 5개를 재작성하면 토큰과 공통 컴포넌트의 부족분이 드러난다. 카드 렌더러(TASK-45)가 토큰 위에 올라타기 **전에** 그것을 발견하는 편이 수정 비용이 낮다. TASK-46이 이후 토큰 값을 바꿔도 화면은 토큰을 참조하므로 자동 반영된다.
- 감수하는 것: DCR-003이 매출 목표의 1순위로 지목한 학부모 도달 자산(리포트 카드)의 완성이 뒤로 밀린다. 사용자가 그 트레이드오프를 인지한 상태에서 선택했다.

### 2026-09-23 — TASK-47 기존 화면 5개 재작성 완료

- TDD Red: NFR-13의 키보드 이동은 **기존 코드에 전혀 없던 동작**이라 새로 만들어야 했다. `components/ui/keyboard-grid.test.tsx`로 다섯 가지를 먼저 고정하고 모듈 부재로 실패시켰다 — 같은 열 유지 행 이동, 마지막 행에서 이탈 금지, 입력란 Enter는 아래로, **버튼 Enter는 가로채지 않음**, 버튼에서도 방향키는 행 이동.
- 네 번째가 설계 판단이다. Enter를 무조건 가로채면 키보드만으로 출결·등급 버튼을 누를 수 없게 된다. 그래서 Enter는 `target`이 입력란일 때만 이동으로 해석한다.
- 열 기준을 **포커스 가능한 요소의 순번이 아니라 `td`의 위치**로 잡았다. 재검사 버튼이 대상 학생 행에만 렌더되므로 행마다 포커스 요소 개수가 달라 순번 방식은 어긋난다. `td` 개수는 표에서 일정하다.
- 좌우 방향키는 다루지 않는다. 입력란 안의 커서 이동이 우선이고 가로 이동은 Tab이 이미 한다. 키 배정은 기준선에 없는 내부 구현 세부사항이라 여기서 정하고 기록한다.
- 화면 단위 진행: 일일 입력(4건) → 대시보드(3건) → 학생·반(5건) → 알림문자. 각 단계마다 해당 테스트를 돌렸고 **기존 테스트는 한 줄도 고치지 않았다**. 의미 기반 쿼리가 마크업 전면 교체를 견딘다는 [ADR-010](./ADR-010-웹-UI-디자인-시스템.md)의 전제가 실측으로 확인됐다.
- 재작성이 제약받은 지점: `ClassesPage`의 반 목록은 `getByText('고2 윤B · 고2 · 금 18:00~22:00')`가 한 요소의 전체 텍스트를 보므로, 반 이름을 별도 요소로 분리해 강조할 수 없었다. 합친 한 줄을 유지하고 카드 안의 행으로만 정리했다. 테스트가 표현 형식을 고정하고 있는 사례이며, 형식을 바꾸려면 테스트가 먼저 바뀌어야 한다.
- 신설 공통 컴포넌트: `toggle`(눌림 상태를 색으로 구분 — 출석 success·지각 warning·결석 danger·조퇴 neutral), `select`, `field`, `stat`, `textarea`, `PageHeader`, 그리고 출결 버튼과 사유 입력을 한 칸에 묶는 `AttendanceCell`. 출결·과제등급·재검사가 모두 같은 `aria-pressed` 구조라 `Toggle` 하나로 흡수했다.
- 자체 리뷰에서 고친 것: 동일한 200자 className이 두 번 반복돼 `Textarea` 컴포넌트로 뽑았다. `accent-[var(--md-color-brand)]` 임의값을 `accent-brand` 토큰 유틸리티로 바꿨다(생성 CSS에서 `accent-color:var(--md-color-brand)` 확인). `ATTENDANCE` 상수는 모듈 밖 사용처가 없어 export를 뗐다. 대시보드의 설명 문단을 `CardDescription`으로 바꿔 TASK-44에서 만들고 쓰지 않던 컴포넌트를 실제 사용처에 연결했다.
- **미사용으로 남은 것:** `components/ui/dialog.tsx`와 `@radix-ui/react-dialog`. TASK-44의 승인된 범위로 만들었으나 TASK-47의 어느 화면도 대화상자를 쓰지 않았다. 지우지 않은 이유는 FR-40 브랜드 설정 화면(TASK-46)이 유력한 소비처이고 shadcn 패턴에서는 소스 보유가 정상이기 때문이다. **TASK-46이 쓰지 않으면 그 시점에 제거한다.**
- 검증: 웹 29건(기존 24 + 키보드 5), API 78건, `npm run build` 통과. 개발 컨테이너 재빌드 후 dev 서버 200. 번들 JS 355.96 → 362.75 kB, CSS 13.48 → 17.34 kB.
- 미수행: 화면 ①~④의 시각 확인. [계획](../../plan.md)이 자동화하지 않는 시나리오 검증으로 분류한 사용자 판단 항목이다.

### 2026-09-23 — 마스터 데이터 삭제 기능 검토 (사용자 요청 조사)

- 사용자 질문: "학생/반 관리에서 삭제 기능이 있는지 검토해줘".
- **기준선은 하드 삭제를 의도적으로 배제했다.** [FR-05](../../requirements.md#fr-05-상세)는 "퇴원 처리"와 "퇴원 학생은 기본 목록에서 제외되지만 과거 기록은 보존", [FR-07](../../requirements.md#기능-요구사항)은 "활성 여부"를 규정한다. 출결·성적·발송 이력이 학생과 반을 참조하므로 물리 삭제는 과거 기록을 깨뜨린다. 실제 `DELETE`가 허용된 곳은 [FR-08](../../requirements.md#기능-요구사항)의 수강 등록 해제 하나뿐이다.
- **그런데 기준선이 요구한 수정 경로조차 없다(실측 3건):**
  1. `PATCH /students/{id}`는 `status`(`enrolled`/`paused`/`withdrawn`)를 받도록 구현되어 있으나 **웹이 호출하지 않는다.** `apps/web/src/api.ts`의 PATCH·DELETE 호출 0건. 퇴원시킬 방법이 없다.
  2. `PATCH /classes/{id}`는 `name`·`grade`·`teacher_id`·`schedules`만 수정하고 **`is_active`를 다루지 않는다.** `ClassIn` 스키마에도 필드가 없다. FR-07의 활성 여부 수정이 API 레벨에서 미구현이다.
  3. `POST`/`DELETE /classes/{id}/enrollments/...`는 구현되어 있으나 **호출하는 화면이 없다.** 학생을 반에 넣고 빼는 UI가 없다.
- **원인:** [TASK-08](../../plan.md#task-08-마스터-데이터-화면)의 목표는 "학생·반 목록과 등록·**수정** 화면"이었는데 완료 조건이 AC-05(목록 반영)만 검사했다. **완료 조건이 목표보다 좁아서** 수정 기능 없이 통과했다. TASK-47은 이 화면들을 시각적으로만 재작성해 구멍을 그대로 두었다.
- 처리: 사용자 결정으로 [TASK-49~TASK-52](../../plan.md#task-49-마스터-데이터-수정-기능-보완)를 신설해 계획에 등록하고, 테마 작업을 먼저 한다. 하드 삭제 경로는 만들지 않는다.

### 2026-09-23 — 기준선 `v5` 발행 (DCR-004 / ADR-012)

- 계기: 사용자 요청 — "색감은 현재를 라이트모드로 두고 다크모드, 블루모드, 그린모드, 핑크모드를 추가해줘".
- **감지한 충돌:** [FR-40](../../requirements.md#기능-요구사항)이 이미 "시그니처 색을 리포트 카드와 **웹 화면**에 반영"을 규정한다. 학원 색이 빨강인데 강사가 블루모드를 고르면 웹 주색이 무엇인지 기준선이 답하지 못한다. 임의 해석이 불가능한 제품 결정이라 사용자에게 물었다.
- 사용자 결정: **테마는 개인 설정.** 원장·강사가 각자 다른 테마를 쓰고, 학원 시그니처 색은 학부모에게 가는 리포트 카드 전용.
- **재정의의 핵심:** [NFR-18](../../requirements.md#비기능-요구사항)의 일관성 근거를 색에서 **스케일**로 옮겼다. 테마가 생기면 색은 같을 수 없지만, 시각적 일관성은 실제로 타이포·간격 리듬에서 나온다. 웹(내부 도구)과 카드(학부모용 브랜드 자산)는 오히려 색이 달라야 하는 자산이다. [AC-31](../../requirements.md#인수-조건)도 같은 기준으로 개정했다.
- 결정([ADR-012](./ADR-012-테마-팔레트와-적용-방식.md)): `data-theme` 속성 전환(순수 CSS라 카드 인라인 제약 유지), **색 토큰만** 덮어쓰기(스케일은 전 테마 공통), `localStorage` 저장(개인 설정이라 스키마·API 변경 0), 카드는 테마를 따르지 않고 라이트 팔레트 + 시그니처 색, 상태색은 색조 테마에서 고정(출결 구분은 의미 전달이 목적).
- 기각한 대안: JS로 CSS 변수 런타임 주입 — 파일이 순수 CSS가 아니게 되어 카드 인라인이 깨지고 VER-30을 위반한다. `integration_setting` 저장 — 캠퍼스 단위라 개인 설정 결정과 어긋난다. 색+스케일 모두 덮어쓰기 — 테마마다 화면 밀도가 달라져 NFR-13의 표 기반 입력이 불리해진다.
- **보류한 구현 없음:** 이 변경에 해당하는 코드는 한 줄도 작성하지 않은 상태였다. 기존 `tokens.css`의 `.dark` 블록은 전환 수단이 없어 **사용처 0건**(실측)이라 `[data-theme='dark']`로 옮겨도 회귀 위험이 없다.
- 기준선 변경: FR-41·AC-33·AC-34 신설, FR-40 축소(카드 전용), NFR-18·AC-31 재정의, DES-24 상세 갱신, DES-08에 카드 팔레트 고정 명시. **스키마·API 변경 0건.**
- 계획 변경: TASK-48 신설, VER-32·VER-33·VER-34 신설, VER-30 의미 갱신.
- 재승인: 2026-09-23 사용자 응답 `승인` → 기준선 `v5` 발행, ADR-012 `approved`.
- 검증: 문서 변경만이며 코드 변경이 없다. 링크·앵커 전수 검증만 수행했다.

### 2026-09-23 — TASK-48 테마 팔레트와 선택 UI (구현 완료, 사용자 시안 확인 대기)

- TDD Red: `tokens.test.ts`에 팔레트 검사 3건을 추가했다 — (1) 라이트는 `:root`, 나머지는 `[data-theme='…']`로 전환, (2) 5개 팔레트가 **동일한 색 토큰 집합**을 정의(AC-34/VER-32), (3) 팔레트가 **타이포·간격·라운드·그림자 스케일을 재정의하지 않음**(AC-31/VER-30). 팔레트 부재로 의도한 이유로 실패했다.
- (3)이 [NFR-18](../../requirements.md#비기능-요구사항) 재정의의 집행 장치다. 스케일이 웹과 카드의 공유 기반이므로 팔레트가 스케일을 건드리는 순간 일관성 근거가 무너진다. 테스트가 그것을 막는다.
- Green: `[data-theme='dark'|'blue'|'green'|'pink']` 4벌 추가. 속성 선택자만 써서 순수 CSS 제약(카드 인라인)을 유지했다. 색조 테마는 주색뿐 아니라 배경·표면·테두리에도 같은 색조를 옅게 넣었고, 상태색은 의미 전달이 목적이라 재정의하지 않았다. 다크에서만 대비 확보를 위해 상태색 밝기를 올렸다.
- 테마 상태: `src/theme.ts`(`THEMES`·`readTheme`·`applyTheme`)와 `components/ThemeSelect.tsx`. 앱 셸 헤더에 배치했다. 저장값이 알 수 없는 문자열이면 라이트로 떨어진다(테스트로 고정).
- 첫 페인트 번쩍임: `index.html`에 인라인 스크립트를 두어 React보다 먼저 `data-theme`를 적용한다. 저장 키 문자열이 `theme.ts`와 중복되지만, React 로드 전에 실행되어야 하므로 불가피하다. 양쪽에 주석으로 연결해 두었다.
- **자체 리뷰에서 찾은 접근성 결함:** `Toggle`의 지각(warning)이 `text-fg`를 쓰는데, 다크 테마에서 `--md-color-fg`가 거의 흰색(L 0.96)이라 밝은 주황(L 0.8) 위의 흰 글씨가 된다. 명도차 0.16으로 읽히지 않는다. `--md-color-warning-fg`를 신설해 전 팔레트에서 어두운 잉크로 고정했다(다크 0.16 → 0.62).
- **AC-34 테스트가 그 수정을 검증했다.** `warning-fg`를 4개 팔레트에만 넣고 `:root`를 빠뜨렸을 때 테스트가 즉시 실패했다. 팔레트 누락 위험을 닫으려던 테스트가 실제로 누락을 잡은 사례다.
- 대비 점검: 5개 팔레트 × 6개 색 조합의 oklch 명도차를 계산해 전부 0.41 이상임을 확인했다. **수치 점검이지 WCAG 검증이 아니며, 최종 판단은 사용자 육안 확인이다.**
- 검증: 웹 36건(기존 29 + 팔레트 3 + 테마 4), API 78건, `npm run build` 통과. 개발 컨테이너 재빌드 후 200. 번들 CSS 17.34 → 19.19 kB, JS 362.75 → 363.31 kB.
- **완료(2026-09-23 20:20):** 사용자가 라이트·다크·블루·그린·핑크 5개 테마의 스크린샷으로 시안을 확인하고 완료 처리를 지시했다. 색값에 대한 수정 요청은 없었다.

### 2026-09-23 — 헤더 메뉴 줄바꿈 수정 (경량 경로)

- 계기: 사용자가 **휴대폰(약 390px)** 으로 테스트 운영 주소를 열었고, 헤더 메뉴가 한 글자씩 세로로 쪼개졌다. 스크린샷 5장으로 확인.
- 원인: nav 링크에 줄바꿈 방지가 없어 폭이 모자라면 한글이 글자 단위로 접힌다. `flex` 항목들이 축소되면서 로고·사용자 영역도 함께 눌렸다.
- 수정: nav 링크에 `whitespace-nowrap`, 헤더 행에 `overflow-x-auto`, 로고·nav·사용자 영역에 `shrink-0`. **폭이 모자라면 줄을 접지 않고 가로로 스크롤한다.** 좁은 데스크톱 창에서도 옳은 동작이라 모바일 전용 처리가 아니다.
- 분류: 경량 경로. 동작·공개 인터페이스·데이터 모델·보안에 영향이 없고 CSS 클래스 추가만이라 되돌리기 쉽다. 자명한 스타일 변경이라 테스트를 추가하지 않았고, 기존 36건으로 회귀만 확인했다.
- **기준선과의 관계(중요):** [NFR-14](../../requirements.md#비기능-요구사항)는 "최신 Chrome·Edge·Safari에서 1280px 이상 화면을 지원"으로 모바일을 명시적으로 범위 밖에 둔다. 이번 수정은 줄바꿈 방지일 뿐 모바일 지원을 추가한 것이 아니다. **사용자가 실제로는 휴대폰으로 사용한다는 사실이 확인되었으므로 NFR-14의 가정 자체를 재검토할지 물어야 한다.** 재검토한다면 DCR 대상이다.
- 남은 모바일 문제(이번 범위 밖, 미수정): 화면 제목이 2줄로 접힘, KPI 타일 4개가 좁은 폭에서 눌림, 사용자 표기 `원장(director)`가 잘림.

### 2026-09-23 — 기준선 `v6` 발행 (DCR-005, 모바일 지원 범위)

- 계기: 사용자가 휴대폰(약 390px)으로 쓰고 있다는 사실이 스크린샷으로 드러났다. [NFR-14](../../requirements.md#비기능-요구사항)는 "1280px 이상 데스크톱 전용, 모바일 반응형은 범위 밖"이었다.
- **검증되지 않은 전제였다:** 요구사항 도출 시 모바일 필요 여부를 사용자에게 확인한 기록이 없다. "업무용 도구 = 데스크톱"이라고 단정한 결과이며, [DCR-003](./DCR-003-브랜드-자산으로서의-시각-설계.md)에서 디자인 요구사항이 통째로 빠졌던 것과 같은 종류의 도출 단계 누락이다.
- 사용자 의견 요청에 대한 권고: **화면별 차등 지원.** 화면마다 폰 적합도가 근본적으로 다르다. 대시보드·알림문자는 숫자를 훑고 버튼을 누르는 화면이라 폰이 오히려 편하지만, 일일 입력은 13명 × 5열에 행마다 버튼 10개이고 [NFR-13](../../requirements.md#비기능-요구사항)이 키보드 이동을 요구한다 — 폰에는 키보드도 마우스도 없다.
- **NFR-13을 함께 고친 이유:** NFR-13에 적용 환경이 적혀 있지 않아, NFR-14를 390px로 내리는 순간 두 요구사항이 모순된다. "데스크톱에서"를 명시했다. 요구사항을 약화한 것이 아니라 원래 의도했던 적용 범위를 적은 것이다.
- 기각한 대안: 전 화면 균일 지원 — 일일 입력 표를 학생별 카드로 다시 짜야 하고, 이는 폰에서 NFR-13을 포기한다는 별개 결정과 입력 방식 두 벌 유지를 요구한다. 태블릿(768px)까지만 — 사용자가 실제 쓰는 폭을 덮지 못해 계기를 해결하지 못한다.
- **ADR을 만들지 않은 이유:** 지원 범위 조정이며 구현 수단은 [ADR-010](./ADR-010-웹-UI-디자인-시스템.md)이 정한 Tailwind 반응형 유틸리티를 그대로 쓴다. 새 기술 결정이나 되돌리기 어려운 결정이 없다.
- 기준선 변경: NFR-14 개정(최소 390px + 부류별 목표), NFR-14 상세 신설, NFR-13 적용 환경 명확화, AC-35 신설, DES-24 상세의 대상 환경 교체와 좁은 폭 레이아웃 방침 추가. **API·스키마 변경 0건.**
- 계획 변경: TASK-53 신설(**후순위** — 사용자가 리포트 카드 뒤로 지정), VER-35 신설.
- 재승인: 2026-09-23 사용자 응답 `승인` → 기준선 `v6` 발행.
- 순서에 대해 사용자에게 밝힌 우려: 리포트 카드(TASK-45·46)가 TASK-47 → TASK-48 → 모바일로 세 번 밀렸고, [DCR-003](./DCR-003-브랜드-자산으로서의-시각-설계.md)이 매출 1순위로 지목한 자산이다. 사용자가 **카드 먼저, 모바일은 문서화만 하고 후순위**로 결정했다.
- 검증: 문서 변경만이며 코드 변경이 없다. 링크·앵커 전수 검증만 수행했다.

### 2026-09-23 — TASK-45 리포트 카드 HTML 렌더러 전환 완료

- TDD Red: `tests/test_report_html.py`로 템플릿 계약 5건을 먼저 고정했다 — (1) **토큰 파일을 통째로 인라인**(VER-30 카드 측), (2) 카드가 테마를 적용하지 않음(ADR-012 결정 7), (3) 본문 내용 포함, (4) 브랜드 색이 `--md-color-brand`만 덮어씀, (5) 사용자 입력 이스케이프. `TOKENS_CSS` 부재로 의도한 이유로 실패했다.
- (1)이 핵심이다. 토큰 **값을 베껴 적으면** 웹과 카드가 조용히 갈라진다. 파일 내용이 HTML 안에 그대로 들어 있는지 검사해 그 경로를 막았다.
- 테스트 자체를 고친 건 1건: "카드가 테마를 따르지 않는다"를 `"data-theme" not in html`로 썼는데, 인라인된 tokens.css에 `[data-theme='dark']` 팔레트 선택자가 들어 있어 걸렸다. 의도는 "테마를 **적용**하지 않는다"이므로 `<style>` 블록을 뺀 마크업에서만 확인하도록 고쳤다. 구현이 아니라 테스트가 틀렸다.
- 구조 변경: Playwright는 비동기 API를 써야 하므로(동기 API는 asyncio 루프 안에서 못 돈다) `render_report_png`가 async가 되고 호출부가 `await`로 바뀌었다. 브라우저는 `ReportRenderer`로 감싸 lifespan에서 warm 유지한다 — 콜드 스타트 0.17s를 요청 경로에서 뺀다(NFR-19).
- **해상도를 올렸다(760 → 1520px).** 레이아웃은 CSS 760px 그대로 두고 2배로 촬영한다. 카톡으로 받은 카드를 폰에서 확대해 보는 일이 흔해 1배는 흐리다. 기존 테스트의 `image.width == 760`은 **Pillow 구현의 산출물 크기를 고정한 것**이지 계약이 아니었다 — [AC-16](../../requirements.md#인수-조건)은 "본문과 동일한 내용"만 규정하고 픽셀 크기를 말하지 않으며, 계획이 명시한 계약도 "PNG 반환·내용 변경 시 변화·스코프 거부"였다. 의도가 드러나게 `CARD_WIDTH * SCALE`로 고쳤다.
- **빌드 컨텍스트를 바꿨다.** 토큰 파일이 `apps/web`에 있는데 API 이미지 컨텍스트는 `./apps/api`라 닿지 않았다. `compose.yaml`의 api 빌드를 저장소 루트 컨텍스트 + `dockerfile: apps/api/Dockerfile`로 바꿔 파일을 복사한다. 토큰을 복제하지 않고 단일 소스([DES-24])를 지키기 위한 선택이다.
- **이미지 크기 문제와 해결:** `playwright install --with-deps chromium`이 전체 Chromium과 ffmpeg까지 깔아 Chromium 레이어만 1.03GB, 이미지 2.11GB가 되었다(계획 예상 +300~400MB를 크게 초과). 스크린샷에는 headless shell만 필요하므로 `--only-shell`로 바꿔 레이어 622MB, 이미지 **1.51GB**로 줄였다.
- **자체 리뷰에서 찾은 보안 결함:** 브랜드 색이 CSS 선언 안으로 들어가는데 `escape()`는 HTML용이라 CSS 주입(`red; } body { display:none`)을 막지 못한다. FR-40 설정값은 원장이 넣지만 신뢰 경계이므로 `#RGB`/`#RRGGBB` 형식을 강제하고 테스트로 고정했다. 최소 구현 원칙에서 입력 검증은 축약 대상이 아니다.
- 검증(전부 실측): **VER-31 컨테이너 30장 p50 83ms · p95 86ms · 최대 101ms**(기준 3000ms) — 호스트 p95 92ms. 이미지 평균 77KB. API 컨테이너 메모리 **216.5MiB**(warm Chromium 포함). 컨테이너에서 카드를 렌더해 꺼내 **한글 글리프 육안 확인**(NanumGothic). 테스트 운영 이미지 빌드 통과 후 토큰 로드까지 확인하고 검증용 이미지 제거. API 83건 통과(기존 78 + HTML 6 − 글리프 1).
- 제거: Pillow 직접 그리기 경로 전체와 글리프 테스트(계획대로). `pillow` 의존성은 **남겼다** — 현재 제품 코드에서는 쓰지 않지만 테스트가 PNG 검사에 쓰고 TASK-34(OMR)가 다시 필요로 한다. 지웠다 되살리는 churn을 피했다.
- **미이행: 시각 회귀 기준 이미지 비교.** [DES-08 상세](../../design.md#des-08-상세)가 규정하지만, [TASK-46](../../plan.md#task-46-카드-재설계와-브랜드-반영)이 카드를 전면 재설계하므로 지금 기준 이미지를 잡으면 곧 폐기된다. 설계가 확정되는 TASK-46에서 함께 수립한다.

### 2026-09-24 — TASK-46 카드 재설계와 브랜드 반영 완료

- 시안 3안을 렌더해 사용자가 **B 컬러 헤더형**을 확정했다. 추천 근거는 [DCR-003](./DCR-003-브랜드-자산으로서의-시각-설계.md)의 목적이다 — 학부모는 카톡 목록에서 섬네일로 먼저 보므로 그 순간 학원 아이덴티티가 드러나야 하는데 셋 중 B만 그렇다. A·C는 잘 정돈된 문서로 보이지 브랜드 자산으로 보이지 않는다.
- **정보 위계를 바꾼 것이 이번 작업의 핵심이다.** 기존 카드는 문자 본문 순서를 그대로 따라 점수가 다섯 번째 섹션에 묻혀 있었다. 학부모가 가장 먼저 보고 싶은 출결·과제·테스트를 헤더 바로 아래 요약으로 올리고, 점수에 `반평균 72.5점 · +5.5`처럼 반평균 대비를 붙였다. 원래는 두 줄로 흩어져 학부모가 직접 비교해야 했다.
- 시그니처 색은 핑크 스킨의 `oklch(0.58 0.17 355)`을 **브라우저로 실측해** `#C3457F`로 확정했다. 눈대중 변환이 아니라 렌더 픽셀값이다.
- 밝은 색 대응: 헤더가 브랜드 색 배경 위에 글자를 얹으므로 밝은 색이면 흰 글씨가 안 읽힌다. 시그니처 색은 원장이 자유롭게 고르므로(FR-40) WCAG 상대 휘도로 글자색을 뒤집는 `header_ink`를 넣고 테스트로 고정했다.
- **학원명은 `campus.name` 단일 소스를 유지했다.** [DES-08 상세](../../design.md#des-08-상세)는 "브랜드(학원명·로고·시그니처 색)는 `integration_setting`에서 읽는다"고 적지만, 학원명은 이미 `campus` 테이블에 있고 대시보드 등이 쓴다. 설정 테이블에 또 두면 같은 사실이 두 곳에 생겨 갈라진다. FR-40의 "설정할 수 있어야 한다"는 `PUT /api/settings/brand`가 `campus.name`을 고치는 것으로 충족한다. 제품 동작이 같으므로 경미한 변경으로 처리한다.
- 로고·색은 평문으로 저장한다. [DES-20](../../design.md#컴포넌트와-책임)은 **민감값만** 암호화하도록 규정하며 이 둘은 민감값이 아니다. 실제 시크릿(알리고 키 등)이 들어오는 시점에 암호화 계층이 필요하다.
- 브랜드 색은 `BrandIn`에서 `pattern`으로 hex를 강제한다. 이 값이 카드의 CSS 선언 안으로 들어가므로 형식을 막지 않으면 CSS 주입이 된다(TASK-45에서 렌더러 쪽에 넣은 방어와 같은 이유로, 입력 경계에서도 막는다).
- 자체 리뷰에서 고친 것: `SettingsPage`가 `useEffect`로 서버 값을 폼에 복사했는데, **응답이 늦게 오면 사용자가 입력 중이던 값을 덮어쓴다.** effect를 없애고 `edited ?? brand.data`로 바꿨다. 테스트가 이 순서 문제를 드러냈다.
- **타입 오류가 빌드를 깨뜨렸다.** 재개 지점에 적어 둔 "`npm test`와 `npm run build`를 함께 실행한다 — 타입 오류가 있는 테스트가 Docker 빌드를 깨뜨린 전례" 그대로였다. `mount()` 기본값에서 `brand_colour`가 `null`로 좁혀져 문자열을 넣을 수 없었다. 두 명령을 함께 돌려 잡았다.
- **시각 회귀 기준 이미지 수립**(TASK-45에서 미룬 항목): `tests/baseline/card.png`를 **컨테이너에서** 만들고 `test_report_visual.py`가 대조한다. 컨테이너 대조 결과 다른 픽셀 0. 글꼴이 호스트(Apple SD Gothic Neo)와 컨테이너(NanumGothic)에서 다르므로 호스트에서는 자동으로 건너뛴다. 갱신 명령은 테스트 머리말에 적었다.
- **미이행: 난이도 분석표 카드 템플릿(FR-30).** 이 카드가 담을 시험 분석 데이터가 아직 없다(TASK-29~36 미착수). 지금 만들면 내용 구조를 추측하게 되므로 디자인 언어만 확립해 두고 데이터가 생기는 TASK-36에서 같은 언어로 만든다.
- **후속 필요:** 시각 회귀 테스트는 컨테이너 글꼴과 `pytest`가 함께 필요한데 운영 이미지는 `--no-dev`다. 이번에는 컨테이너에 pytest를 일회성으로 넣어 통과를 확인했다. 정기 실행하려면 개발 의존성을 포함한 검증용 이미지가 필요하다.
- 검증: API 94건 + 시각 회귀 1건(호스트 스킵/컨테이너 통과), 웹 39건, `npm run build` 통과. AC-30은 시그니처 색 픽셀 대조로 확인(VER-29).

### 2026-09-24 — TASK-53 화면별 차등 모바일 대응 완료

- **검증 수단부터 만들어야 했다.** jsdom은 레이아웃을 계산하지 않아 vitest로는 가로 넘침을 잴 수 없다. 실제 브라우저로 재는 [`ops/verify/responsive.py`](../../../ops/verify/responsive.py)를 만들었고, 이것이 이 작업의 Red였다.
- 처음에는 배포된 테스트 운영 주소에 로그인해 쟀는데, 개발 DB의 원장 비밀번호가 `.env` 값과 달라(기존 계정이 있으면 비밀번호를 갱신하지 않는다) 개발 서버로는 로그인이 안 됐다. **API를 Playwright로 가로채 고정 응답을 주는 방식으로 바꿨다** — 백엔드도 자격 증명도 필요 없고 반복이 빠르다. 하네스가 실제 사이트와 같은 수치(17px·351px)를 재현해 신뢰할 수 있음을 확인했다.
- 착수 시점 실측(390px): 종합 대시보드 통과, **알림문자 17px 넘침**, **학생/반 관리 351px 넘침**, 학원 설정 통과.
- 고친 것: `PageHeader`(제목·필터 세로 쌓기), KPI 타일(`grid-cols-4` → 1/2/4열), 2단 본문(대시보드·알림문자, 1280px 이상에서만 2단), 일일 입력 메모 2열, 등록 폼(고정폭 한 줄 → 줄바꿈 + 데스크톱에서 고정폭 복귀). 표는 `Table`이 이미 `overflow-x-auto`를 가져 그대로 둔다.
- 결과: 390·768·1280px 세 폭에서 조회·발송 화면 4종 모두 넘침 0. 일일 입력은 데스크톱 전제를 지켰다(NFR-13의 키보드 이동과 충돌하지 않기 위해).
- **기존 웹 테스트 39건을 한 줄도 고치지 않았다.** [DCR-005](./DCR-005-모바일-지원-범위.md)가 "반응형 분기는 레이아웃 클래스만 바꾸고 역할·레이블을 건드리지 않는다"고 규정한 대로다.
- **"넘치지 않음"이 "쓸 만함"은 아니다.** 착수 전 대시보드는 넘침 0이었지만 사용자 스크린샷에서 KPI 타일이 눌려 `0 / 8명`이 세 줄로 접혔다. 측정만 믿지 않고 390px 스크린샷을 찍어 눈으로 확인했고, 표의 학생 이름이 중간에 끊기는 것(`학생` / `01`)도 그때 발견해 `whitespace-nowrap`으로 고쳤다.
- 검증 도구를 CI에 넣지 않았다. 웹 빌드 산출물과 Chromium이 함께 필요해 단위 테스트 체계와 결합도가 높다. 웹 레이아웃 변경 후 수동 실행하도록 스크립트 머리말과 계획에 적었다.
- 검증: VER-35 통과(3개 폭), 웹 39건 무수정 통과, `npm run build` 통과. 번들 CSS 19.47 → 19.98 kB.

### 2026-09-24 — TASK-50 학생 수정·퇴원 화면 완료

- 선행 테스트(Red) 2건을 먼저 넣었다: ① 퇴원 학생은 기본 목록에 없고 `퇴원 포함`을 누르면 보인다 ② 행의 `수정`으로 상태를 `퇴원`으로 저장하면 `PATCH /api/students/1`이 전체 필드와 함께 나가고 그 행이 목록에서 사라진다. 둘 다 "`퇴원 포함`·`수정` 버튼이 없다"로 의도대로 실패한 뒤 구현으로 통과시켰다.
- **API는 손대지 않았다.** `PATCH /students/{id}`가 이미 `status`(`enrolled`·`paused`·`withdrawn`)를 받고, 대시보드 KPI도 이미 `status == "enrolled"`만 센다([`stats.py:115`](../../../apps/api/src/mathdesk/stats.py)). 빠져 있던 것은 웹의 호출부뿐이었다(`api.ts`에 PATCH 0건).
- **퇴원 필터는 화면에서 건다.** 서버의 `GET /students?status=`는 한 상태로만 좁힐 수 있어 "퇴원 제외"를 표현하지 못한다. 전 캠퍼스 학생이 수십 명 규모라 목록을 받아 화면에서 거르는 편이 계약 변경보다 싸다. 규모가 커지면 서버 쪽 제외 파라미터가 필요하다.
- **연락처를 폼에 넣은 이유는 데이터 손실이다.** `PATCH`가 `StudentIn` 전체를 받는 전치환이라 보내지 않은 필드는 `null`이 된다. 수정 폼이 연락처를 다루지 않으면 상태만 바꿔도 연락처가 지워진다. 같은 필드 목록(`FIELDS`)을 등록 폼도 쓰므로 등록에도 연락처가 함께 생겼다 — FR-05가 요구하는 항목이라 축소하지 않았다.
- 상태 표기를 화면에서 `재원`·`휴원`·`퇴원`으로 바꿨다. 그전에는 `enrolled`가 그대로 보였다(FR-05의 상태 이름과 불일치).
- 미사용이던 `components/ui/dialog.tsx`를 수정 대화상자에서 처음 썼다. 제거 후보에서 빠진다.
- 검증: 웹 41건 통과(기존 39건 무수정 + 신규 2건), `npm run build` 통과, API 95건 통과(1 skip, 기존과 동일), VER-35(390·768·1280px) 통과. 표에 열이 하나 늘고 목록 상단에 토글 줄이 생겨 반응형을 다시 쟀다.
- API 특성화 테스트 1건을 추가했다([`test_masterdata.py`](../../../apps/api/tests/test_masterdata.py)): 퇴원 처리 후에도 그 학생의 과거 일일 기록(과제 등급 `A`)이 그대로 조회된다. VER-34의 학생 부분 중 "과거 기록 보존"은 서버 동작이라 화면 테스트로는 못 덮는다. 기존 동작을 확인한 것이므로 Red 없이 통과했다.
- 남은 것: 화면의 육안 확인 미수행. 교사 계정에도 `수정` 버튼이 보이고 서버가 403으로 막는다 — 등록 폼과 같은 기존 방식이라 그대로 뒀다(역할별 화면 가림은 이 작업 범위 밖).

### 2026-09-24 — TASK-51 반 수정·활성 여부 완료

- 계획대로 **API부터** 갔다. 선행 테스트(Red)는 "`is_active: false`로 PATCH하면 `GET /classes` 기본 목록에서 빠지고 대시보드의 활성 반 수가 0이 되며 `?include_inactive=true`로는 보인다"였고, `assert True is False`(PATCH가 `is_active`를 무시)로 의도대로 실패했다.
- `ClassIn.is_active`를 추가하고 `update_class`가 이를 반영한다. `create_class`도 함께 반영한다 — 스키마에 있는 필드를 조용히 버리는 쪽이 더 나쁘다.
- **`GET /classes`의 기본 응답을 활성 반으로 좁혔다**(`?include_inactive=true`로 전부). 학생은 화면에서 걸렀지만 반은 서버에서 거른다. 반 목록은 반 관리 화면만 쓰는 게 아니라 대시보드·일일 입력·알림문자의 **반 선택 목록**이기도 해서, 서버에서 한 번 거르면 세 화면이 자동으로 맞는다. `status`와 달리 `is_active`는 불리언이라 기본 제외를 파라미터로 표현할 수 있다는 점도 다르다. [TASK-51의 검증 방법](../../plan.md#task-51-반-수정활성-여부-api-보완-포함)이 이 동작을 명시하고 있어 계획 범위 안이다.
- **과거 기록은 그대로 열린다.** 필터를 `list_classes`에만 넣고 `_visible_classes`/`_visible_class`는 건드리지 않았다. 여기에 넣었으면 비활성 반의 지난 일일 기록과 대시보드가 403이 됐을 것이다. API 테스트가 비활성화 후 `GET /daily` 200을 함께 검사한다.
- **react-query 함정 하나.** `queryFn: fetchClasses`처럼 함수를 그대로 넘기면 첫 인자로 쿼리 컨텍스트 객체가 들어온다. `fetchClasses(includeInactive = false)`로 바꾼 순간 그 객체가 `true`로 취급돼 세 화면이 비활성 반까지 받게 된다. 대시보드·일일 입력·알림문자의 호출부를 `() => fetchClasses()`로 바꿨다. 테스트가 아니라 시그니처를 바꾸며 호출부를 훑다가 발견했다.
- 화면: 행별 `수정` 대화상자(반 이름·학년·활성 여부)와 `비활성 포함` 토글. 비활성 행에는 `(비활성)` 표시를 붙인다. 목록 위 문구는 토글 상태에 따라 `활성 N개 반` / `총 N개 반`으로 바뀐다 — 전에는 전부 보여주면서 `활성 N개 반`이라고 적고 있었다.
- **`PATCH /classes`는 시간표를 전치환한다.** 보내지 않으면 `class_schedule` 행이 지워진다. 수정 대화상자가 `teacher_id`와 `schedules`를 원본 그대로 실어 보내게 했고, 웹 테스트가 PATCH 본문 전체를 `toEqual`로 검사해 이를 고정한다. 대화상자에는 시간표를 읽기 전용으로 보여준다(시간표 편집 UI는 이 작업 범위 밖).
- 검증: API 96건 통과(1 skip), 웹 43건 통과(기존 41건 무수정 + 신규 2건), `npm run build` 통과, VER-35(390·768·1280px) 통과.

### 2026-09-24 — 기본 날짜가 UTC였다 (경량 경로 버그 수정)

- 대시보드·일일 입력·알림문자가 각자 가진 `today()`가 `new Date().toISOString().slice(0, 10)`이었다. UTC 날짜라 **KST 오전 0~9시에는 어제가 기본 선택된다.** 이 작업을 하던 시각(9/24 00:30 KST)에 앱은 9/23을 기본값으로 쓰고 있었다.
- TASK-52의 해제가 이 값을 종료일로 쓰기 때문에 먼저 고쳤다. 잘못된 날짜로 기간을 끊으면 학생이 오늘 명단에서 사라진다.
- 세 벌을 [`src/lib/date.ts`](../../../apps/web/src/lib/date.ts) 한 곳으로 모으고 로컬 달력 기준으로 바꿨다. 고정 시각(`2026-09-23T15:30Z`)에서 로컬 날짜와 일치하는지 검사하는 테스트를 붙였고, 기존 구현이 그 단언에서 `09-23` 대 `09-24`로 실패하는 것을 확인한 뒤 고쳤다.
- 한계: 머신 시간대가 UTC면 이 테스트는 두 구현 모두 통과한다(개발·검증 머신은 `Asia/Seoul`).

### 2026-09-24 — TASK-52 수강 배정·해제 화면 완료 (TASK-49 분해 완료)

- **해제를 `DELETE`로 하지 않았다.** FR-08이 배정 기간 이력 보존을 요구하고, [`daily.py`의 `_enrolled_students`](../../../apps/api/src/mathdesk/daily.py)가 `start_date`/`end_date` 범위로 그날의 명단을 재현한다. 행을 지우면 과거 수업일의 소속 반이 사라진다. `PATCH /classes/{id}/enrollments/{id}`를 신설해 종료일을 넣는 방식으로 했고, 기존 `DELETE`는 오등록 취소 전용이라고 docstring에 못박았다.
- 선행 테스트(Red, 405로 실패): 9/17로 종료하면 9/18 명단·일일 기록에서 빠지고 **9/11 일일 기록에는 그대로 남는다**. 이것이 FR-08의 "과거 수업일의 소속 반 재현"이다. 종료일이 시작일보다 빠르면 422로 거절한다(그 배정은 어느 날짜에도 안 잡혀 조용히 사라진다).
- `delete_enrollment`와 조회 로직이 같아 `_enrollment()` 헬퍼로 합쳤다.
- **종료일이 오늘이면 오늘 명단에는 아직 남는다.** `end_date >= on`이라 그렇고, 오늘 수업의 출결이 이미 잡혀 있을 수 있으므로 이게 맞는 동작이다. 문제는 화면이었다 — 해제를 눌러도 아무 변화가 없어 보인다. 명단 행이 `<종료일> 종료`를 표시하고 해제 버튼을 감추게 했다. **처음 쓴 웹 테스트 스텁이 해제 후 빈 명단을 돌려주고 있었다**(서버 동작과 다름). 스텁을 실제 규칙대로 고치고 종료 표시를 검사하도록 바꿨다.
- 화면: 반 행의 `명단` 대화상자. 배정은 오늘부터, 해제는 오늘까지. 학생 선택 목록에서 이미 배정된 학생과 퇴원 학생을 뺀다. 배정 이력에 이름이 필요해 학생 목록과 조인한다(`GET /enrollments`는 `student_id`만 준다).
- 검증: API 98건 통과(1 skip), 웹 46건 통과(기존 44건 무수정 + 신규 2건), `npm run build` 통과, VER-35(390·768·1280px) 통과.
- 이로써 [TASK-49](../../plan.md#task-49-마스터-데이터-수정-기능-보완)의 분해 3건이 모두 끝났다. VER-34의 세 조건(퇴원 학생 목록 제외·과거 보존, 비활성 반 활성 수 제외, 수강 해제 후 과거 재현)이 자동 테스트로 덮였다.

### 2026-09-24 — TASK-25 통계 집계 API와 엑셀 내보내기 완료

- 선행 테스트 3건을 먼저 썼다(AC-19·AC-20을 통합 테스트로 전환): 3주치 기록을 넣고 ① 학생 8주 시계열의 값과 같은 주 반 평균 ② 반 통계의 학생 행·점수 분포·등급 분포·비교 기간 ③ 내보낸 xlsx를 파싱해 화면 행과 같은지. `KeyError: 'student'`·`KeyError: 'period'`·`ModuleNotFoundError: openpyxl`로 실패시킨 뒤 구현했다.
- **기대값을 직접 계산해 검증했다.** 처음 쓴 기대값(기간 평균 81.0, 분포 4칸)이 틀렸다 — 점수를 잘못 골랐다. 날짜의 요일과 주 시작(월요일), 실제 점수 집합을 다시 계산해 77.0과 3칸으로 고쳤다. 테스트가 먼저 있으니 구현이 아니라 기대값이 틀렸다는 것이 드러났다.
- 엔드포인트는 설계의 REST 계약 그대로다: `GET /stats/students/{id}`, `GET /stats/classes/{id}`, `GET /stats/export`. [DES-06](../../design.md#컴포넌트와-책임)대로 저장 집계 테이블 없이 SQL 집계로 계산하고, 대시보드가 쓰던 `_completion_rate`·`_week_bounds`·`ATTENDING`·`ScopedRepository`를 그대로 재사용했다.
- **새 의존성 `openpyxl` 1건.** xlsx는 표준 라이브러리로 만들 수 없고(zip+XML을 손으로 쓰는 편이 더 길고 위험하다) 저장소에 다른 엑셀 경로가 없다. 되돌릴 수 있는 내부 선택이라 ADR을 만들지 않았다. `uv.lock`이 갱신되어 테스트 운영 이미지(`uv sync --frozen`)도 함께 받는다.
- **권한 구멍을 자체 리뷰에서 잡았다.** 학생 이력 조회가 `ScopedRepository`(캠퍼스 필터)만 거쳐서, 담당 반이 없는 강사도 남의 반 학생 이력을 200으로 받았다. [설계의 권한 표](../../design.md#권한)는 통계를 "원장 캠퍼스 전체 / 강사 담당 반 한정"으로 규정한다. 재현 테스트를 먼저 만들고(403 기대, 200 관측) `_current_class`에 강사 조건을 넣어 403으로 막았다 — 이름조차 돌려주지 않는다.
- 점수 분포는 10점 구간이며 90~100을 한 칸으로 묶었다. 만점이 1점짜리 칸으로 떨어지지 않게 하기 위함이다.
- 검증: API 102건 통과(1 skip). AC-19·AC-20은 **API 절반**만 닫혔고 화면 표시는 TASK-26이 닫는다.

### 2026-09-24 — TASK-26 통계 화면 완료 (TASK-24 분해 완료)

- 계획이 지정한 선행 테스트(표본 없음 → 빈 상태)와 완료 조건(8주 추이 표시), 그리고 엑셀 링크 3건을 먼저 썼다. 모듈이 없어 import 해석 실패로 Red를 확인했다.
- **`npm test`는 통과했는데 `npm run build`가 막았다.** 테스트 픽스처의 `test.average: null`이 추론된 `number`와 안 맞았다. 인계에 적힌 "두 명령을 함께 돌린다"가 세 번째로 값을 했다 — 픽스처에 `PeriodStats`·`StudentHistory` 타입을 달아 고쳤다.
- **차트 계열색을 브랜드색으로 쓰지 않았다.** 브랜드는 테마·학원별로 바뀌는데(블루·그린·핑크 테마와 FR-40 학원 시그니처 색) 계열 구분은 어느 테마에서나 같은 만큼 벌어져 있어야 한다. 상태색(success·warning·danger)은 출결·경고에 의미가 예약되어 있어 쓸 수 없다. `--md-color-chart-1`(파랑)·`--md-color-chart-2`(청록)를 토큰에 추가했고 `tokens.test.ts`의 필수 목록에 먼저 넣어 Red를 만들었다(5개 팔레트가 같은 색 토큰 집합을 가져야 한다는 기존 규칙이 그대로 강제된다).
- **색 선택을 눈으로 하지 않았다.** 색각 이상·정상 시각 분리와 표면 대비를 계산기로 돌려 골랐다. 첫 후보(브랜드 파랑 + 회색)는 정상 시각 분리 14.7로 기준 미달이었고, 다크에서는 라이트 값을 그대로 쓰면 두 색이 붙어 보여(분리 13.8) **다크용 단계값을 따로 잡았다**(밝기 폭을 벌린 0.55/0.66). 최종은 라이트 16.8·다크 20.4로 통과.
- **번들이 413→819 kB로 두 배가 됐다.** Recharts는 [ADR-010](./ADR-010-웹-UI-디자인-시스템.md)이 정한 라이브러리이지만 주 번들에 있을 이유는 없다. `/stats`만 지연 로딩으로 분리해 다른 화면의 첫 로딩을 원래대로 되돌렸다(주 414 kB + 통계 405 kB).
- **새 화면을 반응형 검증 대상에 넣었다.** 첫 측정에서 390px 28px 넘침. 필터 줄을 유연하게 바꿔도 그대로여서 넘치는 요소를 브라우저에서 직접 찾았더니 그리드 칸(Card)이 394px였다 — 그리드 칸의 기본 `min-width: auto`가 min-content를 따르는데 차트가 자기 폭을 고정하면 칸이 뷰포트보다 넓어진다. `min-w-0`으로 해결.
- **렌더한 결과를 눈으로 봤다.** 1280px 라이트·다크 스크린샷에서 선 끝에 점 두 개가 선과 떨어져 남아 있었다 — 마운트 애니메이션 중간 상태였다. 업무 도구에 애니메이션이 필요 없어 껐다. 비율 열(과제 완수율·출결률)이 점수 열과 구분되지 않아 `%`를 붙였다.
- 차트마다 같은 값을 담은 표를 함께 뒀다. 값이 색에만 실리지 않고, jsdom이 레이아웃을 계산하지 않아 차트 SVG를 테스트할 수 없는 문제도 이 표가 해결한다.
- 검증: 웹 49건 통과(기존 46건 무수정 + 신규 3건), API 102건 통과, `npm run build` 통과, VER-35 통과(390·768·1280px, 성적 통계 포함). 이로써 **AC-19·AC-20이 API와 화면 양쪽에서 닫혔다.**

### 2026-09-24 — TASK-28 공통 기반(Storage·업로드·TaskRunner) 완료

- 계획이 지정한 선행 테스트("작업 상태가 DB에 저장되고 재기동 후 `queued`부터 재개")를 포함해 9건을 먼저 썼다. 모듈·모델이 없어 import 실패로 Red를 확인했다.
- **재기동 재개를 어떻게 흉내 낼지가 이 작업의 핵심이었다.** 실제 프로세스를 죽일 수 없으므로 "`running`으로 끊긴 행"을 만들고 기동 경로(`TaskRunner.resume()`)를 호출한다. `resume()`은 `running`을 전부 `queued`로 되돌린 뒤 대기열을 비운다. 이것이 [RISK-09](../../design.md#위험)가 정한 완화책 그대로다.
- **실행기를 테스트 가능하게 쪼갰다.** `run_pending()`은 대기열을 끝까지 실행하고 건수를 돌려주는 평범한 awaitable이다. 기동 시에는 `asyncio.create_task`로 배경에 띄우고, 테스트는 직접 await한다. 테스트에서 sleep으로 기다리지 않아도 된다.
- **`background_task` 테이블은 [설계의 데이터 모델 목록](../../design.md#데이터-모델)에 없다.** 그러나 RISK-09의 완화책과 이 작업의 검증 방법이 "작업 상태를 DB에 저장"을 명시하고 REST 계약에 `GET /tasks/{task_id}`가 있다. 목록이 열거하지 않았을 뿐 새로운 제품 결정이 아니라고 보고 내부 구현으로 추가했다 — `user_session`과 같은 처리이며 아래 "설계와 달라진 점"에 남겼다.
- **업로드는 신뢰 경계다.** 최소화하지 않은 것 셋: ① 저장 키를 서버가 정한다(`{campus}/{kind}/{sha256}{확장자}`) — 업로드 파일명을 경로에 쓰면 `../`로 루트를 벗어나거나 서로 덮어쓴다. ② `LocalStorage`가 루트 이탈 경로를 `ValueError`로 막는다(전용 테스트 있음). ③ 크기 제한을 **읽기 전에** `upload.size`로 먼저 본다. 처음엔 다 읽고 나서 `len(data)`로 쟀는데, 그러면 큰 파일이 이미 메모리에 올라온 뒤라 제한의 의미가 없다.
- `signed_url`(DES-10)은 Phase A에서 앱 경로 `/api/files/{id}`를 준다. 같은 오리진에서 세션으로 인가하므로 서명 토큰이 필요 없고, 앱 밖에서 직접 받아 가는 Phase B에서 실제 서명 URL이 된다. 지금 토큰 machinery를 만들면 쓰는 곳 없이 유지만 해야 한다.
- **운영 구멍 하나를 자체 리뷰에서 막았다.** 업로드 파일은 DB가 아니라 파일시스템에 있는데 compose에 볼륨이 없어 재배포 때 사라진다. 개발·테스트 운영 양쪽에 `files` 볼륨과 `MATHDESK_STORAGE_ROOT`를 넣었다.
- 없는 `task_id` 조회가 404가 아니라 403이다. 저장소 규약(`ScopedRepository`)이 없는 id와 남의 캠퍼스 id를 구분해 알려주지 않기 때문이다. 처음 쓴 테스트의 기대값(404)을 규약에 맞춰 고쳤다.
- 새 의존성 1건: `python-multipart`(FastAPI 파일 업로드 필수).
- 검증: API 111건 통과(1 skip). 마이그레이션 왕복 테스트 포함. 개발 DB에 `980c6aafb97c` 적용, 개발 API 컨테이너 재빌드 후 `/api/health` 확인.
- 남은 위험: 프로세스 안에서 실행하므로 종료 시점에 진행 중이던 작업은 다음 기동에서 **처음부터** 다시 돈다. 핸들러는 멱등이어야 한다. TASK-31·TASK-34에서 핸들러를 만들 때 지킬 것.

### 2026-09-24 — TASK-30 DocumentIngest 4포맷 정규화 완료 (실파일 미확보)

- **사용자가 실제 시험지 파일이 없다고 확인했다(2026-09-24).** 계획의 완료 조건이 "픽스처 미확보 포맷은 미검증으로 명시"이므로 그대로 따랐다. 검증 범위는 아래와 같고 테스트 파일 머리말에도 같은 내용을 적었다.
  - `.pdf` **실물 검증**: Chromium 인쇄로 만든 텍스트 레이어 PDF와 Pillow로 만든 이미지 PDF 2종. 진짜 PDF라 이 경로는 실제로 동작함이 확인된다.
  - `.hwpx` **미검증**: 공개 규격(OWPML)대로 손으로 만든 최소 zip으로만 검사했다. 규격 해석이 틀렸을 가능성이 남는다.
  - `.hwp` **미검증**: `olefile`이 OLE 파일 생성을 지원하지 않아 컨테이너 픽스처를 만들 수 없다. FileHeader 속성 비트 해석만 단위로 검사했고, 암호 파일의 실제 안내 경로는 확인하지 못했다.
- **PDF 텍스트가 글자 단위로 쪼개져 나왔다.** PDF의 텍스트 개체는 글꼴·자간이 바뀔 때마다 끊기고 한글은 글자 하나가 개체 하나가 되기도 한다. 그대로 두면 블록 66개가 나온다("2026", "학", "년", "도"…). 세로로 겹치는 조각을 한 줄로 합쳐 블록 4개로 만들었다.
- **처음엔 윗변 좌표로 줄을 묶었는데 문장 끝 마침표가 제 줄에서 떨어져 나갔다**(마침표의 글자 상자가 낮다). 겹침 비율로 바꿔 해결했고 테스트가 이 경우를 고정한다 — 떨어진 마침표는 뒤 단계에서 빈 문항 조각이 된다.
- **`.hwp` 본문 추출은 공개 규격대로 썼지만 검증할 방법이 없다.** 조용히 빈 문서를 돌려주면 뒤에서 문항 0개로 흘러가므로, 아무 텍스트도 못 읽으면 사유와 대안(PDF 저장)을 알리며 실패하게 했다. [RISK-02](../../requirements.md#위험)의 완화책(PDF 변환·우선 안내)과 같은 방향이다.
- **라이브러리 선택에서 AGPL을 피했다.** PyMuPDF 하나면 텍스트·좌표·래스터화·암호 감지가 전부 되지만 AGPL이다. 이 제품이 나중에 외부에 서비스되면 §13(네트워크 사용) 의무가 생긴다. 허용적 라이선스인 `pypdfium2`(BSD-3/Apache-2.0)로 같은 범위를 덮고 `.hwp`는 `olefile`(BSD)을 썼다.
- 정규화는 라이브러리까지다. 업로드→정규화 연결과 AC-21의 "업로드하면" 부분은 [TASK-31](../../plan.md#task-31-문항-분할llmadapter분석)의 분석 작업에서 닫힌다.
- 검증: API 118건 통과(1 skip, 신규 7건). 픽스처 3개를 `tests/fixtures/`에 넣었다.

### 2026-09-24 — TASK-31 문항 분할·LlmAdapter·분석 완료

- 선행 테스트 18건을 먼저 썼다(모듈이 없어 import 실패로 Red). AC-22는 30문항 합성 PDF(`tests/fixtures/exam-30.pdf`, Chromium 인쇄)를 업로드 → 시험 등록 → 분석 작업 → 초안 조회까지 API로 돌린다. AC-23은 설정만 바꿔 구현체가 바뀌는지, AC-27은 발송 경로에서 세 어댑터의 `analyze`가 한 번도 불리지 않는지 검사한다.
- **구현체 3종이 같은 계약 테스트를 공유한다.** Anthropic은 SDK에 `httpx2.MockTransport`를, OpenAI 호환은 `httpx.MockTransport`를 끼워 외부로 나가지 않는다. 가짜 전송 계층이 요청 본문도 검사한다 — 구조화 출력(`output_config.format`), 시스템 블록의 `cache_control`, 폴백 파라미터가 실제로 실려 나가는지.
- **화이트리스트를 구조로 강제했다.** 계약이 받는 `QuestionInput`의 필드가 문항 번호·텍스트·이미지 셋뿐이고, 분석기의 `_payload()` 한 곳에서만 만든다. 테스트가 필드 집합을 고정한다. 공급자를 바꿔도 이 경계는 움직이지 않는다(ADR-009 결정 4).
- **거절(refusal)이면 본문을 읽지 않는다.** 가짜 응답이 거절과 함께 JSON이 아닌 본문을 주는데, 파싱을 시도하면 예외가 나므로 이 테스트가 "읽지 않음"을 증명한다.
- **자격 증명 부재는 첫 호출에서 알린다.** 클라이언트를 첫 호출 때 만들고, 401은 "Anthropic 자격 증명이 없거나 올바르지 않습니다"로 바꾼다. 키가 없어도 서버는 기동한다(개발 컨테이너로 확인).
- **계획 밖 추가 1건 — 서버 측 거절 폴백.** Anthropic 호출에 `fallbacks: "default"`(beta `server-side-fallback-2026-07-01`)를 켰다. 안전 분류기가 거절하면 서버가 거절 범주에 맞는 모델로 같은 요청을 다시 돌린다. 그 모델까지 거절해야 설계대로 문항 단위 실패 경로를 탄다. 실제로 응답한 모델을 `llm_call_log.model`에 남기므로 비용 재구성(NFR-15)이 깨지지 않는다. ADR-009의 거절 처리를 바꾸지 않고 앞단에 한 겹을 더한 것이라 DCR로 보지 않았지만, 사용자가 원하지 않으면 두 줄로 끈다.
- **재시도·상한·기록.** 문항 단위로 2회 재시도(오류와 거절 모두)하고 끝내 실패한 문항만 미분석·`확인 필요`로 남긴다. 실패한 호출도 `llm_call_log`에 남긴다(비용이 든다). 토큰 상한(입력 200,000·출력 30,000)을 넘으면 즉시 멈추고 사용량·비용을 사유에 담아 작업을 실패시키되, 이미 분석한 문항은 저장한다 — 쓴 비용의 결과를 버리지 않는다.
- **핸들러를 멱등으로 만들었다(TASK-28의 제약).** 초안을 통째로 지우고 다시 쓰므로 재기동으로 작업이 처음부터 돌아도 문항이 중복되지 않는다. 테스트가 같은 시험을 두 번 분석한다. 확정된 시험은 다시 분석하지 못하게(409) 막아 사용자가 고친 내용이 덮이지 않게 했다.
- 분할은 문항 번호가 1씩 늘 때만 새 문항으로 본다. 본문 속 "3." 같은 줄을 문항 시작으로 오인하지 않기 위해서다. 텍스트로 문항을 못 찾은 문서(스캔본)는 페이지 하나를 문항 하나로 보고 이미지를 보내며 항상 `확인 필요`로 둔다.
- **프롬프트 캐싱은 켰지만 지금은 걸리지 않을 가능성이 높다.** 분류 체계 프롬프트가 수백 토큰이라 모델별 최소 캐시 길이보다 짧다. 짧으면 조용히 캐시되지 않을 뿐 오류는 없다. 실측(`cache_read_input_tokens`)은 [TASK-43](../../plan.md#task-43-claude-실호출-검증)에서 한다 — 분류 체계를 늘리려고 프롬프트를 부풀리지는 않았다.
- 새 의존성: `anthropic` 1.8.0. 개발 API 컨테이너를 재빌드해 새 의존성 import와 `/api/health`를 확인했다.
- 검증: API 137건 통과(1 skip, 신규 19건). Anthropic 실호출은 미수행(이 작업의 완료 조건이 아님).

## 설계와 달라진 점

| 항목 | 내용 | 처리 |
|---|---|---|
| `user_session` 테이블 | [설계 데이터 모델](../../design.md#데이터-모델)의 테이블 목록에 없지만 [DES-03](../../design.md#des-03-상세)이 "서버 측 세션 레코드"를 규정한다. 목록이 이를 열거하지 않았을 뿐이며 새로운 제품 결정이 아니라고 판단해 내부 구현으로 추가했다 | 경미한 변경으로 처리, DCR 없음 |
| `GET /api/daily`의 세션 생성 | 설계 REST 계약에는 세션 생성 엔드포인트가 없고 [DES-05](../../design.md#des-05-상세)는 "첫 입력 시 생성"만 규정한다. 조회 시점에 만드는 것으로 해석했다 | 경미한 변경으로 처리, DCR 없음 |
| `background_task` 테이블 | [설계 데이터 모델](../../design.md#데이터-모델)의 테이블 목록에 없지만 [RISK-09](../../design.md#위험)가 "작업 상태를 DB에 저장하고 재기동 시 `queued`부터 재개"를 완화책으로 규정하고 REST 계약에 `GET /tasks/{task_id}`가 있다. 목록이 이를 열거하지 않았을 뿐이라고 판단해 내부 구현으로 추가했다(`user_session`과 같은 처리) | 경미한 변경으로 처리, DCR 없음 |
| 서버 측 거절 폴백 | [ADR-009](./ADR-009-LLM-공급자-추상화와-Claude-연결.md)는 `refusal`을 문항 단위 실패로 처리한다. 그 앞단에 서버 측 폴백(`fallbacks: "default"`)을 더해 거절 범주에 맞는 모델이 한 번 더 시도하게 했다. 최종 거절은 여전히 ADR대로 실패 경로를 타고, 실제 응답 모델을 호출 기록에 남긴다 | 경미한 변경으로 처리, 사용자에게 보고(원하지 않으면 제거) |
| `core/` 패키지 | [TASK-28 계획](../../plan.md#task-28-공통-기반--storage업로드taskrunner)의 변경 대상은 `apps/api/core/storage.py`였으나 저장소에 `core/` 패키지가 없고 모듈이 `src/mathdesk/` 평면에 있다. 기존 구조를 따랐다 | 경미한 변경으로 처리 |
| 로그인 시도 제한 | [보안과 품질 속성](../../design.md#보안과-품질-속성)의 "로그인 실패 지연·시도 제한" 중 실패 지연만 구현했다. 시도 제한은 임계값·잠금 시간이 기준선에 없어 임의로 정하면 실사용자가 잠길 수 있다 | [TASK-40](../../plan.md#task-40-로그인-시도-제한)으로 분리, 임계값은 사용자 확인 대기 |

## 미완료 항목

- TASK-27·TASK-32~TASK-39·TASK-43(사이클 2)
- AC-27의 OMR 경로 검사 — 판독기가 생기는 TASK-34에서 넣는다(발송 경로는 TASK-31에서 닫음)
- 알리고 실발송 경로 미검증([Q-02](../../requirements.md#가정과-미해결-질문))
- AC-05의 브라우저 육안 확인 미수행(자동화 제외 항목)
- 구 경로 `/api/messages/report.png`의 Cloudflare 엣지 캐시 잔존 — 퍼지 또는 TTL 만료 대기
- VER-01~VER-10·VER-25·VER-26·VER-27 통과
- 실제 재부팅에서의 자동 기동은 미검증(사용자 재부팅 시 확인)
- 테스트 운영 자격 증명이 `director`/`director` — 배포 이관 단계에서 교체하기로 합의된 의도된 상태
- AC-05의 실제 브라우저 육안 확인은 미수행(자동화 제외 항목, 사용자 확인 필요)
- VER-23(마이그레이션 왕복)은 TASK-03에서 1차 확보. 나머지 VER 항목은 미수행
- 로그인 시도 제한 임계값·잠금 시간 미결정 (TASK-40)
- 화면 ①~④의 시각 확인 — 대시보드는 2026-09-23 사용자 스크린샷으로 확인됨. 나머지는 미수행
- 학생·반 관리 화면의 육안 확인 미수행 — 수정·명단 대화상자와 목록 토글은 vitest·빌드·반응형 측정만 거쳤다
- 수강 해제의 종료일은 항상 오늘이다. 지난 날짜로 끊는 경로는 API(`PATCH`)에만 있고 화면에는 없다
- 반 시간표 편집 UI 없음 — 등록은 빈 시간표로 만들고 수정 대화상자는 시간표를 읽기 전용으로 보여준다. 시간표는 시드로만 들어간다
- lucide-react 미설치 — ADR-010 결정은 유효하나 아직 쓸 자리가 없다. Recharts는 TASK-26에서 설치했다
- 통계 화면의 기간 비교(`compare`)는 API만 있고 화면에는 없다 — FR-25의 두 기간 비교는 API로 충족되나 UI는 후속 작업이다
- [Q-02·Q-03·Q-08](../../requirements.md#가정과-미해결-질문) 미해소 — TASK-19·TASK-34·TASK-37의 실발송·실스캔 검증이 제한된다
- **`.hwp`·`.hwpx` 실파일 미확보(2026-09-24 사용자 확인)** — 두 포맷의 정규화 경로는 합성 픽스처로만 검사했다. 실파일을 얻으면 [TASK-30](../../plan.md#task-30-documentingest-4포맷-정규화)의 검증을 다시 돌려야 한다

## 재개 지점

- 다음 작업: [TASK-32 시험 등록·문항 확인 화면](../../plan.md#task-32-시험-등록문항-확인-화면)
- 사용자가 지정한 순서(2026-09-24): 모바일(완료) → 마스터 데이터 수정(완료) → 사이클 2 재개
- 먼저 확인할 사항: [계획 트리](../../plan.md#계획-트리)의 현재 상태, `git status`가 깨끗한지, `docker compose ps`로 개발 스택 기동 여부
- 필요한 문서: [TASK-32 정의](../../plan.md#task-32-시험-등록문항-확인-화면), [FR-29~FR-31](../../requirements.md#기능-요구사항), [DES-08 상세](../../design.md#des-08-상세)(난이도 분석표 카드는 리포트 카드 렌더러를 쓴다), 화면 ④ 참조 캡쳐
- 필요한 명령: `docker compose up -d`, `cd apps/web && npm test && npm run build`, `cd apps/api && uv run pytest`
- **이 작업의 핵심 제약**
  - **하드 삭제 경로를 만들지 않는다.** 기준선이 의도적으로 배제했다 — 출결·성적·발송 이력이 학생과 반을 참조하므로 물리 삭제는 과거 기록을 깨뜨린다. 학생은 상태 전이(`재원`·`휴원`·`퇴원`), 반은 `is_active` 플래그를 쓴다.
  - **`PATCH`는 대체로 전치환이다**(학생·반). 폼이 다루지 않는 필드를 함께 실어 보내지 않으면 지워진다. 수강 배정만 부분 갱신(`EnrollmentUpdate`)이다.
  - 마스터 데이터 수정 화면 3건(TASK-50~52)이 쓴 방식: 행별 대화상자 + 목록 토글 + 오늘 날짜는 [`lib/date.ts`의 `today()`](../../../apps/web/src/lib/date.ts).
  - **개인정보 경계는 최소화 대상이 아니다.** 외부로 나가는 것은 학생 정보가 없는 문항 텍스트·이미지뿐이다([NFR-04 상세](../../requirements.md#nfr-04-상세)). 화이트리스트 검증을 생략하지 않는다.
  - 백그라운드 작업 핸들러는 **멱등이어야 한다.** 프로세스가 죽으면 진행 중이던 작업이 다음 기동에서 처음부터 다시 돈다(`TaskRunner.resume()`).
  - 업로드 저장 키는 서버가 정한다(`{campus}/{kind}/{sha256}{확장자}`). 업로드 파일명을 경로에 쓰지 않는다.
  - 차트를 그리면 계열색은 `--md-color-chart-*`를 쓰고(브랜드·상태색 금지) 표를 함께 둔다. 새 화면은 [`ops/verify/responsive.py`](../../../ops/verify/responsive.py)의 `BROWSE`와 응답 스텁에 추가한다. 무거운 라이브러리를 쓰는 화면은 `App.tsx`에서 지연 로딩으로 분리한다.
  - `queryFn: fetchXxx`를 그대로 넘기지 않는다. react-query가 컨텍스트 객체를 첫 인자로 주므로 선택 인자가 있는 API 함수는 `() => fetchXxx()`로 감싼다.
  - TASK-52: `DELETE /classes/{id}/enrollments/{id}`가 이미 있으나, FR-08이 "배정 기간 이력을 보존"을 요구하므로 **해제는 기간 종료(`end_date`)로 처리하고 기존 DELETE는 오등록 취소 용도로 한정**한다.
- **반드시 지킬 것**
  - `npm test`와 `npm run build`를 **함께** 실행한다. 타입 오류가 있는 테스트가 Docker 빌드를 깨뜨린 전례가 두 번 있다.
  - `docker compose up -d --build`는 빌드 실패에도 기존 이미지로 컨테이너를 올리고 0을 반환한다. 빌드 출력을 확인한다.
  - 역할(`role`)과 레이블을 보존한다. 웹 테스트가 전부 의미 기반이므로 **테스트가 깨지면 마크업이 잘못된 것**이다. TASK-47에서 화면 5개를 전면 교체하고, TASK-53에서 반응형 분기를 넣고도 기존 테스트를 한 줄도 고치지 않았다.
  - 웹 레이아웃을 바꾸면 `cd apps/web && npm run build && cd ../api && uv run python ../../ops/verify/responsive.py`로 AC-35를 확인한다. jsdom은 레이아웃을 계산하지 않아 vitest로는 못 잡는다.
  - `tokens.css`에 전처리 지시어나 외부 파일 참조를 넣지 않는다. 카드 렌더러가 이 파일을 그대로 인라인하므로 깨지면 카드에서만 조용히 드러난다. `tokens.test.ts`가 이를 막는다.
  - 저장소 루트 `.dockerignore`를 지우지 않는다. 없으면 `Dockerfile.testops`가 호스트 `dist/`·`node_modules/`·`.env`까지 빌드 컨텍스트에 담는다.
  - API 이미지의 빌드 컨텍스트는 **저장소 루트**다(`compose.yaml`). 토큰 파일이 `apps/web`에 있기 때문이며 되돌리면 카드 렌더러가 토큰을 못 찾는다.
  - `playwright install`에 `--only-shell`을 유지한다. 빼면 이미지가 1.51GB → 2.11GB가 된다.
  - 카드를 바꾸면 시각 회귀 기준 이미지를 **컨테이너에서** 갱신한다(호스트는 글꼴이 달라 어긋난다). 명령은 `apps/api/tests/make_baseline.py` 머리말 참조.
  - 개발 DB 마이그레이션은 호스트에서 `DATABASE_URL`을 지정해 실행한다(API 컨테이너에 `migrations/`가 없다). 테스트 운영 이미지는 기동 시 자동 적용.
  - **개발 스택 로그인 주의:** 개발 DB의 `director` 비밀번호가 `.env`의 `MATHDESK_INITIAL_ADMIN_PASSWORD`와 다르다(계정이 이미 있으면 갱신하지 않는다). 개발 서버로 브라우저 검증이 필요하면 API를 가로채는 방식(`ops/verify/responsive.py`)을 쓴다. 테스트 운영은 `director`/`director`.

## 인계

- 다음 단계 또는 워크플로우: wf-implement 구현 — TASK-32부터
- 시작 조건: 충족됨 — 기준선 `v6` 승인(2026-09-23), 분석 경로(TASK-30·31) 완료, `git status` 깨끗
- 입력 문서와 기준선: [PLAN-mathdesk](../../plan.md), [REQ-mathdesk](../../requirements.md) `v6`, [DESIGN-mathdesk](../../design.md) `v6`, [결정 등록부](../../decisions.md)(ADR-001~012, DCR-001~005 모두 `approved`)
- 완료된 항목: 기준선 v1~v6 승인, ADR-001~012, DCR-001~005, 사이클 1 전체(TASK-01~TASK-22), TASK-23, TASK-40~TASK-42, 시각 설계 TASK-44~TASK-48, 모바일 TASK-53, 마스터 데이터 수정 TASK-49~TASK-52, M5 통계 TASK-24~TASK-26, 공통 기반 TASK-28, M6 정규화·분석 TASK-30·TASK-31 — 작업 53건 중 40건
- 미완료 항목: TASK-27, TASK-32~TASK-39, TASK-43
- 차단 요인: 없음
- 다음 행동: **[TASK-32 시험 등록·문항 확인 화면](../../plan.md#task-32-시험-등록문항-확인-화면).** API는 `POST /exams`·`POST /exams/{id}/analyze`·`GET /exams/{id}/questions`까지 있다(`exams.py`). 이 작업은 시험 정보 편집(문항 수·배점·홀짝 정답표 — `GET/PATCH /exams/{id}`, `PATCH /exams/{id}/questions`), 문항 확인·확정 화면, 난이도 분석표 카드를 더한다. 선행 테스트는 "저신뢰 문항에 `확인 필요`가 표시되고 확정 시 사라진다". **확정 후 재분석은 409로 막혀 있으니** 확정 흐름은 `exam.status = confirmed`로 두고, 문항을 수정·확정하면 `needs_review`를 끈다. 분석 진행은 `GET /tasks/{task_id}`를 폴링한다. 난이도 분석표 카드는 [DES-08 상세](../../design.md#des-08-상세)대로 리포트 카드 렌더러에 템플릿만 추가한다(시각 회귀 기준 이미지는 컨테이너에서 만든다)
- 재개 프롬프트: 작업 20260922-mathdesk-baseline 재개 — docs/work/20260922-mathdesk-baseline/work-log.md의 인계 절을 읽고 "다음 행동"부터 진행하라.
- 커밋 리듬: TASK 하나가 끝날 때마다 커밋하고 **push까지 함께** 수행한다(사용자 지시 2026-09-22, 별도 지시 전까지 유효).
