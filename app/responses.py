"""Consistent JSON response builders.

The /extract-text success body keeps the exact fields required by the
challenge (success, text, confidence, processing_time_ms) and adds optional
bonus fields (metadata, cached).
"""


def ocr_response(
    text: str,
    confidence: float,
    processing_time_ms: int,
    metadata: dict | None = None,
    cached: bool = False,
):
    message = "Text extracted successfully." if text else "No text found in image."
    body = {
        "success": True,
        "text": text,
        "confidence": confidence,
        "processing_time_ms": processing_time_ms,
        "message": message,
        "cached": cached,
    }
    if metadata is not None:
        body["metadata"] = metadata
    return body, 200


def batch_response(results: list[dict], processing_time_ms: int):
    return {
        "success": True,
        "count": len(results),
        "processing_time_ms": processing_time_ms,
        "results": results,
    }, 200


def error_response(status_code: int, message: str):
    return {"success": False, "error": message}, status_code
