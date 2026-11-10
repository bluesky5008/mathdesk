#!/usr/bin/env bash
# ops/server-bootstrap.sh 검사 — 시스템 명령(apt·docker 설치·useradd·crontab·chown·swap)은 가짜로 바꾸고,
# 파일 배치(compose·ops 사본, authorized_keys 의 command= 제한, 권한, cron 한 줄)만 실제 파일로 확인한다.
#
#   ops/verify/server-bootstrap.test.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/bin" "$WORK/src/ops" "$WORK/home"
cp "$ROOT/compose.prod.yaml" "$WORK/src/"
cp "$ROOT/ops/deploy.sh" "$ROOT/ops/backup.sh" "$ROOT/ops/backup-cron.sh" "$WORK/src/ops/"
chmod -x "$WORK/src/ops/"*.sh      # scp 로 올리면 실행 비트가 없을 수 있다

# 가짜 시스템 명령: 호출만 기록한다
for cmd in timedatectl apt-get useradd usermod chown fallocate mkswap swapon id; do
  printf '#!/usr/bin/env bash\necho "%s $*" >> "$LOG"\n' "$cmd" > "$WORK/bin/$cmd"
done
printf '#!/usr/bin/env bash\necho "id $*" >> "$LOG"\nexit 1\n' > "$WORK/bin/id"   # deploy 계정 없음 → useradd 경로
printf '#!/usr/bin/env bash\necho "curl $*" >> "$LOG"\necho "echo fake-docker-installer"\n' > "$WORK/bin/curl"
printf '#!/usr/bin/env bash\necho "crontab $*" >> "$LOG"\ncat > "$CRON_OUT"\n' > "$WORK/bin/crontab"
printf '#!/usr/bin/env bash\necho "docker $*" >> "$LOG"\n' > "$WORK/bin/docker"
chmod +x "$WORK/bin/"*

export PATH="$WORK/bin:$PATH" LOG="$WORK/log" CRON_OUT="$WORK/cron"
export DEPLOY_HOME="$WORK/home/deploy" SRC_DIR="$WORK/src" BACKUP_ROOT="$WORK/var/backups/mathdesk" LOG_DIR="$WORK/var/log/mathdesk"
export SWAPFILE="$WORK/swapfile" FSTAB="$WORK/fstab" INSTALL_DOCKER=yes
printf '#!/usr/bin/env bash\necho "fallocate $*" >> "$LOG"\n: > "${@: -1}"\n' > "$WORK/bin/fallocate"   # 가짜 swap 파일을 만든다
: > "$LOG"

PUB="ssh-ed25519 AAAATESTKEY mathdesk-deploy-test"
bash "$ROOT/ops/server-bootstrap.sh" "$PUB" > "$WORK/out" 2>&1 || { echo "실패: 스크립트 종료 코드 $?"; cat "$WORK/out"; cat "$LOG"; exit 1; }

fail() { echo "실패: $*"; echo "--- out ---"; cat "$WORK/out"; echo "--- log ---"; cat "$LOG"; exit 1; }

# 1. 시스템 준비 호출 순서: 시간대 → apt → docker 설치 → swap → deploy 계정(docker 그룹)
grep -q '^timedatectl set-timezone Asia/Seoul' "$LOG" || fail "시간대"
grep -q '^apt-get .*upgrade' "$LOG" || fail "apt upgrade"
grep -q '^curl .*get.docker.com' "$LOG" || fail "docker 설치"
grep -q '^fallocate .*2G' "$LOG" && grep -q '^swapon' "$LOG" && grep -q "^$SWAPFILE none swap" "$FSTAB" || fail "swap 2G"
grep -q '^useradd .*-G docker.* deploy' "$LOG" || fail "deploy 계정"

# 2. 파일 배치: compose·ops 사본, 실행 비트, 소스 저장소 없음
[ -f "$DEPLOY_HOME/mathdesk/compose.prod.yaml" ] || fail "compose 사본"
[ -x "$DEPLOY_HOME/mathdesk/ops/deploy.sh" ] || fail "deploy.sh 실행 비트"
[ -x "$DEPLOY_HOME/mathdesk/ops/backup-cron.sh" ] || fail "backup-cron.sh 실행 비트"
[ ! -d "$DEPLOY_HOME/mathdesk/.git" ] || fail "저장소를 clone 하면 안 된다"
grep -q "^chown -R deploy:deploy $DEPLOY_HOME/mathdesk" "$LOG" || fail "소유자"

# 3. 배포 키: command= 로 deploy.sh 만, 터널·pty 금지. 두 번 돌려도 같은 키는 한 줄
AK="$DEPLOY_HOME/.ssh/authorized_keys"
[ -f "$AK" ] || fail "authorized_keys"
grep -q "^command=\"$DEPLOY_HOME/mathdesk/ops/deploy.sh\",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding $PUB\$" "$AK" || fail "command= 제한 줄"
[ "$(stat -f %Lp "$AK" 2>/dev/null || stat -c %a "$AK")" = 600 ] || fail "authorized_keys 권한"
[ "$(stat -f %Lp "$DEPLOY_HOME/.ssh" 2>/dev/null || stat -c %a "$DEPLOY_HOME/.ssh")" = 700 ] || fail ".ssh 권한"
bash "$ROOT/ops/server-bootstrap.sh" "$PUB" > /dev/null 2>&1 || fail "두 번째 실행"
[ "$(grep -c "$PUB" "$AK")" = 1 ] || fail "키 중복 등록"

# 4. 백업: 디렉터리와 cron 한 줄(04:00, deploy 계정)
[ -d "$BACKUP_ROOT" ] && [ -d "$LOG_DIR" ] || fail "백업·로그 디렉터리"
grep -q '^crontab -u deploy -' "$LOG" || fail "crontab -u deploy"
grep -q "^0 4 \* \* \* $DEPLOY_HOME/mathdesk/ops/backup-cron.sh\$" "$CRON_OUT" || fail "cron 줄"

# 5. 키 인자가 없으면 2 로 거절
if bash "$ROOT/ops/server-bootstrap.sh" > /dev/null 2>&1; then fail "키 없이 통과"; fi
bash "$ROOT/ops/server-bootstrap.sh" "" > /dev/null 2>&1 && fail "빈 키 통과" || [ $? = 2 ] || fail "빈 키 종료 코드"

echo "server-bootstrap.sh 검사 통과 (5건)"
