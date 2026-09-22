# WORK-20260922-mathdesk-baseline: 작업 기록

> 문서 유형: `work-log`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `in-progress`
> 기준선: `v1`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-22`
> 관련 문서: [PLAN-mathdesk: 구현 계획](../../plan.md), [REQ-mathdesk: 요구사항](../../requirements.md), [DESIGN-mathdesk: 설계](../../design.md), [결정 등록부](../../decisions.md)

## 요약

- 목적: 기준선 `v1`의 구현 진행 상태, 결정, 검증 결과와 재개 지점을 기록한다.
- 현재 결론 또는 상태: TASK-02~TASK-08·TASK-10을 완료했다. 일일 기록의 3개 저장 단위가 서로를 덮어쓰지 않고 동작하며 AC-11·AC-12가 통과한다.
- 다음 행동: [TASK-11 출결 확정·재검사 판정](../../plan.md#task-11-출결-확정재검사-판정) — AC-06·AC-09·AC-10을 인수 테스트(Red)로 먼저 작성한다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | implementation | [PLAN-mathdesk: 구현 계획](../../plan.md) | TASK-01~TASK-39 | 이 기록이 수행하는 계획 |
| input | baseline | [REQ-mathdesk: 요구사항](../../requirements.md) | AC-01~AC-27 | 검증 대상 인수 조건 |
| input | baseline | [DESIGN-mathdesk: 설계](../../design.md) | DES-01~DES-22 | 적용 설계 기준선 |
| input | decision | [결정 등록부](../../decisions.md) | ADR-001~ADR-007 | 적용 결정 |

## 기준선과 현재 계획

- 적용 기준선: [REQ-mathdesk](../../requirements.md) `v1`, [DESIGN-mathdesk](../../design.md) `v1` (2026-09-22 사용자 승인)
- 현재 계획: [PLAN-mathdesk](../../plan.md) — 작업 39건, 사이클 1(MVP M0~M4, TASK-01~22) / 사이클 2(확장 M5~M9, TASK-23~39)
- 발생한 DCR: 없음

## 현재 상태

- 진행 중인 작업: [TASK-11 출결 확정·재검사 판정](../../plan.md#task-11-출결-확정재검사-판정) (미착수, 상태만 `in-progress`)
- 마지막 완료 작업: [TASK-10 일일 기록 API (3 저장 단위)](../../plan.md#task-10-일일-기록-api-3-저장-단위) (2026-09-22 13:02)
- 차단 요인: 없음. [TASK-40 로그인 시도 제한](../../plan.md#task-40-로그인-시도-제한)은 임계값 결정을 기다린다

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

## 설계와 달라진 점

| 항목 | 내용 | 처리 |
|---|---|---|
| `user_session` 테이블 | [설계 데이터 모델](../../design.md#데이터-모델)의 테이블 목록에 없지만 [DES-03](../../design.md#des-03-상세)이 "서버 측 세션 레코드"를 규정한다. 목록이 이를 열거하지 않았을 뿐이며 새로운 제품 결정이 아니라고 판단해 내부 구현으로 추가했다 | 경미한 변경으로 처리, DCR 없음 |
| `GET /api/daily`의 세션 생성 | 설계 REST 계약에는 세션 생성 엔드포인트가 없고 [DES-05](../../design.md#des-05-상세)는 "첫 입력 시 생성"만 규정한다. 조회 시점에 만드는 것으로 해석했다 | 경미한 변경으로 처리, DCR 없음 |
| 로그인 시도 제한 | [보안과 품질 속성](../../design.md#보안과-품질-속성)의 "로그인 실패 지연·시도 제한" 중 실패 지연만 구현했다. 시도 제한은 임계값·잠금 시간이 기준선에 없어 임의로 정하면 실사용자가 잠길 수 있다 | [TASK-40](../../plan.md#task-40-로그인-시도-제한)으로 분리, 임계값은 사용자 확인 대기 |

## 미완료 항목

- TASK-01(자식 1건 잔여: TASK-40), TASK-09(자식 2건 잔여), TASK-11~TASK-39
- VER-01·VER-02(AC-02·AC-03 전부)·VER-03·VER-04·VER-08·VER-09 통과
- AC-05의 실제 브라우저 육안 확인은 미수행(자동화 제외 항목, 사용자 확인 필요)
- VER-23(마이그레이션 왕복)은 TASK-03에서 1차 확보. 나머지 VER 항목은 미수행
- 로그인 시도 제한 임계값·잠금 시간 미결정 (TASK-40)
- [Q-02·Q-03·Q-08](../../requirements.md#가정과-미해결-질문) 미해소 — TASK-19·TASK-34·TASK-37의 실발송·실스캔 검증이 제한된다

## 재개 지점

- 다음 작업: [TASK-11 출결 확정·재검사 판정](../../plan.md#task-11-출결-확정재검사-판정)
- 먼저 확인할 사항: [계획 트리](../../plan.md#계획-트리)의 현재 상태, `docker compose ps`로 postgres 기동 여부
- 필요한 명령 또는 파일: `docker compose up -d`, `cd apps/api && uv run pytest`, `cd apps/web && npm test`, [설계 DES-05 상세](../../design.md#des-05-상세)

## 인계

- 다음 단계 또는 워크플로우: wf-implement 구현 — TASK-02부터
- 시작 조건: 충족됨 — 기준선 `v1` 승인, 계획 수립 완료
- 입력 문서와 기준선: [PLAN-mathdesk](../../plan.md), [REQ-mathdesk](../../requirements.md) `v1`, [DESIGN-mathdesk](../../design.md) `v1`
- 완료된 항목: 기준선 승인, ADR-001~007, 계획, TASK-02~TASK-08, TASK-10
- 미완료 항목: TASK-01(TASK-40), TASK-09(TASK-11·TASK-12), TASK-13~TASK-39
- 차단 요인: 없음
- 다음 행동: TASK-11의 AC-06·AC-09·AC-10 인수 테스트(Red)를 먼저 작성한다
- 재개 프롬프트: 작업 20260922-mathdesk-baseline 재개 — docs/work/20260922-mathdesk-baseline/work-log.md의 인계 절을 읽고 "다음 행동"부터 진행하라.
