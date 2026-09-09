"""
Integration Test for Multi-Party Group Conversations (>2 Participants)
"""

from pathlib import Path
import pytest
from unittest.mock import AsyncMock

from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Language, Participant
from backend.adapters.stt.mock_stt import MockSpeechRecognizer as MockWhisperSTT
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService


@pytest.mark.asyncio
async def test_multi_party_group_conversation_broadcasting():
    stt = MockWhisperSTT()
    lang_det = RuleBasedLanguageDetector()
    translator = MockTranslator()
    synthesizer = MockVoiceSynthesizer()
    profile_service = SecureVoiceProfileService(storage_dir=Path("data/voice_profiles"))

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=lang_det,
        translator=translator,
        tts=synthesizer,
        profile_service=profile_service,
    )
    gateway = SessionGateway(pipeline)

    session = gateway.create_session(host_user_id="user_host", room_code="GROUP_ROOM_3P")

    ws_host = AsyncMock()
    ws_guest1 = AsyncMock()
    ws_guest2 = AsyncMock()

    p_host = Participant(
        participant_id="p_host",
        user_id="user_host",
        display_name="Rajesh (Hindi)",
        preferred_speaking_language=Language.HINDI,
        preferred_listening_language=Language.ENGLISH,
    )
    p_guest1 = Participant(
        participant_id="p_guest1",
        user_id="user_guest1",
        display_name="Sarah (English)",
        preferred_speaking_language=Language.ENGLISH,
        preferred_listening_language=Language.SPANISH,
    )
    p_guest2 = Participant(
        participant_id="p_guest2",
        user_id="user_guest2",
        display_name="Carlos (Spanish)",
        preferred_speaking_language=Language.SPANISH,
        preferred_listening_language=Language.ENGLISH,
    )

    await gateway.register_participant(session.session_id, p_host, ws_host)
    await gateway.register_participant(session.session_id, p_guest1, ws_guest1)
    await gateway.register_participant(session.session_id, p_guest2, ws_guest2)

    assert len(session.participants) == 3

    # Host speaks in Hindi
    audio_frame = b"\x00\x00" * 8000
    turn = await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="p_host",
        audio_bytes=audio_frame,
        transcript_override="kal 11 baje meeting hai",
    )

    assert turn is not None
    assert turn.speaker_id == "p_host"
    # Verify events broadcasted to guest1 and guest2
    assert ws_guest1.send_text.called
    assert ws_guest2.send_text.called
