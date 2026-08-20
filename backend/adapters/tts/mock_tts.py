"""
Voice Synthesizer (Mock & Testing Adapter)
Generates audio output parameterized by authorized voice profile identity.
"""

import asyncio
import math
import struct
from typing import AsyncGenerator
from backend.domain.interfaces import VoiceSynthesizer
from backend.domain.models import Language, VoiceProfile


def generate_synthesized_pcm(
    text: str,
    sample_rate: int = 16000,
    base_freq: float = 220.0,
    duration_per_char: float = 0.04,
) -> bytes:
    """
    Generates deterministic, smoothly windowed synthesized speech audio PCM samples.
    """
    duration = max(0.5, len(text) * duration_per_char)
    num_samples = int(sample_rate * duration)
    pcm_data = bytearray()

    for i in range(num_samples):
        t = i / sample_rate
        # Composite harmonic wave reflecting speech vocal tract resonances (formants)
        freq = base_freq + 20.0 * math.sin(2 * math.pi * 3.0 * t)
        sample_val = (
            0.5 * math.sin(2 * math.pi * freq * t)
            + 0.25 * math.sin(2 * math.pi * freq * 2.0 * t)
            + 0.12 * math.sin(2 * math.pi * freq * 3.0 * t)
        )
        # Apply smooth attack and release envelope
        envelope = min(1.0, i / (0.05 * sample_rate)) * min(1.0, (num_samples - i) / (0.05 * sample_rate))
        sample_int = int(sample_val * envelope * 28000)
        pcm_data.extend(struct.pack("<h", max(-32768, min(32767, sample_int))))

    return bytes(pcm_data)


def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, channels: int = 1) -> bytes:
    """Wraps raw 16-bit PCM bytes with standard RIFF WAV header."""
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2
    data_size = len(pcm_bytes)
    riff_chunk_size = 36 + data_size

    header = bytearray(b"RIFF")
    header.extend(struct.pack("<I", riff_chunk_size))
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, 16))
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    return bytes(header) + pcm_bytes


class MockVoiceSynthesizer(VoiceSynthesizer):
    """
    Mock Voice Synthesizer with speaker timbre modulation and streaming chunk generator.
    """

    def __init__(self, simulated_latency_ms: float = 120.0):
        self.simulated_latency_ms = simulated_latency_ms

    async def synthesize(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> bytes:
        await asyncio.sleep(self.simulated_latency_ms / 1000.0)
        # Modulate frequency based on user_id hash for unique voice identity consistency
        freq_offset = (hash(voice_profile.voice_id) % 80)
        base_freq = 180.0 + freq_offset
        pcm = generate_synthesized_pcm(text, base_freq=base_freq)
        return pcm_to_wav(pcm)

    async def synthesize_stream(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> AsyncGenerator[bytes, None]:
        await asyncio.sleep(self.simulated_latency_ms / 1000.0)
        freq_offset = (hash(voice_profile.voice_id) % 80)
        base_freq = 180.0 + freq_offset
        pcm = generate_synthesized_pcm(text, base_freq=base_freq)
        
        # Stream in 100ms chunks (3200 bytes per chunk at 16kHz 16-bit mono)
        chunk_size = 3200
        for i in range(0, len(pcm), chunk_size):
            yield pcm[i : i + chunk_size]
            await asyncio.sleep(0.02)
