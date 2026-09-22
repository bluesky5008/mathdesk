# mathdesk

수학학원 운영 관리 프로그램 — 학생/반 관리, 일일 수업·진도·성적 입력, 시험지 분석, OMR 자동 채점, 성적 통계, 학부모 문자·카카오 알림톡 발송.

| 항목 | 내용 |
|---|---|
| 상태 | 기준선 `v4` · 사이클 1(MVP) 완료 · 사이클 2 진행 중 ([계획](docs/plan.md)) |
| 스택 | React 18 + Vite + TypeScript / FastAPI (Python 3.12) + SQLAlchemy 2.0 + Alembic / PostgreSQL |
| 배포 | Phase A: 로컬 `docker compose` · Phase A′: 테스트 운영 <https://mathdesk.yongs-wiki.com> ([ops](ops/README.md)) → Phase B: Kubernetes |
| 요구사항 | [`docs/requirements.md`](docs/requirements.md) |
| 설계 | [`docs/design.md`](docs/design.md) |
| 설계 결정 | [`docs/decisions.md`](docs/decisions.md) (ADR-001~007) |
| 기획 아웃라인 | [`docs/SPEC-mathdesk-outline.md`](docs/SPEC-mathdesk-outline.md) ([HTML](docs/SPEC-mathdesk-outline.html)) |

## 폴더 구조

```
apps/api/      FastAPI 서버 (Python 3.12)
apps/web/      React 18 + Vite + TypeScript SPA
compose.yaml   Phase A 로컬 실행 (api + web + postgres)
docs/          요구사항·설계·결정 기준선 문서
  requirements.md  현행 요구사항 (FR/NFR/AC)
  design.md        현행 설계 (DES-01~22)
  decisions.md     결정 등록부
  work/<작업-ID>/  작업별 ADR·DCR
  SPEC-mathdesk-outline.md  최초 기획 아웃라인 (선행 명세)
prototype/     검증용 프로토타입
  notice-generator.html   학부모 공지 생성기 (M4 메시지 템플릿 병합의 출발점)
  omr/                    OMR 템플릿 추출·판독 참조 구현 (ksat-2027-math.json, omr_reader.py, test_omr.py)
assets/omr/    OMR 답안지 원본 (2027학년도 수능 수학영역 양식 PDF, 300 DPI 렌더)
assets/capture/ 참조 프로그램 화면 캡쳐 4장 (요구사항 출처)
```

## 로컬 실행 (Phase A)

```bash
docker compose up -d --build     # api + web + postgres
open http://localhost:5173       # 웹 (API 상태 표시)
curl http://localhost:8080/api/health
docker compose down
```

호스트 포트가 겹치면 `API_PORT`·`WEB_PORT`·`POSTGRES_PORT`로 바꾼다(기본 8080·5173·55432). `POSTGRES_PASSWORD`는 로컬 개발 기본값이 있으므로 실사용 전 `.env`로 덮어쓴다.

초기 원장 계정은 `.env`의 `MATHDESK_INITIAL_ADMIN_ID`·`MATHDESK_INITIAL_ADMIN_PASSWORD`로 만든다. 값을 비우면 계정을 만들지 않으며, 이미 비밀번호가 설정된 계정은 덮어쓰지 않는다.

스키마 적용과 개발용 시드 데이터(반 4개 · 학생 47명).

```bash
cd apps/api
export DATABASE_URL=postgresql+asyncpg://mathdesk:mathdesk@localhost:55432/mathdesk
uv run alembic upgrade head
uv run python -m mathdesk.seed
```

API 테스트와 웹 빌드는 컨테이너 없이도 실행할 수 있다. 마이그레이션 테스트는 `mathdesk_test`
데이터베이스를 지우고 다시 만들므로 postgres 컨테이너가 떠 있어야 한다(`MATHDESK_TEST_DATABASE_URL`로 대상 변경 가능).

```bash
cd apps/api && uv sync --group dev && uv run pytest
cd apps/web && npm install && npm test && npm run build
```

## OMR 프로토타입 실행

```bash
pip install opencv-python-headless numpy pymupdf
cd prototype/omr
python test_omr.py          # 합성 마킹 + 회전/원근 왜곡 → 판독 검증
python omr_reader.py ksat-2027-math.json <scan.png>   # 실제 스캔 판독
```

## 다음 단계

기준선 `v1` 승인 후 [`docs/plan.md`](docs/plan.md)의 TASK-01~47로 구현 중이다. 사이클 1(MVP: M0~M4 인증·학생/반·일일 입력·대시보드·알림문자)이 2026-09-22 승인으로 완료되었다. 테스트 운영은 <https://mathdesk.yongs-wiki.com>에서 접근할 수 있다. 다음은 시각 설계(TASK-44~47 — 디자인 토큰, 리포트 카드 HTML 렌더링, 브랜드 반영)이며 그 뒤가 사이클 2(M5~M9)다. M6 문항 분석의 LLM 공급자는 기준선 `v3`([DCR-002](docs/work/20260922-mathdesk-baseline/DCR-002-M6-LLM-공급자-중립화와-Claude-연결.md))에서 설정으로 교체 가능한 구조가 되었다. 기본 공급자는 테스트 모드이며 Anthropic 실호출 검증은 최종 단계(TASK-43)에서 수행한다.
