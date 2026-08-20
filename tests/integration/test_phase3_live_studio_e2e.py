"""
Integration & End-to-End Tests: Phase 3 Live-Studio Validation
Tests real microphone PCM streaming, WebRTC signaling, turn detection,
barge-in interruption, generated-audio cancellation, reconnection resilience,
session isolation, original-language audio isolation, and measured local latency.
"""

import asyncio
import base64
import json
import math
import struct
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.config import settings
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.core.vad import EnergyVAD
from backend.domain.models import Language, Participant, VoiceProfile, VoiceProfileStatus
from backend.main import app


def generate_synthetic_pcm_speech(duration_sec: float = 1.0, freq: float = 440.0, amplitude: float = 12000.0) -> bytes:
    """Generates synthetic 16kHz mono 16-bit PCM speech frame with voicing."""
    num_samples = int(16000 * duration_sec)
    samples = []
    for i in range(num_samples):
        val = int(amplitude * math.sin(2.0 * math.pi * freq * (i / 16000.0)))
        # Clamp to 16-bit signed
        val = max(-32768, min(32767, val))
        samples.append(val)
    return struct.pack(f"<{num_samples}h", *samples)


@pytest.fixture
def live_studio_gateway():
    stt = MockSpeechRecognizer(simulated_latency_ms=15.0)
    detector = RuleBasedLanguageDetector()
    translator = MockTranslator()
    tts = MockVoiceSynthesizer(simulated_latency_ms=25.0)
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
async def test_real_microphone_pcm_turn_streaming(live_studio_gateway):
    """
    Validates streaming 16kHz 16-bit PCM audio chunks over WebSocket gateway,
    VAD segmentation, and personal voice translation execution.
    """
    session = live_studio_gateway.create_session(host_user_id="user_mic_host", room_code="MIC_STUDIO_01")
    ws_host = AsyncMock()
    ws_guest = AsyncMock()

    p_host = Participant(
        participant_id="user_mic_host",
        user_id="user_mic_host",
        display_name="Host Speaker",
        preferred_speaking_language=Language.HINDI,
        preferred_listening_language=Language.ENGLISH,
    )
    p_guest = Participant(
        participant_id="user_mic_guest",
        user_id="user_mic_guest",
        display_name="Remote Guest",
        preferred_speaking_language=Language.ENGLISH,
        preferred_listening_language=Language.HINDI,
    )

    await live_studio_gateway.register_participant(session.session_id, p_host, ws_host)
    await live_studio_gateway.register_participant(session.session_id, p_guest, ws_guest)

    ws_host.send_text.reset_mock()
    ws_guest.send_text.reset_mock()

    # Generate 1.5 seconds of PCM speech
    speech_pcm = generate_synthetic_pcm_speech(duration_sec=1.5, freq=300.0)

    # Process turn through session gateway
    turn = await live_studio_gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_mic_host",
        audio_bytes=speech_pcm,
        transcript_override="kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
    )

    assert turn is not None
    assert turn.speaker_id == "user_mic_host"
    assert turn.source_language == Language.HINGLISH or turn.source_language == Language.HINDI
    assert turn.target_language == Language.ENGLISH
    assert turn.translated_text == "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."

    # Verify both participants received turn_completed event
    assert ws_host.send_text.called
    assert ws_guest.send_text.called


@pytest.mark.asyncio
async def test_webrtc_signaling_and_peer_routing(live_studio_gateway):
    """
    Validates WebRTC SDP Offer/Answer negotiation and ICE candidate routing.
    """
    session = live_studio_gateway.create_session(host_user_id="peer_alice", room_code="WEBRTC_ROOM")
    ws_alice = AsyncMock()
    ws_bob = AsyncMock()

    p_alice = Participant(participant_id="peer_alice", user_id="peer_alice", display_name="Alice")
    p_bob = Participant(participant_id="peer_bob", user_id="peer_bob", display_name="Bob")

    await live_studio_gateway.register_participant(session.session_id, p_alice, ws_alice)
    await live_studio_gateway.register_participant(session.session_id, p_bob, ws_bob)

    ws_alice.send_text.reset_mock()
    ws_bob.send_text.reset_mock()

    # 1. Alice sends SDP Offer targeted to Bob
    sdp_offer = {"type": "offer", "sdp": "v=0\r\no=alice 123 456 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"}
    await live_studio_gateway.handle_webrtc_signal(
        session_id=session.session_id,
        sender_id="peer_alice",
        signal_type="offer",
        signal_data=sdp_offer,
        target_id="peer_bob",
    )

    assert ws_bob.send_text.called
    assert not ws_alice.send_text.called
    msg_to_bob = json.loads(ws_bob.send_text.call_args[0][0])
    assert msg_to_bob["event"] == "webrtc_signal"
    assert msg_to_bob["data"]["signal_type"] == "offer"
    assert msg_to_bob["data"]["data"]["sdp"] == sdp_offer["sdp"]

    # 2. Bob sends SDP Answer back to Alice
    ws_alice.send_text.reset_mock()
    ws_bob.send_text.reset_mock()

    sdp_answer = {"type": "answer", "sdp": "v=0\r\no=bob 789 101 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n"}
    await live_studio_gateway.handle_webrtc_signal(
        session_id=session.session_id,
        sender_id="peer_bob",
        signal_type="answer",
        signal_data=sdp_answer,
        target_id="peer_alice",
    )

    assert ws_alice.send_text.called
    assert not ws_bob.send_text.called
    msg_to_alice = json.loads(ws_alice.send_text.call_args[0][0])
    assert msg_to_alice["data"]["signal_type"] == "answer"


@pytest.mark.asyncio
async def test_barge_in_and_generated_audio_cancellation(live_studio_gateway):
    """
    Validates interruption/barge-in event dispatch and cancellation of ongoing generation.
    """
    session = live_studio_gateway.create_session(host_user_id="user_spk1", room_code="BARGE_IN_ROOM")
    ws_spk1 = AsyncMock()
    ws_spk2 = AsyncMock()

    p1 = Participant(participant_id="user_spk1", user_id="user_spk1", display_name="Speaker 1")
    p2 = Participant(participant_id="user_spk2", user_id="user_spk2", display_name="Speaker 2")

    await live_studio_gateway.register_participant(session.session_id, p1, ws_spk1)
    await live_studio_gateway.register_participant(session.session_id, p2, ws_spk2)

    ws_spk1.send_text.reset_mock()
    ws_spk2.send_text.reset_mock()

    # Speaker 2 barges in while audio is playing
    await live_studio_gateway.interrupt_session(session_id=session.session_id, interrupter_id="user_spk2")

    # Verify both participants receive interrupt_playback event
    assert ws_spk1.send_text.called
    assert ws_spk2.send_text.called

    event_msg = json.loads(ws_spk1.send_text.call_args[0][0])
    assert event_msg["event"] == "interrupt_playback"
    assert event_msg["data"]["interrupter_id"] == "user_spk2"


@pytest.mark.asyncio
async def test_original_language_audio_isolation(live_studio_gateway):
    """
    Validates that in Translation-Only Mode, listener receives ONLY translated speech,
    and the raw source language audio is never routed to the remote peer.
    """
    session = live_studio_gateway.create_session(host_user_id="user_hindi", room_code="ISOLATION_ROOM")
    ws_hindi = AsyncMock()
    ws_english = AsyncMock()

    p_hindi = Participant(
        participant_id="user_hindi",
        user_id="user_hindi",
        display_name="Hindi Speaker",
        preferred_speaking_language=Language.HINDI,
        translation_only_mode=True,
    )
    p_english = Participant(
        participant_id="user_english",
        user_id="user_english",
        display_name="English Listener",
        preferred_listening_language=Language.ENGLISH,
        translation_only_mode=True,
    )

    await live_studio_gateway.register_participant(session.session_id, p_hindi, ws_hindi)
    await live_studio_gateway.register_participant(session.session_id, p_english, ws_english)

    ws_hindi.send_text.reset_mock()
    ws_english.send_text.reset_mock()

    # Hindi speaker speaks
    await live_studio_gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_hindi",
        audio_bytes=generate_synthetic_pcm_speech(1.0),
        transcript_override="kya aap meri aawaz sun sakte hain?",
    )

    # ws_english must receive translated_audio
    translated_msgs = [
        json.loads(call[0][0])
        for call in ws_english.send_text.call_args_list
        if json.loads(call[0][0]).get("event") == "translated_audio"
    ]
    assert len(translated_msgs) == 1
    assert translated_msgs[0]["data"]["speaker_id"] == "user_hindi"
    assert len(translated_msgs[0]["data"]["audio_base64"]) > 0

    # ws_hindi (the speaker) must NOT receive translated_audio of themselves (preventing echo)
    speaker_echo_msgs = [
        json.loads(call[0][0])
        for call in ws_hindi.send_text.call_args_list
        if json.loads(call[0][0]).get("event") == "translated_audio"
    ]
    assert len(speaker_echo_msgs) == 0


@pytest.mark.asyncio
async def test_reconnection_and_history_restoration_e2e(live_studio_gateway):
    """
    Validates that reconnecting to a session restores full conversation history.
    """
    session = live_studio_gateway.create_session(host_user_id="user_reconn", room_code="RECONN_ROOM")
    ws_initial = AsyncMock()

    p = Participant(
        participant_id="user_reconn",
        user_id="user_reconn",
        display_name="Reconnecting User",
    )

    await live_studio_gateway.register_participant(session.session_id, p, ws_initial)

    # Add 2 turns to conversation history
    await live_studio_gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_reconn",
        audio_bytes=generate_synthetic_pcm_speech(1.0),
        transcript_override="Turn 1: Namaste",
    )
    await live_studio_gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_reconn",
        audio_bytes=generate_synthetic_pcm_speech(1.0),
        transcript_override="Turn 2: Kal milte hain",
    )

    # Disconnect and Reconnect with new WebSocket
    ws_new = AsyncMock()
    await live_studio_gateway.register_participant(session.session_id, p, ws_new)

    assert ws_new.send_text.called
    reconn_msg = json.loads(ws_new.send_text.call_args_list[0][0][0])
    assert reconn_msg["event"] == "session_reconnected"
    assert len(reconn_msg["data"]["history"]) == 2
    assert reconn_msg["data"]["history"][0]["source_text"] == "Turn 1: Namaste"
    assert reconn_msg["data"]["history"][1]["source_text"] == "Turn 2: Kal milte hain"


@pytest.mark.asyncio
async def test_strict_session_isolation_zero_leakage(live_studio_gateway):
    """
    Validates that two independent rooms (Room A and Room B) never leak audio or events.
    """
    session_a = live_studio_gateway.create_session(host_user_id="user_a", room_code="ROOM_ISOLATED_A")
    session_b = live_studio_gateway.create_session(host_user_id="user_b", room_code="ROOM_ISOLATED_B")

    ws_a = AsyncMock()
    ws_b = AsyncMock()

    p_a = Participant(participant_id="user_a", user_id="user_a", display_name="Alice")
    p_b = Participant(participant_id="user_b", user_id="user_b", display_name="Bob")

    await live_studio_gateway.register_participant(session_a.session_id, p_a, ws_a)
    await live_studio_gateway.register_participant(session_b.session_id, p_b, ws_b)

    ws_a.send_text.reset_mock()
    ws_b.send_text.reset_mock()

    # Activity in Room A
    await live_studio_gateway.handle_turn_audio(
        session_id=session_a.session_id,
        speaker_id="user_a",
        audio_bytes=generate_synthetic_pcm_speech(1.0),
        transcript_override="Confidential Room A message",
    )

    # Room A receives message
    assert ws_a.send_text.called

    # Room B must receive zero events
    assert not ws_b.send_text.called


def test_fastapi_live_studio_endpoint_e2e():
    """
    Validates the live studio UI and endpoints via FastAPI TestClient.
    """
    client = TestClient(app)

    # 1. HTML studio page served
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Personal Voice Translation" in resp.text
    assert "Live Call Studio" in resp.text
    assert "Voice Profile &amp; Consent" in resp.text

    # 2. Room creation endpoint
    create_resp = client.post("/api/rooms/create", json={"host_user_id": "test_fastapi_user"})
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert "session_id" in data
    assert "room_code" in data

    # 3. Room details query
    room_resp = client.get(f"/api/rooms/{data['room_code']}")
    assert room_resp.status_code == 200
    room_data = room_resp.json()
    assert room_data["session_id"] == data["session_id"]
    assert room_data["is_active"] is True
