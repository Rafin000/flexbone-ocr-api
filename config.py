"""Central configuration.

Follows the microservice convention of a single `config.py` exposing a
`Config` class, with every value overridable from the environment so nothing
is hard-coded across the app.
"""
import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    # --- Upload limits (challenge spec: JPG only, max 10 MB) ---
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024

    ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg"}
    ALLOWED_EXTENSIONS = {"jpg", "jpeg"}

    # Bonus: accept PNG too when explicitly enabled (off by default per spec).
    if os.getenv("ALLOW_PNG", "false").lower() == "true":
        ALLOWED_CONTENT_TYPES.add("image/png")
        ALLOWED_EXTENSIONS.add("png")

    # --- Optional API-key auth ---
    # The endpoint is public by default (the challenge is tested with a plain
    # curl). If API_KEY is set, the @require_api_key decorator enforces it —
    # the same header-token pattern used across our other microservices.
    API_KEY = os.getenv("API_KEY", "")

    # --- Server ---
    # Cloud Run injects PORT; default to 8080 for local runs.
    PORT = int(os.getenv("PORT", "8080"))
    GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
