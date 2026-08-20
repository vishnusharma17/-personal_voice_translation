"""
Integration Tests: End-to-End Pipeline
"""

import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer, generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.core.pipeline import TranslationPipeline
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_end_to_end_hindi_to_english_turn():
    stt = MockSpeechRecognizer(simulated_latency_ms=40.0)
    detector = RuleBasedLanguageDetector()
    translator = MockTranslator()
    tts = MockVoiceSynthesizer(simulated_latency_ms=60.0)
    profile_service = SecureVoiceProfileService()

    # Pre-register profile
    statement = "I authorize voice synthesis."
    sample_audio = generate_synthesized_pcm("This is Raj speaking to enroll my voice profile", duration_per_char=0.08)
    consent = await profile_service.record_consent("speaker_raj", statement, sample_audio)
    await profile_service.create_profile(
        user_id="speaker_raj",
        display_name="Raj",
        consent_id=consent.consent_id,
        audio_sample_bytes=sample_audio,
        native_language=Language.HINDI,
    )

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    # Ingest audio turn
    stt.set_next_transcript("Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.")
    
    turn, synthesized_wav = await pipeline.process_turn(
        session_id="sess_integration_test",
        speaker_id="speaker_raj",
        speaker_name="Raj",
        audio_bytes=b"\x05\x00" * 16000,
        source_language_hint=Language.HINDI,
        target_language_preference=Language.ENGLISH,
    )

    assert turn.source_text == "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
    assert turn.translated_text == "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
    assert turn.source_language == Language.HINGLISH
    assert turn.target_language == Language.ENGLISH
    assert len(synthesized_wav) > 0
    assert synthesized_wav.startswith(b"RIFF")
    assert turn.latency.total_latency_ms > 0
    assert turn.latency.total_latency_ms < 1500  # Within target latency budget
