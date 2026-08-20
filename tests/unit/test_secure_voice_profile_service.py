"""
Unit Tests: Secure Voice Profile Service & Consent
"""

import tempfile
from pathlib import Path

import pytest

from backend.adapters.tts.mock_tts import generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.domain.models import VoiceProfileStatus


@pytest.fixture
def profile_service():
    with tempfile.TemporaryDirectory() as tmpdir:
        service = SecureVoiceProfileService(storage_dir=Path(tmpdir))
        yield service


@pytest.mark.asyncio
async def test_consent_recording_and_hashing(profile_service):
    statement = "I explicitly authorize my voice to be synthesized exclusively for real-time translation calls."
    dummy_audio = b"dummy_audio_sample_bytes_123"
    
    consent = await profile_service.record_consent(
        user_id="user_raj",
        statement_text=statement,
        audio_signature_bytes=dummy_audio,
    )
    assert consent.consent_id.startswith("consent_user_raj_")
    assert consent.user_id == "user_raj"
    assert consent.is_revoked is False
    assert len(consent.signature_hash) == 64


@pytest.mark.asyncio
async def test_audio_quality_validation_pass(profile_service):
    # Generate 4 seconds of clean audio
    clean_pcm = generate_synthesized_pcm("This is a 4-second audio sample for quality analysis", duration_per_char=0.08)
    metrics = await profile_service.validate_audio_quality(clean_pcm)
    assert metrics.duration_sec >= 3.0
    assert metrics.is_acceptable is True
    assert metrics.clipping_rate < 0.03


@pytest.mark.asyncio
async def test_audio_quality_validation_fail_short(profile_service):
    short_pcm = b"\x00\x01" * 1000  # less than 1 second
    metrics = await profile_service.validate_audio_quality(short_pcm)
    assert metrics.is_acceptable is False


@pytest.mark.asyncio
async def test_create_profile_without_consent_raises(profile_service):
    sample_pcm = generate_synthesized_pcm("Valid duration speech sample text", duration_per_char=0.08)
    with pytest.raises(PermissionError):
        await profile_service.create_profile(
            user_id="user_unauthorized",
            display_name="Unauthorized User",
            consent_id="fake_consent_id",
            audio_sample_bytes=sample_pcm,
        )


@pytest.mark.asyncio
async def test_create_and_delete_profile_lifecycle(profile_service):
    statement = "I authorize voice translation synthesis."
    sample_pcm = generate_synthesized_pcm("Valid speech sample for complete lifecycle test", duration_per_char=0.08)
    
    consent = await profile_service.record_consent("user_lifecycle", statement, sample_pcm)
    profile = await profile_service.create_profile(
        user_id="user_lifecycle",
        display_name="Lifecycle User",
        consent_id=consent.consent_id,
        audio_sample_bytes=sample_pcm,
    )
    assert profile.status == VoiceProfileStatus.READY
    assert profile.user_id == "user_lifecycle"

    # Verify retrieval
    retrieved = await profile_service.get_profile("user_lifecycle")
    assert retrieved is not None
    assert retrieved.voice_id == profile.voice_id

    # Verify deletion / reset (GDPR compliance)
    deleted = await profile_service.delete_profile("user_lifecycle")
    assert deleted is True
    assert await profile_service.get_profile("user_lifecycle") is None
