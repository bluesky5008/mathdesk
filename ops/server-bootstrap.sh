#!/usr/bin/env bash
# 빈 Lightsail 서버(Ubuntu 24.04)를 mathdesk 운영 서버로 준비한다(ops/README 운영 1절, ADR-013·ADR-015, DES-25).
# root 로 1회 실행한다. 다시 실행해도 안전하다(같은 키는 한 번만 등록).
#
#   맥에서:
#     scp compose.prod.yaml ubuntu@<IP>:/tmp/ && scp -r ops ubuntu@<IP>:/tmp/
#     ssh ubuntu@<IP> "sudo bash /tmp/ops/server-bootstrap.sh '$(cat ~/.ssh/mathdesk-deploy-<클라이언트>.pub)'"
#
# 하는 일: 시간대 → apt 갱신 → Docker → 스왑 2G → deploy 계정(docker 그룹) → ~/mathdesk/{compose.prod.yaml,ops/} 사본
#          → 배포 공개키를 command= 제한(deploy.sh 만)으로 등록 → 백업·로그 디렉터리 → 일일 백업 cron(04:00).
# 하지 않는 일: .env(비밀값) 작성, 첫 기동. 둘 다 README 1절의 다음 단계로 한다.
# 검사: ops/verify/server-bootstrap.test.sh
set -euo pipefail

PUB="${1:-}"
if [ -z "$PUB" ]; then
  echo "사용법: server-bootstrap.sh '<배포 공개키 한 줄>'" >&2
  exit 2
fi

DEPLOY_HOME="${DEPLOY_HOME:-/home/deploy}"
SRC_DIR="${SRC_DIR:-/tmp}"                       # scp 로 올린 compose.prod.yaml 과 ops/ 가 있는 곳
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/mathdesk}"
LOG_DIR="${LOG_DIR:-/var/log/mathdesk}"
SWAPFILE="${SWAPFILE:-/swapfile}"
FSTAB="${FSTAB:-/etc/fstab}"
APP_DIR="$DEPLOY_HOME/mathdesk"

echo "== 시스템"
timedatectl set-timezone Asia/Seoul
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get -y -q upgrade
if [ "${INSTALL_DOCKER:-auto}" = yes ] || ! command -v docker > /dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

# 스왑 2G: 2GB 서버에서 이미지 pull·마이그레이션 때 OOM 을 막는다
if [ ! -f "$SWAPFILE" ]; then
  fallocate -l 2G "$SWAPFILE"
  chmod 600 "$SWAPFILE"
  mkswap "$SWAPFILE"
  swapon "$SWAPFILE"
  echo "$SWAPFILE none swap sw 0 0" >> "$FSTAB"
fi

echo "== deploy 계정"
if ! id deploy > /dev/null 2>&1; then
  useradd -m -s /bin/bash -G docker -d "$DEPLOY_HOME" deploy
else
  usermod -aG docker deploy
fi

echo "== 앱 디렉터리 (compose·ops 사본, 소스 없음)"
mkdir -p "$APP_DIR/ops"
cp "$SRC_DIR/compose.prod.yaml" "$APP_DIR/compose.prod.yaml"
cp -R "$SRC_DIR/ops/." "$APP_DIR/ops/"
chmod +x "$APP_DIR"/ops/*.sh
chown -R deploy:deploy "$APP_DIR"

echo "== 배포 키 (deploy.sh 만 실행)"
mkdir -p "$DEPLOY_HOME/.ssh"
chmod 700 "$DEPLOY_HOME/.ssh"
AK="$DEPLOY_HOME/.ssh/authorized_keys"
touch "$AK"
chmod 600 "$AK"
LINE="command=\"$APP_DIR/ops/deploy.sh\",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding $PUB"
grep -qxF "$LINE" "$AK" || echo "$LINE" >> "$AK"
chown -R deploy:deploy "$DEPLOY_HOME/.ssh"

echo "== 백업 디렉터리와 cron"
mkdir -p "$BACKUP_ROOT" "$LOG_DIR"
chmod 700 "$BACKUP_ROOT" "$LOG_DIR"
chown deploy:deploy "$BACKUP_ROOT" "$LOG_DIR"
echo "0 4 * * * $APP_DIR/ops/backup-cron.sh" | crontab -u deploy -

echo "준비 완료. 다음: $APP_DIR/.env 작성(.env.example 운영 절) → sudo -u deploy bash -lc 'cd ~/mathdesk && ops/deploy.sh <태그>'"
