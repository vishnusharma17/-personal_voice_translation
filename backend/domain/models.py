"""
Domain Models
Core entities and data structures for Personal Voice Translation.
"""

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Language(str, Enum):
    HINDI = "hi"
    ENGLISH = "en"
    HINGLISH = "hi-en"
    AUTO = "auto"


class AudioFormat(str, Enum):
    PCM_16K = "pcm_16k"
    WAV = "wav"
    OPUS = "opus"
    MP3 = "mp3"


class VoiceProfileStatus(str, Enum):
    PENDING_CONSENT = "pending_consent"
    VALIDATING = "validating"
    READY = "ready"
    REJECTED = "rejected"
    REVOKED = "revoked"


class AudioQualityMetrics(BaseModel):
    snr_db: float = Field(..., description="Signal-to-Noise ratio in decibels")
    clipping_rate: float = Field(..., description="Fraction of audio samples clipped (0.0 to 1.0)")
    background_noise_db: float = Field(..., description="Estimated background noise floor in dB")
    duration_sec: float = Field(..., description="Duration of audio sample in seconds")
    is_acceptable: bool = Field(..., description="Whether sample meets high-quality synthesis bar")
    feedback: list[str] = Field(default_factory=list, description="Actionable advice if quality is low")


class ConsentRecord(BaseModel):
    consent_id: str
    user_id: str
    statement_text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    signature_hash: str
    audio_sample_checksum: str
    is_revoked: bool = False
    revoked_at: datetime | None = None


class VoiceProfile(BaseModel):
    voice_id: str
    user_id: str
    display_name: str
    native_language: Language = Language.HINDI
    target_language: Language = Language.ENGLISH
    status: VoiceProfileStatus = VoiceProfileStatus.PENDING_CONSENT
    sample_duration_sec: float = 0.0
    quality_metrics: AudioQualityMetrics | None = None
    consent_id: str | None = None
    embedding_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LatencyBreakdown(BaseModel):
    vad_ms: float = 0.0
    stt_ms: float = 0.0
    translation_ms: float = 0.0
    tts_ms: float = 0.0
    total_latency_ms: float = 0.0

    def compute_total(self) -> float:
        self.total_latency_ms = round(self.vad_ms + self.stt_ms + self.translation_ms + self.tts_ms, 2)
        return self.total_latency_ms


class Turn(BaseModel):
    turn_id: str
    session_id: str
    speaker_id: str
    speaker_name: str
    source_language: Language
    target_language: Language
    source_text: str
    translated_text: str
    confidence: float = 1.0
    is_final: bool = True
    audio_duration_ms: float = 0.0
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Participant(BaseModel):
    participant_id: str
    user_id: str
    display_name: str
    preferred_speaking_language: Language = Language.HINDI
    preferred_listening_language: Language = Language.ENGLISH
    voice_profile_id: str | None = None
    translation_only_mode: bool = True  # Listener receives only synthesized translation
    joined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationSession(BaseModel):
    session_id: str
    room_code: str
    host_user_id: str
    participants: dict[str, Participant] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TranslationEvent(BaseModel):
    event_type: str  # "transcript_interim" | "turn_complete" | "audio_chunk" | "error" | "latency_report"
    session_id: str
    speaker_id: str
    data: dict
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
