# ============================================================================
# Multi-stage Dockerfile for Arash External API Service v1.1
# Optimized for production deployment with uv dependency management
# ============================================================================
# Architecture: Single container running both FastAPI service + Telegram bot
# Base Image: Python 3.11 slim (Debian-based)
# Build System: uv for fast, reliable dependency management
# Security: Non-root user, minimal attack surface, health checks enabled
# ============================================================================

# ============================================================================
# Stage 1: Builder - Install dependencies with uv
# ============================================================================
FROM python:3.11-slim AS builder

# Build arguments for versioning and metadata
ARG VERSION=1.1.0
ARG BUILD_DATE
ARG VCS_REF

# Set working directory for build stage
WORKDIR /build

# Install system dependencies required for Python package compilation
# gcc: C compiler for Python packages with native extensions
# curl: Download uv installer
# libpq-dev: PostgreSQL client library headers (for psycopg2)
# postgresql-client: PostgreSQL command-line tools (for migrations)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv - ultra-fast Python package installer and resolver
# uv is 10-100x faster than pip and more reliable than Poetry
ENV UV_VERSION=0.8.17
RUN curl -LsSf https://astral.sh/uv/${UV_VERSION}/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files first (better layer caching)
# Docker will cache this layer unless pyproject.toml or uv.lock changes
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
# --frozen: Use exact versions from uv.lock (no resolution)
# --no-dev: Skip development dependencies (pytest, black, ruff, etc.)
# --no-editable: Install as regular packages, not editable
RUN uv sync --frozen --no-dev --no-editable

# ============================================================================
# Stage 2: Production - Minimal runtime image
# ============================================================================
FROM python:3.11-slim AS production

# Add metadata labels following OCI image spec
# Provides image provenance, version tracking, and documentation
LABEL maintainer="Arash Team <team@example.com>" \
      version="1.1.0" \
      description="Arash External API Service - Multi-platform AI chatbot with integrated Telegram bot" \
      org.opencontainers.image.title="Arash Bot" \
      org.opencontainers.image.description="Multi-platform AI chatbot with team-based access control" \
      org.opencontainers.image.version="1.1.0" \
      org.opencontainers.image.vendor="Arash Team"

# Set environment variables for Python runtime optimization
# PYTHONUNBUFFERED: Enable real-time logging (critical for Docker logs)
# PYTHONDONTWRITEBYTECODE: Prevent .pyc file creation (reduces image size)
# DEBIAN_FRONTEND: Non-interactive apt-get (avoids prompts during build)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies (smaller than build dependencies)
# libpq-dev: Required for psycopg2 runtime (PostgreSQL client)
# postgresql-client: Required for Alembic migrations
# curl: Required for health checks
# Note: gcc and build tools are NOT needed in production image
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security best practices
# Running as root inside containers is a security risk
# UID 1000 is conventional for first non-root user in Linux systems
# Create app directory structure with proper permissions
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
# Virtual environment contains all installed packages
# This approach is more efficient than copying system site-packages
COPY --from=builder /build/.venv /app/.venv

# Activate virtual environment by setting PATH and VIRTUAL_ENV
# All subsequent python/pip commands will use this virtual environment
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy application code with proper ownership
# --chown ensures files are owned by appuser from the start
# This eliminates the need for a separate chown command
COPY --chown=appuser:appuser . .

# Create logs directory with proper permissions for runtime logging
# Application writes logs to this directory at runtime
RUN mkdir -p logs && chown -R appuser:appuser logs

# Switch to non-root user
# All subsequent commands (including CMD) run as appuser
# This prevents privilege escalation attacks
USER appuser

# Expose port 3000 (application default)
# Must match the port configured in Kubernetes manifests
# Note: EXPOSE is documentation only, doesn't actually publish the port
EXPOSE 3000

# Health check for container orchestration (Kubernetes/Docker)
# Kubernetes uses this for liveness and readiness probes
# --interval: Check every 30 seconds
# --timeout: Kill check if it takes longer than 10 seconds
# --start-period: Grace period for application startup (40 seconds)
# --retries: Mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

# Default command to start the application
# Runs Uvicorn ASGI server with FastAPI application
# --host 0.0.0.0: Listen on all interfaces (required for Docker)
# --port 3000: Application port (must match EXPOSE and K8s config)
# --no-access-log: Disable access logs (reduces noise, use structured logging instead)
#
# Note: This command runs both the FastAPI service AND the integrated Telegram bot
# The bot runs in a background asyncio task when RUN_TELEGRAM_BOT=true
#
# Signal handling: Uvicorn handles SIGTERM gracefully for clean shutdowns
# Kubernetes sends SIGTERM during pod termination, giving 30s grace period
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000", "--no-access-log"]
