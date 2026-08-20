"""
Unit Tests: Whisper STT Adapter
"""

import pytest
from backend.adapters.stt.whisper_stt import WhisperSTT
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_whisper_stt_fallback_transcription():
    # When no API key is provided, should cleanly fall back to local/mock recognition
    stt = WhisperSTT(api_key=None)
    sample_pcm = b"\x00\x05" * 3200
    res = await stt.transcribe_chunk(sample_pcm, source_language=Language.HINDI)
    assert res is not None
    assert "text" in res
    assert res["is_final"] is True
    assert res["confidence"] > 0.8


@pytest.mark.asyncio
async def test_whisper_stt_short_audio_handling():
    stt = WhisperSTT(api_key="sk-dummy")
    short_audio = b"\x00" * 100
    res = await stt.transcribe_chunk(short_audio)
    assert res["text"] == ""
    assert res["confidence"] == 0.0
