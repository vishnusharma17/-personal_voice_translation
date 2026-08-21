"""
Integration Tests: Strict Session Isolation & Cross-Session Audio Leakage Prevention
"""

from unittest.mock import AsyncMock

import pytest

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Participant


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


@pytest.mark.asyncio
async def test_custom_room_codes_bidirectional_and_isolation():
    """
    Verify user-entered custom room codes:
    1. Participants using the same custom room code (e.g. PVT-YRTIOV) connect to each other.
    2. Participants using different custom room codes (e.g. PVT-YRTIOV vs CLIENT-001) cannot connect or hear each other.
    """
    stt = MockSpeechRecognizer(simulated_latency_ms=5.0)
    detector = RuleBasedLanguageDetector()
    translator = MockTranslator()
    tts = MockVoiceSynthesizer(simulated_latency_ms=5.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    gateway = SessionGateway(pipeline=pipeline)

    # 1. Device A and Device B connect to custom Room Code 'PVT-YRTIOV'
    session_yrtiov = gateway.create_session(host_user_id="user_mac_1", room_code="PVT-YRTIOV")
    ws_mac_1 = AsyncMock()
    ws_phone_1 = AsyncMock()

    p_mac_1 = Participant(participant_id="user_mac_1", user_id="user_mac_1", display_name="Mac User (PVT-YRTIOV)")
    p_phone_1 = Participant(participant_id="user_phone_1", user_id="user_phone_1", display_name="Phone User (PVT-YRTIOV)")

    await gateway.register_participant(session_yrtiov.session_id, p_mac_1, ws_mac_1)
    await gateway.register_participant(session_yrtiov.session_id, p_phone_1, ws_phone_1)

    # 2. Device C connects to separate custom Room Code 'CLIENT-001'
    session_client = gateway.create_session(host_user_id="user_client_1", room_code="CLIENT-001")
    ws_client_1 = AsyncMock()

    p_client_1 = Participant(participant_id="user_client_1", user_id="user_client_1", display_name="Client 001 User")
    await gateway.register_participant(session_client.session_id, p_client_1, ws_client_1)

    # Reset mock call counters after join broadcasts
    ws_mac_1.send_text.reset_mock()
    ws_phone_1.send_text.reset_mock()
    ws_client_1.send_text.reset_mock()

    # 3. Speak turn in PVT-YRTIOV
    stt.set_next_transcript("Kal 11 baje meeting rakh lete hain")
    await gateway.handle_turn_audio(
        session_id=session_yrtiov.session_id,
        speaker_id="user_mac_1",
        audio_bytes=b"\x00\x02" * 800,
    )

    # Verify both participants in PVT-YRTIOV received events
    assert ws_mac_1.send_text.called
    assert ws_phone_1.send_text.called

    # Verify CLIENT-001 received ZERO events
    assert not ws_client_1.send_text.called

    # 4. Speak turn in CLIENT-001
    ws_mac_1.send_text.reset_mock()
    ws_phone_1.send_text.reset_mock()
    ws_client_1.send_text.reset_mock()

    stt.set_next_transcript("Hello client, welcome to the room.")
    await gateway.handle_turn_audio(
        session_id=session_client.session_id,
        speaker_id="user_client_1",
        audio_bytes=b"\x00\x03" * 800,
    )

    # Verify CLIENT-001 received its own turn event
    assert ws_client_1.send_text.called

    # Verify PVT-YRTIOV participants received ZERO events from CLIENT-001
    assert not ws_mac_1.send_text.called
    assert not ws_phone_1.send_text.called
