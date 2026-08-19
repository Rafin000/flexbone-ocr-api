"""OCR namespace: the /extract-text endpoint."""
import time

from flask import current_app, request
from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage

from app.decorators import handle_errors, require_api_key
from app.ocr_service import OcrError, ocr_service
from app.responses import error_response, ocr_response

ocr_ns = Namespace("ocr", description="Text extraction from images", path="/")

UPLOAD_FIELD = "image"  # matches the challenge test: -F "image=@test.jpg"

# Document the multipart upload so it shows up in the Swagger UI.
upload_parser = ocr_ns.parser()
upload_parser.add_argument(
    UPLOAD_FIELD,
    location="files",
    type=FileStorage,
    required=True,
    help="JPG image file (max 10 MB)",
)


@ocr_ns.route("/extract-text")
class ExtractText(Resource):
    @ocr_ns.expect(upload_parser)
    @handle_errors
    @require_api_key
    def post(self):
        """Extract text from an uploaded JPG.

        Returns: { success, text, confidence, processing_time_ms }
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
        allowed_types = current_app.config["ALLOWED_CONTENT_TYPES"]
        if file.mimetype not in allowed_types:
            return error_response(
                415,
                f"Unsupported file type '{file.mimetype}'. "
                f"Allowed: {', '.join(sorted(allowed_types))}.",
            )

        # --- Extension (defence in depth against a spoofed content type) ---
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
            return error_response(
                415, f"Unsupported file extension '.{ext}'. Allowed: JPG/JPEG."
            )

        # --- Read + non-empty check (hard cap enforced by MAX_CONTENT_LENGTH) ---
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
