"""
Unit Tests: Voice Synthesizer
"""

import pytest

from backend.adapters.tts.mock_tts import (
    MockVoiceSynthesizer,
    generate_synthesized_pcm,
    pcm_to_wav,
)
from backend.domain.models import Language, VoiceProfile


@pytest.mark.asyncio
async def test_pcm_generation_properties():
    pcm = generate_synthesized_pcm("Hello world test sentence", sample_rate=16000)
    assert len(pcm) > 0
    assert len(pcm) % 2 == 0  # 16-bit PCM has 2 bytes per sample


def test_pcm_to_wav_header():
    pcm = generate_synthesized_pcm("Testing WAV wrapping")
    wav = pcm_to_wav(pcm, sample_rate=16000, channels=1)
    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:12]
    assert len(wav) == len(pcm) + 44


@pytest.mark.asyncio
async def test_synthesizer_streaming_chunks():
    tts = MockVoiceSynthesizer(simulated_latency_ms=10.0)
    profile = VoiceProfile(
        voice_id="vp_test",
        user_id="user_123",
        display_name="Test Speaker",
    )
    chunks = []
    async for chunk in tts.synthesize_stream("This is a streaming test", profile, Language.ENGLISH):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    total_bytes = sum(len(c) for c in chunks)
    assert total_bytes > 0
