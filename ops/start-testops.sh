#!/bin/sh
# 로그인 시 테스트 운영 스택을 올린다.
# Docker Desktop의 restart 정책만으로는 엔진 재시작 후 컨테이너가 복구되지 않아 launchd로 보완한다.
set -eu

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DOCKER=/usr/local/bin/docker

# Docker 엔진이 뜰 때까지 최대 5분 기다린다.
i=0
while ! "$DOCKER" info >/dev/null 2>&1; do
    i=$((i + 1))
    [ "$i" -gt 60 ] && echo "docker engine not ready after 5 minutes" >&2 && exit 1
    sleep 5
done

cd "$PROJECT_DIR"
exec "$DOCKER" compose -f compose.testops.yaml up -d
