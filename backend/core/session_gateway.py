"""
Realtime Session Gateway & Isolation Manager
Manages WebRTC / WebSocket rooms, participant state, and guarantees strict session audio isolation.
"""

import asyncio
from datetime import datetime, timezone
import json
from typing import Dict, List, Optional, Set
from fastapi import WebSocket

from backend.core.pipeline import TranslationPipeline
from backend.domain.models import (
    ConversationSession,
    Language,
    Participant,
    Turn,
)


class SessionGateway:
    """
    Manages active calling rooms and realtime communication.
    Guarantees session boundaries and translation-only delivery.
    """

    def __init__(self, pipeline: TranslationPipeline):
        self.pipeline = pipeline
        self._sessions: Dict[str, ConversationSession] = {}
        self._active_connections: Dict[str, Dict[str, WebSocket]] = {}  # session_id -> {participant_id: ws}
        self._conversation_history: Dict[str, List[Turn]] = {}  # session_id -> turns

    def create_session(self, host_user_id: str, room_code: Optional[str] = None) -> ConversationSession:
        import uuid
        session_id = f"sess_{uuid.uuid4().hex[:10]}"
        room_code = room_code or uuid.uuid4().hex[:6].upper()

        session = ConversationSession(
            session_id=session_id,
            room_code=room_code,
            host_user_id=host_user_id,
            participants={},
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self._sessions[session_id] = session
        self._active_connections[session_id] = {}
        self._conversation_history[session_id] = []
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        return self._sessions.get(session_id)

    def get_session_by_code(self, room_code: str) -> Optional[ConversationSession]:
        for s in self._sessions.values():
            if s.room_code.upper() == room_code.upper() and s.is_active:
                return s
        return None

    async def register_participant(
        self,
        session_id: str,
        participant: Participant,
        websocket: WebSocket,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return False

        session.participants[participant.participant_id] = participant
        self._active_connections[session_id][participant.participant_id] = websocket

        # Broadcast room state to all members in THIS session only
        await self.broadcast_event(
            session_id=session_id,
            event_type="participant_joined",
            payload={
                "participant_id": participant.participant_id,
                "display_name": participant.display_name,
                "participants": [
                    {
                        "participant_id": p.participant_id,
                        "display_name": p.display_name,
                        "speaking_language": p.preferred_speaking_language,
                        "listening_language": p.preferred_listening_language,
                    }
                    for p in session.participants.values()
                ],
            },
        )
        return True

    async def unregister_participant(self, session_id: str, participant_id: str):
        if session_id in self._active_connections:
            self._active_connections[session_id].pop(participant_id, None)

        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.participants.pop(participant_id, None)

            if len(session.participants) == 0:
                session.is_active = False
                session.ended_at = datetime.now(timezone.utc)
            else:
                await self.broadcast_event(
                    session_id=session_id,
                    event_type="participant_left",
                    payload={"participant_id": participant_id},
                )

    async def broadcast_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict,
        exclude_participant_id: Optional[str] = None,
    ):
        """Dispatches JSON events strictly to clients within the given session."""
        connections = self._active_connections.get(session_id, {})
        dead_connections: List[str] = []

        message_str = json.dumps({"event": event_type, "data": payload})

        for pid, ws in connections.items():
            if exclude_participant_id and pid == exclude_participant_id:
                continue
            try:
                await ws.send_text(message_str)
            except Exception:
                dead_connections.append(pid)

        for pid in dead_connections:
            await self.unregister_participant(session_id, pid)

    async def handle_turn_audio(
        self,
        session_id: str,
        speaker_id: str,
        audio_bytes: bytes,
        transcript_override: Optional[str] = None,
    ) -> Turn:
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            raise ValueError(f"Session {session_id} is inactive or not found.")

        speaker = session.participants.get(speaker_id)
        speaker_name = speaker.display_name if speaker else "User"
        source_lang = speaker.preferred_speaking_language if speaker else Language.HINDI

        # Get context of previous turns in this session
        history = self._conversation_history.get(session_id, [])
        context_payload = [
            {"speaker": t.speaker_name, "text": t.translated_text}
            for t in history[-5:]
        ]

        turn, synthesized_audio = await self.pipeline.process_turn(
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            audio_bytes=audio_bytes,
            source_language_hint=source_lang,
            conversation_context=context_payload,
            transcript_override=transcript_override,
        )

        history.append(turn)

        # Broadcast turn results to room participants
        # 1. Send text event to everyone
        await self.broadcast_event(
            session_id=session_id,
            event_type="turn_completed",
            payload={
                "turn_id": turn.turn_id,
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "source_language": turn.source_language,
                "target_language": turn.target_language,
                "source_text": turn.source_text,
                "translated_text": turn.translated_text,
                "confidence": turn.confidence,
                "latency": turn.latency.model_dump(),
            },
        )

        # 2. In Translation-Only Mode: Send translated personal voice audio to listeners
        # (Listeners receive translated audio in speaker's authorized personal voice)
        if synthesized_audio and len(synthesized_audio) > 0:
            import base64
            audio_b64 = base64.b64encode(synthesized_audio).decode("ascii")
            
            # Send audio payload to other participants (the listeners)
            for pid, ws in self._active_connections.get(session_id, {}).items():
                if pid != speaker_id:
                    try:
                        await ws.send_text(
                            json.dumps({
                                "event": "translated_audio",
                                "data": {
                                    "turn_id": turn.turn_id,
                                    "speaker_id": speaker_id,
                                    "audio_base64": audio_b64,
                                    "mime_type": "audio/wav",
                                }
                            })
                        )
                    except Exception:
                        pass

        return turn
