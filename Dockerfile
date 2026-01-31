# =============================================================================
# Multi-stage Dockerfile for MSNA 2025 Analysis - Marimo Notebooks with Nginx
# Uses uv for fast dependency installation + nginx as reverse proxy
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with uv
# -----------------------------------------------------------------------------
FROM python:3.10-slim AS builder

WORKDIR /app

# Copy uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies including the project (non-editable for portability)
RUN uv sync --locked --no-dev --no-editable

# Copy the entire project after dependencies are installed
COPY . /app

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image with nginx
# -----------------------------------------------------------------------------
FROM python:3.10-slim

WORKDIR /app

# Install nginx and supervisor (to run multiple processes)
RUN apt-get update && \
    apt-get install -y nginx supervisor && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 msnauser && \
    chown -R msnauser:msnauser /app

# Copy virtual environment from builder
COPY --from=builder --chown=msnauser:msnauser /app/.venv /app/.venv

# Copy source code (required for notebooks imports)
COPY --chown=msnauser:msnauser src/ /app/src/

# Copy notebooks and data
COPY --chown=msnauser:msnauser notebooks/ /app/notebooks/
COPY --chown=msnauser:msnauser data/ /app/data/

# Copy landing page to nginx html directory
COPY --chown=root:root docs/index.html /usr/share/nginx/html/index.html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy startup script
COPY start-notebooks.sh /app/start-notebooks.sh
RUN chmod +x /app/start-notebooks.sh

# Create supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set Python path to use the virtual environment and add /app to PYTHONPATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

# Expose main port (nginx will handle routing)
EXPOSE 2718

# Run supervisor to manage nginx + both notebooks
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
