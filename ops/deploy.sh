#!/usr/bin/env bash
# 운영 서버에서 릴리스 태그 하나를 반영한다(ADR-015 결정 3·8, DES-25 배포).
#
#   ops/deploy.sh 2026.10.17            # 서버에서 직접
#   ssh deploy@<서버> 2026.10.17        # GitHub Actions deploy.yml — authorized_keys 의 command= 로 이 스크립트만 실행된다
#
# 순서: 태그 형식 → GHCR 의 `<태그>-verified` 꼬리표(release.yml 스모크 통과) 확인 → DB 가 있으면 백업
#       → .env 의 MATHDESK_IMAGE_TAG 교체 → pull → up -d(기동 시 alembic upgrade head) → /api/health 확인.
# 실패하면 이전 태그로 되돌리는 명령을 출력한다. 종료 코드: 2 태그 형식, 3 미검증 태그, 4 헬스 실패.
# 검사: ops/verify/deploy-sh.test.sh
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${1:-${SSH_ORIGINAL_COMMAND:-}}"
if ! [[ "$TAG" =~ ^20[0-9]{2}\.[0-9]{2}\.[0-9]{2}(-[0-9]+)?$ ]]; then
  echo "태그 형식 오류: '$TAG' (예: 2026.10.17, 2026.10.17-2)" >&2
  exit 2
fi

IMAGE="${MATHDESK_IMAGE:-ghcr.io/bluesky5008/mathdesk}"
COMPOSE=(docker compose -f compose.prod.yaml)

if ! docker manifest inspect "$IMAGE:$TAG-verified" > /dev/null 2>&1; then
  echo "미검증 태그: $IMAGE:$TAG-verified 가 없습니다. release 워크플로의 스모크를 통과한 태그만 배포합니다." >&2
  exit 3
fi

PREV="$(grep -E '^MATHDESK_IMAGE_TAG=' .env 2>/dev/null | tail -1 | cut -d= -f2- || true)"
echo "배포 시작: $TAG (현재: ${PREV:-없음})"

# 배포 전 백업(DES-25). 첫 설치처럼 DB 컨테이너가 없으면 백업할 것이 없다
if [ -n "$("${COMPOSE[@]}" ps -q postgres 2>/dev/null)" ]; then
  PROJECT=mathdesk MATHDESK_COMPOSE=compose.prod.yaml ops/backup.sh "${BACKUP_ROOT:-/var/backups/mathdesk}"
else
  echo "DB 컨테이너가 없어 백업을 건너뜁니다(첫 설치)"
fi

# .env 의 태그 교체(권한 유지를 위해 덮어쓴다). macOS·GNU sed 차이를 피한다
{ grep -v -E '^MATHDESK_IMAGE_TAG=' .env 2>/dev/null || true; echo "MATHDESK_IMAGE_TAG=$TAG"; } > .env.tmp
cat .env.tmp > .env && rm -f .env.tmp

"${COMPOSE[@]}" pull app
"${COMPOSE[@]}" up -d

# 헬스: 앱 컨테이너 안에서 확인한다(호스트 포트를 게시하지 않으므로)
TRIES="${HEALTH_TRIES:-30}"
WAIT="${HEALTH_WAIT:-2}"
for _ in $(seq 1 "$TRIES"); do
  if "${COMPOSE[@]}" exec -T app python -c \
    "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=3).status == 200 else 1)" \
    > /dev/null 2>&1; then
    echo "배포 완료: $TAG (이전: ${PREV:-없음})"
    "${COMPOSE[@]}" images app 2>/dev/null || true
    exit 0
  fi
  sleep "$WAIT"
done

echo "헬스 실패: $TAG 가 ${TRIES}회 안에 응답하지 않았습니다. 로그: docker compose -f compose.prod.yaml logs app" >&2
if [ -n "$PREV" ]; then
  echo "되돌리기: ops/deploy.sh $PREV" >&2
fi
exit 4
