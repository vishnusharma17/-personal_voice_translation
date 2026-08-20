"""
Integration Tests: Phase 2 Real-Time Conversational Translation & Contextual Multi-Turn Pipeline
"""

import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.whisper_stt import WhisperSTT
from backend.adapters.translation.gemini_translator import GeminiTranslator
from backend.adapters.tts.elevenlabs_tts import ElevenLabsTTS
from backend.adapters.tts.mock_tts import generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.core.pipeline import TranslationPipeline
from backend.domain.models import Language


@pytest.mark.asyncio
async def test_phase2_bidirectional_conversational_dialogue():
    stt = WhisperSTT(api_key=None)
    detector = RuleBasedLanguageDetector()
    translator = GeminiTranslator(api_key=None)
    tts = ElevenLabsTTS(api_key=None)
    profile_service = SecureVoiceProfileService()

    # Enroll Speaker A (Rajesh - Hindi native)
    consent_a = await profile_service.record_consent("speaker_a", "I authorize voice synthesis", b"sample_a")
    sample_a_pcm = generate_synthesized_pcm("This is Rajesh speaking naturally to enroll his voice profile sample", duration_per_char=0.08)
    await profile_service.create_profile(
        user_id="speaker_a",
        display_name="Rajesh",
        consent_id=consent_a.consent_id,
        audio_sample_bytes=sample_a_pcm,
        native_language=Language.HINDI,
    )

    # Enroll Speaker B (Sarah - English native)
    consent_b = await profile_service.record_consent("speaker_b", "I authorize voice synthesis", b"sample_b")
    sample_b_pcm = generate_synthesized_pcm("This is Sarah speaking naturally to enroll her voice profile sample", duration_per_char=0.08)
    await profile_service.create_profile(
        user_id="speaker_b",
        display_name="Sarah",
        consent_id=consent_b.consent_id,
        audio_sample_bytes=sample_b_pcm,
        native_language=Language.ENGLISH,
    )

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    # TURN 1: Rajesh speaks Hindi/Hinglish -> Sarah receives English
    turn_1, audio_1 = await pipeline.process_turn(
        session_id="sess_phase2_call",
        speaker_id="speaker_a",
        speaker_name="Rajesh",
        audio_bytes=sample_a_pcm,
        source_language_hint=Language.HINDI,
        target_language_preference=Language.ENGLISH,
        transcript_override="Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
    )
    assert turn_1.source_text == "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
    assert turn_1.translated_text == "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
    assert turn_1.target_language == Language.ENGLISH
    assert len(audio_1) > 0
    assert turn_1.latency.total_latency_ms < 1500

    # TURN 2: Sarah responds in English -> Rajesh receives Hindi (with conversation context)
    context = [{"speaker": "Rajesh", "text": turn_1.translated_text}]
    turn_2, audio_2 = await pipeline.process_turn(
        session_id="sess_phase2_call",
        speaker_id="speaker_b",
        speaker_name="Sarah",
        audio_bytes=sample_b_pcm,
        source_language_hint=Language.ENGLISH,
        target_language_preference=Language.HINDI,
        conversation_context=context,
        transcript_override="Yes, I can hear you clearly.",
    )
    assert turn_2.source_text == "Yes, I can hear you clearly."
    assert "हाँ, मैं आपको साफ़ सुन सकता हूँ" in turn_2.translated_text
    assert turn_2.target_language == Language.HINDI
    assert len(audio_2) > 0
    assert turn_2.latency.total_latency_ms < 1500
