# backend/app/routers/multimodal.py
"""
Multimodal input endpoints: speech-to-text and OCR.

These are preprocessing-only endpoints:
  - They do NOT write to journal_entries
  - They return a draft text for user confirmation
  - Only after user confirms does the text flow into the existing /api/journal pipeline

Routes:
  POST /api/transcribe    — audio file → transcript text
  POST /api/ocr-diary     — image file → extracted text
"""
import os
import uuid
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from .. import schemas
from ..services import stt_service, ocr_service

router = APIRouter(tags=["multimodal"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# File storage helpers
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(tempfile.gettempdir()) / "mindjournal_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_AUDIO = {"audio/webm", "audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/x-wav"}
ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


def _save_upload(file: UploadFile, subdir: str) -> tuple[str, str]:
    """
    Save an uploaded file to disk and return (filepath, stored_filename).
    The stored filename is random UUID-based to avoid collisions.
    """
    dest_dir = UPLOAD_DIR / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}_{file.filename or 'unknown'}"
    dest_path = dest_dir / stored_name

    with dest_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return str(dest_path), stored_name


def _allowed(content_type: str, allowed_set: set) -> bool:
    return content_type in allowed_set or (
        # Sometimes browser sends type with charset, e.g. audio/webm; codecs=...
        any(content_type.startswith(p.rsplit("/", 1)[0]) for p in allowed_set)
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/transcribe",
    response_model=schemas.TranscribeResponse,
    summary="Speech-to-Text for journal voice input",
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (WEBM, MP3, WAV, OGG)"),
):
    """
    Receive an audio file and return a transcription.

    Flow:
      1. User records audio in browser
      2. Frontend uploads to this endpoint
      3. Backend runs STT and returns transcript
      4. Frontend shows editable text box with draft
      5. User confirms/edits → calls /api/journal with confirmed text
    """
    logger.info(
        f"[TRANSCRIBE] filename={file.filename}  content_type={file.content_type}  "
        f"input_mode=voice"
    )

    # --- Validate ---
    if not file.size or file.size == 0:
        raise HTTPException(
            status_code=400,
            detail="Audio file is empty. Please record or upload a valid audio file.",
        )

    # Most browsers send audio/webm; allow broad audio types
    allowed_bases = {"audio", "video"}
    ct = (file.content_type or "").lower()
    if not any(ct.startswith(b) for b in allowed_bases) and ct not in ALLOWED_AUDIO:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported audio format: {file.content_type}. "
                f"Supported: WEBM, MP3, WAV, OGG."
            ),
        )

    if file.size and file.size > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Audio file too large. Maximum size is 25 MB.",
        )

    # --- Save temporarily ---
    try:
        stored_path, stored_name = _save_upload(file, "audio")
        logger.info(f"[TRANSCRIBE] saved to {stored_path}")
    except Exception as e:
        logger.error(f"[TRANSCRIBE] file save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save audio file.")

    # --- Transcribe ---
    try:
        with open(stored_path, "rb") as f:
            audio_bytes = f.read()

        result = await stt_service.transcribe_audio(
            audio_bytes=audio_bytes,
            filename=file.filename or "audio.webm",
        )

        transcript = result.get("transcript", "")
        warnings = result.get("warnings") or []

        logger.info(
            f"[TRANSCRIBE] success  transcript_len={len(transcript)}  "
            f"backend={result.get('backend')}  source_type=voice"
        )

        # Clean up temp file
        try:
            os.unlink(stored_path)
        except OSError:
            pass

        if not transcript:
            warnings.append(
                "No speech was detected. Please speak closer to the microphone "
                "or upload a clearer recording."
            )

        return schemas.TranscribeResponse(
            transcript=transcript,
            language=result.get("language"),
            duration_seconds=result.get("duration_seconds"),
            segments=result.get("segments"),
            warnings=warnings if warnings else None,
        )

    except RuntimeError as e:
        logger.error(f"[TRANSCRIBE] STT failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"[TRANSCRIBE] unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Transcription service encountered an error. Please try again or type manually.",
        )


@router.post(
    "/ocr-diary",
    response_model=schemas.OCRDiaryResponse,
    summary="OCR for handwritten diary images",
)
async def ocr_diary(
    file: UploadFile = File(..., description="Diary image (JPG, PNG, WEBP, BMP)"),
):
    """
    Receive a diary image and return extracted text.

    Flow:
      1. User uploads a photo of their handwritten/printed diary page
      2. Frontend uploads to this endpoint
      3. Backend runs vision OCR and returns raw + clean text
      4. Frontend shows editable text box with draft
      5. User confirms/edits → calls /api/journal with confirmed text

    Note: The vision model only extracts text. It does NOT perform psychological analysis.
    """
    logger.info(
        f"[OCR] filename={file.filename}  content_type={file.content_type}  "
        f"input_mode=image"
    )

    # --- Validate ---
    if not file.size or file.size == 0:
        raise HTTPException(
            status_code=400,
            detail="Image file is empty. Please upload a valid image.",
        )

    ct = (file.content_type or "").lower()
    if ct not in ALLOWED_IMAGE and not ct.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported image format: {file.content_type}. "
                f"Supported: JPG, PNG, WEBP, BMP."
            ),
        )

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image file too large. Maximum size is 10 MB.",
        )

    # --- Save temporarily ---
    try:
        stored_path, stored_name = _save_upload(file, "images")
        logger.info(f"[OCR] saved to {stored_path}")
    except Exception as e:
        logger.error(f"[OCR] file save failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to save image file.")

    # --- OCR ---
    try:
        with open(stored_path, "rb") as f:
            image_bytes = f.read()

        result = await ocr_service.ocr_diary_image(
            image_bytes=image_bytes,
            filename=file.filename or "diary.jpg",
        )

        raw_text = result.get("raw_text", "")
        clean_text = result.get("clean_text", "")
        warnings = result.get("warnings") or []

        logger.info(
            f"[OCR] success  raw_len={len(raw_text)}  clean_len={len(clean_text)}  "
            f"backend={result.get('backend')}  source_type=image"
        )

        # Clean up temp file
        try:
            os.unlink(stored_path)
        except OSError:
            pass

        return schemas.OCRDiaryResponse(
            raw_text=raw_text,
            clean_text=clean_text,
            confidence=result.get("confidence"),
            warnings=warnings if warnings else None,
        )

    except RuntimeError as e:
        logger.error(f"[OCR] vision failed: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"[OCR] unexpected error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="OCR service encountered an error. Please try a clearer image or type manually.",
        )
