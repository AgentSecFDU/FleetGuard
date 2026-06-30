FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
COPY uv.lock* ./

RUN uv sync --frozen 2>/dev/null || uv sync

COPY src/ ./src/
COPY policies/ ./policies/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/seed.py ./scripts/

EXPOSE 8000

ENV PYTHONPATH=/app/src

CMD ["sh", "-c", "uv run alembic upgrade head 2>/dev/null; uv run python scripts/seed.py; uv run uvicorn afc.main:app --host 0.0.0.0 --port 8000"]
