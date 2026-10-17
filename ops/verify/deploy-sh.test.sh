#!/usr/bin/env bash
# ops/deploy.sh 의 게이트 로직 검사 — 태그 형식, `-verified` 꼬리표 확인, 백업 → pull → up → 헬스, 실패 시 이전 태그 안내.
# docker 와 ops/backup.sh 를 가짜로 바꿔 돌린다(네트워크·컨테이너 없음).
#
#   ops/verify/deploy-sh.test.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 저장소 사본: compose·ops 만 있는 운영 서버 모양
mkdir -p "$WORK/mathdesk/ops" "$WORK/bin"
cp "$ROOT/ops/deploy.sh" "$WORK/mathdesk/ops/deploy.sh"
cp "$ROOT/compose.prod.yaml" "$WORK/mathdesk/compose.prod.yaml"
printf 'POSTGRES_PASSWORD=x\nMATHDESK_IMAGE_TAG=2026.10.01\n' > "$WORK/mathdesk/.env"

# 가짜 backup.sh: 호출 사실만 남긴다
cat > "$WORK/mathdesk/ops/backup.sh" <<'EOF'
#!/usr/bin/env bash
echo "backup $PROJECT $MATHDESK_COMPOSE" >> "$LOG"
EOF
# 가짜 docker: 호출을 기록하고, 시나리오 변수대로 응답한다
cat > "$WORK/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "docker $*" >> "$LOG"
case "$*" in
  "manifest inspect "*-verified) [ "${VERIFIED:-1}" = 1 ] ;;
  *"ps -q postgres"*) [ "${DB_RUNNING:-1}" = 1 ] && echo cid || true ;;
  *"exec -T app python"*) [ "${HEALTHY:-1}" = 1 ] ;;
  *) exit 0 ;;
esac
EOF
chmod +x "$WORK/bin/docker" "$WORK/mathdesk/ops/backup.sh" "$WORK/mathdesk/ops/deploy.sh"
export PATH="$WORK/bin:$PATH" LOG="$WORK/log" HEALTH_TRIES=2 HEALTH_WAIT=0

fail() { echo "실패: $*"; echo "--- log ---"; cat "$LOG" 2>/dev/null || true; exit 1; }
run() { : > "$LOG"; (cd "$WORK/mathdesk" && ops/deploy.sh "$@" > "$WORK/out" 2>&1); }

# 1. 태그 형식이 틀리면 아무것도 하지 않고 2
run 'v1; rm -rf /' && fail "잘못된 태그를 받아들임"
[ $? -eq 2 ] || fail "태그 오류 코드"
[ ! -s "$LOG" ] || fail "태그 오류인데 docker 호출"

# 2. -verified 꼬리표가 없으면 3, 백업·pull 없음
VERIFIED=0 run 2026.10.17 && fail "미검증 태그를 받아들임"
[ $? -eq 3 ] || fail "미검증 오류 코드"
grep -q backup "$LOG" && fail "미검증인데 백업"

# 3. 정상: 백업 → .env 태그 교체 → pull → up -d → 헬스, 이전 태그 출력
run 2026.10.17 || fail "정상 배포가 실패"
grep -q "^backup mathdesk compose.prod.yaml" "$LOG" || fail "백업이 운영 프로필로 돌지 않음"
grep -q "MATHDESK_IMAGE_TAG=2026.10.17" "$WORK/mathdesk/.env" || fail ".env 태그 미교체"
grep -q "compose -f compose.prod.yaml pull" "$LOG" || fail "pull 없음"
grep -q "compose -f compose.prod.yaml up -d" "$LOG" || fail "up -d 없음"
grep -q "2026.10.01" "$WORK/out" || fail "이전 태그 안내 없음"
awk '/backup/{b=NR} /pull/{p=NR} END{exit !(b && p && b<p)}' "$LOG" || fail "백업이 pull 보다 뒤"

# 4. 첫 배포(DB 없음)는 백업을 건너뛰고 진행
DB_RUNNING=0 run 2026.10.18 || fail "첫 배포 실패"
grep -q backup "$LOG" && fail "DB 없는데 백업 시도"

# 5. 헬스 실패면 4, 이전 태그로 되돌리는 명령 안내
HEALTHY=0 run 2026.10.19 && fail "헬스 실패를 성공으로"
[ $? -eq 4 ] || fail "헬스 오류 코드"
grep -q "ops/deploy.sh 2026.10.18" "$WORK/out" || fail "되돌리기 명령 안내 없음"

# 6. SSH forced command: 인자 없이 SSH_ORIGINAL_COMMAND 로 태그를 받는다
: > "$LOG"; (cd "$WORK/mathdesk" && SSH_ORIGINAL_COMMAND=2026.10.20 ops/deploy.sh > "$WORK/out" 2>&1) || fail "SSH_ORIGINAL_COMMAND 경로 실패"
grep -q "MATHDESK_IMAGE_TAG=2026.10.20" "$WORK/mathdesk/.env" || fail "SSH 경로 태그 미교체"

echo "deploy.sh 검사 6건 통과"
