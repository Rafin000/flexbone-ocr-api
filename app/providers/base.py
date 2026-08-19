"""OCR provider contract.

Every provider implements the same `extract_text` interface and returns the
same `OcrResult`, so the rest of the app depends on the abstraction, not on
any specific OCR engine (mirrors the LLM provider abstraction pattern).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class OcrResult:
    text: str
    confidence: float


class OcrError(Exception):
    """Raised when an OCR provider fails."""


class OcrProvider(ABC):
    """Interface all OCR providers implement."""

    @abstractmethod
    def extract_text(self, image_bytes: bytes) -> OcrResult:
        """Return the text (and a confidence score) found in the image."""
        raise NotImplementedError
