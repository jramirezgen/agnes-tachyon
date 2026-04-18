"""Voice Pipeline — STT (faster-whisper) + TTS (edge-tts) for continuous conversation."""
import asyncio
import io
import logging
import tempfile
import time
from pathlib import Path

import edge_tts
import numpy as np

from . import config

log = logging.getLogger("tachyon.voice")

# ── Lazy-loaded Whisper model (heavy, load once) ──────────────────
_whisper_model = None


def get_whisper():
    """Load faster-whisper model on first use (CPU)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        log.info("Loading Whisper model '%s' on %s...",
                 config.WHISPER_MODEL, config.WHISPER_DEVICE)
        _whisper_model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
        log.info("Whisper model loaded.")
    return _whisper_model


async def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    """Transcribe audio bytes (WAV/PCM 16-bit mono) to text using Whisper."""
    loop = asyncio.get_event_loop()

    def _transcribe():
        model = get_whisper()
        # Write to temp file (faster-whisper needs file path or numpy)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            segments, info = model.transcribe(
                tmp.name,
                language="es",
                beam_size=3,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )
            text = " ".join(s.text.strip() for s in segments)
        return text.strip()

    return await loop.run_in_executor(None, _transcribe)


async def synthesize_speech(text: str, voice: str = None) -> bytes:
    """Convert text to speech audio (MP3 bytes) using edge-tts."""
    voice = voice or config.TTS_VOICE
    communicate = edge_tts.Communicate(
        text,
        voice=voice,
        rate=config.TTS_RATE,
        volume=config.TTS_VOLUME,
    )

    audio_chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    return b"".join(audio_chunks)


async def list_voices(language: str = "es") -> list[dict]:
    """List available TTS voices for a language."""
    voices = await edge_tts.list_voices()
    return [
        {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
        for v in voices if v["Locale"].startswith(language)
    ]


# ── Preload Whisper on module import in background ────────────────
def preload_whisper():
    """Call this at startup to preload the whisper model."""
    import threading
    def _load():
        get_whisper()
    t = threading.Thread(target=_load, daemon=True)
    t.start()
