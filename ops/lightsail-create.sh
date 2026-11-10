#!/usr/bin/env bash
# 클라이언트 AWS 계정에 mathdesk 운영 서버(Lightsail)를 만든다(ADR-013, ops/README 운영 1절 앞 단계).
# 다시 실행해도 안전하다 — 이미 있는 키·인스턴스·고정 IP 는 건너뛰고 방화벽·스냅샷만 다시 맞춘다.
#
#   AWS_PROFILE=bam ops/lightsail-create.sh bam         # bam | pingsu
#
# 하는 일: 사용자 SSH 공개키 등록(PUBKEY, 기본 ~/.ssh/id_ed25519.pub) → 서울(ap-northeast-2a) Ubuntu 24.04 2GB(small_3_0)
#          인스턴스 → running 대기 → 고정 IP 할당·연결 → 방화벽 22/tcp 만 → 자동 스냅샷(18:00 UTC = 03:00 KST)
#          → GitHub 환경 변수에 넣을 DEPLOY_HOST·DEPLOY_HOST_KEY 출력.
# 자격: IAM 사용자 yongs(정책 lightsail:*)의 액세스 키를 AWS_PROFILE 로. 키는 저장소에 두지 않는다.
# 검사: ops/verify/lightsail-create.test.sh
set -euo pipefail

CLIENT="${1:-}"
if [ -z "$CLIENT" ]; then
  echo "사용법: lightsail-create.sh <클라이언트 이름 (bam|pingsu)>" >&2
  exit 2
fi

NAME="mathdesk-$CLIENT"
IP_NAME="$NAME-ip"
REGION="${REGION:-ap-northeast-2}"
AZ="${AZ:-${REGION}a}"
BLUEPRINT="${BLUEPRINT:-ubuntu_24_04}"
BUNDLE="${BUNDLE:-small_3_0}"            # 2GB·2vCPU·60GB, $12
KEY_NAME="${KEY_NAME:-yongs-macmini}"
PUBKEY="${PUBKEY:-$HOME/.ssh/id_ed25519.pub}"
INSTANCE_WAIT="${INSTANCE_WAIT:-5}"
ls_() { aws lightsail "$@" --region "$REGION"; }

echo "== 사용자 SSH 키 $KEY_NAME"
if ! ls_ get-key-pair --key-pair-name "$KEY_NAME" > /dev/null 2>&1; then
  ls_ import-key-pair --key-pair-name "$KEY_NAME" --public-key-base64 "$(base64 < "$PUBKEY" | tr -d '\n')" > /dev/null
  echo "등록함: $PUBKEY"
fi

echo "== 인스턴스 $NAME ($AZ, $BLUEPRINT, $BUNDLE)"
if ! ls_ get-instance --instance-name "$NAME" --query 'instance.state.name' --output text > /dev/null 2>&1; then
  ls_ create-instances --instance-names "$NAME" --availability-zone "$AZ" \
    --blueprint-id "$BLUEPRINT" --bundle-id "$BUNDLE" --key-pair-name "$KEY_NAME" > /dev/null
  echo "생성 요청함"
fi
for _ in $(seq 1 60); do
  STATE="$(ls_ get-instance --instance-name "$NAME" --query 'instance.state.name' --output text 2>/dev/null || echo pending)"
  [ "$STATE" = running ] && break
  sleep "$INSTANCE_WAIT"
done
[ "$STATE" = running ] || { echo "인스턴스가 running 이 되지 않았습니다: $STATE" >&2; exit 3; }

echo "== 고정 IP $IP_NAME"
if ! INFO="$(ls_ get-static-ip --static-ip-name "$IP_NAME" --query 'staticIp.[ipAddress,isAttached]' --output text 2>/dev/null)"; then
  ls_ allocate-static-ip --static-ip-name "$IP_NAME" > /dev/null
  INFO="$(ls_ get-static-ip --static-ip-name "$IP_NAME" --query 'staticIp.[ipAddress,isAttached]' --output text)"
fi
IP="$(echo "$INFO" | awk '{print $1}')"
ATTACHED="$(echo "$INFO" | awk '{print $2}')"
if [ "$ATTACHED" != True ]; then
  ls_ attach-static-ip --static-ip-name "$IP_NAME" --instance-name "$NAME" > /dev/null
fi

echo "== 방화벽: 22/tcp 만 (Cloudflare 터널이 밖으로 나가므로 80·443 불필요)"
ls_ put-instance-public-ports --instance-name "$NAME" --port-infos fromPort=22,toPort=22,protocol=tcp > /dev/null

echo "== 자동 스냅샷 (매일 18:00 UTC, 7일 보관)"
ls_ enable-add-on --resource-name "$NAME" \
  --add-on-request "addOnType=AutoSnapshot,autoSnapshotAddOnRequest={snapshotTimeOfDay=18:00}" > /dev/null

echo "== 호스트 키"
HOSTKEY=""
for _ in $(seq 1 30); do
  HOSTKEY="$(ssh-keyscan -t ed25519 "$IP" 2>/dev/null | grep -v '^#' | head -1 || true)"
  [ -n "$HOSTKEY" ] && break
  sleep "$INSTANCE_WAIT"
done

cat <<EOT

서버 준비됨: $NAME
  접속:            ssh ubuntu@$IP
  GitHub 환경 변수: DEPLOY_HOST=$IP
                   DEPLOY_HOST_KEY=${HOSTKEY:-(ssh-keyscan 실패 — 잠시 뒤 ssh-keyscan -t ed25519 $IP)}
  알리고 발송 서버 IP 로 등록할 값: $IP
다음: scp compose.prod.yaml ubuntu@$IP:/tmp/ && scp -r ops ubuntu@$IP:/tmp/ → ssh ubuntu@$IP "sudo bash /tmp/ops/server-bootstrap.sh '<배포 공개키>'"
EOT
