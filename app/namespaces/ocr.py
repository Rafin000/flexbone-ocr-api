"""OCR namespace: single (/extract-text) and batch (/extract-text/batch)."""
import logging
import time

from flask import current_app, request
from flask_restx import Namespace, Resource
from werkzeug.datastructures import FileStorage

from app.cache import ocr_cache
from app.decorators import handle_errors, require_api_key
from app.extensions import limiter
from app.ocr_service import OcrError, ocr_service
from app.responses import batch_response, error_response, ocr_response
from app.utils import clean_text, extract_metadata, image_hash

logger = logging.getLogger(__name__)

ocr_ns = Namespace("ocr", description="Text extraction from images", path="/")

SINGLE_FIELD = "image"   # matches the challenge test: -F "image=@test.jpg"
BATCH_FIELD = "images"

# Rate limit read dynamically from config so it stays configurable.
_rate_limit = lambda: current_app.config.get("RATE_LIMIT", "60 per minute")  # noqa: E731

# --- Swagger request docs ---
single_parser = ocr_ns.parser()
single_parser.add_argument(
    SINGLE_FIELD, location="files", type=FileStorage, required=True,
    help="Image file (JPG/PNG/GIF, max 10 MB)",
)
batch_parser = ocr_ns.parser()
batch_parser.add_argument(
    BATCH_FIELD, location="files", type=FileStorage, required=True,
    help="Image file. Send the 'images' field multiple times for a batch "
         "(e.g. curl -F images=@a.jpg -F images=@b.jpg).",
)


def _validate(file: FileStorage) -> str | None:
    """Return an error message if the file is invalid, else None."""
    if not file or file.filename == "":
        return "No file selected."
    allowed_types = current_app.config["ALLOWED_CONTENT_TYPES"]
    if file.mimetype not in allowed_types:
        return (
            f"Unsupported file type '{file.mimetype}'. "
            f"Allowed: {', '.join(sorted(allowed_types))}."
        )
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return f"Unsupported file extension '.{ext}'."
    return None


def _process(contents: bytes) -> dict:
    """Run OCR (with caching), returning the shaped payload fields."""
    use_cache = current_app.config.get("CACHE_ENABLED", True)
    key = image_hash(contents) if use_cache else None

    if key:
        cached = ocr_cache.get(key)
        if cached is not None:
            logger.info("Cache hit for image %s", key[:12])
            return {**cached, "cached": True}

    result = ocr_service.extract_text(contents)
    payload = {
        "text": clean_text(result.text),           # bonus: text preprocessing
        "confidence": result.confidence,            # bonus: confidence score
        "metadata": extract_metadata(contents),     # bonus: image metadata
    }
    if key:
        ocr_cache.set(key, payload)
    logger.info("OCR extracted %d chars (confidence %.3f)", len(payload["text"]), payload["confidence"])
    return {**payload, "cached": False}


@ocr_ns.route("/extract-text")
class ExtractText(Resource):
    decorators = [limiter.limit(_rate_limit)]

    @ocr_ns.expect(single_parser)
    @handle_errors
    @require_api_key
    def post(self):
        """Extract text from a single uploaded image.

        Returns: { success, text, confidence, processing_time_ms, metadata, cached }
        """
        started = time.perf_counter()

        if SINGLE_FIELD not in request.files:
            return error_response(
                400, f"No file provided. Upload an image in the '{SINGLE_FIELD}' field."
            )
        file = request.files[SINGLE_FIELD]

        err = _validate(file)
        if err:
            return error_response(415 if "Unsupported" in err else 400, err)

        contents = file.read()
        if len(contents) == 0:
            return error_response(400, "Uploaded file is empty.")

        try:
            data = _process(contents)
        except OcrError as exc:
            return error_response(502, f"OCR provider error: {exc}")

        elapsed = int((time.perf_counter() - started) * 1000)
        return ocr_response(
            data["text"], data["confidence"], elapsed,
            metadata=data.get("metadata"), cached=data["cached"],
        )


@ocr_ns.route("/extract-text/batch")
class ExtractTextBatch(Resource):
    decorators = [limiter.limit(_rate_limit)]

    @ocr_ns.expect(batch_parser)
    @handle_errors
    @require_api_key
    def post(self):
        """Batch OCR (bonus): extract text from multiple images in one call.

        Upload several files under the 'images' field. Each result includes
        its filename and either the extracted text or a per-file error.
        """
        started = time.perf_counter()

        files = request.files.getlist(BATCH_FIELD)
        if not files:
            return error_response(
                400, f"No files provided. Upload images in the '{BATCH_FIELD}' field."
            )

        max_files = current_app.config["MAX_BATCH_FILES"]
        if len(files) > max_files:
            return error_response(413, f"Too many files (max {max_files} per batch).")

        results: list[dict] = []
        for file in files:
            err = _validate(file)
            if err:
                results.append({"filename": file.filename, "success": False, "error": err})
                continue
            contents = file.read()
            if len(contents) == 0:
                results.append({"filename": file.filename, "success": False, "error": "Empty file."})
                continue
            try:
                data = _process(contents)
                results.append({
                    "filename": file.filename,
                    "success": True,
                    "text": data["text"],
                    "confidence": data["confidence"],
                    "metadata": data.get("metadata"),
                    "cached": data["cached"],
                })
            except OcrError as exc:
                results.append({"filename": file.filename, "success": False, "error": str(exc)})

        elapsed = int((time.perf_counter() - started) * 1000)
        return batch_response(results, elapsed)
