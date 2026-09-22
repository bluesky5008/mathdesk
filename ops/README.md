# ops — 테스트 운영 (Phase A′)

`mathdesk.yongs-wiki.com`으로 접근하는 테스트 운영 스택. 근거는 [DCR-001](../docs/work/20260922-mathdesk-baseline/DCR-001-테스트-운영-환경-노출.md)과 [ADR-008](../docs/work/20260922-mathdesk-baseline/ADR-008-테스트-운영-노출-구성.md)이다.

| 구성 | 내용 |
|---|---|
| 프로젝트 | `mathdesk-testops` (로컬 개발용 `compose.yaml`과 분리) |
| 서비스 | `postgres` · `app`(웹 정적 빌드 + API 단일 오리진) · `cloudflared` |
| 외부 경로 | Cloudflare 터널 `mathdesk` (`4724c8d8-…`) → `http://app:8000` |
| 호스트 게시 포트 | 없음. 터널이 유일한 진입점이다(NFR-17) |
| 데이터 | 합성 시드만. 실제 학생·학부모 정보를 넣지 않는다 |

기존 `homewiki` 터널과 home-wiki 서비스는 이 스택과 무관하며 설정을 공유하지 않는다.

## 기동

사전 조건: `.env`에 `POSTGRES_PASSWORD`·`MATHDESK_INITIAL_ADMIN_ID`·`MATHDESK_INITIAL_ADMIN_PASSWORD` 기입([`.env.example`](../.env.example) 참조), `ops/cloudflared/config.yml`과 `credentials.json` 배치([`config.example.yml`](cloudflared/config.example.yml) 참조).

```bash
docker compose -f compose.testops.yaml up -d --build
docker compose -f compose.testops.yaml exec app python -m mathdesk.seed   # 최초 1회
```

마이그레이션은 `app` 컨테이너가 기동 시 `alembic upgrade head`로 적용한다.

## 터널 재생성

```bash
cloudflared tunnel create mathdesk
cp ~/.cloudflared/<TUNNEL_ID>.json ops/cloudflared/credentials.json
# config.yml의 tunnel 값을 <TUNNEL_ID>로 수정
cloudflared --config /tmp/empty.yml tunnel route dns --overwrite-dns mathdesk mathdesk.yongs-wiki.com
```

`--config`를 비워 두지 않으면 `~/.cloudflared/config.yml`의 `tunnel:` 값이 인자를 덮어써 **기존 homewiki 터널로 라우팅된다.** 실제로 한 번 발생했다.

## 상태 확인

```bash
docker compose -f compose.testops.yaml ps
docker compose -f compose.testops.yaml logs cloudflared | tail
curl https://mathdesk.yongs-wiki.com/api/health
```

## 롤백 / 배포처 이전

```bash
docker compose -f compose.testops.yaml down          # 컨테이너 중지(데이터 유지)
docker compose -f compose.testops.yaml down -v       # 데이터까지 제거
cloudflared tunnel delete mathdesk                   # 터널 제거
# Cloudflare 대시보드에서 mathdesk.yongs-wiki.com CNAME 삭제
```

세 가지를 제거하면 흔적이 남지 않는다. `yongs-wiki.com`은 어느 단계에서도 영향받지 않는다.

## 알려진 제약

- 재부팅 후 자동 기동은 Docker Desktop이 로그인 시 시작되어야 성립한다. 현재 `AutoStart`가 꺼져 있어 수동 기동이 필요하다. 설정에서 "Start Docker Desktop when you sign in"을 켜면 `restart: unless-stopped`가 나머지를 처리한다.
- 접근 통제는 앱 로그인뿐이다. 로그인 시도 제한(연속 10회 → 3분 잠금)이 적용되어 있으며, 더 강한 통제가 필요하면 터널 앞단에 Cloudflare Access를 둔다.
