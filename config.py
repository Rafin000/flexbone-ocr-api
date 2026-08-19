"""Central configuration.

A single `config.py` exposing a `Config` class, every value overridable from
the environment so nothing is hard-coded across the app.
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # --- Upload limits ---
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024

    # Core spec requires JPG; PNG and GIF are supported too (bonus: multi-format).
    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/gif"}
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

    # --- Optional API-key auth (public by default; the challenge uses plain curl) ---
    API_KEY = os.getenv("API_KEY", "")

    # --- Rate limiting (bonus) — per client IP ---
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT = os.getenv("RATE_LIMIT", "60 per minute")

    # --- In-memory cache for identical images (bonus) ---
    CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    CACHE_MAX_ENTRIES = int(os.getenv("CACHE_MAX_ENTRIES", "128"))

    # --- Batch endpoint (bonus) ---
    MAX_BATCH_FILES = int(os.getenv("MAX_BATCH_FILES", "10"))

    # --- Server ---
    PORT = int(os.getenv("PORT", "8080"))
    GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
