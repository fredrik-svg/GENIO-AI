# Dockerfile optimized for Raspberry Pi 5 (64-bit / arm64)
# Build on an image that supports multi-arch; the official python slim images are multi-arch.
FROM --platform=linux/arm64 python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# System deps for audio processing, espeak-ng, ffmpeg, and building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    espeak-ng \
    libasound2 \
    libasound2-dev \
    portaudio19-dev \
    libsndfile1 \
    git \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies (use the web-specific requirements)
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements-web.txt

# Expose the web UI port
EXPOSE 8080

# Create a non-root user (optional but recommended)
RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

# Entrypoint: run uvicorn to serve the web UI
CMD ["uvicorn", "webapp:app", "--host", "0.0.0.0", "--port", "8080"]
