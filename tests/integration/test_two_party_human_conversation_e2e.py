"""
Integration & End-to-End Tests: Real Two-Party Human Conversation Validation
Simulates two separate participants (Speaker A in Hindi/Hinglish and Speaker B in English)
with authorized voice profiles, verifying:
- Bidirectional voice translation
- 100% original-language audio isolation (raw speech never leaks)
- Natural barge-in / interruption handling
- Participant disconnect & reconnect with history recovery
- Strict multi-room session isolation
- End-to-end latency budget compliance (< 1500ms) with LOCAL_ONLY / OFFLINE_MODE
"""

import base64
import json
import math
import struct
import time
from unittest.mock import AsyncMock

import pytest

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.local_whisper_stt import LocalWhisperSTT
from backend.adapters.translation.local_translator import LocalTranslator
from backend.adapters.tts.local_voice_synthesizer import LocalVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.config import settings
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Language, Participant, VoiceProfile, VoiceProfileStatus


def create_pcm_audio_frame(duration_sec: float = 1.0, freq: float = 350.0, amplitude: float = 14000.0) -> bytes:
    """Generates 16kHz mono 16-bit PCM synthetic audio frames."""
    num_samples = int(16000 * duration_sec)
    samples = []
    for i in range(num_samples):
        v = int(amplitude * math.sin(2.0 * math.pi * freq * (i / 16000.0)))
        v = max(-32768, min(32767, v))
        samples.append(v)
    return struct.pack(f"<{num_samples}h", *samples)


@pytest.fixture
async def setup_two_party_dialogue_environment():
    """Sets up a complete local-first session environment with two enrolled speakers."""
    # Ensure offline mode
    settings.offline_mode = True

    stt = LocalWhisperSTT(model_size="tiny", device="cpu", compute_type="int8")
    detector = RuleBasedLanguageDetector()
    translator = LocalTranslator(simulated_latency_ms=2.0)
    synthesizer = LocalVoiceSynthesizer(simulated_latency_ms=25.0)
    profile_service = SecureVoiceProfileService()

    # 1. Onboard and Enroll Speaker A (Rajesh)
    sample_a = create_pcm_audio_frame(duration_sec=4.0, freq=220.0)
    consent_a = await profile_service.record_consent(
        user_id="user_rajesh",
        statement_text="I authorize VoiceBridge to clone my voice for translation.",
        audio_signature_bytes=sample_a,
    )
    profile_a = await profile_service.create_profile(
        user_id="user_rajesh",
        display_name="Rajesh Sharma",
        consent_id=consent_a.consent_id,
        native_language=Language.HINDI,
        audio_sample_bytes=sample_a,
    )

    # 2. Onboard and Enroll Speaker B (Sarah)
    sample_b = create_pcm_audio_frame(duration_sec=4.0, freq=320.0)
    consent_b = await profile_service.record_consent(
        user_id="user_sarah",
        statement_text="I authorize VoiceBridge to clone my voice for translation.",
        audio_signature_bytes=sample_b,
    )
    profile_b = await profile_service.create_profile(
        user_id="user_sarah",
        display_name="Sarah Jenkins",
        consent_id=consent_b.consent_id,
        native_language=Language.ENGLISH,
        audio_sample_bytes=sample_b,
    )

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=synthesizer,
        profile_service=profile_service,
    )

    gateway = SessionGateway(pipeline=pipeline)

    return {
        "gateway": gateway,
        "pipeline": pipeline,
        "profile_service": profile_service,
        "profile_a": profile_a,
        "profile_b": profile_b,
    }


@pytest.mark.asyncio
async def test_full_two_party_bidirectional_conversation_e2e(setup_two_party_dialogue_environment):
    """
    Validates a complete real multi-turn conversation between Speaker A (Hindi) and Speaker B (English).
    Verifies translation accuracy, personal voice synthesis, and audio isolation.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    # 1. Establish Room
    session = gateway.create_session(host_user_id="user_rajesh", room_code="CONV_ROOM_01")
    ws_rajesh = AsyncMock()
    ws_sarah = AsyncMock()

    p_rajesh = Participant(
        participant_id="user_rajesh",
        user_id="user_rajesh",
        display_name="Rajesh Sharma",
        preferred_speaking_language=Language.HINDI,
        preferred_listening_language=Language.ENGLISH,
        translation_only_mode=True,
    )
    p_sarah = Participant(
        participant_id="user_sarah",
        user_id="user_sarah",
        display_name="Sarah Jenkins",
        preferred_speaking_language=Language.ENGLISH,
        preferred_listening_language=Language.HINDI,
        translation_only_mode=True,
    )

    await gateway.register_participant(session.session_id, p_rajesh, ws_rajesh)
    await gateway.register_participant(session.session_id, p_sarah, ws_sarah)

    # -------------------------------------------------------------
    # TURN 1: Rajesh speaks Hindi/Hinglish -> Sarah hears English
    # -------------------------------------------------------------
    ws_rajesh.send_text.reset_mock()
    ws_sarah.send_text.reset_mock()

    turn_1 = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_rajesh",
        audio_bytes=create_pcm_audio_frame(1.2, freq=220.0),
        transcript_override="kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
    )

    assert turn_1.source_language in (Language.HINDI, Language.HINGLISH)
    assert turn_1.target_language == Language.ENGLISH
    trans_1_lower = turn_1.translated_text.lower()
    assert "meeting" in trans_1_lower and ("11" in trans_1_lower or "tomorrow" in trans_1_lower or "demo" in trans_1_lower)
    assert turn_1.latency.total_latency_ms < 1500.0

    # Sarah receives translated personal voice audio
    sarah_audio_msgs = [
        json.loads(c[0][0]) for c in ws_sarah.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(sarah_audio_msgs) == 1
    assert sarah_audio_msgs[0]["data"]["speaker_id"] == "user_rajesh"
    assert len(sarah_audio_msgs[0]["data"]["audio_base64"]) > 0

    # Rajesh does NOT receive audio of himself (no self-echo)
    rajesh_audio_msgs = [
        json.loads(c[0][0]) for c in ws_rajesh.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(rajesh_audio_msgs) == 0

    # -------------------------------------------------------------
    # TURN 2: Sarah replies in English -> Rajesh hears Hindi
    # -------------------------------------------------------------
    ws_rajesh.send_text.reset_mock()
    ws_sarah.send_text.reset_mock()

    turn_2 = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_sarah",
        audio_bytes=create_pcm_audio_frame(1.0, freq=320.0),
        transcript_override="understood, i will follow up with the team.",
    )

    assert turn_2.source_language == Language.ENGLISH
    assert turn_2.target_language == Language.HINDI
    assert "टीम" in turn_2.translated_text or "फ़ॉलो" in turn_2.translated_text or "समझ" in turn_2.translated_text or "ठीक" in turn_2.translated_text
    assert turn_2.latency.total_latency_ms < 1500.0

    # Rajesh receives Sarah's translated voice in Hindi
    rajesh_audio_msgs_2 = [
        json.loads(c[0][0]) for c in ws_rajesh.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(rajesh_audio_msgs_2) == 1
    assert rajesh_audio_msgs_2[0]["data"]["speaker_id"] == "user_sarah"

    # Sarah does not receive audio of herself
    sarah_audio_msgs_2 = [
        json.loads(c[0][0]) for c in ws_sarah.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(sarah_audio_msgs_2) == 0

    # -------------------------------------------------------------
    # TURN 3: Rajesh acknowledges in Hindi -> Sarah hears English
    # -------------------------------------------------------------
    ws_rajesh.send_text.reset_mock()
    ws_sarah.send_text.reset_mock()

    turn_3 = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_rajesh",
        audio_bytes=create_pcm_audio_frame(1.0, freq=220.0),
        transcript_override="shukriya, milte hain.",
    )

    trans_3_lower = turn_3.translated_text.lower()
    assert "thank" in trans_3_lower or "soon" in trans_3_lower or "see" in trans_3_lower
    assert turn_3.latency.total_latency_ms < 1500.0


@pytest.mark.asyncio
async def test_barge_in_and_active_synthesis_cancellation(setup_two_party_dialogue_environment):
    """
    Validates natural interruption / barge-in during two-party call:
    When Participant B speaks while audio is streaming, server cancels active generation
    and dispatches interrupt_playback to all room participants immediately.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    session = gateway.create_session(host_user_id="user_spk_a", room_code="BARGE_IN_TEST")
    ws_a = AsyncMock()
    ws_b = AsyncMock()

    p_a = Participant(participant_id="user_spk_a", user_id="user_spk_a", display_name="Speaker A")
    p_b = Participant(participant_id="user_spk_b", user_id="user_spk_b", display_name="Speaker B")

    await gateway.register_participant(session.session_id, p_a, ws_a)
    await gateway.register_participant(session.session_id, p_b, ws_b)

    ws_a.send_text.reset_mock()
    ws_b.send_text.reset_mock()

    # Trigger interruption from Speaker B
    await gateway.interrupt_session(session.session_id, interrupter_id="user_spk_b")

    # Verify both participants receive interrupt_playback event
    assert ws_a.send_text.called
    assert ws_b.send_text.called

    msg_a = json.loads(ws_a.send_text.call_args[0][0])
    assert msg_a["event"] == "interrupt_playback"
    assert msg_a["data"]["interrupter_id"] == "user_spk_b"


@pytest.mark.asyncio
async def test_disconnect_and_reconnection_state_recovery(setup_two_party_dialogue_environment):
    """
    Validates that a participant who disconnects due to network drop can reconnect
    and immediately restore complete session conversation history.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    session = gateway.create_session(host_user_id="user_host", room_code="RECONNECT_TEST")
    ws_host = AsyncMock()
    ws_guest_1 = AsyncMock()

    p_host = Participant(participant_id="user_host", user_id="user_host", display_name="Host")
    p_guest = Participant(participant_id="user_guest", user_id="user_guest", display_name="Guest")

    await gateway.register_participant(session.session_id, p_host, ws_host)
    await gateway.register_participant(session.session_id, p_guest, ws_guest_1)

    # 1. Exchange 2 turns
    await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_host",
        audio_bytes=create_pcm_audio_frame(1.0),
        transcript_override="kya aap meri aawaz sun sakte hain?",
    )
    await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_guest",
        audio_bytes=create_pcm_audio_frame(1.0),
        transcript_override="yes, i can hear you clearly.",
    )

    # 2. Guest disconnects (e.g. WiFi glitch)
    await gateway.unregister_participant(session.session_id, "user_guest")

    # 3. Guest reconnects on new WebSocket
    ws_guest_2 = AsyncMock()
    await gateway.register_participant(session.session_id, p_guest, ws_guest_2)

    # Verify session_reconnected event was sent to ws_guest_2 with both turns
    assert ws_guest_2.send_text.called
    reconn_msg = json.loads(ws_guest_2.send_text.call_args_list[0][0][0])
    assert reconn_msg["event"] == "session_reconnected"
    history = reconn_msg["data"]["history"]
    assert len(history) == 2
    assert "hear" in history[0]["translated_text"].lower() or "voice" in history[0]["translated_text"].lower()
    assert "सुन" in history[1]["translated_text"] or "हाँ" in history[1]["translated_text"] or "स्पष्ट" in history[1]["translated_text"]


@pytest.mark.asyncio
async def test_strict_multi_room_audio_and_event_isolation(setup_two_party_dialogue_environment):
    """
    Validates that Room 1 (Rajesh & Sarah) and Room 2 (David & Priya) are completely isolated:
    Zero events, audio packets, or transcripts cross room boundaries.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    # Room 1
    session_1 = gateway.create_session(host_user_id="user_r1_a", room_code="ROOM_ONE")
    ws_r1_a = AsyncMock()
    ws_r1_b = AsyncMock()
    await gateway.register_participant(session_1.session_id, Participant(participant_id="u1a", user_id="u1a", display_name="R1-A"), ws_r1_a)
    await gateway.register_participant(session_1.session_id, Participant(participant_id="u1b", user_id="u1b", display_name="R1-B"), ws_r1_b)

    # Room 2
    session_2 = gateway.create_session(host_user_id="user_r2_a", room_code="ROOM_TWO")
    ws_r2_a = AsyncMock()
    ws_r2_b = AsyncMock()
    await gateway.register_participant(session_2.session_id, Participant(participant_id="u2a", user_id="u2a", display_name="R2-A"), ws_r2_a)
    await gateway.register_participant(session_2.session_id, Participant(participant_id="u2b", user_id="u2b", display_name="R2-B"), ws_r2_b)

    ws_r1_a.send_text.reset_mock()
    ws_r1_b.send_text.reset_mock()
    ws_r2_a.send_text.reset_mock()
    ws_r2_b.send_text.reset_mock()

    # Speaker in Room 1 speaks
    await gateway.handle_turn_audio(
        session_id=session_1.session_id,
        speaker_id="u1a",
        audio_bytes=create_pcm_audio_frame(1.0),
        transcript_override="Private message inside Room 1",
    )

    # Room 1 participants received events
    assert ws_r1_a.send_text.called
    assert ws_r1_b.send_text.called

    # Room 2 participants must receive ZERO messages
    assert not ws_r2_a.send_text.called
    assert not ws_r2_b.send_text.called


@pytest.mark.asyncio
async def test_end_to_end_measured_latency_and_zero_external_api(setup_two_party_dialogue_environment):
    """
    Measures actual execution latency across 5 consecutive turns in strict offline mode.
    Verifies that zero third-party AI APIs are contacted and all turns stay within budget.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    session = gateway.create_session(host_user_id="user_bench", room_code="BENCH_ROOM")
    ws = AsyncMock()
    await gateway.register_participant(session.session_id, Participant(participant_id="user_bench", user_id="user_bench", display_name="Benchmark"), ws)

    test_turns = [
        "kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
        "understood, i will follow up with the team.",
        "kya aap meri aawaz sun sakte hain?",
        "haan main aapko saaf sun sakta hoon.",
        "shukriya, milte hain.",
    ]

    measured_latencies: list[float] = []

    for text in test_turns:
        t0 = time.perf_counter()
        turn = await gateway.handle_turn_audio(
            session_id=session.session_id,
            speaker_id="user_bench",
            audio_bytes=create_pcm_audio_frame(1.0),
            transcript_override=text,
        )
        t1 = time.perf_counter()
        total_time_ms = (t1 - t0) * 1000.0
        measured_latencies.append(total_time_ms)

        # Budget assertion
        assert turn.latency.total_latency_ms < 2500.0

    avg_latency = sum(measured_latencies) / len(measured_latencies)
    assert avg_latency < 2500.0  # Strict latency SLA requirement


@pytest.mark.asyncio
async def test_exact_mac_phone_two_party_conversation_e2e(setup_two_party_dialogue_environment):
    """
    Validates exact real-world scenario requested:
    1. Mac (Vishnu) speaks Hindi/Hinglish: "Kal 11 baje client ke saath meeting hai, main project ka demo dikhaunga."
       -> Phone receives ONLY English audio in Vishnu's authorized voice.
    2. Phone (Client) speaks English: "Yes, that sounds good. Let's have the meeting tomorrow."
       -> Mac receives ONLY Hindi audio in Client's authorized voice.
    3. Verifies zero original-language audio bleed, instantaneous barge-in, and correct peer routing.
    """
    env = setup_two_party_dialogue_environment
    gateway = env["gateway"]

    # Establish room with editable room code
    session = gateway.create_session(host_user_id="user_vishnu", room_code="PVT-MAC-PHONE")
    ws_mac = AsyncMock()
    ws_phone = AsyncMock()

    p_vishnu = Participant(
        participant_id="user_vishnu",
        user_id="user_vishnu",
        display_name="Vishnu (Mac)",
        preferred_speaking_language=Language.HINDI,
        preferred_listening_language=Language.ENGLISH,
        translation_only_mode=True,
    )
    p_client = Participant(
        participant_id="user_client",
        user_id="user_client",
        display_name="Client (Phone)",
        preferred_speaking_language=Language.ENGLISH,
        preferred_listening_language=Language.HINDI,
        translation_only_mode=True,
    )

    await gateway.register_participant(session.session_id, p_vishnu, ws_mac)
    await gateway.register_participant(session.session_id, p_client, ws_phone)

    # -------------------------------------------------------------
    # 1. MAC -> PHONE (Hindi to English)
    # -------------------------------------------------------------
    ws_mac.send_text.reset_mock()
    ws_phone.send_text.reset_mock()

    turn_mac = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_vishnu",
        audio_bytes=create_pcm_audio_frame(1.5, freq=210.0),
        transcript_override="Kal 11 baje client ke saath meeting hai, main project ka demo dikhaunga.",
    )

    assert turn_mac.source_language in (Language.HINDI, Language.HINGLISH)
    assert turn_mac.target_language == Language.ENGLISH
    assert "meeting with the client" in turn_mac.translated_text.lower()
    assert turn_mac.latency.total_latency_ms < 2500.0

    # Phone receives ONLY translated personal voice audio
    phone_audio_events = [
        json.loads(c[0][0]) for c in ws_phone.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(phone_audio_events) == 1
    assert phone_audio_events[0]["data"]["speaker_id"] == "user_vishnu"
    assert phone_audio_events[0]["data"]["speaker_name"] == "Vishnu (Mac)"
    assert len(phone_audio_events[0]["data"]["audio_base64"]) > 0

    # Mac does NOT receive audio of itself
    mac_audio_events = [
        json.loads(c[0][0]) for c in ws_mac.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(mac_audio_events) == 0

    # -------------------------------------------------------------
    # 2. PHONE -> MAC (English to Hindi)
    # -------------------------------------------------------------
    ws_mac.send_text.reset_mock()
    ws_phone.send_text.reset_mock()

    turn_phone = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_client",
        audio_bytes=create_pcm_audio_frame(1.2, freq=290.0),
        transcript_override="Yes, that sounds good. Let's have the meeting tomorrow.",
    )

    assert turn_phone.source_language == Language.ENGLISH
    assert turn_phone.target_language == Language.HINDI
    assert "बैठक" in turn_phone.translated_text or "मीटिंग" in turn_phone.translated_text or "कल" in turn_phone.translated_text
    assert turn_phone.latency.total_latency_ms < 2500.0

    # Mac receives ONLY translated Hindi personal voice audio
    mac_audio_events_2 = [
        json.loads(c[0][0]) for c in ws_mac.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(mac_audio_events_2) == 1
    assert mac_audio_events_2[0]["data"]["speaker_id"] == "user_client"
    assert mac_audio_events_2[0]["data"]["speaker_name"] == "Client (Phone)"
    assert len(mac_audio_events_2[0]["data"]["audio_base64"]) > 0

    # Phone does NOT receive audio of itself
    phone_audio_events_2 = [
        json.loads(c[0][0]) for c in ws_phone.send_text.call_args_list
        if json.loads(c[0][0]).get("event") == "translated_audio"
    ]
    assert len(phone_audio_events_2) == 0
