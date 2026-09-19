FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000 \
    BGUTIL_POT_PROVIDER_URL=http://127.0.0.1:4416

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    ffmpeg \
    git \
    curl \
    ca-certificates \
    unzip \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# JavaScript runtime required by modern yt-dlp
RUN curl -fsSL https://deno.land/install.sh | sh \
    && ln -sf /root/.deno/bin/deno /usr/local/bin/deno

# BgUtils PO-token provider
RUN git clone --depth 1 --branch 1.3.2 \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil \
    && cd /opt/bgutil/server \
    && npm ci \
    && npx tsc

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r /app/requirements.txt

# PRIME x BEATS package
RUN mkdir -p /app/primebeats
COPY *.py /app/primebeats/
COPY assets /app/primebeats/assets
RUN touch /app/primebeats/__init__.py

# Verify code AND media assets are present in the image.
RUN test -f /app/primebeats/app.py \
    && test -f /app/primebeats/youtube.py \
    && test -f /app/primebeats/assets/fearless_ping.jpg \
    && test -f /app/primebeats/assets/fearless_start.jpg \
    && test -f /app/primebeats/assets/fearless_start.mp4 \
    && test -f /app/primebeats/assets/fearless_help.png \
    && test -f /app/primebeats/assets/fearless_daddy.jpg \
    && python -m py_compile /app/primebeats/*.py

EXPOSE 10000

CMD ["sh", "-c", "set -eu; cd /opt/bgutil/server; node build/main.js > /tmp/bgutil.log 2>&1 & BGUTIL_PID=$!; trap 'kill $BGUTIL_PID 2>/dev/null || true' EXIT TERM INT; echo '[startup] BgUtils starting...'; ready=0; for i in $(seq 1 60); do if curl -fsS http://127.0.0.1:4416/ping >/dev/null 2>&1; then ready=1; echo '[startup] BgUtils READY'; break; fi; sleep 1; done; if [ \"$ready\" -ne 1 ]; then echo '[startup] ERROR: BgUtils did not start'; cat /tmp/bgutil.log || true; exit 1; fi; echo '[startup] Starting PRIME x BEATS...'; exec python -m primebeats.app"]
