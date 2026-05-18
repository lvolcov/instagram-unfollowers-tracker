# ============================================================================
# Stage 1: Build the React frontend
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ ./
RUN npm run build
# Output: /build/dist

# ============================================================================
# Stage 2: Python backend with Playwright + Chromium pre-installed
# ============================================================================
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy AS backend

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC

WORKDIR /app

# Install system deps for noVNC + websockify + supervisord.
# noVNC lets users access the Playwright browser through the web dashboard
# for the initial Instagram login flow (handles 2FA, security challenges).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    supervisor \
    x11vnc \
    xvfb \
    novnc \
    websockify \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source
COPY backend/ ./backend/

# Frontend built artifacts → served as static files by FastAPI
COPY --from=frontend-builder /build/dist ./frontend_dist/

# Supervisor config to run uvicorn + Xvfb + x11vnc + websockify together
COPY docker/supervisord.conf /etc/supervisor/conf.d/instagram-tracker.conf

# Data dir for SQLite + IG sessions (mounted as volume in compose)
RUN mkdir -p /app/data/sessions

EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
