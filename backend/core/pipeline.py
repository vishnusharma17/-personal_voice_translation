"""
Core Realtime Translation Pipeline
Orchestrates Audio -> STT -> Language/Context -> Translation -> Personal Voice Synthesis.
"""

import time
import uuid

from backend.domain.interfaces import (
    LanguageDetector,
    SpeechRecognizer,
    Translator,
    VoiceProfileService,
    VoiceSynthesizer,
)
from backend.domain.models import (
    Language,
    LatencyBreakdown,
    Turn,
    VoiceProfile,
    VoiceProfileStatus,
)


class TranslationPipeline:
    """
    End-to-End Voice Translation Pipeline with sub-system latency monitoring.
    """

    def __init__(
        self,
        stt: SpeechRecognizer,
        lang_detector: LanguageDetector,
        translator: Translator,
        tts: VoiceSynthesizer,
        profile_service: VoiceProfileService,
    ):
        self.stt = stt
        self.lang_detector = lang_detector
        self.translator = translator
        self.tts = tts
        self.profile_service = profile_service

    async def process_turn(
        self,
        session_id: str,
        speaker_id: str,
        speaker_name: str,
        audio_bytes: bytes,
        source_language_hint: Language | None = None,
        target_language_preference: Language | None = None,
        conversation_context: list[dict] | None = None,
        transcript_override: str | None = None,
    ) -> tuple[Turn, bytes]:
        """
        Executes complete turn translation and personal voice synthesis pipeline.
        Returns Turn metadata along with synthesized audio payload.
        """
        turn_id = f"turn_{uuid.uuid4().hex[:8]}"
        latency = LatencyBreakdown()
        
        # 1. Speech-to-Text
        t0 = time.perf_counter()
        if transcript_override:
            stt_result = {
                "text": transcript_override,
                "confidence": 1.0,
                "detected_language": "hi-en",
            }
        else:
            stt_result = await self.stt.transcribe_chunk(audio_bytes, source_language_hint)
        t1 = time.perf_counter()
        latency.stt_ms = round((t1 - t0) * 1000.0, 2)

        source_text = str(stt_result.get("text", "")).strip()
        if not source_text:
            # Empty turn
            latency.compute_total()
            turn = Turn(
                turn_id=turn_id,
                session_id=session_id,
                speaker_id=speaker_id,
                speaker_name=speaker_name,
                source_language=source_language_hint or Language.HINDI,
                target_language=target_language_preference or Language.ENGLISH,
                source_text="",
                translated_text="",
                confidence=0.0,
                latency=latency,
            )
            return turn, b""

        # 2. Language Detection & Direction Assignment
        detected_lang = await self.lang_detector.detect_language(source_text)
        
        effective_source: Language
        effective_target: Language
        if detected_lang in (Language.HINDI, Language.HINGLISH):
            effective_source = detected_lang
            effective_target = target_language_preference or Language.ENGLISH
        else:
            effective_source = Language.ENGLISH
            effective_target = target_language_preference or Language.HINDI

        # 3. Context-Aware Natural Translation
        t2 = time.perf_counter()
        translated_text = await self.translator.translate(
            text=source_text,
            source_language=effective_source,
            target_language=effective_target,
            conversation_context=conversation_context,
        )
        t3 = time.perf_counter()
        latency.translation_ms = round((t3 - t2) * 1000.0, 2)

        # 4. Personal Voice Synthesis
        t4 = time.perf_counter()
        profile = await self.profile_service.get_profile(speaker_id)
        if not profile:
            # Generate fallback ephemeral profile if not onboarded yet
            profile = VoiceProfile(
                voice_id=f"ephemeral_{speaker_id}",
                user_id=speaker_id,
                display_name=speaker_name,
                status=VoiceProfileStatus.READY,
            )

        synthesized_audio = await self.tts.synthesize(
            text=translated_text,
            voice_profile=profile,
            target_language=effective_target,
        )
        t5 = time.perf_counter()
        latency.tts_ms = round((t5 - t4) * 1000.0, 2)

        latency.compute_total()

        turn = Turn(
            turn_id=turn_id,
            session_id=session_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            source_language=effective_source,
            target_language=effective_target,
            source_text=source_text,
            translated_text=translated_text,
            confidence=float(stt_result["confidence"]) if "confidence" in stt_result and isinstance(stt_result["confidence"], (int, float)) else 1.0,
            is_final=True,
            latency=latency,
        )

        return turn, synthesized_audio
