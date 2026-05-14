# syntax=docker/dockerfile:1.7

# ---- Stage 1: build venv with locked deps -----------------------------------
FROM python:3.12-slim AS builder

# uv for fast deterministic installs from uv.lock
COPY --from=ghcr.io/astral-sh/uv:0.11.13 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Copy lockfile + project metadata first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Install runtime deps only (skip dev group)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source + install the project itself
COPY lib ./lib
COPY apps ./apps
RUN uv sync --frozen --no-dev


# ---- Stage 2: runtime --------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Non-root user
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# Copy the resolved venv + source from the builder
COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

# Lightweight healthcheck against the FastAPI /api/health endpoint
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request, sys; \
        urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2); \
        sys.exit(0)" || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
