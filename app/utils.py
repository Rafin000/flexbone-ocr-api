"""Small, focused helpers used by the OCR routes."""
import hashlib
import io

from PIL import Image


def clean_text(text: str) -> str:
    """Text preprocessing (bonus): trim trailing whitespace on each line and
    collapse runs of blank lines, so the output is tidy without altering the
    actual content."""
    if not text:
        return ""
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        is_blank = line == ""
        if is_blank and prev_blank:
            continue  # skip consecutive blank lines
        cleaned.append(line)
        prev_blank = is_blank
    return "\n".join(cleaned).strip()


def image_hash(image_bytes: bytes) -> str:
    """SHA-256 of the raw bytes — the cache key for identical images."""
    return hashlib.sha256(image_bytes).hexdigest()


def extract_metadata(image_bytes: bytes) -> dict:
    """Image metadata extraction (bonus): dimensions, format, mode, size."""
    meta: dict = {"size_kb": round(len(image_bytes) / 1024, 2)}
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            meta.update(
                {
                    "width": img.width,
                    "height": img.height,
                    "format": img.format,
                    "mode": img.mode,
                }
            )
    except Exception:
        # Metadata is best-effort; never fail the request over it.
        pass
    return meta
