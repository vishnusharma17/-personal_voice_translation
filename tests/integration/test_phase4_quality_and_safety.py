"""
Integration Tests: Phase 4 Quality, Voice Similarity, Translation Naturalness, Latency Profiling & Security Audit
"""

import pytest
from backend.adapters.language_detector.detector import RuleBasedLanguageDetector
from backend.adapters.stt.mock_stt import MockSpeechRecognizer
from backend.adapters.translation.mock_translator import MockTranslator
from backend.adapters.tts.mock_tts import MockVoiceSynthesizer, generate_synthesized_pcm
from backend.adapters.voice_profile.secure_profile_service import SecureVoiceProfileService
from backend.core.evaluation import LatencyBenchmark, TranslationQualityEvaluator, VoiceSimilarityEvaluator
from backend.core.pipeline import TranslationPipeline
from backend.core.security import create_access_token, verify_access_token
from backend.domain.models import Language, VoiceProfileStatus


@pytest.mark.asyncio
async def test_voice_similarity_evaluation():
    ref_pcm = generate_synthesized_pcm("Reference voice enrollment sample", base_freq=210.0, duration_per_char=0.08)
    syn_pcm = generate_synthesized_pcm("Synthesized translated output speech", base_freq=210.0, duration_per_char=0.08)

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
async def test_latency_budget_stress_profiling():
    stt = MockSpeechRecognizer(simulated_latency_ms=30.0)
    detector = RuleBasedLanguageDetector()
    translator = MockTranslator()
    tts = MockVoiceSynthesizer(simulated_latency_ms=40.0)
    profile_service = SecureVoiceProfileService()

    pipeline = TranslationPipeline(
        stt=stt,
        lang_detector=detector,
        translator=translator,
        tts=tts,
        profile_service=profile_service,
    )

    latencies: list[float] = []
    # Run 10 consecutive turns through the complete pipeline
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
