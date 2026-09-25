"""Google Cloud service integrations.

Each integration is optional and fails soft: if credentials or the API are
unavailable, the caller gets ``None`` and the product keeps working.

  * Cloud Vision        — OCR for photographed / scanned documents
  * Cloud Translation   — output in 10+ Indian languages beyond English/Hindi
  * Cloud Text-to-Speech — read-aloud for low-literacy and visually impaired users
  * Firestore           — anonymous feedback (never document content)
  * Cloud Logging       — structured logs on Cloud Run
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from functools import lru_cache

log = logging.getLogger("karar.gcp")

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")

# UI language code -> (Cloud Translation code, Text-to-Speech voice locale)
LANGUAGES: dict[str, dict[str, str]] = {
    "en": {"name": "English", "native": "English", "tts": "en-IN"},
    "hi": {"name": "Hindi", "native": "हिन्दी", "tts": "hi-IN"},
    "bn": {"name": "Bengali", "native": "বাংলা", "tts": "bn-IN"},
    "mr": {"name": "Marathi", "native": "मराठी", "tts": "mr-IN"},
    "ta": {"name": "Tamil", "native": "தமிழ்", "tts": "ta-IN"},
    "te": {"name": "Telugu", "native": "తెలుగు", "tts": "te-IN"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ", "tts": "kn-IN"},
    "ml": {"name": "Malayalam", "native": "മലയാളം", "tts": "ml-IN"},
    "gu": {"name": "Gujarati", "native": "ગુજરાતી", "tts": "gu-IN"},
    "pa": {"name": "Punjabi", "native": "ਪੰਜਾਬੀ", "tts": "pa-IN"},
    "ur": {"name": "Urdu", "native": "اردو", "tts": "ur-IN"},
}
NATIVE_LANGS = {"en", "hi"}  # fully authored in the knowledge base; others are machine-translated
TTS_MAX_BYTES = 4800  # Text-to-Speech request limit is 5000 bytes


def enabled() -> bool:
    return bool(PROJECT) and os.getenv("KARAR_OFFLINE", "").lower() not in ("1", "true")


# ------------------------------------------------------------------ Cloud Logging
def setup_logging() -> None:
    """Attach Cloud Logging when running on Cloud Run; plain logging elsewhere."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if os.getenv("K_SERVICE") and enabled():
        try:
            import google.cloud.logging

            google.cloud.logging.Client(project=PROJECT).setup_logging(log_level=logging.INFO)
            log.info("Cloud Logging attached")
        except Exception as exc:  # pragma: no cover - depends on runtime credentials
            log.warning("Cloud Logging unavailable: %s", exc)


# ------------------------------------------------------------------ Cloud Vision
def ocr_image(data: bytes) -> str | None:
    if not enabled():
        return None
    try:
        from google.cloud import vision

        client = _vision_client()
        resp = client.document_text_detection(
            image=vision.Image(content=data), image_context={"language_hints": ["en", "hi"]}
        )
        if resp.error.message:
            raise RuntimeError(resp.error.message)
        return resp.full_text_annotation.text or None
    except Exception as exc:
        log.warning("Vision OCR failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def _vision_client():
    from google.cloud import vision

    return vision.ImageAnnotatorClient()


# ------------------------------------------------------------------ Cloud Translation
def translate(texts: list[str], target: str) -> list[str] | None:
    """Batch-translate English strings. Returns None if the service is unavailable."""
    if not texts or target == "en":
        return texts
    if not enabled() or target not in LANGUAGES:
        return None
    try:
        client = _translate_client()
        out: list[str] = []
        for i in range(0, len(texts), 100):  # API limit per request
            batch = texts[i : i + 100]
            resp = client.translate_text(
                request={
                    "parent": f"projects/{PROJECT}/locations/global",
                    "contents": batch,
                    "mime_type": "text/plain",
                    "source_language_code": "en",
                    "target_language_code": target,
                }
            )
            out.extend(t.translated_text for t in resp.translations)
        return out
    except Exception as exc:
        log.warning("Translation failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def _translate_client():
    from google.cloud import translate_v3

    return translate_v3.TranslationServiceClient()


# ------------------------------------------------------------------ Text-to-Speech
def speak(text: str, lang: str) -> bytes | None:
    if not enabled():
        return None
    try:
        from google.cloud import texttospeech

        locale = LANGUAGES.get(lang, LANGUAGES["en"])["tts"]
        text = text.encode("utf-8")[:TTS_MAX_BYTES].decode("utf-8", errors="ignore")
        resp = _tts_client().synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(language_code=locale),
            audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.92),
        )
        return resp.audio_content
    except Exception as exc:
        log.warning("Text-to-Speech failed: %s", exc)
        return None


@lru_cache(maxsize=1)
def _tts_client():
    from google.cloud import texttospeech

    return texttospeech.TextToSpeechClient()


# ------------------------------------------------------------------ Firestore
def save_feedback(entry: dict) -> bool:
    """Store anonymous feedback. Callers must never pass document text or PII."""
    if not enabled():
        return False
    try:
        record = {**entry, "created_at": datetime.now(UTC)}
        _firestore_client().collection("feedback").add(record)
        return True
    except Exception as exc:
        log.warning("Firestore write failed: %s", exc)
        return False


@lru_cache(maxsize=1)
def _firestore_client():
    from google.cloud import firestore

    return firestore.Client(project=PROJECT)
