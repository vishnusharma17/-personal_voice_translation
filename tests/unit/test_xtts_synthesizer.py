"""
Unit Tests for CoquiXTTSVoiceSynthesizer
"""

import pytest

from backend.adapters.tts.xtts_synthesizer import CoquiXTTSVoiceSynthesizer
from backend.domain.models import Language, VoiceProfile, VoiceProfileStatus


@pytest.mark.asyncio
async def test_xtts_speaker_embedding_extraction():
    synthesizer = CoquiXTTSVoiceSynthesizer(simulated_latency_ms=0.0)
    audio_samples = b"\x00\x00" * 4000
    emb = synthesizer.extract_speaker_embedding(audio_samples)
    assert "speaker_signature" in emb
    assert emb["sample_length"] == len(audio_samples)


@pytest.mark.asyncio
async def test_xtts_synthesis_and_revoked_rejection():
    synthesizer = CoquiXTTSVoiceSynthesizer(simulated_latency_ms=0.0)

    ready_profile = VoiceProfile(
        voice_id="v_1",
        user_id="u_1",
        display_name="User Test",
        status=VoiceProfileStatus.READY,
    )

    wav_bytes = await synthesizer.synthesize(
        text="Hello world",
        voice_profile=ready_profile,
        target_language=Language.ENGLISH,
    )
    assert len(wav_bytes) > 44  # Valid WAV header + PCM frames
    assert wav_bytes.startswith(b"RIFF")

    revoked_profile = VoiceProfile(
        voice_id="v_2",
        user_id="u_2",
        display_name="User Revoked",
        status=VoiceProfileStatus.REVOKED,
    )

    with pytest.raises(ValueError, match="revoked/rejected"):
        await synthesizer.synthesize(
            text="Hello world",
            voice_profile=revoked_profile,
            target_language=Language.ENGLISH,
        )
