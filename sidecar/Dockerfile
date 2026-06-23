FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only sidecar + policies
COPY sidecar/ .
COPY policies/ ./policies/

# Install dependencies
RUN uv sync

# Default command
ENTRYPOINT ["uv", "run", "python", "-m", "fleetguard_sidecar.main"]
