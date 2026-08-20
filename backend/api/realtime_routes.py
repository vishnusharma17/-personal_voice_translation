"""
Realtime Room and WebSocket Gateway API Routes
"""

import base64
import json

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from backend.adapters.factory import (
    get_language_detector,
    get_stt_adapter,
    get_translator_adapter,
    get_tts_adapter,
    get_voice_profile_service,
)
from backend.core.pipeline import TranslationPipeline
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Language, Participant

router = APIRouter(tags=["Realtime Gateway"])

# Initialize providers and pipeline via factory
voice_profile_service = get_voice_profile_service()
stt_adapter = get_stt_adapter()
lang_detector = get_language_detector()
translator_adapter = get_translator_adapter()
tts_adapter = get_tts_adapter()

pipeline = TranslationPipeline(
    stt=stt_adapter,
    lang_detector=lang_detector,
    translator=translator_adapter,
    tts=tts_adapter,
    profile_service=voice_profile_service,
)

session_gateway = SessionGateway(pipeline=pipeline)


class CreateRoomRequest(BaseModel):
    host_user_id: str
    room_code: str | None = None


class CreateRoomResponse(BaseModel):
    session_id: str
    room_code: str
    host_user_id: str


class TranslateTurnRequest(BaseModel):
    session_id: str | None = "demo_session"
    speaker_id: str = "user_1"
    speaker_name: str = "Speaker A"
    text_prompt: str | None = None
    audio_base64: str | None = None
    source_language: str | None = "hi"
    target_language: str | None = "en"


@router.post("/api/rooms/create", response_model=CreateRoomResponse)
async def create_room(req: CreateRoomRequest):
    session = session_gateway.create_session(host_user_id=req.host_user_id, room_code=req.room_code)
    return CreateRoomResponse(
        session_id=session.session_id,
        room_code=session.room_code,
        host_user_id=session.host_user_id,
    )


@router.get("/api/rooms/{room_code}")
async def get_room(room_code: str):
    session = session_gateway.get_session_by_code(room_code)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found or expired.")
    return {
        "session_id": session.session_id,
        "room_code": session.room_code,
        "is_active": session.is_active,
        "participants_count": len(session.participants),
        "participants": [
            {
                "participant_id": p.participant_id,
                "display_name": p.display_name,
                "speaking_language": p.preferred_speaking_language,
                "listening_language": p.preferred_listening_language,
            }
            for p in session.participants.values()
        ],
    }


@router.post("/api/pipeline/translate-turn")
async def direct_translate_turn(req: TranslateTurnRequest):
    """Direct testing endpoint for voice translation pipeline."""
    audio_bytes = b""
    if req.audio_base64:
        try:
            audio_bytes = base64.b64decode(req.audio_base64)
        except Exception:
            pass

    src_lang = Language(req.source_language) if req.source_language in [l.value for l in Language] else Language.HINDI
    tgt_lang = Language(req.target_language) if req.target_language in [l.value for l in Language] else Language.ENGLISH

    turn, synth_audio = await pipeline.process_turn(
        session_id=req.session_id or "demo_session",
        speaker_id=req.speaker_id,
        speaker_name=req.speaker_name,
        audio_bytes=audio_bytes,
        source_language_hint=src_lang,
        target_language_preference=tgt_lang,
        transcript_override=req.text_prompt,
    )

    audio_b64 = base64.b64encode(synth_audio).decode("ascii") if synth_audio else ""

    return {
        "turn": turn.model_dump(),
        "synthesized_audio_base64": audio_b64,
        "mime_type": "audio/wav",
    }


@router.websocket("/ws/call/{room_code}")
async def websocket_call_endpoint(
    websocket: WebSocket,
    room_code: str,
    user_id: str = "guest",
    display_name: str = "Guest",
    speaking_lang: str = "hi",
    listening_lang: str = "en",
):
    await websocket.accept()

    # Find or auto-create session for room_code
    session = session_gateway.get_session_by_code(room_code)
    if not session:
        session = session_gateway.create_session(host_user_id=user_id, room_code=room_code)

    participant = Participant(
        participant_id=user_id,
        user_id=user_id,
        display_name=display_name,
        preferred_speaking_language=Language(speaking_lang) if speaking_lang in [l.value for l in Language] else Language.HINDI,
        preferred_listening_language=Language(listening_lang) if listening_lang in [l.value for l in Language] else Language.ENGLISH,
        translation_only_mode=True,
    )

    registered = await session_gateway.register_participant(session.session_id, participant, websocket)
    if not registered:
        await websocket.close(code=1008, reason="Could not register into session")
        return

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
            except Exception:
                continue

            event_type = data.get("type", "")
            
            if event_type == "audio_turn":
                # Audio turn received from client
                audio_b64 = data.get("audio_base64", "")
                text_override = data.get("text_override")
                audio_bytes = base64.b64decode(audio_b64) if audio_b64 else b""

                await session_gateway.handle_turn_audio(
                    session_id=session.session_id,
                    speaker_id=user_id,
                    audio_bytes=audio_bytes,
                    transcript_override=text_override,
                )

            elif event_type == "interrupt":
                # Explicit user interruption / barge-in
                await session_gateway.interrupt_session(session.session_id, interrupter_id=user_id)

            elif event_type == "webrtc_signal":
                # Route WebRTC SDP offer, answer, or ICE candidate to room peers
                signal_type = data.get("signal_type", "candidate")
                signal_data = data.get("signal_data", {})
                target_id = data.get("target_id")
                await session_gateway.handle_webrtc_signal(
                    session_id=session.session_id,
                    sender_id=user_id,
                    signal_type=signal_type,
                    signal_data=signal_data,
                    target_id=target_id,
                )

            elif event_type == "ping":
                await websocket.send_text(json.dumps({"event": "pong", "timestamp": data.get("timestamp")}))

    except WebSocketDisconnect:
        await session_gateway.unregister_participant(session.session_id, user_id)
    except Exception:
        await session_gateway.unregister_participant(session.session_id, user_id)
