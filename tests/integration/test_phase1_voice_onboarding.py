"""
Integration Tests: Phase 1 Voice Onboarding, Quality Validation, and Security LifeCycle
"""

import pytest
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer, generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.domain.models import Language, VoiceProfileStatus


@pytest.mark.asyncio
async def test_full_phase1_voice_onboarding_lifecycle():
    profile_service = SecureVoiceProfileService()
    user_id = "user_onboard_test"
    display_name = "Kavita Verma"

    # 1. Step 1: Explicit Consent Recording
    consent_statement = (
        "I hereby give full explicit consent to VoiceBridge to analyze my speech "
        "and synthesize translated audio exclusively in my personal authorized voice during real-time calls."
    )
    sample_speech = generate_synthesized_pcm("This is Kavita enrolling my voice profile sample", duration_per_char=0.09)
    
    consent = await profile_service.record_consent(
        user_id=user_id,
        statement_text=consent_statement,
        audio_signature_bytes=sample_speech,
    )
    assert consent.consent_id.startswith(f"consent_{user_id}_")
    assert consent.is_revoked is False
    assert len(consent.signature_hash) == 64

    # 2. Step 2: Audio Quality Validation
    quality_metrics = await profile_service.validate_audio_quality(sample_speech)
    assert quality_metrics.is_acceptable is True
    assert quality_metrics.duration_sec >= 3.0
    assert quality_metrics.snr_db > 12.0
    assert quality_metrics.clipping_rate < 0.03

    # 3. Step 3: Secure Profile Creation
    profile = await profile_service.create_profile(
        user_id=user_id,
        display_name=display_name,
        consent_id=consent.consent_id,
        audio_sample_bytes=sample_speech,
        native_language=Language.HINDI,
    )
    assert profile.status == VoiceProfileStatus.READY
    assert profile.voice_id.startswith(f"vp_{user_id}_")
    assert profile.quality_metrics.is_acceptable is True

    # 4. Step 4: Voice Synthesis with Authorized Profile
    tts = MockVoiceSynthesizer(simulated_latency_ms=20.0)
    synthesized_audio = await tts.synthesize(
        text="Hello, thank you for joining the call.",
        voice_profile=profile,
        target_language=Language.ENGLISH,
    )
    assert synthesized_audio is not None
    assert len(synthesized_audio) > 0
    assert synthesized_audio.startswith(b"RIFF")

    # 5. Step 5: Complete Voice Deletion & Revocation (GDPR Compliance)
    deleted = await profile_service.delete_profile(user_id)
    assert deleted is True
    assert await profile_service.get_profile(user_id) is None
