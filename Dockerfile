# Production Dockerfile for CineVault.
#
# Build context: project root.
# Runtime:      python:3.11-slim (matches the project's tested interpreter).
# Final image runs gunicorn as an unprivileged user.

FROM python:3.11-slim AS base

# System deps. ffmpeg is required for thumbnail generation. We install it
# from Debian repos (not the bundled ./ffmpeg binary) to keep the image lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first to maximize layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==21.2.0

# Copy the app source.
COPY . .

# Ensure runtime dirs exist and are owned by the unprivileged user.
RUN mkdir -p thumbnails sessions \
    && useradd --create-home --shell /bin/bash cinevault \
    && chown -R cinevault:cinevault /app
USER cinevault

# The bundled ./ffmpeg is dev-only; the system ffmpeg is on $PATH.
ENV FFMPEG_PATH=/usr/bin/ffmpeg \
    PROXY_FIX_DEPTH=0

EXPOSE 55300

# 4 workers is a reasonable default for a 2-core box. Tune via env or by
# overriding the command.
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:55300", "--access-logfile", "-", "app:app"]
