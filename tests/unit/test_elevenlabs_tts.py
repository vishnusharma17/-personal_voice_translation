"""
Unit Tests: ElevenLabs Voice Synthesizer Adapter
"""

import pytest

from backend.adapters.tts.elevenlabs_tts import ElevenLabsTTS
from backend.domain.models import Language, VoiceProfile, VoiceProfileStatus


@pytest.mark.asyncio
async def test_elevenlabs_tts_unauthorized_profile_raises():
    tts = ElevenLabsTTS(api_key="dummy_key")
    unauthorized_profile = VoiceProfile(
        voice_id="vp_unauthorized",
        user_id="user_bad",
        display_name="Bad User",
        status=VoiceProfileStatus.REJECTED,
    )
    with pytest.raises(PermissionError):
        await tts.synthesize("Test text", unauthorized_profile, Language.ENGLISH)


@pytest.mark.asyncio
async def test_elevenlabs_tts_fallback_synthesis():
    tts = ElevenLabsTTS(api_key=None)
    profile = VoiceProfile(
        voice_id="vp_valid",
        user_id="user_valid",
        display_name="Valid User",
        status=VoiceProfileStatus.READY,
    )
    audio = await tts.synthesize("Let's test fallback voice synthesis", profile, Language.ENGLISH)
    assert audio is not None
    assert len(audio) > 0
    assert audio.startswith(b"RIFF")
