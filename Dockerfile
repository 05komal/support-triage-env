# ─── Support Ticket Triage Environment ───────────────────────────────────────
# OpenEnv-compatible Docker image for Hugging Face Spaces
# Build: docker build -t support-triage-env -f server/Dockerfile .
# Run:   docker run -p 8000:8000 support-triage-env
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
RUN pip install --no-cache-dir "openenv-core[core]>=0.2.2" uvicorn

# Copy environment code
COPY . /app/env

# Make sure the env root is importable
ENV PYTHONPATH="/app/env:${PYTHONPATH}"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 8000"]
