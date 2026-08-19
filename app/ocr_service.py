"""OCR entry point.

Exposes a single `ocr_service` instance built by the provider factory from
config (OCR_PROVIDER). The rest of the app imports from here and stays
unaware of which OCR engine is in use.
"""
from app.providers.base import OcrError, OcrResult  # re-exported for callers
from app.providers.factory import OcrProviderFactory

# Provider chosen at startup from config (vision | tesseract).
ocr_service = OcrProviderFactory.create()

__all__ = ["ocr_service", "OcrError", "OcrResult"]
