# backend/app/services/stt_service.py
"""
Speech-to-Text service for journal voice input.

Architecture: Audio file → STT → transcript text
The transcript is returned to frontend, user confirms/edits,
then the confirmed text goes into the existing diary analysis pipeline.

Supported backends (tried in order):
1. whisper (OpenAI Whisper API via httpx) — requires OPENAI_API_KEY
2. google (Google Speech Recognition via speech_recognition) — free, no key needed

For production use, replace whisper with your preferred cloud STT provider
(Zhipu, Azure, AWS, etc.) by implementing the same interface.
"""
import io
import tempfile
import os
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Whisper STT (OpenAI-compatible API)
# ---------------------------------------------------------------------------

async def _transcribe_whisper(audio_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Transcribe audio using OpenAI Whisper API.
    Requires OPENAI_API_KEY in environment.
    """
    try:
        import httpx
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}

        files = {"file": (filename, io.BytesIO(audio_bytes), "audio/mpeg")}
        data = {"model": "whisper-1"}  # no language → Whisper auto-detects (Cantonese, Mandarin, English, etc.)

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            result = resp.json()

        transcript = result.get("text", "").strip()
        duration = result.get("duration")
        language = result.get("language")

        logger.info(
            f"[STT/Whisper] success  transcript_len={len(transcript)}  "
            f"duration={duration}s  language={language}"
        )
        return {
            "transcript": transcript,
            "language": language,
            "duration_seconds": duration,
            "backend": "whisper",
        }
    except Exception as e:
        logger.error(f"[STT/Whisper] failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Google Speech Recognition (free fallback)
# ---------------------------------------------------------------------------

def _transcribe_google(audio_bytes: bytes, filename: str) -> Dict[str, Any]:
    """
    Transcribe audio using Google Speech Recognition via speech_recognition.
    Works without any API key but requires an internet connection.
    Note: Only supports short audio clips (< 60s) due to Google API limits.
    """
    try:
        import speech_recognition as sr
        import wave

        recognizer = sr.Recognizer()

        # Try to open as WAV first
        wav_path = None
        try:
            wav_path = tempfile.mktemp(suffix=".wav")
            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
        finally:
            if wav_path and os.path.exists(wav_path):
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

        # Try Chinese first, then English, then auto-detect
        transcript = None
        for lang in ["zh-CN", "en-US"]:
            try:
                transcript = recognizer.recognize_google(audio_data, language=lang)
                break
            except (sr.UnknownValueError, sr.RequestError):
                continue

        if not transcript:
            transcript = recognizer.recognize_google(audio_data)

        logger.info(
            f"[STT/Google] success  transcript_len={len(transcript)}  "
            f"backend=google_speech"
        )
        return {
            "transcript": transcript.strip(),
            "language": None,
            "duration_seconds": None,
            "backend": "google_speech",
        }
    except ImportError:
        raise ImportError(
            "speech_recognition not installed. "
            "Run: pip install SpeechRecognition"
        )
    except Exception as e:
        logger.error(f"[STT/Google] failed: {e}")
        raise


# ---------------------------------------------------------------------------
# Main entry point — tries backends in priority order
# ---------------------------------------------------------------------------

async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> Dict[str, Any]:
    """
    Transcribe an audio file to text.

    Returns:
        {
            "transcript": str,           # The transcribed text
            "language": str | None,      # Detected or specified language
            "duration_seconds": float | None,
            "backend": str,              # Which backend was used
            "warnings": List[str] | None,
        }
    """
    logger.info(
        f"[STT] audio_size={len(audio_bytes)} bytes  filename={filename}  "
        f"input_mode=voice"
    )

    warnings: List[str] = []
    warnings_append = warnings.append

    # --- Try Whisper first (higher quality) ---
    if os.environ.get("OPENAI_API_KEY"):
        try:
            result = await _transcribe_whisper(audio_bytes, filename)
            result["warnings"] = warnings if warnings else None
            return result
        except Exception as e:
            logger.warning(f"[STT] Whisper failed, falling back: {e}")
            warnings_append(f"Whisper unavailable ({e}), used fallback")

    # --- Fall back to Google Speech Recognition ---
    try:
        result = _transcribe_google(audio_bytes, filename)
        result["warnings"] = warnings if warnings else None
        return result
    except Exception as e:
        logger.error(f"[STT] Google STT also failed: {e}")
        raise RuntimeError(
            f"Speech-to-text failed. "
            f"Please upload a supported audio format (WAV, MP3, WEBM, OGG) "
            f"or type your journal directly. "
            f"Error: {e}"
        )
