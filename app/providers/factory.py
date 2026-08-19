"""OCR provider factory.

Picks the OCR engine from config (OCR_PROVIDER), mirroring the LLM
provider-factory pattern: one interface, multiple implementations, selected at
startup. Adding a new engine is a new class + one case here.
"""
from app.providers.base import OcrProvider
from config import Config


class OcrProviderFactory:
    @staticmethod
    def create(provider: str | None = None) -> OcrProvider:
        provider = (provider or Config.OCR_PROVIDER).lower()

        if provider == "vision":
            from app.providers.vision_provider import VisionOcrProvider

            return VisionOcrProvider()

        if provider == "tesseract":
            from app.providers.tesseract_provider import TesseractOcrProvider

            return TesseractOcrProvider()

        raise ValueError(f"Unsupported OCR provider: {provider}")
