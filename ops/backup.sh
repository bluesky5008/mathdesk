#!/usr/bin/env bash
# NFR-11 — DB 전체 덤프와 업로드 파일을 한 번에 백업한다.
#
#   ops/backup.sh [백업 루트]          # 기본 ~/mathdesk-backups
#
# 결과: <백업 루트>/<YYYYmmdd-HHMMSS>/{db.dump, files.tar.gz, SHA256SUMS}
# 백업에는 학생·학부모 정보가 들어간다. 폴더를 본인만 읽을 수 있게 만든다(umask 077).
# 복원은 ops/restore.sh.
set -euo pipefail
umask 077

cd "$(dirname "$0")/.."
PROJECT="${PROJECT:-mathdesk-testops}"
COMPOSE=(docker compose -p "$PROJECT" -f compose.testops.yaml)
OUT="${1:-$HOME/mathdesk-backups}/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

# 사용자 정의 형식(-Fc): 압축되고 pg_restore로 골라 복원할 수 있다
"${COMPOSE[@]}" exec -T postgres pg_dump -U mathdesk -Fc mathdesk > "$OUT/db.dump"

# 업로드 파일은 DB가 아니라 files 볼륨에 있다(DES-10). 읽기 전용으로 붙여 묶는다
docker run --rm -v "${PROJECT}_files:/data:ro" postgres:17-alpine \
  tar -C /data -czf - . > "$OUT/files.tar.gz"

(cd "$OUT" && shasum -a 256 db.dump files.tar.gz > SHA256SUMS)
echo "$OUT"
