"""
services/whisper_service.py — OpenAI Whisper transcription service.

Uses the `openai-whisper` Python library (local inference) by default.
Can be switched to the OpenAI Whisper API by setting WHISPER_BACKEND=api in .env.

Usage:
    from app.services.whisper_service import whisper_service

    # Simple transcript
    text = await whisper_service.transcribe(Path("audio.mp3"))

    # With language / duration metadata
    result = await whisper_service.transcribe_with_meta(Path("audio.mp3"))
    print(result["text"], result["language"], result["duration"])
"""

import asyncio
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class WhisperService:
    """
    Uses the OpenAI Whisper API for transcription.
    """

    async def transcribe(self, file_path: Path) -> str:
        """
        Transcribe an audio/video file and return the plain text transcript.
        """
        from app.services.openai_service import openai_service
        
        # Check file size (OpenAI Whisper API limit is 25MB)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:
            raise ValueError(f"File size ({file_size_mb:.2f}MB) exceeds the OpenAI Whisper API limit of 25MB. Please compress the file or split it into smaller chunks.")

        with open(file_path, "rb") as audio_file:
            response = await openai_service.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            
        text = response.strip()
        logger.info("Transcribed '%s' via API → %d chars", file_path.name, len(text))
        return text

    async def transcribe_with_meta(self, file_path: Path) -> dict:
        """
        Transcribe and return full metadata using verbose_json format.
        """
        from app.services.openai_service import openai_service
        
        # Check file size (OpenAI Whisper API limit is 25MB)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > 25:
            raise ValueError(f"File size ({file_size_mb:.2f}MB) exceeds the OpenAI Whisper API limit of 25MB. Please compress the file or split it into smaller chunks.")

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

# Singleton instance
whisper_service = WhisperService()
