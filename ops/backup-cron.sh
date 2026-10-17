#!/usr/bin/env bash
# 운영 서버 일일 백업(DES-25, NFR-11). deploy 계정의 cron 에 건다:
#   0 4 * * * /home/deploy/mathdesk/ops/backup-cron.sh
# /var/backups/mathdesk/<일시>/ 에 남기고 14일 지난 폴더를 지운다. 결과는 로그 파일에 쌓인다.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="${BACKUP_ROOT:-/var/backups/mathdesk}"
LOG="${BACKUP_LOG:-/var/log/mathdesk/backup.log}"
mkdir -p "$ROOT" "$(dirname "$LOG")"
{
  echo "== $(date '+%F %T') 시작"
  if out=$(PROJECT=mathdesk MATHDESK_COMPOSE=compose.prod.yaml ops/backup.sh "$ROOT"); then
    echo "백업: $out"
    find "$ROOT" -mindepth 1 -maxdepth 1 -type d -mtime +14 -print -exec rm -rf {} + | sed 's/^/삭제: /'
    echo "== 완료"
  else
    echo "== 실패(종료 코드 $?)"
  fi
} >> "$LOG" 2>&1
