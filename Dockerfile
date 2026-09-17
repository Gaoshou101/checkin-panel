# Check-in Panel - Docker Edition
#
# Two stages: Node.js builds the SPA frontend, Python runs the headless server.

# ---------------------------------------------------------------------------
# Stage 1 — Frontend SPA (React + Tailwind + HeroUI)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS spa

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY frontend/ ./
RUN npm run build


# ---------------------------------------------------------------------------
# Stage 2 — Headless Backend (Python + Playwright / Pre-baked Chromium)
# ---------------------------------------------------------------------------
FROM python:3.14-slim

# System dependencies: tzdata for schedule window calculation, ca-certificates for TLS
RUN apt-get update \
	&& apt-get install -y --no-install-recommends tzdata ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements and Chromium OS runtime dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
	&& playwright install-deps chromium \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*

# Runtime defaults:
# - CLOAKBROWSER_CACHE_DIR points to /opt/cloakbrowser (baked in, volume-safe)
# - PANEL_PROMO=0 disables external promo polling by default
ENV CLOAKBROWSER_CACHE_DIR=/opt/cloakbrowser \
	CHECKIN_BROWSER_PROFILE_DIR=/app/.browser_profiles \
	PYTHONUNBUFFERED=1 \
	PANEL_HOST=0.0.0.0 \
	PANEL_PORT=8000 \
	PANEL_PROMO=0

# Pre-download Chromium into the image so the container is 100% self-contained
RUN mkdir -p /opt/cloakbrowser \
	&& python -c "from cloakbrowser import ensure_binary; ensure_binary()"

COPY panel/ ./panel/
COPY run.py pytest.ini CONTEXT.md ./
COPY --from=spa /build/dist ./frontend/dist

# Run as non-root user (uid 10001) for security
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin panel \
	&& mkdir -p /app/data /app/.browser_profiles \
	&& chown -R panel:panel /app /opt/cloakbrowser

USER panel

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
	CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"]

CMD ["python", "run.py"]
