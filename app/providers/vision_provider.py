"""Google Cloud Vision OCR provider."""
from google.cloud import vision

from app.providers.base import OcrError, OcrProvider, OcrResult


class VisionOcrProvider(OcrProvider):
    """Uses Cloud Vision's document text detection (gives per-block confidence).

    The client is created lazily and reused across requests.
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
        response = self.client.document_text_detection(image=image)

        if response.error.message:
            raise OcrError(response.error.message)

        annotation = response.full_text_annotation
        text = (annotation.text or "").strip()
        if not text:
            return OcrResult(text="", confidence=0.0)

        return OcrResult(text=text, confidence=self._average_confidence(annotation))

    @staticmethod
    def _average_confidence(annotation) -> float:
        confidences = [
            block.confidence for page in annotation.pages for block in page.blocks
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 4)
