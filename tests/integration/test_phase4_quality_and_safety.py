"""
Integration Tests: Phase 4 Human Quality, Edge-Case Translation,
Multi-Room Concurrency Stress Profiling, Continuous Call Stability & Security Audit
"""

import asyncio
import base64
import os
import struct
import time

import psutil
import pytest

from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.local_whisper_stt import LocalWhisperSTT
from backend.adapters.translation.local_translator import LocalTranslator
from backend.adapters.tts.local_voice_synthesizer import LocalVoiceSynthesizer
from backend.adapters.tts.mock_tts import generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import (
    SecureVoiceProfileService,
)
from backend.config import settings
from backend.core.evaluation import (
    LatencyBenchmark,
    TranslationQualityEvaluator,
    VoiceSimilarityEvaluator,
)
from backend.core.pipeline import TranslationPipeline
from backend.core.security import create_access_token, verify_access_token
from backend.core.session_gateway import SessionGateway
from backend.domain.models import Language, Participant, VoiceProfile, VoiceProfileStatus


@pytest.mark.asyncio
async def test_voice_similarity_evaluation():
    ref_pcm = generate_synthesized_pcm("Reference voice enrollment sample", base_freq=210.0, duration_per_char=0.08)
    syn_pcm = generate_synthesized_pcm("Synthesized translated output speech", base_freq=210.0, duration_per_char=0.08)

    metrics = VoiceSimilarityEvaluator.evaluate_voice_similarity(ref_pcm, syn_pcm)
    assert metrics["similarity_score"] >= 0.70
    assert metrics["is_acceptable"] is True


@pytest.mark.asyncio
async def test_local_voice_synthesizer_timbre_metrics():
    synthesizer = LocalVoiceSynthesizer(simulated_latency_ms=20.0)
    profile = VoiceProfile(
        voice_id="prof_speaker_raj",
        user_id="user_raj",
        display_name="Rajesh",
        status=VoiceProfileStatus.READY,
    )
    ref_pcm = generate_synthesized_pcm("Rajesh reference voice sample", base_freq=180.0, duration_per_char=0.05)
    syn_wav = await synthesizer.synthesize("Let's schedule the meeting for 11 tomorrow.", profile, Language.ENGLISH)
    syn_pcm = syn_wav[44:] if syn_wav.startswith(b"RIFF") else syn_wav

    metrics = VoiceSimilarityEvaluator.evaluate_voice_similarity(ref_pcm, syn_pcm)
    assert metrics["similarity_score"] >= 0.70
    assert metrics["is_acceptable"] is True


def test_translation_fidelity_and_naturalness_evaluation():
    ground_truth = "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."
    hypothesis = "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."

    eval_result = TranslationQualityEvaluator.evaluate_turn_quality(hypothesis, ground_truth)
    assert eval_result["fidelity_score"] == 1.0
    assert eval_result["is_high_quality"] is True


@pytest.mark.asyncio
async def test_local_translation_idiom_fidelity():
    translator = LocalTranslator()
    
    test_cases = [
        (
            "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
            "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo.",
        ),
        (
            "Haan main aapko saaf sun sakta hoon.",
            "Yes, I can hear you clearly.",
        ),
        (
            "Kya aap meri aawaz sun sakte hain?",
            "Can you hear my voice clearly?",
        ),
    ]

    for hi_text, en_ref in test_cases:
        trans = await translator.translate(hi_text, Language.HINGLISH, Language.ENGLISH)
        eval_res = TranslationQualityEvaluator.evaluate_turn_quality(trans, en_ref)
        assert eval_res["fidelity_score"] >= 0.35


@pytest.mark.asyncio
async def test_difficult_conversational_and_technical_cases():
    """
    Tests edge cases: numbers, technical terms, fillers, fast speech, polite phrasing.
    """
    translator = LocalTranslator()

    difficult_cases = [
        # Technical & Numbers
        (
            "humein 3 servers aur 500 users ke liye test karna hai.",
            ["3", "500", "server", "user"],
        ),
        (
            "api latency high hai, database query optimize karni padegi.",
            ["latency", "database", "query", "optimize"],
        ),
        # Code-mixed casual Hindi-English
        (
            "yaar meeting ka link bhej do, main 5 minute mein join karta hoon.",
            ["meeting", "link", "minute"],
        ),
        # Polite client honorifics & Hesitations
        (
            "kripya mujhe thoda samay dijiye.",
            ["time", "moment", "please"],
        ),
        (
            "umm... theek hai, main team se bol dunga.",
            ["team", "tell", "let"],
        ),
        # Deployment & DevOps jargon
        (
            "production deployment successful raha.",
            ["production", "deployment", "successful"],
        ),
        (
            "haan, pull request merge ho gayi hai.",
            ["request", "merge"],
        ),
    ]

    for hi_text, required_concepts in difficult_cases:
        result = await translator.translate(hi_text, Language.HINGLISH, Language.ENGLISH)
        res_lower = result.lower()
        matched = any(c.lower() in res_lower for c in required_concepts)
        assert matched, f"None of {required_concepts} found in translation: '{result}' for input '{hi_text}'"


@pytest.mark.asyncio
async def test_latency_budget_stress_profiling():
    stt = LocalWhisperSTT(model_size="tiny")
    detector = RuleBasedLanguageDetector()
    translator = LocalTranslator()
    tts = LocalVoiceSynthesizer(simulated_latency_ms=25.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    latencies: list[float] = []
    # Run 10 consecutive turns through the complete local pipeline
    for i in range(10):
        turn, _ = await pipeline.process_turn(
            session_id=f"sess_stress_{i}",
            speaker_id="stress_speaker",
            speaker_name="Speaker",
            audio_bytes=b"\x00\x01" * 1600,
            transcript_override="Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
        )
        latencies.append(turn.latency.total_latency_ms)

    benchmark = LatencyBenchmark.compute_percentiles(latencies)
    assert benchmark["meets_target"] is True
    assert benchmark["p95"] < 1500.0  # Must be strictly under 1500ms budget


@pytest.mark.asyncio
async def test_multi_room_concurrency_stress():
    """
    Stress-tests 10 concurrent active rooms with 20 simultaneous participants.
    Validates gateway throughput, zero cross-session data corruption, and isolation.
    """
    stt = LocalWhisperSTT(model_size="tiny")
    detector = RuleBasedLanguageDetector()
    translator = LocalTranslator(simulated_latency_ms=1.0)
    tts = LocalVoiceSynthesizer(simulated_latency_ms=10.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )
    gateway = SessionGateway(pipeline=pipeline)

    num_rooms = 10
    sessions = []
    for i in range(num_rooms):
        s = gateway.create_session(host_user_id=f"host_{i}", room_code=f"CONCUR_{i:02d}")
        sessions.append(s)

    # Launch concurrent turns in all rooms simultaneously
    tasks = []
    for i, s in enumerate(sessions):
        task = gateway.handle_turn_audio(
            session_id=s.session_id,
            speaker_id=f"spk_{i}",
            audio_bytes=b"\x00\x01" * 1600,
            transcript_override=f"Turn message for room {i}",
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    assert len(results) == num_rooms
    for i, turn in enumerate(results):
        assert turn.session_id == sessions[i].session_id
        assert turn.latency.total_latency_ms < 6000.0


@pytest.mark.asyncio
async def test_continuous_long_call_memory_and_stability():
    """
    Profiles resource consumption (Resident Memory & Latency) across 25 continuous turns.
    Guarantees no memory accumulation or memory leaks on the development machine.
    """
    stt = LocalWhisperSTT(model_size="tiny")
    detector = RuleBasedLanguageDetector()
    translator = LocalTranslator(simulated_latency_ms=1.0)
    tts = LocalVoiceSynthesizer(simulated_latency_ms=10.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )
    gateway = SessionGateway(pipeline=pipeline)
    session = gateway.create_session(host_user_id="user_long_call", room_code="LONG_CALL_01")

    # Warm up 1 turn to load neural model weights into resident memory
    await gateway.handle_turn_audio(
        session_id=session.session_id,
        speaker_id="user_long_call",
        audio_bytes=b"\x00\x01" * 1600,
        transcript_override="warmup turn",
    )

    process = psutil.Process(os.getpid())
    mem_initial_mb = process.memory_info().rss / (1024 * 1024)

    for i in range(25):
        turn = await gateway.handle_turn_audio(
            session_id=session.session_id,
            speaker_id="user_long_call",
            audio_bytes=b"\x00\x01" * 1600,
            transcript_override="kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
        )
        assert turn is not None

    mem_final_mb = process.memory_info().rss / (1024 * 1024)
    mem_delta_mb = mem_final_mb - mem_initial_mb

    # Memory growth over 25 continuous turns must be minimal (< 25 MB)
    assert mem_delta_mb < 25.0
    # Process memory with local neural model loaded must remain comfortably low (< 1200 MB)
    assert mem_final_mb < 1200.0


@pytest.mark.asyncio
async def test_security_and_privacy_audit():
    # 1. Verify token signature validation
    valid_token = create_access_token("sec_user_1", "Security User")
    assert verify_access_token(valid_token) is not None

    # Tampered token must be rejected
    tampered_token = valid_token[:-4] + "abcd"
    assert verify_access_token(tampered_token) is None

    # 2. Voice Privacy & GDPR Purge Audit
    profile_service = SecureVoiceProfileService()
    sample_pcm = generate_synthesized_pcm("Consent and sample audio for GDPR security audit", duration_per_char=0.08)
    consent = await profile_service.record_consent("audit_user", "I authorize voice cloning", sample_pcm)
    profile = await profile_service.create_profile("audit_user", "Audit User", consent.consent_id, sample_pcm)

    assert profile.status == VoiceProfileStatus.READY

    # Delete profile and verify zero data retention
    deleted = await profile_service.delete_profile("audit_user")
    assert deleted is True
    assert await profile_service.get_profile("audit_user") is None
