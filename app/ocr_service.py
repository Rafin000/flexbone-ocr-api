"""OCR integration with Google Cloud Vision.

Isolated from the web layer so the routes stay thin and the OCR provider can
be swapped (e.g. to Tesseract) without touching the views.
"""
from dataclasses import dataclass

from google.cloud import vision


@dataclass
class OcrResult:
    text: str
    confidence: float


class OcrError(Exception):
    """Raised when the OCR provider returns an error."""


class VisionOcrService:
    """Thin wrapper around the Cloud Vision client.

    The client is created lazily and reused across requests (it holds a
    connection pool and is safe to share).
    """

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self) -> vision.ImageAnnotatorClient:
        if self._client is None:
            self._client = vision.ImageAnnotatorClient()
        return self._client

    def extract_text(self, image_bytes: bytes) -> OcrResult:
        image = vision.Image(content=image_bytes)
        # document_text_detection exposes per-block confidence (unlike the
        # simpler text_detection), so we can report a real confidence score.
        response = self.client.document_text_detection(image=image)

        if response.error.message:
            raise OcrError(response.error.message)

        annotation = response.full_text_annotation
        text = (annotation.text or "").strip()

        if not text:
            # "No text found" is a valid, successful outcome — not an error.
            return OcrResult(text="", confidence=0.0)

        return OcrResult(text=text, confidence=self._average_confidence(annotation))

    @staticmethod
    def _average_confidence(annotation) -> float:
        """Vision reports confidence per block; average them into one number."""
        confidences = [
            block.confidence
            for page in annotation.pages
            for block in page.blocks
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 4)


# Single shared instance, imported by the views.
ocr_service = VisionOcrService()
