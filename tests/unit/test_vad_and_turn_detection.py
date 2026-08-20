"""
Unit Tests: Voice Activity Detection (VAD)
"""

import pytest
from backend.adapters.tts.mock_tts import generate_synthesized_pcm
from backend.core.vad import EnergyVAD


def test_vad_silence_detection():
    vad = EnergyVAD(energy_threshold_db=-38.0, silence_timeout_ms=300)
    # Generate 400ms of pure silence (zeros)
    silence_pcm = b"\x00\x00" * 3200
    is_speaking, completed_turn = vad.process_chunk(silence_pcm)
    assert is_speaking is False
    assert completed_turn is None


def test_vad_speech_and_turn_segmentation():
    vad = EnergyVAD(energy_threshold_db=-38.0, silence_timeout_ms=300, min_speech_duration_ms=200)
    
    # 1. Provide 500ms of voiced audio
    speech_pcm = generate_synthesized_pcm("Hello speaking speech sample", duration_per_char=0.08)
    is_speaking, turn_1 = vad.process_chunk(speech_pcm)
    assert is_speaking is True
    assert turn_1 is None  # Not completed yet until silence timeout

    # 2. Provide 400ms of silence (12800 bytes at 16kHz 16-bit) to close turn
    silence_pcm = b"\x00\x00" * 6400
    is_speaking_after, completed_turn = vad.process_chunk(silence_pcm)
    assert completed_turn is not None
    assert len(completed_turn) > 0
