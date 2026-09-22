# DESIGN-mathdesk: 수학학원 운영 관리 프로그램 설계

> 문서 유형: `design`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `approved`
> 기준선: `v2`
> 작성일: `2026-09-22`
> 최종 갱신: `2026-09-22`
> 관련 문서: [REQ-mathdesk: 요구사항](./requirements.md), [결정 등록부](./decisions.md), [SPEC-mathdesk-outline: 구현 아웃라인](./SPEC-mathdesk-outline.md)

## 요약

- 목적: [REQ-mathdesk](./requirements.md)의 기능·비기능 요구사항을 만족하는 시스템 구조, 데이터 모델, 인터페이스 계약, 동작 흐름과 검증 전략을 정의한다.
- 현재 결론 또는 상태: React SPA + FastAPI + PostgreSQL 단일 백엔드로 구성하고, 외부 의존(메시징·LLM·스토리지·OMR 판독·문서 파싱)을 5개 어댑터 인터페이스 뒤에 둔다. 컴포넌트 22개와 테이블 24개, REST 계약, OMR·메시지·시험지 흐름을 정의했다. 기준선 `v1` 승인 후 [DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md)로 테스트 운영 노출 구성이 추가되어 기준선 `v2`가 유효하다.
- 다음 행동: wf-implement 스킬로 구현 계획을 수립한다. M0~M4를 선행 단계로 분할한다.

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [REQ-mathdesk: 요구사항](./requirements.md) | FR-01~FR-39, NFR-01~NFR-16, AC-01~AC-27 | 이 설계의 입력 기준선 |
| input | decision | [ADR-001: 기술 스택과 실행 형태](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) | document | DES-01, DES-02 |
| input | decision | [ADR-002: PostgreSQL 단일 저장소](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) | document | DES-21 |
| input | decision | [ADR-003: AI 작업 분리와 개인정보 경계](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) | document | DES-13, DES-14, DES-15 |
| input | decision | [ADR-004: 문서 입력 정규화 파이프라인](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) | document | DES-11, DES-12 |
| input | decision | [ADR-005: 메시징 어댑터 단일화](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) | document | DES-09 |
| input | decision | [ADR-006: OMR 양식 고정과 템플릿 판독](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) | document | DES-15, DES-16, DES-17 |
| input | decision | [ADR-007: 인증·권한 모델](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) | document | DES-03 |
| input | decision | [ADR-008: 테스트 운영 노출 구성](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) | document | DES-03, DES-23 |
| input | change | [DCR-001: 테스트 운영 환경 노출](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) | DES-03, DES-23 | 기준선 v2로 올린 설계 변경 |
| output | decision | [결정 등록부](./decisions.md) | ADR-001~ADR-008, DCR-001 | 결정 전체 목록 |
| output | implementation | [PLAN-mathdesk: 구현 계획](./plan.md) | TASK-01~TASK-39 | 이 설계를 구현하는 계획 |

## 설계 목표와 제약

| 목표 | 설계상 의미 |
|---|---|
| 한 번 입력해 여러 산출물로 재사용 | 수업일 기록을 단일 원천으로 두고 KPI·통계·메시지를 모두 파생 뷰로 계산한다. 메시지 본문을 저장하지 않는다(FR-18) |
| Phase A→B 전환 비용 최소화 | 실행 형태를 바꾸지 않는 웹 SPA, 파일은 스토리지 인터페이스, 설정은 환경변수(NFR-08) |
| 개인정보의 외부 유출 차단 | 외부로 나가는 경로를 LLM 어댑터 1곳으로 좁히고 전송 필드를 화이트리스트로 고정(NFR-04, AC-27) |
| AI 결과의 오류를 사람이 통제 | 문항 분석과 OMR 판독은 항상 사용자 확정 단계를 거치고, 교정 결과를 학습 데이터로 축적(FR-29, FR-35) |
| 입력 속도 | 일일 입력의 저장 단위를 3개로 분리하고 각각 부분 갱신 API로 처리(FR-14, NFR-02) |

제약: [REQ-mathdesk 제약과 의존성](./requirements.md#제약과-의존성)을 따른다.

## 시스템 경계와 구조

```text
┌─ 브라우저 ────────────────────────────────┐
│ React 18 + Vite SPA (TypeScript)          │
│  라우팅 React Router / 서버 상태 TanStack │
└───────────────┬───────────────────────────┘
                │ REST/JSON, 세션 쿠키
┌───────────────▼───────────────────────────────────────────────┐
│ FastAPI (Python 3.12)                                         │
│  api 계층(라우터·스키마) → service 계층(도메인 규칙)          │
│                          → repository 계층(SQLAlchemy async)  │
│  ├ AuthN/AuthZ (세션, 역할, 캠퍼스 스코프)                    │
│  ├ Aggregation (KPI·통계 집계)                                │
│  ├ MessageRenderer / ReportImageRenderer                      │
│  ├ TaskRunner (업로드 후 비동기 처리)                         │
│  └ 어댑터: Storage / Messaging / Llm / DocumentIngest / Omr    │
└───┬───────────┬───────────────┬───────────────┬───────────────┘
    │           │               │               │
┌───▼────┐ ┌────▼─────┐ ┌───────▼──────┐ ┌──────▼────────────┐
│Postgres│ │Storage   │ │알리고 API    │ │OpenAI 호환 LLM API│
│        │ │(로컬→S3) │ │SMS/LMS/MMS   │ │(외부 기본·로컬 폴백)│
└────────┘ └──────────┘ │+카카오 알림톡│ └───────────────────┘
                        └──────────────┘
```

테스트 운영(Phase A′)에서는 위 구조 앞에 외부 노출 경계가 하나 붙는다.

```text
인터넷 ── HTTPS ── Cloudflare ── cloudflared 터널 `mathdesk`
                                      └── http://localhost:8090
                                            [API 컨테이너]
                                              ├── /api/*  REST
                                              └── /*      웹 정적 빌드(SPA fallback)
                                                    └── [postgres] 호스트 게시 없음
```

경계 규칙

1. SPA는 DB·외부 API에 직접 접근하지 않고 모든 요청을 FastAPI를 경유한다.
2. 외부 네트워크로 나가는 호출은 `MessagingAdapter`와 `LlmAdapter` 두 곳뿐이다. `OmrReader`와 `DocumentIngest`는 로컬 실행만 수행한다(NFR-04).
3. 파일은 DB에 저장하지 않고 `StorageAdapter`를 통해 저장하며 DB에는 `stored_file` 메타데이터만 둔다.
4. 도메인 규칙은 service 계층에만 두고 라우터와 리포지토리에 분산시키지 않는다.
5. 테스트 운영에서 외부로 열린 경로는 터널 하나뿐이며 웹과 API는 같은 오리진을 공유한다. 개발용 Vite 서버는 노출하지 않는다.

## 컴포넌트와 책임

| ID | 항목 | 내용 |
|---|---|---|
| DES-01 | Web SPA | 화면·라우팅·입력 상태 관리. 서버 상태는 TanStack Query 캐시로 다루고 저장 단위별로 별도 뮤테이션을 둔다 |
| DES-02 | API 서버 골격 | FastAPI 앱, 의존성 주입, 요청 검증(Pydantic), 공통 오류 표현, 트랜잭션 경계 |
| DES-03 | 인증·권한 | 로그인·세션, 비밀번호 해시, 역할(`원장`·`강사`) 판정, 캠퍼스 스코프 강제. [상세](#des-03-상세) |
| DES-04 | 마스터 데이터 서비스 | 캠퍼스·사용자·학생·보호자·반·시간표·수강 등록·상담일지 CRUD와 무결성 규칙 |
| DES-05 | 일일 기록 서비스 | 수업 세션(반 단위)과 학생 일일 기록의 부분 갱신, 출결 확정·해제, 재검사 대상 판정. [상세](#des-05-상세) |
| DES-06 | 집계 서비스 | 대시보드 KPI와 통계 조회를 SQL 집계로 계산. 저장 집계 테이블을 두지 않는다 |
| DES-07 | 메시지 렌더러 | 세션·학생 기록·등급 문구·템플릿을 병합해 본문 문자열 생성. 순수 함수로 두어 단위 테스트 대상으로 삼는다 |
| DES-08 | 리포트 이미지 렌더러 | 렌더된 본문을 카드형 HTML로 구성해 이미지로 변환 |
| DES-09 | MessagingAdapter | `send(channel, recipients, body|template_id, vars)` 단일 인터페이스. 알리고 구현, 테스트 모드 구현, 알림톡→SMS 폴백 |
| DES-10 | StorageAdapter | `put/get/delete/signed_url`. Phase A는 로컬 파일시스템, Phase B는 오브젝트 스토리지 |
| DES-11 | DocumentIngest | `.hwp`·`.hwpx`·`.pdf`·이미지를 `{pages, blocks, page_images}`로 정규화 |
| DES-12 | QuestionSegmenter | 정규화 결과에서 문항 번호 기준으로 문항 단위 블록·이미지를 분리 |
| DES-13 | QuestionAnalyzer | 문항 단위 입력으로 단원·세부 유형·난이도·판단 근거·신뢰도를 생성. 전송 필드 화이트리스트를 여기서 강제 |
| DES-14 | LlmAdapter | OpenAI 호환 `chat/completions` 클라이언트. 엔드포인트·모델·토큰 상한을 설정으로 주입, 호출 기록 |
| DES-15 | OmrReader | 템플릿 JSON 기반 판독기. 정합 → R채널 드롭아웃 → 버블 농도 → 필드 판정·플래그 |
| DES-16 | OMR 검수 서비스 | 스캔 페이지·판독값·플래그 관리, 학생 매칭, 교정값 반영과 라벨 교정 기록 저장 |
| DES-17 | 채점 엔진 | 문형별 정답표 대조, 학생 점수·문항별 정답률·오답 유형 통계 계산 |
| DES-18 | TaskRunner | 업로드 후 오래 걸리는 작업(시험지 분석, OMR 판독)을 백그라운드로 실행하고 진행 상태를 폴링으로 제공 |
| DES-19 | 발송·감사 로그 | 발송 로그 스냅샷, LLM 호출 로그, 권한 거부·확정 이벤트 감사 기록 |
| DES-20 | 설정·시크릿 관리 | 연동 설정 저장(민감값 암호화), 환경변수 우선순위, 연결 상태 점검 |
| DES-21 | 스키마 마이그레이션 | Alembic 리비전과 시드 데이터 스크립트 |
| DES-22 | 내보내기 | 통계·시험 결과 엑셀 생성, 난이도 분석표·리포트 이미지 파일 생성 |
| DES-23 | 테스트 운영 서빙 | 웹 정적 빌드를 API가 SPA fallback으로 서빙하고, `Secure` 쿠키와 노출 표면 축소를 설정으로 제어한다. 외부 경로는 cloudflared 터널 하나다 |

#### DES-03 상세

- 세션: 서버 측 세션 레코드 + `HttpOnly`·`SameSite=Lax` 쿠키. 유휴 만료 12시간.
- 비밀번호: Argon2id 해시. 초기 원장 계정은 마이그레이션 후 최초 기동 시 환경변수로 1회 생성한다.
- 스코프 강제: 모든 리포지토리 조회가 `campus_id` 필터를 요구하는 공통 기반 클래스를 사용하고, 라우터는 `CurrentScope(user, campus_id, role)` 의존성을 통해서만 서비스를 호출한다.
- 권한 매트릭스

| 자원 | 원장 | 강사 |
|---|---|---|
| 대시보드·통계 | 캠퍼스 전체 | 담당 반 한정 |
| 학생·반 CRUD | 가능 | 담당 반 학생 조회·수정, 반 생성·삭제 불가 |
| 일일 기록 | 가능 | 담당 반만 가능 |
| 메시지 발송 | 가능 | 담당 반 학생만 가능 |
| 시험·OMR | 가능 | 담당 반 시험만 가능 |
| 사용자·연동 설정 | 가능 | 불가 |

#### DES-05 상세

- 수업 세션 식별자는 `(class_id, session_date)`로 유일하다. 첫 입력 시 생성한다.
- 학생 일일 기록은 `(session_id, student_id)`로 유일하며, 세션 시점의 수강 등록으로 대상 학생을 결정한다(FR-08).
- 저장 단위별 API를 분리해 서로의 필드를 건드리지 않는다(FR-14).
- 재검사 대상 판정은 저장값이 아니라 조회 시 계산한다: 같은 반에서 해당 학생의 직전 세션 과제 등급이 기준 등급 이하이면 대상이다. 판정 근거(직전 등급·직전 수업일)를 함께 반환한다.
- 출결 확정은 세션 단위 상태(`attendance_confirmed_at`, `attendance_confirmed_by`)로 관리하며 확정 상태에서 학생 출결 필드 변경 요청은 409로 거부한다.

## 데이터와 인터페이스

### 데이터 모델

```text
campus 1─* app_user_campus *─1 app_user
campus 1─* student 1─* guardian
campus 1─* class 1─* class_schedule
class 1─* enrollment *─1 student
class 1─* class_session 1─* class_session_progress
class_session 1─* student_daily_record *─1 student
campus 1─* exam 1─* exam_question
exam 1─* exam_attempt 1─* exam_answer
exam 1─* omr_scan
campus 1─* message_log,  campus 1─* consult_log
campus 1─* stored_file,  campus 1─* integration_setting
```

| 테이블 | 주요 컬럼 | 비고 |
|---|---|---|
| `campus` | `id`, `name`, `is_active` | 모든 도메인 테이블의 스코프 기준 |
| `app_user` | `id`, `login_id`, `password_hash`, `display_name`, `role`, `is_active` | 역할 `director`·`teacher` |
| `app_user_campus` | `user_id`, `campus_id` | 접근 가능 캠퍼스 |
| `student` | `id`, `campus_id`, `name`, `school`, `grade`, `phone`, `status`, `omr_number` | `omr_number`는 캠퍼스 내 유일, 자리별 범위 검증(FR-05) |
| `guardian` | `id`, `student_id`, `relation`, `name`, `phone`, `is_notify_target` | |
| `class` | `id`, `campus_id`, `name`, `grade`, `teacher_id`, `is_active` | |
| `class_schedule` | `id`, `class_id`, `weekday`, `start_time`, `end_time` | |
| `enrollment` | `id`, `class_id`, `student_id`, `start_date`, `end_date` | 기간 이력 보존 |
| `class_session` | `id`, `class_id`, `session_date`, `homework`, `video_url`, `teacher_note`, `test_name`, `test_max_score`, `attendance_confirmed_at`, `attendance_confirmed_by` | `(class_id, session_date)` 유일 |
| `class_session_progress` | `session_id`, `period`, `content` | 교시 1~4 |
| `student_daily_record` | `id`, `session_id`, `student_id`, `attendance_status`, `attendance_reason`, `homework_grade`, `recheck_result`, `test_score_num`, `test_score_text` | `(session_id, student_id)` 유일 |
| `grade_comment` | `campus_id`, `grade`, `comment_text` | 등급→문구(FR-19) |
| `message_template` | `id`, `campus_id`, `kind`, `body`, `is_default` | |
| `message_log` | `id`, `campus_id`, `student_id`, `recipient_type`, `recipient_phone`, `channel`, `status`, `body_snapshot`, `cost_unit`, `is_test`, `requested_at`, `result_code`, `error` | 스냅샷 불변(AC-18) |
| `consult_log` | `id`, `campus_id`, `student_id`, `consulted_on`, `content`, `follow_up`, `author_id` | |
| `exam` | `id`, `campus_id`, `class_id`, `name`, `exam_date`, `source_file_id`, `question_count`, `max_score`, `status`, `answer_key_odd`, `answer_key_even` | 상태 `draft`·`confirmed` |
| `exam_question` | `exam_id`, `no`, `unit`, `sub_type`, `difficulty`, `rationale`, `points`, `needs_review`, `confidence` | |
| `exam_attempt` | `id`, `exam_id`, `student_id`, `form_type`, `score`, `source`, `flags` | `source`는 `omr`·`manual` |
| `exam_answer` | `attempt_id`, `question_no`, `raw_value`, `is_correct` | |
| `omr_scan` | `id`, `exam_id`, `file_id`, `page_no`, `status`, `matched_student_id`, `read_payload`, `flags` | 상태 `read`·`needs_review`·`applied` |
| `label_correction` | `id`, `kind`, `source_ref`, `before_value`, `after_value`, `asset_ref`, `corrected_by`, `corrected_at` | 학습 데이터 축적(FR-35) |
| `stored_file` | `id`, `campus_id`, `kind`, `path`, `content_type`, `size`, `sha256` | |
| `integration_setting` | `campus_id`, `key`, `value_encrypted` | 민감값 암호화(NFR-05) |
| `llm_call_log` | `id`, `campus_id`, `purpose`, `model`, `exam_id`, `prompt_tokens`, `completion_tokens`, `cost`, `created_at` | 비용 통제(NFR-15) |
| `audit_log` | `id`, `campus_id`, `actor_id`, `action`, `target`, `detail`, `created_at` | 권한 거부·확정 이벤트 |

열거값

| 대상 | 값 |
|---|---|
| 출결 상태 | `unchecked`, `present`, `late`, `absent`, `early_leave` |
| 과제 등급 | `A+`, `A`, `B`, `C`, `D`, `F` |
| 재검사 결과 | `pass`, `fail`, `null`(미선택) |
| 난이도 | `low`, `mid`, `high`, `top` |
| 메시지 채널 | `sms`, `lms`, `mms`, `alimtalk` |
| 발송 상태 | `test`, `queued`, `sent`, `failed`, `fallback_sent` |
| OMR 플래그 | `blank`, `multi`, `low_confidence`, `unmatched` |

### REST 계약

공통 규칙: 기본 경로 `/api`, 인증은 세션 쿠키, 캠퍼스는 `X-Campus-Id` 헤더로 전달하며 서버가 접근 권한을 검사한다. 오류는 `{code, message, details}` 형태로 반환하고 권한 없음은 404가 아닌 403으로 통일하되 자원 존재 여부를 본문에 노출하지 않는다.

| 그룹 | 엔드포인트 |
|---|---|
| 인증 | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| 사용자·캠퍼스 | `GET/POST/PATCH /users`, `GET /campuses` |
| 학생·보호자 | `GET/POST /students`, `GET/PATCH /students/{id}`, `GET/POST/PATCH /students/{id}/guardians` |
| 반·수강 | `GET/POST /classes`, `PATCH /classes/{id}`, `GET/POST/DELETE /classes/{id}/enrollments` |
| 일일 기록 | `GET /daily?class_id=&date=`, `PUT /daily/{session_id}/notes`, `PUT /daily/{session_id}/records`, `PUT /daily/{session_id}/records/{student_id}/recheck`, `POST /daily/{session_id}/attendance/confirm`, `POST /daily/{session_id}/attendance/unlock` |
| 대시보드·통계 | `GET /dashboard?class_id=&date=`, `GET /stats/students/{id}`, `GET /stats/classes/{id}`, `GET /stats/export` |
| 메시지 | `GET /messages/preview?session_id=&student_id=`, `POST /messages/send`, `GET /messages/logs`, `GET /messages/balance`, `GET/PUT /messages/templates`, `GET/PUT /messages/grade-comments` |
| 시험지 | `POST /exams/uploads`, `POST /exams`, `GET /exams`, `GET/PATCH /exams/{id}`, `GET/PATCH /exams/{id}/questions`, `POST /exams/{id}/analyze`, `GET /tasks/{task_id}` |
| OMR | `POST /exams/{id}/omr/uploads`, `GET /exams/{id}/omr/scans`, `PATCH /exams/{id}/omr/scans/{scan_id}`, `POST /exams/{id}/omr/apply` |
| 시험 결과 | `GET /exams/{id}/results`, `GET /exams/{id}/question-stats` |
| 상담 | `GET/POST/PATCH /students/{id}/consults` |
| 설정 | `GET/PUT /settings/integrations`, `POST /settings/integrations/test` |

주요 요청·응답 예시

```jsonc
// PUT /daily/{session_id}/records  — 표 일괄 저장(FR-14)
{ "records": [
  { "student_id": 12, "attendance_status": "late", "attendance_reason": "버스 지연",
    "homework_grade": "B", "test_score_num": 78 } ] }

// GET /daily?class_id=3&date=2026-09-20 — 응답 일부
{ "session": { "id": 91, "attendance_confirmed_at": null,
               "progress": [{"period":1,"content":"..."}], "homework": "...",
               "test_name": "4차연합고사", "test_max_score": 100 },
  "records": [ { "student_id": 12, "name": "김나윤", "attendance_status": "unchecked",
                 "recheck": { "target": true, "prev_grade": "B", "prev_date": "2026-09-18",
                              "result": null } } ] }
```

### 어댑터 인터페이스

```python
class StorageAdapter(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...

class MessagingAdapter(Protocol):
    def send(self, channel: Channel, recipients: list[Recipient],
             body: str | None, template_id: str | None,
             vars: dict, attachments: list[str] | None) -> list[SendResult]: ...
    def balance(self) -> Balance: ...

class LlmAdapter(Protocol):
    def complete(self, messages: list[Message], *, model: str,
                 max_tokens: int, response_schema: dict | None) -> LlmResult: ...

class DocumentIngest(Protocol):
    def normalize(self, file_ref: str) -> NormalizedDocument: ...

class OmrReader(Protocol):
    def read(self, page_image: bytes, template_id: str) -> OmrReadResult: ...
```

- 각 인터페이스는 테스트용 가짜 구현을 함께 제공한다(NFR-12).
- `LlmAdapter` 호출은 `QuestionAnalyzer`를 통해서만 이루어지며, 전송 페이로드는 문항 번호·문항 텍스트·문항 이미지로 제한한다(NFR-04).

## 정상·실패·복구 흐름

### 일일 입력

1. 사용자가 반·날짜를 선택하면 `GET /daily`로 세션·학생 기록·재검사 판정을 한 번에 받는다.
2. 표 편집 후 일괄 저장하면 `PUT /daily/{id}/records`가 해당 필드만 갱신한다.
3. 재검사 선택은 즉시 `PUT .../recheck`을 호출한다.
4. 메모 저장은 `PUT /daily/{id}/notes`로 반 단위 필드만 갱신한다.
5. 출결 확정은 `POST .../attendance/confirm`이며 이후 출결 필드 변경은 409로 거부된다. 해제는 `unlock`이고 두 이벤트 모두 감사 로그에 남는다.

실패 처리: 동시 편집으로 세션 버전이 달라지면 409와 함께 최신 값을 반환하고 클라이언트는 사용자에게 충돌을 알린다. 네트워크 실패 시 화면의 미저장 상태를 유지한다.

### 메시지 발송

1. `GET /messages/preview`가 세션·학생 기록·등급 문구·템플릿을 병합해 본문을 만든다(저장하지 않는다).
2. 발송 요청은 수신자 목록·채널을 서버가 결정(본문 길이·첨부 유무)한 뒤 `MessagingAdapter.send`를 호출한다.
3. 테스트 모드면 외부 호출 없이 `status=test`로 로그만 남긴다.
4. 알림톡 실패 시 설정에 따라 SMS·LMS로 재시도하고 `fallback_sent`로 기록한다. 두 시도 모두 로그에 남는다.
5. 부분 실패(수신자 일부 실패)는 수신자 단위로 상태를 분리 기록하고 화면에 실패 건만 재시도 버튼을 제공한다.

### 시험지 분석

1. 업로드 → `stored_file` 생성 → `POST /exams/{id}/analyze`가 백그라운드 작업을 등록하고 `task_id`를 반환한다.
2. `DocumentIngest.normalize` → `QuestionSegmenter.split` → 문항별 `QuestionAnalyzer.analyze`(LLM) 순으로 처리한다.
3. 결과는 `exam_question`에 `status=draft`로 저장하고 신뢰도가 임계값 미만이면 `needs_review=true`로 표시한다.
4. 파싱 실패(암호·배포 금지 `.hwp`)는 작업을 실패로 종료하고 사용자에게 사유와 대안(PDF 변환)을 안내한다.
5. LLM 호출 실패는 문항 단위로 재시도 2회 후 해당 문항만 미분석으로 남기고 나머지는 저장한다. 토큰 상한 초과 시 작업을 중단하고 사용한 비용을 알린다(NFR-15).

### OMR 채점

1. PDF 업로드 → 페이지 분리 → 페이지마다 `OmrReader.read` 실행(백그라운드).
2. 판독 결과를 `omr_scan`에 저장하고 수험번호로 학생을 매칭한다. 실패하면 `unmatched` 플래그.
3. 플래그가 하나라도 있으면 `status=needs_review`가 되어 검수 전까지 채점에 반영하지 않는다.
4. 검수 화면에서 교정하면 `label_correction`에 교정 전·후 값과 원본 크롭 참조를 저장한다.
5. `POST /exams/{id}/omr/apply`가 문형별 정답표와 대조해 `exam_attempt`·`exam_answer`를 생성하고 문항별 정답률을 갱신한다. 이미 반영된 스캔을 다시 적용하면 기존 시도를 대체하고 감사 로그를 남긴다.
6. 정합 실패(모서리 마크 미검출)는 해당 페이지만 실패로 표시하고 다른 페이지 처리를 계속한다.

## 보안과 품질 속성

| 항목 | 설계 |
|---|---|
| 인증 | Argon2id 해시, 서버 세션, 로그인 실패 지연(계정 유무와 무관한 동일 검증 비용)과 시도 제한(기본 연속 10회 실패 → 3분 잠금, 설정값). 쿠키의 `Secure`는 `MATHDESK_COOKIE_SECURE`로 제어하며 HTTPS 노출 구성에서 `true` |
| 권한 | 라우터 의존성으로 `CurrentScope` 주입, 리포지토리 기반 클래스가 `campus_id` 필터를 강제, 권한 거부는 감사 로그 기록 |
| 개인정보 | 외부 전송 화이트리스트(문항 텍스트·이미지). OMR 원본과 학생 식별 정보는 로컬 처리. 업로드 파일은 캠퍼스 스코프 키로 저장 |
| 비밀 정보 | 환경변수 우선, DB 저장 시 대칭키 암호화. 응답과 로그에서 마스킹 |
| 성능 | 대시보드·통계는 인덱스(`class_session(class_id, session_date)`, `student_daily_record(session_id)`, `enrollment(class_id, student_id, start_date)`) 기반 집계 쿼리. 무거운 작업은 백그라운드로 분리 |
| 자원 | OMR 판독은 페이지 단위 스트리밍 처리로 메모리 상한을 유지, 업로드 20MB·30쪽 제한 |
| 관측성 | 구조화 JSON 로그(요청 ID 포함), `message_log`·`llm_call_log`·`audit_log` 도메인 기록 |
| 가용성 | Phase A 단일 노드. 백그라운드 작업은 재시작 시 `queued` 상태부터 재개 가능하게 상태를 DB에 둔다 |
| 노출 표면 | 테스트 운영에서 postgres·API 호스트 포트를 게시하지 않고 터널만 외부 경로로 둔다. 개발용 기본 비밀번호를 쓰지 않으며 합성 데이터만 보관한다(NFR-17) |
| 유지보수성 | 어댑터 경계 5개, 모듈별 패키지 분리(`auth`, `masterdata`, `daily`, `stats`, `messaging`, `exams`, `omr`) |

## 마이그레이션과 롤백

- 신규 시스템이므로 이관할 기존 데이터가 없다. 초기 데이터는 학생·반 등록 화면 또는 시드 스크립트로 투입한다.
- 스키마는 Alembic 리비전으로만 변경하며 빈 DB에서 `alembic upgrade head`로 전체 재현이 가능해야 한다(NFR-09).
- 각 리비전은 `downgrade`를 제공한다. 파괴적 변경(컬럼 삭제)은 두 단계(사용 중단 → 삭제)로 나눈다.
- Phase A→B 전환: DB는 `pg_dump`/`pg_restore`, 파일은 `StorageAdapter` 구현 교체와 일괄 복사, 설정은 환경변수 교체로 수행한다. 애플리케이션 이미지는 동일하다.
- 롤백: 애플리케이션은 이전 이미지 태그로 되돌리고, 스키마는 해당 리비전으로 `downgrade` 후 복원한다.
- 테스트 운영(Phase A′) 기동: 테스트 운영 compose로 빌드·기동 → `cloudflared tunnel create mathdesk` → DNS 라우트 → launchd 등록. 기존 `homewiki` 터널 설정은 수정하지 않는다.
- 테스트 운영 롤백: launchd 서비스 해제 → DNS 레코드 삭제 → 컨테이너 중지. 배포처를 옮길 때도 이 3개만 제거하면 된다.

## 검증 전략

| 대상 | 방법 |
|---|---|
| AC-01~AC-03 (인증·권한) | API 통합 테스트. 역할·캠퍼스 조합별 접근 거부 케이스 포함 |
| AC-04, AC-05 (마스터 데이터) | 단위 테스트(수험번호 검증) + 통합 테스트(등록 시나리오) |
| AC-06~AC-12 (일일 입력) | API 통합 테스트. 토글·확정·잠금·저장 단위 독립성·집계값 검증 |
| AC-13 (KPI) | 고정 시드 데이터에 대한 집계 쿼리 단위 테스트 |
| AC-14~AC-16 (메시지 렌더) | 렌더러 순수 함수 단위 테스트(스냅샷 비교) + 이미지 생성 통합 테스트 |
| AC-17, AC-18, AC-26 (발송) | 가짜 `MessagingAdapter`로 통합 테스트. 폴백 경로와 로그 불변성 포함 |
| AC-19, AC-20 (통계·내보내기) | 통합 테스트 + 생성 파일 파싱 검증 |
| AC-21 (문서 정규화) | 샘플 파일 4종 고정 픽스처 단위 테스트 |
| AC-22, AC-23 (문항 분석) | 가짜 `LlmAdapter`로 결정적 응답 주입, 엔드포인트 교체 테스트 |
| AC-24, AC-25 (OMR) | [기존 합성 테스트](../prototype/omr/test_omr.py)를 제품 테스트로 이식하고 검수·반영 통합 테스트 추가 |
| AC-27 (외부 전송 경계) | 외부 HTTP 호출을 차단한 환경에서 OMR·메시지 경로 실행, `LlmAdapter` 호출 카운터 0 확인 |
| NFR-01~NFR-03 | 시드 데이터 규모에서 응답 시간 측정 스크립트 |
| NFR-09 | 빈 DB `upgrade head` → `downgrade base` 왕복 테스트 |
| AC-28 (VER-25) | 공개 도메인에서 로그인 후 `Set-Cookie`의 `Secure`·`HttpOnly` 확인, 로그아웃 후 보호 경로 401 |
| AC-29 (VER-26) | 임계 횟수 연속 실패 후 올바른 비밀번호 거부, 잠금 시간 경과 후 허용, 감사 로그 확인 |
| NFR-17 (VER-27) | 노출 구성의 호스트 포트 게시 목록 확인, 기본 비밀번호 미사용 확인 |

## 대안과 결정

| 결정 | 선택 | 기각안과 이유 | 문서 |
|---|---|---|---|
| 기술 스택·실행 형태 | React SPA + FastAPI, 로컬 `docker compose` | Electron/Tauri는 웹 전환 시 재작업 발생. Node 백엔드는 문서 파싱·OpenCV·모델 추론을 별도 서비스로 분리해야 함 | [ADR-001](./work/20260922-mathdesk-baseline/ADR-001-기술-스택과-실행-형태.md) |
| 저장소 | PostgreSQL 단일 | SQLite는 Phase B 전환 시 쿼리·타입 차이로 재검증 필요 | [ADR-002](./work/20260922-mathdesk-baseline/ADR-002-PostgreSQL-단일-저장소.md) |
| AI 배치·개인정보 경계 | OMR은 로컬 OpenCV, 문항 분석은 외부 LLM 기본·로컬 폴백 | VLM 전면 사용은 판독 오류와 개인정보 전송 위험, 로컬 전용은 분석 품질 부족 | [ADR-003](./work/20260922-mathdesk-baseline/ADR-003-AI-작업-분리와-개인정보-경계.md) |
| 문서 입력 | 4포맷을 공통 구조로 정규화 | 포맷별 개별 처리 경로는 분석 코드가 4중 분기됨 | [ADR-004](./work/20260922-mathdesk-baseline/ADR-004-문서-입력-정규화-파이프라인.md) |
| 메시징 | 알리고 단일 어댑터로 SMS·알림톡 통합 | 채널별 SDK 분리는 폴백 구현이 복잡해짐 | [ADR-005](./work/20260922-mathdesk-baseline/ADR-005-메시징-어댑터-단일화.md) |
| OMR | 수능 양식 고정 + 템플릿 좌표 판독 | 범용 OMR 인식은 정확도·개발량 모두 불리 | [ADR-006](./work/20260922-mathdesk-baseline/ADR-006-OMR-양식-고정과-템플릿-판독.md) |
| 인증·권한 | Phase A부터 다계정·역할·캠퍼스 스코프 | 단일 계정 후 도입은 전 API 재작업 유발 | [ADR-007](./work/20260922-mathdesk-baseline/ADR-007-인증-권한-모델.md) |
| 테스트 운영 노출 | 전용 터널 + 단일 오리진 API 서빙 + 앱 로그인 | 기존 터널 공유는 home-wiki 순단, 교차 오리진은 `SameSite=None`·CORS 필요, 개발 서버 노출은 운영 부적합 | [ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) |

ADR로 분리하지 않은 설계 판단

- 메시지 본문을 저장하지 않고 렌더 시점 생성: 원천 데이터 변경이 미리보기에 즉시 반영되어야 하고, 발송 시 스냅샷으로 감사 요건을 충족한다.
- 재검사 대상을 저장하지 않고 조회 시 계산: 기준 등급이 설정값이라 저장값은 설정 변경 시 즉시 낡는다.
- KPI 집계 테이블 미도입: 현재 데이터 규모(반 10·학생 200)에서 실시간 집계로 NFR-01을 만족한다. 규모가 커지면 DCR로 재검토한다.

## 가정과 미해결 질문

[REQ-mathdesk 가정과 미해결 질문](./requirements.md#가정과-미해결-질문)의 Q-01~Q-08을 그대로 승계한다. 설계 고유 항목은 다음과 같다.

| ID | 질문·가정 | 해소 조건 |
|---|---|---|
| Q-09 | 가정 — 백그라운드 작업은 별도 워커 프로세스 없이 FastAPI 프로세스 내 작업 큐로 충분하다 | 시험지·OMR 동시 처리 부하 측정 후 재검토 |
| Q-10 | 가정 — 리포트 이미지는 서버에서 HTML을 렌더해 생성한다(헤드리스 브라우저 의존) | 의존성 크기가 문제되면 클라이언트 렌더로 전환, DCR 대상 |
| Q-11 | 질문 — 한글 수식 스크립트를 LLM 입력으로 그대로 쓸지 LaTeX로 변환할지 | 초기 분석 품질 측정 후 결정 |

## 위험

[REQ-mathdesk 위험](./requirements.md#위험)의 RISK-01~RISK-07을 승계한다. 설계 고유 위험은 다음과 같다.

| ID | 위험 | 영향 | 완화 |
|---|---|---|---|
| RISK-08 | 캠퍼스 스코프 검사 누락이 한 곳이라도 생기면 데이터 격리가 깨진다 | 정보 노출 | 리포지토리 기반 클래스 강제, 권한 테스트를 엔드포인트 목록 기반으로 생성 |
| RISK-09 | 프로세스 내 작업 큐는 재시작 시 진행 중 작업이 유실될 수 있다 | 재업로드 필요 | 작업 상태를 DB에 저장하고 재기동 시 `queued`부터 재개 |
| RISK-10 | 헤드리스 브라우저 의존으로 컨테이너 이미지가 커지고 실행 환경이 까다로워질 수 있다 | 배포 복잡도 | Q-10에 따라 대안 평가 |

## 추적성

| 요구사항 | 설계 | 인수 조건 |
|---|---|---|
| [FR-01, FR-02](./requirements.md#기능-요구사항) | [DES-03](#컴포넌트와-책임) | [AC-01](./requirements.md#인수-조건) |
| [FR-03](./requirements.md#fr-03-상세), [NFR-07](./requirements.md#비기능-요구사항) | [DES-03](#des-03-상세) | [AC-02, AC-03](./requirements.md#인수-조건) |
| [FR-04](./requirements.md#기능-요구사항) | [DES-20](#컴포넌트와-책임) | [AC-23](./requirements.md#인수-조건) |
| [FR-05~FR-08, FR-39](./requirements.md#기능-요구사항) | [DES-04](#컴포넌트와-책임) | [AC-04, AC-05](./requirements.md#인수-조건) |
| [FR-09~FR-14](./requirements.md#fr-09-상세) | [DES-05](#des-05-상세) | [AC-06~AC-12](./requirements.md#인수-조건) |
| [FR-15~FR-17, FR-24~FR-26](./requirements.md#fr-15-상세) | [DES-06](#컴포넌트와-책임), [DES-22](#컴포넌트와-책임) | [AC-07, AC-13, AC-19, AC-20](./requirements.md#인수-조건) |
| [FR-18~FR-22](./requirements.md#fr-18-상세) | [DES-07](#컴포넌트와-책임), [DES-08](#컴포넌트와-책임) | [AC-14~AC-16](./requirements.md#인수-조건) |
| [FR-23, FR-37, FR-38](./requirements.md#fr-23-상세) | [DES-09](#컴포넌트와-책임), [DES-19](#컴포넌트와-책임) | [AC-17, AC-18, AC-26](./requirements.md#인수-조건) |
| [FR-27](./requirements.md#fr-27-상세) | [DES-11](#컴포넌트와-책임) | [AC-21](./requirements.md#인수-조건) |
| [FR-28~FR-31](./requirements.md#기능-요구사항) | [DES-12](#컴포넌트와-책임), [DES-13](#컴포넌트와-책임), [DES-14](#컴포넌트와-책임), [DES-18](#컴포넌트와-책임) | [AC-22, AC-23](./requirements.md#인수-조건) |
| [FR-32~FR-36](./requirements.md#fr-33-상세) | [DES-15](#컴포넌트와-책임), [DES-16](#컴포넌트와-책임), [DES-17](#컴포넌트와-책임) | [AC-24, AC-25](./requirements.md#인수-조건) |
| [NFR-04](./requirements.md#nfr-04-상세) | [DES-13](#컴포넌트와-책임), [DES-14](#컴포넌트와-책임), [DES-15](#컴포넌트와-책임) | [AC-27](./requirements.md#인수-조건) |
| [NFR-08~NFR-11](./requirements.md#비기능-요구사항) | [DES-10](#컴포넌트와-책임), [DES-19](#컴포넌트와-책임), [DES-21](#컴포넌트와-책임) | — |
| [NFR-06](./requirements.md#비기능-요구사항), [NFR-17](./requirements.md#비기능-요구사항) | [DES-03](#des-03-상세), [DES-23](#컴포넌트와-책임) | [AC-28, AC-29](./requirements.md#인수-조건) |

작업(`TASK-NN`)과 검증(`VER-NN`) 연결은 승인 후 wf-implement 스킬 계획 수립 시점에 추가한다.

## 승인 기록

| 항목 | 내용 |
|---|---|
| 승인 대상 | 이 문서 전체 (DES-01~DES-22)와 [ADR-001~ADR-007](./decisions.md#등록부) |
| 결과 | 승인 |
| 결정자 | 사용자 |
| 결정 일시 | 2026-09-22 |
| 근거 | 2026-09-22 대화형 승인 관문 응답 `승인` |
| 유효 기준선 | `v1` (효력 시작 2026-09-22) |
| 제외 범위 | 없음. [Q-09~Q-11](#가정과-미해결-질문)은 승인 범위에 포함되며, 해소 결과가 승인된 설계를 바꾸면 DCR로 처리한다 |
| 후속 상태 변경 | [REQ-mathdesk](./requirements.md) 동시 승인, ADR-001~ADR-007 → `approved` |

기준선 `v2` (2026-09-22): [DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md) 재승인으로 테스트 운영 노출 경계(DES-23)와 보안 속성이 반영되었고 [ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md)이 `approved`로 전이되었다.

## 변경 이력

| 날짜 | 변경 | 근거 | 상태 또는 기준선 | 작성자·승인자 |
|---|---|---|---|---|
| 2026-09-22 | 최초 작성 — 컴포넌트 22개, 테이블 24개, REST 계약, 흐름·검증 전략 정의 | [REQ-mathdesk](./requirements.md), ADR-001~ADR-007 | draft → awaiting-approval | Claude / 승인자 미정 |
| 2026-09-22 | 사용자 승인 — 기준선 `v1` 발행, ADR-001~007 approved | 대화형 승인 관문 응답 `승인` | awaiting-approval → approved, 기준선 v1 | Claude / 사용자 |
| 2026-09-22 | 구현 계획 문서 링크 추가 (기준선 의미 변경 없는 역방향 링크 보완) | [PLAN-mathdesk](./plan.md) 생성 | approved 유지, 기준선 v1 | Claude |
| 2026-09-22 | 테스트 운영 노출 경계·DES-23·보안 속성 추가 | [DCR-001](./work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md), [ADR-008](./work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md) | approved 유지, 기준선 v1 → v2 | Claude / 사용자 |

## 인계

- 다음 단계 또는 워크플로우: wf-implement 스킬(Workflow 2) — 구현 계획 수립
- 시작 조건: 충족됨 — [REQ-mathdesk](./requirements.md)와 이 문서가 `approved`이고 기준선 `v1`이 2026-09-22에 발행되었다
- 입력 문서와 기준선: [REQ-mathdesk: 요구사항](./requirements.md), [DESIGN-mathdesk: 설계](./design.md), [결정 등록부](./decisions.md)
- 완료된 항목: 요구사항 도출, 설계 결정 7건, 컴포넌트·데이터·인터페이스 정의, 검증 전략
- 미완료 항목: 검증 실행. 구현 계획과 작업 분해는 [PLAN-mathdesk](./plan.md)에서 완료
- 차단 요인: 없음. 다만 [Q-02·Q-03·Q-08](./requirements.md#가정과-미해결-질문)은 M4·M8·OMR의 실검증 범위를 제한할 수 있다
- 다음 행동: [PLAN-mathdesk](./plan.md)의 TASK-02부터 구현한다
