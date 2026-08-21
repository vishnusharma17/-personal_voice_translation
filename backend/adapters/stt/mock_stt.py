"""
Streaming Speech Recognizer (Mock & Testing Adapter)
Emits realistic interim and final transcription events for Hindi, Hinglish, and English audio.
"""

import asyncio
from collections.abc import AsyncGenerator

from backend.domain.interfaces import SpeechRecognizer
from backend.domain.models import Language


class MockSpeechRecognizer(SpeechRecognizer):
    """
    Mock STT adapter for testing and deterministic latency evaluation.
    """

    def __init__(self, simulated_latency_ms: float = 80.0):
        self.simulated_latency_ms = simulated_latency_ms
        self.test_transcript_override: str | None = None

    def set_next_transcript(self, text: str):
        """Allows test harness to inject known transcript for incoming audio."""
        self.test_transcript_override = text

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        source_language: Language | None = None,
    ) -> AsyncGenerator[dict, None]:
        buffer = bytearray()
        async for chunk in audio_stream:
            buffer.extend(chunk)
            # Emit interim hypothesis if enough bytes accumulated
            if len(buffer) > 3200:  # ~100ms at 16kHz 16-bit
                yield {
                    "text": "Kal 11 baje...",
                    "is_final": False,
                    "confidence": 0.85,
                    "detected_language": "hi-en",
                }

        await asyncio.sleep(self.simulated_latency_ms / 1000.0)
        
        if self.test_transcript_override:
            final_text = self.test_transcript_override
            self.test_transcript_override = None
        elif source_language == Language.ENGLISH:
            final_text = "Yes, that sounds good. Let's have the meeting tomorrow."
        else:
            final_text = "Kal 11 baje client ke saath meeting hai, main project ka demo dikhaunga."

        detected = "en" if source_language == Language.ENGLISH else "hi-en"

        yield {
            "text": final_text,
            "is_final": True,
            "confidence": 0.98,
            "detected_language": detected,
        }

    async def transcribe_chunk(
        self, audio_bytes: bytes, source_language: Language | None = None
    ) -> dict:
        await asyncio.sleep(self.simulated_latency_ms / 1000.0)
        if self.test_transcript_override:
            final_text = self.test_transcript_override
            self.test_transcript_override = None
        elif source_language == Language.ENGLISH:
            final_text = "Yes, that sounds good. Let's have the meeting tomorrow."
        else:
            final_text = "Kal 11 baje client ke saath meeting hai, main project ka demo dikhaunga."

        detected = "en" if source_language == Language.ENGLISH else "hi-en"
        return {
            "text": final_text,
            "is_final": True,
            "confidence": 0.98,
            "detected_language": detected,
        }
