"""
Integration Tests: Phase 2 Local-First Migration, Offline Enforcement, and Benchmarking
"""

import pytest

from backend.adapters.factory import (
    get_stt_adapter,
    get_translator_adapter,
    get_tts_adapter,
)
from backend.adapters.stt.local_whisper_stt import LocalWhisperSTT
from backend.adapters.translation.local_translator import LocalTranslator
from backend.adapters.tts.local_voice_synthesizer import LocalVoiceSynthesizer
from backend.adapters.tts.mock_tts import generate_synthesized_pcm, pcm_to_wav
from backend.config import settings
from backend.core.benchmarking import run_full_local_pipeline_benchmark
from backend.domain.models import Language, VoiceProfile, VoiceProfileStatus


@pytest.mark.asyncio
async def test_local_stt_offline_execution():
    stt = LocalWhisperSTT(model_size="tiny")
    sample_pcm = generate_synthesized_pcm("Kal 11 baje meeting rakh lete hain", duration_per_char=0.045)
    wav_audio = pcm_to_wav(sample_pcm, sample_rate=16000, channels=1)

    result = await stt.transcribe_chunk(wav_audio, source_language=Language.HINDI)
    assert result["is_final"] is True
    assert len(result["text"]) > 0
    assert result["confidence"] > 0.0


@pytest.mark.asyncio
async def test_local_translator_hinglish_fidelity():
    translator = LocalTranslator()
    
    # Turn 1: Hinglish -> Natural English
    hi_input = "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
    en_output = await translator.translate(hi_input, Language.HINGLISH, Language.ENGLISH)
    en_lower = en_output.lower()
    assert "meeting" in en_lower and ("11" in en_lower or "tomorrow" in en_lower or "demo" in en_lower)

    # Turn 2: English -> Hindi
    en_input = "Yes, I can hear you clearly."
    hi_output = await translator.translate(en_input, Language.ENGLISH, Language.HINDI)
    assert "सुन" in hi_output or "हाँ" in hi_output or "स्पष्ट" in hi_output


@pytest.mark.asyncio
async def test_local_voice_synthesizer_consent_and_timbre():
    synthesizer = LocalVoiceSynthesizer()

    # Unauthorized profile must be rejected
    unauthorized_profile = VoiceProfile(
        voice_id="unauth_1",
        user_id="user_unauth",
        display_name="Unauthorized",
        status=VoiceProfileStatus.PENDING_CONSENT,
    )
    with pytest.raises(PermissionError):
        await synthesizer.synthesize("Unauthorized test", unauthorized_profile, Language.ENGLISH)

    # Authorized profile must produce valid WAV audio
    authorized_profile = VoiceProfile(
        voice_id="auth_1",
        user_id="user_auth",
        display_name="Authorized Speaker",
        status=VoiceProfileStatus.READY,
    )
    audio = await synthesizer.synthesize("Let's schedule the meeting for 11 tomorrow.", authorized_profile, Language.ENGLISH)
    assert len(audio) > 1000
    assert audio.startswith(b"RIFF")


def test_factory_defaults_to_local():
    settings.stt_provider = "local"
    settings.translation_provider = "local"
    settings.tts_provider = "local"

    stt = get_stt_adapter()
    translator = get_translator_adapter()
    tts = get_tts_adapter()

    assert isinstance(stt, LocalWhisperSTT)
    assert isinstance(translator, LocalTranslator)
    assert isinstance(tts, LocalVoiceSynthesizer)


def test_strict_offline_mode_rejection():
    settings.offline_mode = True
    settings.stt_provider = "whisper"
    settings.translation_provider = "gemini"
    settings.tts_provider = "elevenlabs"

    with pytest.raises(RuntimeError, match="Cannot use external Whisper API"):
        get_stt_adapter()

    with pytest.raises(RuntimeError, match="Cannot use external Gemini API"):
        get_translator_adapter()

    with pytest.raises(RuntimeError, match="Cannot use external ElevenLabs API"):
        get_tts_adapter()

    # Reset back to local
    settings.stt_provider = "local"
    settings.translation_provider = "local"
    settings.tts_provider = "local"


@pytest.mark.asyncio
async def test_end_to_end_local_pipeline_benchmark():
    benchmark_report = await run_full_local_pipeline_benchmark()
    assert benchmark_report["meets_1500ms_budget"] is True
    assert benchmark_report["total_pipeline_latency_ms"] < 1500.0
    assert benchmark_report["final_ram_mb"] > 0
    assert benchmark_report["translation"]["is_high_quality"] is True
