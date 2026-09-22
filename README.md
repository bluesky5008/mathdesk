# mathdesk

수학학원 운영 관리 프로그램 — 학생/반 관리, 일일 수업·진도·성적 입력, 시험지 분석, OMR 자동 채점, 성적 통계, 학부모 문자·카카오 알림톡 발송.

| 항목 | 내용 |
|---|---|
| 상태 | 요구사항·설계 기준선 `v1` 승인 완료 (2026-09-22) · 구현 계획 수립 예정 |
| 스택 | React 18 + Vite + TypeScript / FastAPI (Python 3.12) + SQLAlchemy 2.0 + Alembic / PostgreSQL |
| 배포 | Phase A: 로컬 `docker compose` → Phase B: Kubernetes |
| 요구사항 | [`docs/requirements.md`](docs/requirements.md) |
| 설계 | [`docs/design.md`](docs/design.md) |
| 설계 결정 | [`docs/decisions.md`](docs/decisions.md) (ADR-001~007) |
| 기획 아웃라인 | [`docs/SPEC-mathdesk-outline.md`](docs/SPEC-mathdesk-outline.md) ([HTML](docs/SPEC-mathdesk-outline.html)) |

## 폴더 구조

```
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

## OMR 프로토타입 실행

```bash
pip install opencv-python-headless numpy pymupdf
cd prototype/omr
python test_omr.py          # 합성 마킹 + 회전/원근 왜곡 → 판독 검증
python omr_reader.py ksat-2027-math.json <scan.png>   # 실제 스캔 판독
```

## 다음 단계

[`docs/requirements.md`](docs/requirements.md)와 [`docs/design.md`](docs/design.md)가 기준선 `v1`로 승인되었다. 다음은 wf-implement로 구현 계획을 수립하고 M0~M4부터 구현한다.
