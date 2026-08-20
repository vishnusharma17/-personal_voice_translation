"""
Provider Factory
Instantiates active Speech Recognizer, Translator, Language Detector, and Voice Synthesizer
with Local-First Open-Source adapters as default.
"""

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.local_whisper_stt import LocalWhisperSTT
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.stt.whisper_stt import WhisperSTT
from backend.adapters.translation.gemini_translator import GeminiTranslator
from backend.adapters.translation.local_translator import LocalTranslator
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.elevenlabs_tts import ElevenLabsTTS
from backend.adapters.tts.local_voice_synthesizer import LocalVoiceSynthesizer
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.config import settings
from backend.domain.interfaces import (
    LanguageDetector,
    SpeechRecognizer,
    Translator,
    VoiceProfileService,
    VoiceSynthesizer,
)


def get_stt_adapter() -> SpeechRecognizer:
    provider = settings.stt_provider.lower()
    if provider in ("local", "faster-whisper", "whisper.cpp"):
        return LocalWhisperSTT()
    elif provider == "whisper":
        if settings.offline_mode:
            raise RuntimeError("Cannot use external Whisper API when OFFLINE_MODE/LOCAL_ONLY is enabled.")
        return WhisperSTT()
    return MockSpeechRecognizer()


def get_language_detector() -> LanguageDetector:
    return RuleBasedLanguageDetector()


def get_translator_adapter() -> Translator:
    provider = settings.translation_provider.lower()
    if provider in ("local", "neural", "marian"):
        return LocalTranslator()
    elif provider == "gemini":
        if settings.offline_mode:
            raise RuntimeError("Cannot use external Gemini API when OFFLINE_MODE/LOCAL_ONLY is enabled.")
        return GeminiTranslator()
    return MockTranslator()


def get_tts_adapter() -> VoiceSynthesizer:
    provider = settings.tts_provider.lower()
    if provider in ("local", "neural", "piper"):
        return LocalVoiceSynthesizer()
    elif provider == "elevenlabs":
        if settings.offline_mode:
            raise RuntimeError("Cannot use external ElevenLabs API when OFFLINE_MODE/LOCAL_ONLY is enabled.")
        return ElevenLabsTTS()
    return MockVoiceSynthesizer()


def get_voice_profile_service() -> VoiceProfileService:
    return SecureVoiceProfileService()
