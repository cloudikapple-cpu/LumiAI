# =============================================================================
# LumiAI Bot - Production Dockerfile
# =============================================================================
# Multi-stage build for smaller production image
# =============================================================================

FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# =============================================================================
# Production stage
# =============================================================================
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash app

WORKDIR /home/app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=app:app app/ ./app/

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/home/app

# Switch to non-root user
USER app

# Expose port for FastAPI
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8443/api/v1/health/live').raise_for_status()" || exit 1

# Default: run bot + API together
# For Railway, override with: python -m app.main --mode bot
CMD ["python", "-m", "app.main", "--mode", "all"]