"""
Provider Factory
Instantiates active Speech Recognizer, Translator, Language Detector, and Voice Synthesizer
based on environment configuration and available credentials.
"""

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.stt.whisper_stt import WhisperSTT
from backend.adapters.translation.gemini_translator import GeminiTranslator
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.elevenlabs_tts import ElevenLabsTTS
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.config import settings
from backend.domain.interfaces import (
    LanguageDetector,
    SpeechRecognizer,
    Translator,
    VoiceProfileService,
    VoiceSynthesizer,
)


def get_stt_adapter() -> SpeechRecognizer:
    if settings.stt_provider.lower() == "whisper":
        return WhisperSTT()
    return MockSpeechRecognizer()


def get_language_detector() -> LanguageDetector:
    return RuleBasedLanguageDetector()


def get_translator_adapter() -> Translator:
    if settings.translation_provider.lower() == "gemini":
        return GeminiTranslator()
    return MockTranslator()


def get_tts_adapter() -> VoiceSynthesizer:
    if settings.tts_provider.lower() == "elevenlabs":
        return ElevenLabsTTS()
    return MockVoiceSynthesizer()


def get_voice_profile_service() -> VoiceProfileService:
    return SecureVoiceProfileService()
