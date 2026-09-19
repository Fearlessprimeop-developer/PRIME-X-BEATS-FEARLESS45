FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    git \
    curl \
    ca-certificates \
    && python -m pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Python source files live at the repository root.
RUN mkdir -p /app/primebeats/assets
COPY *.py /app/primebeats/

# Media files must be stored in: main/assets/
COPY assets /app/primebeats/assets

# Required media used by the bot.
# NOTE: fearless_start.jpg is intentionally NOT required because /start
# is a text welcome message followed by fearless_start.mp4.
RUN test -f /app/primebeats/app.py \
    && test -f /app/primebeats/youtube.py \
    && test -f /app/primebeats/assets/fearless_ping.jpg \
    && test -f /app/primebeats/assets/fearless_start.mp4 \
    && test -f /app/primebeats/assets/fearless_help.png \
    && test -f /app/primebeats/assets/fearless_daddy.jpg \
    && python -m py_compile /app/primebeats/*.py

RUN touch /app/primebeats/__init__.py

EXPOSE 10000

CMD ["python", "-m", "primebeats"]
