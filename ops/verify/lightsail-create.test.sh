#!/usr/bin/env bash
# ops/lightsail-create.sh 검사 — aws CLI 와 ssh-keyscan 을 가짜로 바꿔 호출 순서·인자를 확인한다(네트워크 없음).
#
#   ops/verify/lightsail-create.test.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
echo "ssh-ed25519 AAAATEST yongs-test" > "$WORK/id.pub"

# 가짜 aws: 호출을 기록하고 조회 명령에는 시나리오 변수대로 답한다
cat > "$WORK/bin/aws" <<'EOS'
#!/usr/bin/env bash
echo "aws $*" >> "$LOG"
case "$*" in
  *"get-key-pair"*)   [ "${KEY_EXISTS:-0}" = 1 ] ;;
  *"get-instance "*)
    if [ "${INSTANCE_EXISTS:-0}" = 1 ]; then echo running; exit 0; fi
    n=$(cat "$POLL" 2>/dev/null || echo 0); echo $((n+1)) > "$POLL"
    [ "$n" -eq 0 ] && exit 1            # 첫 조회: 없음
    [ "$n" -ge 3 ] && echo running || echo pending ;;
  *"get-static-ip"*)  { [ "${IP_EXISTS:-0}" = 1 ] || [ -f "$POLL.ip" ]; } && echo "203.0.113.10	${IP_ATTACHED:-False}" ;;
  *"allocate-static-ip"*) touch "$POLL.ip" ;;
  *) exit 0 ;;
esac
EOS
printf '#!/usr/bin/env bash\necho "ssh-keyscan $*" >> "$LOG"\necho "203.0.113.10 ssh-ed25519 AAAAHOSTKEY"\n' > "$WORK/bin/ssh-keyscan"
chmod +x "$WORK/bin/"*
export PATH="$WORK/bin:$PATH" LOG="$WORK/log" POLL="$WORK/poll" PUBKEY="$WORK/id.pub" INSTANCE_WAIT=0

fail() { echo "실패: $*"; echo "--- out ---"; cat "$WORK/out"; echo "--- log ---"; cat "$LOG"; exit 1; }
run() { : > "$LOG"; rm -f "$POLL" "$POLL.ip"; (bash "$ROOT/ops/lightsail-create.sh" "$@" > "$WORK/out" 2>&1); }

# 1. 인자 없음 → 2
run || [ $? = 2 ] || fail "인자 없음 종료 코드"
grep -q '^aws' "$LOG" && fail "인자 없이 aws 호출"

# 2. 새 서버: 키 가져오기 → 서울 2GB Ubuntu 24.04 생성 → running 대기 → 고정 IP 할당·연결 → 방화벽 22만 → 자동 스냅샷 → 호스트 키
run bam || fail "정상 실행 종료 코드 $?"
grep -q '^aws lightsail import-key-pair --key-pair-name yongs-macmini --public-key-base64 ' "$LOG" || fail "키 가져오기"
grep -q '^aws lightsail create-instances --instance-names mathdesk-bam --availability-zone ap-northeast-2a --blueprint-id ubuntu_24_04 --bundle-id small_3_0 --key-pair-name yongs-macmini' "$LOG" || fail "인스턴스 생성"
[ "$(grep -c '^aws lightsail get-instance ' "$LOG")" -ge 3 ] || fail "running 대기 폴링"
grep -q '^aws lightsail allocate-static-ip --static-ip-name mathdesk-bam-ip' "$LOG" || fail "고정 IP 할당"
grep -q '^aws lightsail attach-static-ip --static-ip-name mathdesk-bam-ip --instance-name mathdesk-bam' "$LOG" || fail "고정 IP 연결"
grep -q '^aws lightsail put-instance-public-ports --instance-name mathdesk-bam --port-infos fromPort=22,toPort=22,protocol=tcp --region' "$LOG" || fail "방화벽 22만"
grep -q '^aws lightsail enable-add-on --resource-name mathdesk-bam --add-on-request addOnType=AutoSnapshot' "$LOG" || fail "자동 스냅샷"
grep -q '^ssh-keyscan -t ed25519 203.0.113.10' "$LOG" || fail "호스트 키"
grep -q 'DEPLOY_HOST=203.0.113.10' "$WORK/out" || fail "출력에 IP"
grep -q 'DEPLOY_HOST_KEY=203.0.113.10 ssh-ed25519 AAAAHOSTKEY' "$WORK/out" || fail "출력에 호스트 키"
grep -q -- '--region ap-northeast-2' "$LOG" || fail "서울 리전"
grep -q 'lightsail create-instances' "$LOG" && ! grep -q 'create-instances.*--user-data' "$LOG" || fail "user-data 없음"

# 3. 다시 실행: 이미 있는 키·인스턴스·연결된 IP 는 건너뛴다
KEY_EXISTS=1 INSTANCE_EXISTS=1 IP_EXISTS=1 IP_ATTACHED=True run bam || fail "재실행 종료 코드 $?"
grep -q 'import-key-pair\|create-instances\|allocate-static-ip\|attach-static-ip' "$LOG" && fail "재실행에서 생성 반복"
grep -q 'put-instance-public-ports' "$LOG" || fail "재실행에서도 방화벽 확인"

echo "lightsail-create.sh 검사 통과 (3건)"
