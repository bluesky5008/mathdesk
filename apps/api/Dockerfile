# 빌드 컨텍스트는 저장소 루트다(compose.yaml 참조).
# 디자인 토큰이 apps/web에 있고 카드 렌더러가 그 파일을 읽어야 하므로([DES-24] 단일 소스),
# apps/api만으로는 컨텍스트가 모자란다.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

# 리포트 카드의 한글 글리프. Chromium이 이 글꼴로 카드를 그린다
RUN apt-get update && apt-get install -y --no-install-recommends fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# 헤드리스 Chromium([ADR-011]). 스크린샷에는 headless shell만 있으면 되므로
# --only-shell로 전체 Chromium과 ffmpeg를 뺀다(이미지 1.03GB → 약 0.5GB)
RUN playwright install --with-deps --only-shell chromium && rm -rf /var/lib/apt/lists/*

# 웹과 같은 토큰 파일. 값을 베껴 오지 않고 파일 자체를 복사한다
COPY apps/web/src/styles/tokens.css ./web/tokens.css

EXPOSE 8000
CMD ["uvicorn", "mathdesk.main:app", "--host", "0.0.0.0", "--port", "8000"]
