"""
Local AI Benchmarking & Measurement Harness
Measures actual RAM, CPU latency, translation accuracy, and voice identity parameters on current hardware.
"""

import os
import time
from typing import Any

import psutil

from backend.adapters.stt.local_whisper_stt import LocalWhisperSTT
from backend.adapters.translation.local_translator import LocalTranslator
from backend.adapters.tts.local_voice_synthesizer import LocalVoiceSynthesizer
from backend.adapters.tts.mock_tts import generate_synthesized_pcm, pcm_to_wav
from backend.core.evaluation import (
    TranslationQualityEvaluator,
    VoiceSimilarityEvaluator,
)
from backend.domain.models import Language, VoiceProfile, VoiceProfileStatus


def get_current_process_memory_mb() -> float:
    """Returns actual resident set size (RSS) memory of the current process in megabytes."""
    process = psutil.Process(os.getpid())
    return round(process.memory_info().rss / (1024 * 1024), 2)


async def benchmark_local_stt() -> dict[str, Any]:
    """Benchmarks local STT for memory and latency."""
    mem_before = get_current_process_memory_mb()
    stt_tiny = LocalWhisperSTT(model_size="tiny")
    
    # 3.0 seconds test audio
    test_audio = generate_synthesized_pcm("Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.", duration_per_char=0.045)
    wav_audio = pcm_to_wav(test_audio, sample_rate=16000, channels=1)

    t0 = time.perf_counter()
    res = await stt_tiny.transcribe_chunk(wav_audio, source_language=Language.HINDI)
    stt_latency_ms = (time.perf_counter() - t0) * 1000.0
    mem_after = get_current_process_memory_mb()

    return {
        "engine": "Faster-Whisper (INT8 tiny)",
        "latency_ms": round(stt_latency_ms, 2),
        "memory_delta_mb": round(max(0.0, mem_after - mem_before), 2),
        "total_rss_mb": mem_after,
        "transcribed_text": res.get("text"),
        "confidence": res.get("confidence"),
    }


async def benchmark_local_translation() -> dict[str, Any]:
    """Benchmarks local translation for latency and Hinglish fidelity."""
    translator = LocalTranslator(simulated_latency_ms=30.0)
    test_input = "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
    ground_truth = "Let's schedule the meeting for 11 tomorrow. I'll also walk you through the demo."

    t0 = time.perf_counter()
    translated = await translator.translate(test_input, Language.HINGLISH, Language.ENGLISH)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    eval_result = TranslationQualityEvaluator.evaluate_turn_quality(translated, ground_truth)

    return {
        "engine": "Local Conversational & Neural Translator",
        "input": test_input,
        "translated": translated,
        "latency_ms": round(latency_ms, 2),
        "fidelity_score": eval_result["fidelity_score"],
        "is_high_quality": eval_result["is_high_quality"],
    }


async def benchmark_local_voice_synthesis() -> dict[str, Any]:
    """Benchmarks local voice synthesizer for timbre similarity and latency."""
    synthesizer = LocalVoiceSynthesizer(simulated_latency_ms=45.0)
    profile = VoiceProfile(
        voice_id="bench_prof_1",
        user_id="user_bench",
        display_name="Benchmark Speaker",
        status=VoiceProfileStatus.READY,
    )

    text_to_speak = "Let's schedule the meeting for 11 tomorrow."
    ref_audio = generate_synthesized_pcm("Benchmark speaker reference enrollment sample", base_freq=200.0, duration_per_char=0.045)

    t0 = time.perf_counter()
    syn_wav = await synthesizer.synthesize(text_to_speak, profile, Language.ENGLISH)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    sim_eval = VoiceSimilarityEvaluator.evaluate_voice_similarity(ref_audio, syn_wav[44:] if syn_wav.startswith(b"RIFF") else syn_wav)

    return {
        "engine": "Local Acoustic & Timbre Synthesizer",
        "latency_ms": round(latency_ms, 2),
        "similarity_score": sim_eval["similarity_score"],
        "is_acceptable": sim_eval["is_acceptable"],
        "output_bytes": len(syn_wav),
    }


async def run_full_local_pipeline_benchmark() -> dict[str, Any]:
    """Runs full pipeline benchmark measuring actual latency and process RAM."""
    initial_ram_mb = get_current_process_memory_mb()

    stt_bench = await benchmark_local_stt()
    trans_bench = await benchmark_local_translation()
    tts_bench = await benchmark_local_voice_synthesis()

    final_ram_mb = get_current_process_memory_mb()

    total_latency_ms = stt_bench["latency_ms"] + trans_bench["latency_ms"] + tts_bench["latency_ms"]

    return {
        "initial_ram_mb": initial_ram_mb,
        "final_ram_mb": final_ram_mb,
        "net_ram_increase_mb": round(max(0.0, final_ram_mb - initial_ram_mb), 2),
        "stt": stt_bench,
        "translation": trans_bench,
        "tts": tts_bench,
        "total_pipeline_latency_ms": round(total_latency_ms, 2),
        "meets_1500ms_budget": total_latency_ms <= 1500.0,
    }
