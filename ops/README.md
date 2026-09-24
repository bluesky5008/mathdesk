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

## 자동 기동

Docker Desktop의 `AutoStart`를 켜고(로그인 시 Docker 시작), launchd 에이전트가 엔진이 준비되면 스택을 올린다.

```bash
cp ops/com.mathdesk.testops.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.mathdesk.testops.plist
launchctl list | grep mathdesk
```

해제는 `launchctl bootout gui/$(id -u)/com.mathdesk.testops`.

`restart: unless-stopped`만으로는 부족하다. 이 환경에서 Docker Desktop을 재시작하면 정책이 있어도 컨테이너가 복구되지 않는 것을 실측했다. 로그는 `~/Library/Logs/mathdesk/testops.log`.

## 백업·복원 (NFR-11)

```bash
ops/backup.sh                     # ~/mathdesk-backups/<시각>/{db.dump, files.tar.gz, SHA256SUMS}
ops/restore.sh <백업 폴더>          # 테스트 운영을 백업 시점으로 덮어쓴다(RESTORE 입력 확인)
```

- 백업은 DB 전체(`pg_dump -Fc`)와 업로드 파일(`files` 볼륨)을 한 번에 뜬다. 폴더 권한은 본인 전용(700)이다. 실제 학생 정보가 들어가면 백업도 개인정보다.
- 복원은 앱을 멈추고 DB를 `pg_restore --clean`으로, 업로드 파일을 볼륨 비우고 풀어 되살린 뒤 앱을 올린다. 체크섬이 맞지 않으면 시작하지 않는다.
- 다른 프로젝트로 복원해 확인하려면 `PROJECT=mathdesk-restorecheck YES=1 SKIP_APP=1 ops/restore.sh <폴더>` 후 `docker compose -p mathdesk-restorecheck -f compose.testops.yaml down -v`.
- 자동 주기 백업은 두지 않았다. 필요하면 launchd에 `ops/backup.sh`를 건다.

## 문자·알림톡 실발송

준비 서류와 절차, 서버 설정은 [messaging-setup.md](messaging-setup.md)에 있다. 기본은 테스트 모드다.

## 알려진 제약

- 접근 통제는 앱 로그인뿐이고, 현재 자격 증명은 `director`/`director`다. **가안 단계의 의도된 선택이며 실제 데이터를 넣기 전에 반드시 교체한다.** 더 강한 통제가 필요하면 터널 앞단에 Cloudflare Access를 둔다.
- 저장소 루트의 `.env`는 테스트 운영 전용이다. 개발용 `compose.yaml`은 DB 비밀번호를 고정값으로 두어 두 스택이 섞이지 않게 했다.
