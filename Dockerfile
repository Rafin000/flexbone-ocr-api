# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# System dependency for the Tesseract OCR provider (used when OCR_PROVIDER=tesseract).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code.
COPY config.py wsgi.py ./
COPY app ./app

# Run as a non-root user (security best practice / defense in depth).
RUN useradd --create-home --uid 1000 appuser
USER appuser

# Cloud Run injects PORT (defaults to 8080). Gunicorn binds to it.
ENV PORT=8080
EXPOSE 8080

# Production WSGI server. One worker with a few threads suits Cloud Run's
# per-container concurrency; the work is I/O-bound (calling the Vision API).
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 8 --timeout 120 wsgi:app"]
