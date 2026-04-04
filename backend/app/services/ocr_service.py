# backend/app/services/ocr_service.py
"""
OCR / Document Understanding service for handwritten journal images.

Architecture: Image → Vision model → Extracted text
The extracted text is returned to frontend, user confirms/edits,
then the confirmed text goes into the existing diary analysis pipeline.

Uses Zhipu GLM-4V (glm-4v-plus) via the existing API key configuration.
"""
import os
import re
import json
import httpx
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text cleaning helpers
# ---------------------------------------------------------------------------

def _clean_ocr_text(raw: str) -> str:
    """
    Lightweight post-processing on raw OCR output to remove common artifacts.
    - Removes repeated punctuation
    - Normalizes whitespace
    - Removes obvious garbage characters
    """
    # Normalize multiple newlines to double newline
    text = re.sub(r"\n{3,}", "\n\n", raw)
    # Remove trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    # Remove lines that are pure punctuation or garbage
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        # Skip lines that are only punctuation or very short garbage
        if stripped and not re.fullmatch(r"[.,;:\-\*#@]{1,5}", stripped):
            lines.append(line)
    text = "\n".join(lines)
    return text.strip()


# ---------------------------------------------------------------------------
# Zhipu GLM-4V OCR
# ---------------------------------------------------------------------------

async def _ocr_zhipu_vision(image_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Extract text from a diary image using Zhipu GLM-4V.
    Falls back to returning the raw model output if parsing fails.
    """
    from ..config import settings

    base = settings.zhipu_base_url.rstrip("/")
    # GLM-4V endpoint — adjust if your API uses a different path
    url = f"{base}/chat/completions"

    import base64
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Detect image media type from filename
    ext = os.path.splitext(filename)[1].lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    media_type = media_type_map.get(ext, "image/jpeg")

    payload = {
        "model": "glm-4v-plus",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{b64_image}"
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are an expert OCR and document understanding system. "
                            "Your task is to extract ALL text visible in this image, "
                            "preserving the original language, line breaks, and structure. "
                            "If the image contains a handwritten diary, extract every legible word. "
                            "Do NOT summarize, translate, or interpret the content. "
                            "Only extract text. "
                            "If text is illegible, write [illegible] in place of that segment. "
                            "Output ONLY the extracted text, nothing else."
                        ),
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
        "extra_body": {"thinking": {"type": "disabled"}},
    }

    headers = {
        "Authorization": f"Bearer {settings.zhipu_api_key}",
        "Content-Type": "application/json",
    }

    logger.info(
        f"[OCR] calling Zhipu GLM-4V  filename={filename}  "
        f"image_size={len(image_bytes)} bytes  input_mode=image"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices")
    if not choices:
        raise ValueError(f"GLM-4V returned no choices: {str(data)[:200]}")

    message = choices[0].get("message", {})
    raw_text = message.get("content", "").strip()

    logger.info(
        f"[OCR/GLM-4V] success  raw_text_len={len(raw_text)}  "
        f"first_50={raw_text[:50]!r}"
    )

    return {
        "raw_text": raw_text,
        "backend": "glm-4v-plus",
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def ocr_diary_image(image_bytes: bytes, filename: str = "diary.jpg") -> Dict[str, Any]:
    """
    Extract text from a handwritten/digital diary image.

    Returns:
        {
            "raw_text": str,          # Raw model output
            "clean_text": str,         # Post-processed text
            "confidence": float | None,
            "backend": str,
            "warnings": List[str] | None,
        }
    """
    warnings: List[str] = []
    logger.info(
        f"[OCR] image_size={len(image_bytes)} bytes  filename={filename}  "
        f"input_mode=image"
    )

    try:
        result = await _ocr_zhipu_vision(image_bytes, filename)
    except Exception as e:
        logger.error(f"[OCR] Zhipu GLM-4V failed: {e}")
        raise RuntimeError(
            f"Image OCR failed. Please try a clearer photo or type your journal directly. "
            f"Error: {e}"
        )

    raw_text = result.get("raw_text", "")
    clean_text = _clean_ocr_text(raw_text)

    # Emit warning if output is suspiciously short
    if len(clean_text) < 10:
        warnings.append(
            "Very little text was detected in the image. "
            "Please check image quality or type manually."
        )

    logger.info(
        f"[OCR] done  raw_len={len(raw_text)}  clean_len={len(clean_text)}  "
        f"backend={result.get('backend')}  warnings={warnings}"
    )

    return {
        "raw_text": raw_text,
        "clean_text": clean_text,
        "confidence": None,  # GLM-4V doesn't expose per-character confidence
        "backend": result.get("backend", "unknown"),
        "warnings": warnings if warnings else None,
    }
