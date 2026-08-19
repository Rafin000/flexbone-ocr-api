"""HTTP routes for the OCR service.

Views stay thin: validate the upload, delegate OCR to the service layer, and
return a consistent envelope. Cross-cutting concerns live in decorators.
"""
import time

from flask import request

from app import app
from app.decorators import handle_errors, require_api_key
from app.ocr_service import OcrError, ocr_service
from app.responses import error_response, ocr_response

UPLOAD_FIELD = "image"  # matches the challenge's test: -F "image=@test.jpg"


@app.route("/", methods=["GET"])
def index():
    """Friendly landing page describing how to use the API."""
    return {
        "service": "Flexbone OCR API",
        "status": "ok",
        "endpoint": "POST /extract-text",
        "usage": f'curl -X POST -F "{UPLOAD_FIELD}=@test.jpg" <url>/extract-text',
    }


@app.route("/alive", methods=["GET"])
def alive():
    """Liveness/health check."""
    return {"status": "alive"}


@app.route("/extract-text", methods=["POST"])
@handle_errors
@require_api_key
def extract_text():
    """Accept a JPG upload and return the OCR-extracted text.

    Response: { success, text, confidence, processing_time_ms }
    """
    started = time.perf_counter()

    # --- File presence ---
    if UPLOAD_FIELD not in request.files:
        return error_response(
            400, f"No file provided. Upload a JPG in the '{UPLOAD_FIELD}' field."
        )

    file = request.files[UPLOAD_FIELD]
    if not file or file.filename == "":
        return error_response(400, "No file selected.")

    # --- Content type ---
    allowed_types = app.config["ALLOWED_CONTENT_TYPES"]
    if file.mimetype not in allowed_types:
        return error_response(
            415,
            f"Unsupported file type '{file.mimetype}'. "
            f"Allowed: {', '.join(sorted(allowed_types))}.",
        )

    # --- Extension (defence in depth against a spoofed content type) ---
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in app.config["ALLOWED_EXTENSIONS"]:
        return error_response(
            415, f"Unsupported file extension '.{ext}'. Allowed: JPG/JPEG."
        )

    # --- Read + non-empty check (hard size cap enforced by MAX_CONTENT_LENGTH) ---
    contents = file.read()
    if len(contents) == 0:
        return error_response(400, "Uploaded file is empty.")

    # --- OCR ---
    try:
        result = ocr_service.extract_text(contents)
    except OcrError as exc:
        return error_response(502, f"OCR provider error: {exc}")

    processing_time_ms = int((time.perf_counter() - started) * 1000)
    return ocr_response(result.text, result.confidence, processing_time_ms)


@app.errorhandler(413)
def too_large(_err):
    """Friendly message when Flask rejects an over-limit upload."""
    limit = app.config["MAX_FILE_SIZE_MB"]
    return error_response(413, f"File exceeds the {limit} MB size limit.")
