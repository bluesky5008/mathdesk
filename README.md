# mathdesk

수학학원 운영 관리 프로그램 — 학생/반 관리, 일일 수업·진도·성적 입력, 시험지 분석, OMR 자동 채점, 성적 통계, 학부모 문자·카카오 알림톡 발송.

| 항목 | 내용 |
|---|---|
| 상태 | 기획 단계 (Draft v0.5) |
| 스택 | React 18 + Vite + TypeScript / FastAPI (Python 3.12) + SQLAlchemy 2.0 + Alembic / PostgreSQL |
| 배포 | Phase A: 로컬 `docker compose` → Phase B: Kubernetes |
| 기획 문서 | [`docs/SPEC-mathdesk-outline.md`](docs/SPEC-mathdesk-outline.md) ([HTML](docs/SPEC-mathdesk-outline.html)) |

## 폴더 구조

```
docs/          기획·설계 문서 (SPEC-*)
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

결정 항목은 스펙 §7 참조. D9(wf-workflow 단계 정의) 확정 후 데이터 모델 상세 → API 스펙 → Claude Code에서 구현 착수.
