#!/usr/bin/env bash
# ops/backup.sh로 만든 백업을 되살린다. **대상의 DB와 업로드 파일을 백업 시점으로 덮어쓴다.**
#
#   ops/restore.sh <백업 폴더>                             # 테스트 운영에 복원(확인 질문)
#   PROJECT=mathdesk-restorecheck ops/restore.sh <폴더>    # 다른 compose 프로젝트에 복원
#
# 앱을 멈춘 채 복원하고 다시 올린다. 기동 시 alembic이 스키마를 최신으로 맞춘다.
set -euo pipefail

cd "$(dirname "$0")/.."
SOURCE="${1:?백업 폴더를 지정하세요}"
PROJECT="${PROJECT:-mathdesk-testops}"
COMPOSE=(docker compose -p "$PROJECT" -f compose.testops.yaml)

(cd "$SOURCE" && shasum -a 256 -c SHA256SUMS)

if [ "${YES:-}" != "1" ]; then
  read -r -p "$PROJECT 의 DB와 업로드 파일을 $SOURCE 시점으로 덮어씁니다. 계속하려면 RESTORE 입력: " answer
  [ "$answer" = "RESTORE" ] || { echo "취소했습니다."; exit 1; }
fi

"${COMPOSE[@]}" stop app 2>/dev/null || true
"${COMPOSE[@]}" up -d --wait postgres

# --clean --if-exists: 기존 객체를 지우고 백업 내용으로 다시 만든다
"${COMPOSE[@]}" exec -T postgres pg_restore -U mathdesk -d mathdesk --clean --if-exists --no-owner < "$SOURCE/db.dump"

docker run --rm -i -v "${PROJECT}_files:/data" postgres:17-alpine \
  sh -c 'find /data -mindepth 1 -delete && tar -C /data -xzf -' < "$SOURCE/files.tar.gz"

if [ "${SKIP_APP:-}" != "1" ]; then
  "${COMPOSE[@]}" up -d app
fi
echo "복원 완료: $PROJECT ← $SOURCE"
