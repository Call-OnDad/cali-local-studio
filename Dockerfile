FROM python:3.13-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/runtime OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
    HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY scripts/setup_assets.py ./scripts/setup_assets.py
RUN python scripts/setup_assets.py rhubarb \
    && useradd --uid 10001 --create-home studio \
    && mkdir -p /app/data /app/models \
    && chown -R studio:studio /app/data /app/models
COPY app.py renderer.py test_controls.py ./
COPY static/ ./static/
COPY runtime/ ./runtime/
COPY scripts/ ./scripts/
USER studio
ENV STUDIO_DATA=/app/data STUDIO_MODELS_DIR=/app/models
EXPOSE 8780
VOLUME ["/app/data", "/app/models"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s \
 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8780/health',timeout=3)" || exit 1
ENTRYPOINT ["sh", "scripts/entrypoint.sh"]
