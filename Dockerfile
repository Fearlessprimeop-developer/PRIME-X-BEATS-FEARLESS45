FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

COPY primebeats ./primebeats
COPY assets ./assets

RUN test -f /app/primebeats/__init__.py \
    && test -f /app/primebeats/app.py \
    && test -f /app/primebeats/youtube.py \
    && test -f /app/primebeats/ui.py \
    && python -m py_compile /app/primebeats/*.py \
    && python -c "import py_yt, yt_dlp; print('dependencies: OK'); print('yt-dlp:', yt_dlp.version.__version__)"

CMD ["python", "-m", "primebeats"]
