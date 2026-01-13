# ============================================================
# Dockerfile - Data Agent Container Configuration
# ============================================================
# Build:  docker build -t data-agent .
# Run:    docker run -p 8000:8000 --env-file .env data-agent
# ============================================================

# Base image: Python 3.11 slim
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ============================================================
# System Dependencies
# ============================================================
# - gcc: Required for compiling some Python packages
# - libpq-dev: PostgreSQL client library for psycopg
# - Chromium dependencies: Required for Playwright/Crawl4AI
# ============================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# Python Dependencies (cached layer)
# ============================================================
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# Install Playwright browsers
# ============================================================
RUN playwright install chromium

# ============================================================
# Copy application code
# ============================================================
COPY . .

# Create images directory for generated charts
RUN mkdir -p /app/images
ENV IMAGES_DIR=/app/images

# Expose port
EXPOSE 8000

# ============================================================
# Start Command: FastAPI + Chainlit (挂载模式)
# ============================================================
# FastAPI 作为底座，Chainlit 挂载到根路径
# - 聊天界面: /
# - API 文档: /api/docs
# - 健康检查: /api/health
# ============================================================
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
