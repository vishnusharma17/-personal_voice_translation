"""
Unit Tests: Domain Models
"""

from backend.domain.models import (
    Language,
    LatencyBreakdown,
    Participant,
    Turn,
)


def test_latency_breakdown_total():
    lat = LatencyBreakdown(vad_ms=45.5, stt_ms=120.0, translation_ms=180.2, tts_ms=150.3)
    total = lat.compute_total()
    assert total == 496.0
    assert lat.total_latency_ms == 496.0


def test_turn_model_creation():
    turn = Turn(
        turn_id="turn_123",
        session_id="sess_abc",
        speaker_id="user_1",
        speaker_name="Raj",
        source_language=Language.HINGLISH,
        target_language=Language.ENGLISH,
        source_text="Kal 11 baje meeting rakh lete hain",
        translated_text="Let's schedule the meeting for 11 tomorrow",
        confidence=0.98,
    )
    assert turn.turn_id == "turn_123"
    assert turn.source_language == Language.HINGLISH
    assert turn.target_language == Language.ENGLISH
    assert turn.confidence == 0.98


def test_participant_translation_only_mode():
    p = Participant(
        participant_id="p_1",
        user_id="u_1",
        display_name="Sarah",
        preferred_speaking_language=Language.ENGLISH,
        preferred_listening_language=Language.HINDI,
        translation_only_mode=True,
    )
    assert p.translation_only_mode is True
    assert p.preferred_speaking_language == Language.ENGLISH
