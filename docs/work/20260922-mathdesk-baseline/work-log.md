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
- 현재 결론 또는 상태: M4 메시지의 발송 어댑터(TASK-19)까지 완료했다. 화면(TASK-20)만 끝내면 MVP 구현이 완료된다.
- 다음 행동: [TASK-20 메시지 화면](../../plan.md#task-20-메시지-화면) — 수신 대상 미선택 시 발송 버튼 비활성 컴포넌트 테스트(Red)부터 작성한다.

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

- 진행 중인 작업: [TASK-20 메시지 화면](../../plan.md#task-20-메시지-화면) (미착수, 상태만 `in-progress`)
- 마지막 완료 작업: [TASK-19 MessagingAdapter·발송 로그](../../plan.md#task-19-messagingadapter발송-로그) (2026-09-22 18:41)
- 차단 요인: 없음. 다만 구 경로(`/api/messages/report.png`)의 Cloudflare 엣지 캐시가 남아 있어 사용자 퍼지가 필요하다(최대 4시간 후 자동 만료). [TASK-40 로그인 시도 제한](../../plan.md#task-40-로그인-시도-제한)은 임계값 결정을 기다린다

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

## 설계와 달라진 점

| 항목 | 내용 | 처리 |
|---|---|---|
| `user_session` 테이블 | [설계 데이터 모델](../../design.md#데이터-모델)의 테이블 목록에 없지만 [DES-03](../../design.md#des-03-상세)이 "서버 측 세션 레코드"를 규정한다. 목록이 이를 열거하지 않았을 뿐이며 새로운 제품 결정이 아니라고 판단해 내부 구현으로 추가했다 | 경미한 변경으로 처리, DCR 없음 |
| `GET /api/daily`의 세션 생성 | 설계 REST 계약에는 세션 생성 엔드포인트가 없고 [DES-05](../../design.md#des-05-상세)는 "첫 입력 시 생성"만 규정한다. 조회 시점에 만드는 것으로 해석했다 | 경미한 변경으로 처리, DCR 없음 |
| 로그인 시도 제한 | [보안과 품질 속성](../../design.md#보안과-품질-속성)의 "로그인 실패 지연·시도 제한" 중 실패 지연만 구현했다. 시도 제한은 임계값·잠금 시간이 기준선에 없어 임의로 정하면 실사용자가 잠길 수 있다 | [TASK-40](../../plan.md#task-40-로그인-시도-제한)으로 분리, 임계값은 사용자 확인 대기 |

## 미완료 항목

- TASK-16(자식 1건 잔여: TASK-20), TASK-21~TASK-39
- 알리고 실발송 경로 미검증([Q-02](../../requirements.md#가정과-미해결-질문))
- 구 경로 `/api/messages/report.png`의 Cloudflare 엣지 캐시 잔존 — 퍼지 또는 TTL 만료 대기
- VER-01~VER-10·VER-25·VER-26·VER-27 통과
- 실제 재부팅에서의 자동 기동은 미검증(사용자 재부팅 시 확인)
- 테스트 운영 자격 증명이 `director`/`director` — 배포 이관 단계에서 교체하기로 합의된 의도된 상태
- AC-05의 실제 브라우저 육안 확인은 미수행(자동화 제외 항목, 사용자 확인 필요)
- VER-23(마이그레이션 왕복)은 TASK-03에서 1차 확보. 나머지 VER 항목은 미수행
- 로그인 시도 제한 임계값·잠금 시간 미결정 (TASK-40)
- [Q-02·Q-03·Q-08](../../requirements.md#가정과-미해결-질문) 미해소 — TASK-19·TASK-34·TASK-37의 실발송·실스캔 검증이 제한된다

## 재개 지점

- 다음 작업: [TASK-20 메시지 화면](../../plan.md#task-20-메시지-화면)
- 먼저 확인할 사항: [계획 트리](../../plan.md#계획-트리)의 현재 상태, `docker compose ps`로 postgres 기동 여부
- 필요한 명령 또는 파일: `docker compose up -d`, `cd apps/api && uv run pytest`, `cd apps/web && npm test`, [설계 DES-05 상세](../../design.md#des-05-상세)

## 인계

- 다음 단계 또는 워크플로우: wf-implement 구현 — TASK-02부터
- 시작 조건: 충족됨 — 기준선 `v1` 승인, 계획 수립 완료
- 입력 문서와 기준선: [PLAN-mathdesk](../../plan.md), [REQ-mathdesk](../../requirements.md) `v1`, [DESIGN-mathdesk](../../design.md) `v1`
- 완료된 항목: 기준선 v1·v2 승인, ADR-001~008, DCR-001, 계획, TASK-02~TASK-15, TASK-17~TASK-19, TASK-40~TASK-42
- 미완료 항목: TASK-16(TASK-20), TASK-21~TASK-39
- 차단 요인: 없음
- 다음 행동: TASK-20의 컴포넌트 테스트(Red)를 작성한다
- 재개 프롬프트: 작업 20260922-mathdesk-baseline 재개 — docs/work/20260922-mathdesk-baseline/work-log.md의 인계 절을 읽고 "다음 행동"부터 진행하라.
