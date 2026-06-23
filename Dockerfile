FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first (layer caching)
COPY pyproject.toml ./
COPY uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code and policies
COPY src/ ./src/
COPY policies/ ./policies/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Expose API port
EXPOSE 8000

# Run migrations + seed + start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python scripts/seed.py && uv run uvicorn fleetguard.main:app --host 0.0.0.0 --port 8000"]
