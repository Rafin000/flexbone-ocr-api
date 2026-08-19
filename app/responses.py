"""Consistent JSON response builders.

Flask-RESTX serializes a returned ``(dict, status_code)`` tuple to JSON, so
these helpers just shape the payload. The /extract-text success body follows
the exact format required by the challenge.
"""


def ocr_response(text: str, confidence: float, processing_time_ms: int):
    message = "Text extracted successfully." if text else "No text found in image."
    return {
        "success": True,
        "text": text,
        "confidence": confidence,
        "processing_time_ms": processing_time_ms,
        "message": message,
    }, 200


def error_response(status_code: int, message: str):
    return {"success": False, "error": message}, status_code
