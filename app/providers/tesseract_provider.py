"""Tesseract OCR provider (open-source, runs in-container, no external API).

Selected via OCR_PROVIDER=tesseract. Demonstrates that the OCR engine is
fully swappable behind the OcrProvider interface.
"""
import io

from app.providers.base import OcrError, OcrProvider, OcrResult


class TesseractOcrProvider(OcrProvider):
    def extract_text(self, image_bytes: bytes) -> OcrResult:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:  # pragma: no cover
            raise OcrError(
                "Tesseract provider requires pytesseract and the tesseract "
                "binary to be installed."
            ) from exc

        try:
            image = Image.open(io.BytesIO(image_bytes))
            # image_to_data gives per-word confidence, like Vision's blocks.
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
        except Exception as exc:
            raise OcrError(f"Tesseract failed: {exc}") from exc

        words = [w for w in data.get("text", []) if w.strip()]
        confs = [
            int(c) for c, w in zip(data.get("conf", []), data.get("text", []))
            if w.strip() and str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        text = " ".join(words).strip()
        if not text:
            return OcrResult(text="", confidence=0.0)

        confidence = round(sum(confs) / len(confs) / 100, 4) if confs else 0.0
        return OcrResult(text=text, confidence=confidence)
