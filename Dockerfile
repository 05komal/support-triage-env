FROM python:3.11-slim-bullseye

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "openenv-core[core]>=0.2.2" \
    "uvicorn>=0.24.0" \
    "fastapi>=0.100.0" \
    "pydantic>=2.0.0"

COPY . /app/env

ENV PYTHONPATH="/app/env:${PYTHONPATH}"

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:7860/health || exit 1

CMD ["sh", "-c", "cd /app/env && uvicorn server.app:app --host 0.0.0.0 --port 7860"]