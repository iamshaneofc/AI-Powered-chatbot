"""
services/whisper_service.py — Hybrid Whisper transcription service.

Supports:
  1. Local inference via `faster-whisper` (fast CPU int8, zero credits needed, 100% offline).
  2. OpenAI Whisper API when configured with an official OpenAI API key.
"""

import asyncio
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhisperService:
    """
    Hybrid Whisper transcription service supporting local faster-whisper and OpenAI API.
    """

    def __init__(self) -> None:
        self._local_model = None

    def _get_local_model(self):
        if self._local_model is None:
            import os
            from faster_whisper import WhisperModel
            model_size = getattr(settings, "WHISPER_MODEL", "base") or "base"
            threads = max(2, min(8, os.cpu_count() or 4))
            logger.info("Loading faster-whisper '%s' (threads=%d)...", model_size, threads)
            self._local_model = WhisperModel(
                model_size,
                device="cpu",
                compute_type="int8",
                cpu_threads=threads,
            )
            logger.info("Local faster-whisper model '%s' loaded successfully.", model_size)
        return self._local_model

    def _transcribe_local(self, file_path: Path) -> dict:
        model = self._get_local_model()
        logger.info("Transcribing media file locally: %s", file_path.name)
        # beam_size=1 with multi-threading gives 3x-4x speedup while preserving all speech & lyrics
        segments, info = model.transcribe(
            str(file_path),
            beam_size=1,
            vad_filter=False,
        )

        segment_list = []
        text_parts = []
        for s in segments:
            clean_text = s.text.strip()
            if clean_text:
                text_parts.append(clean_text)
                segment_list.append({
                    "start": round(s.start, 2),
                    "end": round(s.end, 2),
                    "text": clean_text,
                })

        full_text = " ".join(text_parts).strip()
        logger.info(
            "Local transcription completed: %d chars, %d segments, lang=%s",
            len(full_text), len(segment_list), info.language
        )
        return {
            "text": full_text,
            "language": info.language,
            "duration": round(info.duration, 2) if info.duration else None,
            "segments": segment_list,
        }

    async def transcribe_with_meta(self, file_path: Path) -> dict:
        """
        Transcribe audio or video with segment timestamps.
        Tries OpenAI API if an official key is present; falls back to local faster-whisper.
        """
        # If using OpenRouter or no API key, OpenRouter does not support free audio transcription.
        # Use local faster-whisper directly.
        use_local = (
            getattr(settings, "WHISPER_BACKEND", "local") == "local"
            or settings.OPENAI_API_KEY.startswith("sk-or-")
            or not settings.OPENAI_API_KEY
        )

        if not use_local:
            try:
                from app.services.openai_service import openai_service
                file_size_mb = file_path.stat().st_size / (1024 * 1024)
                if file_size_mb <= 25:
                    with open(file_path, "rb") as audio_file:
                        response = await openai_service.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="verbose_json",
                            timestamp_granularities=["segment"]
                        )
                    segments = response.segments or []
                    return {
                        "text": getattr(response, "text", "").strip(),
                        "language": getattr(response, "language", "unknown"),
                        "duration": getattr(response, "duration", None),
                        "segments": [
                            {
                                "start": s.get("start") if isinstance(s, dict) else getattr(s, "start", 0),
                                "end": s.get("end") if isinstance(s, dict) else getattr(s, "end", 0),
                                "text": s.get("text") if isinstance(s, dict) else getattr(s, "text", ""),
                            }
                            for s in segments
                        ],
                    }
            except Exception as e:
                logger.warning("API Whisper transcription failed: %s. Falling back to local faster-whisper.", e)

        # Run local faster-whisper in background thread pool to keep async loop responsive
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._transcribe_local, file_path)

    async def transcribe(self, file_path: Path) -> str:
        meta = await self.transcribe_with_meta(file_path)
        return meta.get("text", "")


# Singleton instance
whisper_service = WhisperService()
