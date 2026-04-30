"""
OCR utility – lazy-loaded EasyOCR reader singleton.

Uses EasyOCR to extract Chinese and English text from images.
Reader is initialized once on first use and cached globally.
"""
import os
from functools import lru_cache
from typing import Optional

# Lazy import: only torch + easyocr import when actually needed


@lru_cache(maxsize=1)
def _get_reader():
    """Get or create the cached EasyOCR reader (lazy init)."""
    import easyocr
    return easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)


async def ocr_image(image_path: str) -> str:
    """Extract Chinese + English text from an image file.

    Args:
        image_path: Absolute or relative path to the image.

    Returns:
        Concatenated text extracted from the image.
    """
    if not os.path.isfile(image_path):
        return ""

    try:
        reader = _get_reader()
        result = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(result) if result else ""
    except Exception as e:
        raise RuntimeError(f"OCR 识别失败: {e}")


async def ocr_image_b64(base64_str: str) -> str:
    """Extract text from a base64-encoded image (future use)."""
    import base64
    import tempfile
    from PIL import Image
    import io

    try:
        image_data = base64.b64decode(base64_str)
        image = Image.open(io.BytesIO(image_data))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp, format="PNG")
            tmp_path = tmp.name
        text = await ocr_image(tmp_path)
        os.unlink(tmp_path)
        return text
    except Exception as e:
        raise RuntimeError(f"Base64 OCR 识别失败: {e}")
