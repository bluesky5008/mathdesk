# DCR-027: 배포 파이프라인 — CI 이미지와 Actions 승격

> 문서 유형: `dcr`
> 작업 ID: `20260922-mathdesk-baseline`
> 상태: `awaiting-approval`
> 기준선: `v27` (제안 `v28`)
> 작성일: `2026-10-17`
> 최종 갱신: `2026-10-17`
> 관련 문서: [REQ-mathdesk: 요구사항](../../requirements.md), [DESIGN-mathdesk: 설계](../../design.md), [ADR-015: 배포 파이프라인](./ADR-015-배포-파이프라인.md), [ADR-013: 운영 배포처](./ADR-013-운영-배포처-클라이언트별-Lightsail-단일-서버.md), [PLAN-mathdesk](../../plan.md), [결정 등록부](../../decisions.md)

## 요약

- 변경 분류: **설계 변경** — 운영 서빙(DES-25)의 빌드 위치·배포 절차·롤백 수단을 바꾼다. 요구사항·인수 조건은 바뀌지 않는다(NFR-08의 "같은 Dockerfile의 동일 이미지", AC-48의 "두 서버가 같은 이미지 다이제스트"는 CI 이미지로 비로소 글자 그대로 성립한다).
- 변경 요지: 이미지를 **운영 서버에서 빌드하지 않고 GitHub Actions가 한 번 만들어 GHCR에 게시**한다(amd64, 스모크 통과 태그만 배포 가능). 운영 반영은 **Actions `workflow_dispatch`로 사용자가 명령할 때만**, 환경별 필수 승인자와 명령 제한 SSH 키로 잠근다. 스테이징(맥미니)은 지금처럼 로컬 빌드·수동 배포. 결정 본문은 [ADR-015](./ADR-015-배포-파이프라인.md)에 있고, 이 DCR은 그 결정을 설계 문서에 반영한다.
- 사용자 결정(2026-10-17): ① 빌드 = GitHub Actions ② 승격 = Actions가 반영하되 사용자 명령일 때만 ③ 태그 = 날짜형 `YYYY.MM.DD` ④ 스테이징 = 로컬 빌드 유지 + CI 이미지 스모크 보완 ⑤ 반영 방식 = (a) Actions SSH + 보안 대책 전부(키 노출 위협 모델 검토 후 확정)
- 사용자 재승인 결과: 대기

## 문서 연결

| 방향 | 관계 | 대상 문서 | 대상 항목 | 비고 |
|---|---|---|---|---|
| input | baseline | [DESIGN-mathdesk](../../design.md) | DES-25 행·상세(`compose.prod.yaml`·배포·복원·롤백·접근), 전환 절차 | 개정 |
| input | baseline | [REQ-mathdesk](../../requirements.md) | NFR-08, NFR-20, AC-48 | 변경 없음(충족 방식만 바뀜) |
| input | decision | [ADR-015](./ADR-015-배포-파이프라인.md) | 결정 1~10 | 이 DCR이 반영하는 결정 |
| input | decision | [ADR-013](./ADR-013-운영-배포처-클라이언트별-Lightsail-단일-서버.md) | 결정 3 | ADR-015가 대체. 승인 시 ADR-013에 대체 표기 |
| output | plan | [PLAN-mathdesk](../../plan.md) | TASK-57, TASK-97 | TASK-57 변경 대상·검증 갱신 |
| output | related | [결정 등록부](../../decisions.md) | DCR-027 | 등재 |

## 변경 사유와 증거

- **계기:** 사용자 요청(2026-10-17) — 개발 서버(맥미니) + 운영 AWS 2곳 구조에서 배포 방식·파이프라인·자동화 범위를 정하자.
- **확인한 사실:**
  1. 현재 배포는 맥미니에서 `docker compose -f compose.testops.yaml up -d --build` 수동 실행이고 CI가 없다. 테스트는 로컬에서 돌려 작업 기록에 손으로 적는다.
  2. 운영은 클라이언트 2명(밤·핑수) 각자의 Lightsail 2GB 서버다. ADR-013 결정 3은 "서버에서 clone해 빌드"였으나, 서버가 3곳(스테이징 1 + 운영 2)이라 같은 빌드를 세 번 하고, 맥미니(arm64)와 Lightsail(amd64)은 같은 커밋이어도 같은 바이너리가 아니며, 2GB 서버 빌드는 스왑 2GB를 전제해야 한다(이미지 1.73GB: Node 빌드·uv·Chromium headless shell·나눔 글꼴).
  3. 저장소는 공개(`bluesky5008/mathdesk`)라 GitHub Actions·GHCR·환경(필수 승인자, 환경 비밀값)을 무료로 쓸 수 있다. 쓰기 권한 보유자는 사용자 1인이다. 이미지에 `.env`·비밀값은 들어가지 않는다.
  4. 최근 7일 스테이징 배포 21회(하루 최대 9회) — 스테이징에 CI 대기를 끼우면 TASK마다 즉시 배포하는 리듬이 깨진다.
  5. GitHub 공식 문서: 포크에서 트리거된 워크플로에는 비밀값이 전달되지 않는다(`GITHUB_TOKEN` 제외), `workflow_dispatch`는 쓰기 권한이 필요하다, 환경 비밀값은 보호 규칙 통과 후 그 환경을 쓰는 잡에만 전달된다, 서드파티 액션은 SHA 고정·`pull_request_target` 회피를 권고한다.
- **보류한 구현:** 없음(TASK-57 미착수).

## 제안 (기준선 `v28`)

### 요구사항

변경 없음. NFR-08(같은 compose·Dockerfile의 동일 이미지), NFR-17(노출 표면), NFR-20(운영 데이터 보호·접근 회수), AC-48(두 서버 같은 다이제스트, 방화벽 SSH만)은 그대로이며 새 절차로 충족한다.

### 설계

- **DES-25 행:** "서버에서 이미지 빌드" → "GitHub Actions가 게시한 GHCR 이미지를 pull, 운영 반영은 Actions `workflow_dispatch`(ADR-015)".
- **DES-25 상세 표 개정:**

  | 요소 | 변경 후 |
  |---|---|
  | `compose.prod.yaml` | `app`은 `image: ghcr.io/bluesky5008/mathdesk:${MATHDESK_IMAGE_TAG}`(빌드 없음). 나머지(postgres·cloudflared·포트 없음·시드 없음·`restart`)는 그대로 |
  | CI(`.github/workflows/`) | `ci.yml`(main push·PR: pytest + Postgres 서비스, vitest, `tsc -b`), `release.yml`(태그 `YYYY.MM.DD[-n]` push: amd64 이미지 빌드·GHCR 게시 → 이미지 스모크(Postgres와 기동, `alembic upgrade head`·`/api/health`·초기 원장 로그인) → `:<태그>-verified` 꼬리표), `deploy.yml`(`workflow_dispatch`만: 대상 `bam`·`pingsu`·`both`, 태그 → 환경 승인 → SSH → 서버 `deploy.sh`). 서드파티 액션 금지, GitHub 소유 액션 SHA 고정, `pull_request_target` 금지, `GITHUB_TOKEN` 최소 권한 |
  | GitHub 환경 | `bam`, `pingsu`: 필수 승인자 = 사용자, 환경 비밀값 = 그 서버의 배포 전용 SSH 키(ed25519, 환경마다 별도) |
  | 서버 | 기존 항목 유지 + 배포 전용 계정 `deploy`(docker 그룹, `authorized_keys`에 `command="~/mathdesk/ops/deploy.sh",no-pty,no-port-forwarding,no-agent-forwarding`). 소스 저장소 clone 없음. 서버에는 `compose.prod.yaml`·`.env`·`ops/` 사본만 |
  | 배포 | 스테이징(맥미니 로컬 빌드) 확인 → 그 커밋에 태그 push → `release.yml` 통과 → `deploy.yml` 실행(대상·태그) → 승인 → 서버 `deploy.sh`: `-verified` 확인 → `ops/backup.sh` → `docker compose pull` → `up -d`(기동 시 `alembic upgrade head`) → `/api/health`·이미지 태그 확인 → 실패 시 잡 실패·이전 태그 로그. 두 서버는 같은 태그 |
  | 복원·롤백 | 앱은 `deploy.yml`을 이전 태그로 실행(재빌드 없음). 스키마는 `alembic downgrade` 또는 배포 전 백업 복원(`ops/restore.sh`). 되돌릴 수 없는 마이그레이션이 든 릴리스는 태그 메모에 표시. 서버 전체는 스냅샷 복원 |
  | 접근 | 기존 항목 유지 + 클라이언트는 서버에서 `deploy` 계정의 공개키를 지워 배포 경로를 회수할 수 있다 |

- **전환 절차 문구:** "롤백: 애플리케이션은 이전 이미지 태그로 되돌리고"는 그대로 맞다. Phase A→B 문구의 "애플리케이션 이미지는 동일하다"를 "애플리케이션 이미지는 GHCR의 같은 태그·다이제스트다"로 명확화.
- **테스트 운영(DES-23):** 변경 없음. `compose.testops.yaml`은 로컬 빌드 유지.
- **ADR-013:** 결정 3을 ADR-015가 대체한다고 표기(본문은 수정하지 않음). 결정 1·2·4·5·6 유지.

## 변경 항목

| 항목 | 기존 | 변경 | 이유 |
|---|---|---|---|
| 빌드 위치 | 운영 서버에서 `git pull` 후 `--build` | GitHub Actions가 태그마다 amd64 이미지 게시 | 세 번 반복 빌드·2GB 서버 부하 제거, 두 서버 동일 다이제스트 |
| 산출물 검증 | 서버 기동 후 health | CI 이미지 스모크(마이그레이션·health·로그인) 통과 태그만 배포 | 스테이징(arm64 로컬 빌드)과 운영 산출물이 달라지는 틈을 메움 |
| 운영 반영 | 사용자가 서버에 SSH해 수동 | `deploy.yml` `workflow_dispatch` + 환경 승인 → Actions가 SSH | 사용자 명령일 때만, 결과가 한곳(Actions 로그)에 남음 |
| 서버 접근 키 | 사용자 장비의 SSH 키 | + 배포 전용 `deploy` 계정 키(명령 제한)를 GitHub 환경 비밀값에 | 키 유출 시 행위를 "검증된 태그 재배포"로 한정 |
| 운영 서버의 소스 | 저장소 clone 보유 | 없음(compose·`.env`·ops 사본만) | 공격 표면·관리 대상 축소 |
| 롤백 | 이전 커밋 재빌드 | 이전 태그 pull | 수십 초, 빌드 실패 위험 없음 |
| 릴리스 식별 | 커밋 해시 | 날짜형 태그 `YYYY.MM.DD[-n]` = 이미지 태그 | 문서 기준선 `vN`과 구분 |
| 스테이징 | 로컬 빌드·수동 | 그대로 | 하루 최대 9회 배포 리듬 보존(사용자 결정) |

## 대안 분석

[ADR-015 고려한 대안](./ADR-015-배포-파이프라인.md#고려한-대안) 참조 — A 서버 빌드 유지(기각: 반복·불일치), B CI 이미지 + 사용자 명령 승격(채택), C push 자동 반영(기각: 사용자 "매 push 배포 불가"), D 맥미니 교차 빌드 전송(기각). 반영 방식 (a) Actions SSH vs (b) 서버 pull은 키 노출 위협 모델 검토 후 (a) + 대책으로 사용자가 확정했다(ADR-015 결정 10).

## 영향 범위

| 영역 | 영향 |
|---|---|
| 요구사항 | 없음 |
| 설계 | DES-25 행·상세, 전환 절차 문구, ADR-013 결정 3 대체 |
| 공개 인터페이스·데이터 모델 | 없음 |
| 보안 | GitHub 환경 비밀값에 서버 배포 키 1개/환경. 완화: 필수 승인자, 서드파티 액션 금지·SHA 고정, `pull_request_target` 금지, 서버 `command=` 제한, `-verified` 태그만 배포, 쓰기 권한 1인·2단계 인증. NFR-20의 "클라이언트가 접근을 회수할 수 있어야 한다"는 `deploy` 키 삭제로 유지 |
| 테스트 운영 | 변경 없음 |
| 계획 | TASK-57 변경 대상·검증 갱신(워크플로 3개, GitHub 환경 2개, `compose.prod.yaml` 이미지 전환, 서버 `deploy.sh`, 운영 절차서). TASK-59 절차에 "태그 push → 릴리스 → 배포 워크플로" 반영 |
| 비용 | 공개 저장소라 Actions·GHCR 무료. 비공개 전환 시 패키지 비공개·pull 토큰 필요 |

## 마이그레이션과 롤백

- 데이터 마이그레이션 없음(배포 절차 변경).
- 되돌리기: 워크플로 파일 삭제, `compose.prod.yaml`을 `build:`로 되돌림. 운영 서버가 아직 없어 전환 비용은 0이다.

## 검증 방법

- TASK-57에서: `ci.yml`이 main push에서 전체 테스트를 통과시킨다 / 태그 1개로 `release.yml`이 이미지를 게시하고 스모크를 통과시켜 `-verified`를 단다 / 맥미니에서 `compose.prod.yaml`로 그 amd64 이미지를 기동해 health·로그인 확인(로컬 리허설) / 백업·복원 1회 / `deploy.yml`은 환경 승인 흐름까지 확인하고 서버 접속 단계는 TASK-59의 빈 서버에서 리허설.
- AC-48의 "두 서버 같은 다이제스트"는 TASK-59에서 `docker inspect`로 비교.

## 남은 위험과 미해결 사항

- 사용자 GitHub 계정 탈취 시 (a)·(b) 모두 운영 반영 경로가 열린다. 계정 2단계 인증(패스키)이 전제다.
- GitHub 장애 시 릴리스 불가. 우회: 맥미니에서 `docker buildx --platform linux/amd64`로 빌드해 GHCR에 직접 push(개인 토큰, 평소 미사용).
- 스테이징(arm64)과 운영(amd64)의 바이너리 차이는 남는다. 이미지 스모크와 배포 후 health로 잡는다.
- `authorized_keys`의 `command=` 제한으로는 `deploy.sh`의 인자(태그)를 공격자가 고를 수 있다. 스크립트가 `-verified` 태그만 받으므로 과거 검증 태그로의 되돌림까지가 상한이다.

## 승인 기록

| 항목 | 내용 |
|---|---|
| 결과 | 대기 |
| 결정자 | `사용자` |
| 결정 일시 | — |
| 근거 | — |
| 유효 기준선 | — |
| 후속 상태 변경 | — |

## 변경 이력

| 날짜 | 변경 | 근거 | 상태 또는 기준선 | 작성자·승인자 |
|---|---|---|---|---|
| 2026-10-17 | 최초 작성 — ADR-015 결정을 DES-25·전환 절차에 반영, ADR-013 결정 3 대체 | 사용자 결정 5건(2026-10-17), ADR-015 | → awaiting-approval | Claude / 승인자 미정 |
