"""
Realtime Session Gateway & Isolation Manager
Manages WebRTC / WebSocket rooms, participant state, turn interruption handling,
reconnection resilience, and guarantees strict session audio isolation.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

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
    Manages active calling rooms, WebRTC signaling, interruption cancellation,
    and realtime communication with strict room boundaries.
    """

    def __init__(self, pipeline: TranslationPipeline):
        self.pipeline = pipeline
        self._sessions: dict[str, ConversationSession] = {}
        self._active_connections: dict[str, dict[str, WebSocket]] = {}  # session_id -> {participant_id: ws}
        self._conversation_history: dict[str, list[Turn]] = {}  # session_id -> turns
        self._active_turn_tasks: dict[str, asyncio.Task] = {}  # session_id -> running turn task

    def create_session(self, host_user_id: str, room_code: str | None = None) -> ConversationSession:
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

    def get_session(self, session_id: str) -> ConversationSession | None:
        return self._sessions.get(session_id)

    def get_session_by_code(self, room_code: str) -> ConversationSession | None:
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

        is_reconnect = participant.participant_id in session.participants
        session.participants[participant.participant_id] = participant
        self._active_connections[session_id][participant.participant_id] = websocket

        # If reconnecting, send current session history and state
        if is_reconnect:
            history = self._conversation_history.get(session_id, [])
            await websocket.send_text(
                json.dumps({
                    "event": "session_reconnected",
                    "data": {
                        "session_id": session_id,
                        "room_code": session.room_code,
                        "history": [t.model_dump(mode="json") for t in history],
                    },
                }, default=str)
            )

        # Broadcast room state to all members in THIS session only
        await self.broadcast_event(
            session_id=session_id,
            event_type="participant_joined",
            payload={
                "participant_id": participant.participant_id,
                "display_name": participant.display_name,
                "is_reconnect": is_reconnect,
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
        exclude_participant_id: str | None = None,
    ):
        """Dispatches JSON events strictly to clients within the given session."""
        connections = self._active_connections.get(session_id, {})
        dead_connections: list[str] = []

        message_str = json.dumps({"event": event_type, "data": payload}, default=str)

        for pid, ws in list(connections.items()):
            if exclude_participant_id and pid == exclude_participant_id:
                continue
            try:
                await ws.send_text(message_str)
            except Exception:
                dead_connections.append(pid)

        for pid in dead_connections:
            await self.unregister_participant(session_id, pid)

    async def interrupt_session(self, session_id: str, interrupter_id: str):
        """
        Cancels any ongoing generation tasks in the room and commands client audio players to halt.
        """
        # Cancel running task if any
        if session_id in self._active_turn_tasks:
            task = self._active_turn_tasks[session_id]
            if not task.done():
                task.cancel()

        await self.broadcast_event(
            session_id=session_id,
            event_type="interrupt_playback",
            payload={
                "interrupter_id": interrupter_id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            },
        )

    async def handle_webrtc_signal(
        self,
        session_id: str,
        sender_id: str,
        signal_type: str,
        signal_data: dict,
        target_id: str | None = None,
    ):
        """
        Routes WebRTC SDP offer, answer, and ICE candidates between peers within the same room.
        """
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return

        connections = self._active_connections.get(session_id, {})
        payload = {
            "signal_type": signal_type,
            "sender_id": sender_id,
            "data": signal_data,
        }

        if target_id and target_id in connections:
            try:
                await connections[target_id].send_text(
                    json.dumps({"event": "webrtc_signal", "data": payload})
                )
            except Exception:
                pass
        else:
            # Broadcast to all peers except sender
            await self.broadcast_event(
                session_id=session_id,
                event_type="webrtc_signal",
                payload=payload,
                exclude_participant_id=sender_id,
            )

    async def handle_turn_audio(
        self,
        session_id: str,
        speaker_id: str,
        audio_bytes: bytes,
        transcript_override: str | None = None,
    ) -> Turn:
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            raise ValueError(f"Session {session_id} is inactive or not found.")

        # Trigger interruption check if previous generation is still pending
        await self.interrupt_session(session_id, interrupter_id=speaker_id)

        speaker = session.participants.get(speaker_id)
        speaker_name = speaker.display_name if speaker else "User"
        source_lang = speaker.preferred_speaking_language if speaker else Language.HINDI

        # Get context of previous turns in this session
        history = self._conversation_history.get(session_id, [])
        context_payload = [
            {"speaker": t.speaker_name, "text": t.translated_text}
            for t in history[-5:]
        ]

        # Track current turn task for instantaneous barge-in cancellation
        current_t = asyncio.current_task()
        if current_t:
            self._active_turn_tasks[session_id] = current_t

        try:
            turn, synthesized_audio = await self.pipeline.process_turn(
                session_id=session_id,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                audio_bytes=audio_bytes,
                source_language_hint=source_lang,
                conversation_context=context_payload,
                transcript_override=transcript_override,
            )
        finally:
            if self._active_turn_tasks.get(session_id) == current_t:
                self._active_turn_tasks.pop(session_id, None)

        history.append(turn)

        # Broadcast turn results to room participants
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

        # In Translation-Only Mode: Send translated personal voice audio to listeners
        if synthesized_audio and len(synthesized_audio) > 0:
            import base64
            audio_b64 = base64.b64encode(synthesized_audio).decode("ascii")
            
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
