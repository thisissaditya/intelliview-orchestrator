FROM python:3.11-slim-bookworm
# =========================================================
# Stage 1: Builder
# =========================================================
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Build-time dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python environment
RUN python -m venv /opt/venv

# Copy dependency file first for better layer caching
COPY requirements.txt /app/requirements.txt

# Install CPU-only PyTorch
RUN pip install --no-cache-dir \
    torch \
    --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt


# =========================================================
# Stage 2: Runtime
# =========================================================
FROM python:3.11-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    procps \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system \
    --uid 1001 \
    --gid appgroup \
    --create-home \
    --home-dir /home/appuser \
    appuser

# Copy installed Python environment
COPY --from=builder /opt/venv /opt/venv

# Copy application
COPY . /app

# Create writable directories and set ownership
RUN mkdir -p \
    /app/data \
    /app/.cache \
    /app/logs \
    /app/tmp && \
    chown -R appuser:appgroup /app /opt/venv

# Run as non-root
USER appuser

EXPOSE 8000

# FastAPI healthcheck
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=40s \
    --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# Default application
# docker-compose overrides this for worker/flower/etc.
CMD ["uvicorn", "orchestrator.main:app", "--host", "0.0.0.0", "--port", "8000"]