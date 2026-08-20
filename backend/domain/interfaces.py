"""
Provider Interfaces (Protocols / Abstract Base Classes)
Defines stable contracts for STT, Translation, Voice Synthesis, Language Detection, and Profile Management.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from backend.domain.models import (
    AudioQualityMetrics,
    ConsentRecord,
    Language,
    VoiceProfile,
)


class SpeechRecognizer(ABC):
    """
    Streaming Speech Recognition Contract.
    Accepts raw audio chunks and yields transcribed text events.
    """

    @abstractmethod
    def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        source_language: Language | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Yields dicts with format:
        {"text": str, "is_final": bool, "confidence": float, "detected_language": str}
        """

    @abstractmethod
    async def transcribe_chunk(
        self, audio_bytes: bytes, source_language: Language | None = None
    ) -> dict:
        """Transcribe single audio turn synchronously or in batch."""


class LanguageDetector(ABC):
    """
    Language & Hinglish Detection Contract.
    Identifies Hindi, Hinglish (code-mixed), and English utterances.
    """

    @abstractmethod
    async def detect_language(self, text_or_audio: str | bytes) -> Language:
        """Determines primary language of the input."""


class Translator(ABC):
    """
    Context-Aware Natural Translation Contract.
    Preserves conversational tone, intent, and colloquial nuances (e.g. Hinglish -> English).
    """

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_language: Language,
        target_language: Language,
        conversation_context: list[dict] | None = None,
    ) -> str:
        """
        Translates text with tone preservation.
        Never introduces hallucinations or shifts the speaker's core intent.
        """

    @abstractmethod
    def translate_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        source_language: Language,
        target_language: Language,
        conversation_context: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Streaming translation generator for sub-word or sentence-level low latency."""


class VoiceSynthesizer(ABC):
    """
    Personal Voice Synthesis Contract.
    Generates audio in the authorized speaker's cloned voice.
    """

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> bytes:
        """Synthesizes text into complete audio (e.g., PCM 16kHz or WAV)."""

    @abstractmethod
    def synthesize_stream(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> AsyncGenerator[bytes, None]:
        """Yields streaming PCM chunks for low-latency playback."""


class VoiceProfileService(ABC):
    """
    Voice Profile, Consent, and Audio Quality Management Contract.
    Enforces privacy, explicit consent, cryptographic auditing, and data deletion.
    """

    @abstractmethod
    async def record_consent(
        self, user_id: str, statement_text: str, audio_signature_bytes: bytes
    ) -> ConsentRecord:
        """Records cryptographically verifiable consent."""

    @abstractmethod
    async def validate_audio_quality(self, audio_bytes: bytes) -> AudioQualityMetrics:
        """Analyzes SNR, clipping, noise floor, and duration."""

    @abstractmethod
    async def create_profile(
        self,
        user_id: str,
        display_name: str,
        consent_id: str,
        audio_sample_bytes: bytes,
        native_language: Language = Language.HINDI,
    ) -> VoiceProfile:
        """Extracts voice identity representation only after valid consent and quality check."""

    @abstractmethod
    async def get_profile(self, user_id: str) -> VoiceProfile | None:
        """Retrieves authorized profile."""

    @abstractmethod
    async def delete_profile(self, user_id: str) -> bool:
        """Permanently deletes voice embedding, reference audio, and profile data."""
