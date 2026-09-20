FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY renderer_service.py /app/renderer_service.py
COPY fonts/ /usr/local/share/fonts/reels/
RUN fc-cache -f

ENV REELS_RENDER_HOST=0.0.0.0 \
    REELS_RENDER_PORT=8080 \
    REELS_JOBS_ROOT=/media/jobs \
    REELS_STATE_ROOT=/var/lib/reels-render/jobs

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"
ENTRYPOINT ["python", "/app/renderer_service.py"]
