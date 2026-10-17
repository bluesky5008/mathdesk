# ops — 테스트 운영(Phase A′)과 운영(Phase B)

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

## 운영 — 클라이언트별 서버 (Phase B)

근거는 [ADR-013](../docs/work/20260922-mathdesk-baseline/ADR-013-운영-배포처-클라이언트별-Lightsail-단일-서버.md)(서버)과 [ADR-015](../docs/work/20260922-mathdesk-baseline/ADR-015-배포-파이프라인.md)(파이프라인), 설계는 [DES-25 상세](../docs/design.md#des-25-상세)다. 클라이언트(밤·핑수)마다 같은 절차를 반복한다.

| 구성 | 내용 |
|---|---|
| 서버 | 클라이언트 AWS 계정의 Lightsail 서울 2GB, Ubuntu LTS, 고정 IP, 방화벽 SSH만 |
| 스택 | [`compose.prod.yaml`](../compose.prod.yaml) — `postgres`·`app`(GHCR 이미지, 빌드 없음)·`cloudflared`(토큰 터널) |
| 이미지 | `ghcr.io/bluesky5008/mathdesk:<태그>` — [`release.yml`](../.github/workflows/release.yml)이 태그마다 게시·스모크 후 `<태그>-verified` |
| 반영 | [`deploy.yml`](../.github/workflows/deploy.yml)(`workflow_dispatch`) → 환경 승인 → SSH → 서버 [`ops/deploy.sh`](deploy.sh) |
| 서버에 두는 것 | `~/mathdesk/{compose.prod.yaml,.env,ops/}` 사본뿐. 소스 저장소는 clone하지 않는다 |

### 1. 서버 준비 (서버마다 1회, 사용자 SSH 키로)

```bash
# Ubuntu 24.04 (Lightsail 기본 ubuntu 계정)
sudo timedatectl set-timezone Asia/Seoul
sudo apt update && sudo apt -y upgrade
curl -fsSL https://get.docker.com | sudo sh

# 배포 전용 계정. docker 그룹이면 sudo 없이 compose 를 돌린다
sudo useradd -m -s /bin/bash -G docker deploy
sudo install -d -o deploy -g deploy -m 700 /var/backups/mathdesk /var/log/mathdesk
sudo -u deploy mkdir -p /home/deploy/mathdesk/ops

# 저장소에서 compose·ops 만 복사(소스 없음). 갱신도 이 방법으로만 한다 — 배포 키로는 불가
scp compose.prod.yaml ubuntu@<서버>:/tmp/ && scp -r ops ubuntu@<서버>:/tmp/
ssh ubuntu@<서버> 'sudo cp /tmp/compose.prod.yaml /home/deploy/mathdesk/ && sudo cp -r /tmp/ops/. /home/deploy/mathdesk/ops/ && sudo chown -R deploy:deploy /home/deploy/mathdesk && sudo chmod +x /home/deploy/mathdesk/ops/*.sh'

# .env: 서버에서 직접 채운다(.env.example 의 운영 절). 비밀번호는 openssl rand -base64 24
ssh ubuntu@<서버> 'sudo -u deploy install -m 600 /dev/null /home/deploy/mathdesk/.env && sudo -u deploy nano /home/deploy/mathdesk/.env'

# 배포 키: 환경마다 새로 만든다. 공개키는 command= 로 deploy.sh 만 실행되게 묶는다
ssh-keygen -t ed25519 -N '' -C mathdesk-deploy-<클라이언트> -f ~/.ssh/mathdesk-deploy-<클라이언트>
PUB=$(cat ~/.ssh/mathdesk-deploy-<클라이언트>.pub)
ssh ubuntu@<서버> "sudo -u deploy install -d -m 700 /home/deploy/.ssh && echo 'command=\"/home/deploy/mathdesk/ops/deploy.sh\",no-pty,no-port-forwarding,no-agent-forwarding,no-X11-forwarding $PUB' | sudo -u deploy tee -a /home/deploy/.ssh/authorized_keys > /dev/null && sudo chmod 600 /home/deploy/.ssh/authorized_keys"

# 일일 백업 cron(매일 04:00, 14일 보관, 로그 /var/log/mathdesk/backup.log)
ssh ubuntu@<서버> 'echo "0 4 * * * /home/deploy/mathdesk/ops/backup-cron.sh" | sudo -u deploy crontab -'

# 첫 기동: 태그를 손으로 넣고 deploy.sh 로 올린다(DB 가 없으면 백업은 건너뛴다)
ssh ubuntu@<서버> 'sudo -u deploy bash -lc "cd ~/mathdesk && ops/deploy.sh 2026.10.17"'
```

### 2. GitHub 환경 (클라이언트마다 1회)

저장소 Settings → Environments → `bam`(또는 `pingsu`) 생성:

- **Deployment protection rules → Required reviewers**: 사용자 본인.
- **Environment secrets**: `DEPLOY_SSH_KEY` = `~/.ssh/mathdesk-deploy-<클라이언트>` 파일 내용(개인키).
- **Environment variables**: `DEPLOY_HOST` = 고정 IP, `DEPLOY_HOST_KEY` = `ssh-keyscan -t ed25519 <고정 IP>` 출력 한 줄.

### 3. 릴리스 (스테이징에서 확인한 커밋에)

```bash
git tag 2026.10.17 && git push origin 2026.10.17      # 같은 날 두 번째는 2026.10.17-2
gh run watch                                          # release: build → smoke → <태그>-verified
```

### 4. 배포 (사용자 명령일 때만)

```bash
gh workflow run deploy.yml -f target=bam -f tag=2026.10.17      # bam | pingsu | both
# Actions 화면에서 환경 승인 → 잡 로그에 백업 경로·배포 완료·이미지 태그가 남는다
```

두 서버는 같은 태그를 쓴다. 한쪽에 먼저 올려 하루 두고 보는 것은 허용.

### 5. 롤백 · 복원 · 회수

- **롤백**: 같은 명령을 이전 태그로. `deploy.sh` 가 헬스 실패 때 이전 태그를 출력한다. 되돌릴 수 없는 마이그레이션이 든 릴리스는 태그 메모에 적고, 그때는 배포 전 백업 복원으로 되돌린다.
- **복원**: 서버에서 `PROJECT=mathdesk MATHDESK_COMPOSE=compose.prod.yaml ops/restore.sh /var/backups/mathdesk/<일시>` (RESTORE 입력 확인).
- **배포 경로 회수**(클라이언트가 직접 가능): 서버에서 `/home/deploy/.ssh/authorized_keys` 의 해당 줄 삭제. GitHub 쪽은 환경 비밀값 삭제.
- **개발자 접근 전체 회수**: IAM 사용자 비활성화 + `ubuntu` 계정 SSH 키 교체(ADR-013 결정 6).

### 키가 새면 무엇이 가능한가

배포 키는 `command=` 제한으로 `deploy.sh` 만 실행되고, `deploy.sh` 는 GHCR 에 `-verified` 꼬리표가 있는 태그만 받는다. 따라서 상한은 "검증된 과거 태그 재배포·백업 실행"이며 셸·데이터 접근은 안 된다. 워크플로는 서드파티 액션을 쓰지 않고 GitHub 소유 액션을 SHA 로 고정한다(ADR-015 결정 10).

## 문자·알림톡 실발송

준비 서류와 절차, 서버 설정은 [messaging-setup.md](messaging-setup.md)에 있다. 기본은 테스트 모드다.

## 알려진 제약

- 접근 통제는 앱 로그인뿐이고, 현재 자격 증명은 `director`/`director`다. **가안 단계의 의도된 선택이며 실제 데이터를 넣기 전에 반드시 교체한다.** 더 강한 통제가 필요하면 터널 앞단에 Cloudflare Access를 둔다.
- 저장소 루트의 `.env`는 테스트 운영 전용이다. 개발용 `compose.yaml`은 DB 비밀번호를 고정값으로 두어 두 스택이 섞이지 않게 했다.
