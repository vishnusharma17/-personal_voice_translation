"""
Integration Tests: Strict Session Isolation & Cross-Session Audio Leakage Prevention
"""

from unittest.mock import AsyncMock
import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Language, Participant


@pytest.mark.asyncio
async def test_session_isolation_guarantee():
    stt = MockSpeechRecognizer(simulated_latency_ms=10.0)
    detector = RuleBasedLanguageDetector()
    translator = MockTranslator()
    tts = MockVoiceSynthesizer(simulated_latency_ms=10.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    gateway = SessionGateway(pipeline=pipeline)

    # 1. Create Room A
    session_a = gateway.create_session(host_user_id="user_a1", room_code="ROOM_A")
    ws_a1 = AsyncMock()
    ws_a2 = AsyncMock()
    
    p_a1 = Participant(participant_id="user_a1", user_id="user_a1", display_name="Alice (Room A)")
    p_a2 = Participant(participant_id="user_a2", user_id="user_a2", display_name="Bob (Room A)")
    
    await gateway.register_participant(session_a.session_id, p_a1, ws_a1)
    await gateway.register_participant(session_a.session_id, p_a2, ws_a2)

    # 2. Create Room B (Isolated)
    session_b = gateway.create_session(host_user_id="user_b1", room_code="ROOM_B")
    ws_b1 = AsyncMock()
    
    p_b1 = Participant(participant_id="user_b1", user_id="user_b1", display_name="Charlie (Room B)")
    await gateway.register_participant(session_b.session_id, p_b1, ws_b1)

    # Clear join broadcast mocks
    ws_a1.send_text.reset_mock()
    ws_a2.send_text.reset_mock()
    ws_b1.send_text.reset_mock()

    # 3. Speaker A1 speaks in Room A
    stt.set_next_transcript("kya aap meri aawaz sun sakte hain?")
    await gateway.handle_turn_audio(
        session_id=session_a.session_id,
        speaker_id="user_a1",
        audio_bytes=b"\x00\x01" * 1600,
    )

    # 4. Verify Room A received events
    assert ws_a1.send_text.called  # Received turn completed
    assert ws_a2.send_text.called  # Received turn completed and translated audio

    # 5. Verify Room B received absolutely nothing (Zero cross-session leakage)
    assert not ws_b1.send_text.called
