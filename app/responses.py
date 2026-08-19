"""Helpers for building consistent JSON responses.

The success payload for /extract-text follows the exact shape required by the
challenge: { success, text, confidence, processing_time_ms }.
Errors use a matching { success: false, error } envelope.
"""
from flask import jsonify


def ocr_response(text: str, confidence: float, processing_time_ms: int):
    message = "Text extracted successfully." if text else "No text found in image."
    return (
        jsonify(
            {
                "success": True,
                "text": text,
                "confidence": confidence,
                "processing_time_ms": processing_time_ms,
                "message": message,
            }
        ),
        200,
    )


def error_response(status_code: int, message: str):
    return jsonify({"success": False, "error": message}), status_code
