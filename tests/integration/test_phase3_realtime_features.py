"""
Integration Tests: Phase 3 Realtime WebRTC Sessions, Interruption Handling, and Reconnection
"""

import json
from unittest.mock import AsyncMock
import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.core.vad import EnergyVAD
from backend.domain.models import Language, Participant


@pytest.fixture
def session_gateway():
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
    return SessionGateway(pipeline=pipeline)


@pytest.mark.asyncio
async def test_turn_interruption_event_dispatch(session_gateway):
    session = session_gateway.create_session(host_user_id="user_1", room_code="ROOM_INTERRUPT")
    ws_1 = AsyncMock()
    ws_2 = AsyncMock()

    p_1 = Participant(participant_id="user_1", user_id="user_1", display_name="User 1")
    p_2 = Participant(participant_id="user_2", user_id="user_2", display_name="User 2")

    await session_gateway.register_participant(session.session_id, p_1, ws_1)
    await session_gateway.register_participant(session.session_id, p_2, ws_2)

    ws_1.send_text.reset_mock()
    ws_2.send_text.reset_mock()

    # Trigger interruption from User 2
    await session_gateway.interrupt_session(session.session_id, interrupter_id="user_2")

    # Verify both participants receive interrupt_playback event
    assert ws_1.send_text.called
    assert ws_2.send_text.called
    
    call_args_1 = json.loads(ws_1.send_text.call_args[0][0])
    assert call_args_1["event"] == "interrupt_playback"
    assert call_args_1["data"]["interrupter_id"] == "user_2"


@pytest.mark.asyncio
async def test_webrtc_signaling_routing(session_gateway):
    session = session_gateway.create_session(host_user_id="user_alice", room_code="ROOM_WEBRTC")
    ws_alice = AsyncMock()
    ws_bob = AsyncMock()

    p_alice = Participant(participant_id="user_alice", user_id="user_alice", display_name="Alice")
    p_bob = Participant(participant_id="user_bob", user_id="user_bob", display_name="Bob")

    await session_gateway.register_participant(session.session_id, p_alice, ws_alice)
    await session_gateway.register_participant(session.session_id, p_bob, ws_bob)

    ws_alice.send_text.reset_mock()
    ws_bob.send_text.reset_mock()

    # Alice sends WebRTC SDP offer targeted to Bob
    offer_sdp = {"type": "offer", "sdp": "v=0\r\no=alice 123456 ..."}
    await session_gateway.handle_webrtc_signal(
        session_id=session.session_id,
        sender_id="user_alice",
        signal_type="offer",
        signal_data=offer_sdp,
        target_id="user_bob",
    )

    # Bob should receive the signal, Alice should not
    assert ws_bob.send_text.called
    assert not ws_alice.send_text.called

    msg = json.loads(ws_bob.send_text.call_args[0][0])
    assert msg["event"] == "webrtc_signal"
    assert msg["data"]["signal_type"] == "offer"
    assert msg["data"]["sender_id"] == "user_alice"
    assert msg["data"]["data"]["sdp"] == offer_sdp["sdp"]


@pytest.mark.asyncio
async def test_reconnection_and_history_restoration(session_gateway):
    session = session_gateway.create_session(host_user_id="user_reconnect", room_code="ROOM_RECONNECT")
    ws_initial = AsyncMock()
    p = Participant(participant_id="user_reconnect", user_id="user_reconnect", display_name="Reconnecting User")

    await session_gateway.register_participant(session.session_id, p, ws_initial)

    # Ingest a turn to populate history
    await session_gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_reconnect",
        audio_bytes=b"\x00\x01" * 1600,
        transcript_override="Kal 11 baje meeting rakh lete hain",
    )

    # Simulate disconnect and reconnect with a new websocket connection
    ws_reconnected = AsyncMock()
    await session_gateway.register_participant(session.session_id, p, ws_reconnected)

    # Verify ws_reconnected received session_reconnected event with previous history
    assert ws_reconnected.send_text.called
    first_msg = json.loads(ws_reconnected.send_text.call_args_list[0][0][0])
    assert first_msg["event"] == "session_reconnected"
    assert len(first_msg["data"]["history"]) == 1
    assert first_msg["data"]["history"][0]["source_text"] == "Kal 11 baje meeting rakh lete hain"


def test_adaptive_noise_tracking_vad():
    vad = EnergyVAD(energy_threshold_db=-38.0, silence_timeout_ms=300, adaptive_noise_tracking=True)
    
    # Process several frames of background room noise (-45 dBFS)
    # 16-bit PCM values around 180 (approx -45 dBFS)
    import struct
    noise_frame = struct.pack("<h", 180) * 320
    
    for _ in range(10):
        is_speech, turn = vad.process_chunk(noise_frame)
        assert is_speech is False
        assert turn is None

    # Noise floor should have adapted
    assert vad.current_threshold_db >= -38.0
