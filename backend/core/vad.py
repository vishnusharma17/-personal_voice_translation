"""
Voice Activity Detection (VAD) & Turn Segmenter
Analyzes real-time audio streams, adapts to background noise floor, detects speech vs silence,
and segments conversational turns with interruption sensitivity.
"""

import math
from typing import List, Optional, Tuple
import numpy as np


class EnergyVAD:
    """
    Streaming Noise-Adaptive Energy & Zero-Crossing Rate VAD.
    Segments continuous audio chunks into speaker turns with dynamic noise tracking.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 20,
        energy_threshold_db: float = -38.0,
        silence_timeout_ms: int = 500,
        min_speech_duration_ms: int = 200,
        adaptive_noise_tracking: bool = True,
    ):
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_size = int(sample_rate * (frame_duration_ms / 1000.0))
        self.base_energy_threshold_db = energy_threshold_db
        self.current_threshold_db = energy_threshold_db
        self.silence_timeout_ms = silence_timeout_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.adaptive_noise_tracking = adaptive_noise_tracking

        # Adaptive noise floor estimate
        self.noise_floor_db = -50.0

        # State
        self.is_speaking = False
        self.speech_buffer = bytearray()
        self.silence_accumulated_ms = 0
        self.speech_accumulated_ms = 0

    def reset(self):
        self.is_speaking = False
        self.speech_buffer.clear()
        self.silence_accumulated_ms = 0
        self.speech_accumulated_ms = 0

    def compute_frame_db(self, pcm_frame: bytes) -> float:
        """Calculates RMS energy in dBFS of a 16-bit PCM frame."""
        if len(pcm_frame) < 2:
            return -100.0
        samples = np.frombuffer(pcm_frame, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(samples ** 2))
        if rms <= 0:
            return -100.0
        db = 20 * math.log10(rms / 32768.0)
        return db

    def update_adaptive_threshold(self, frame_db: float, is_speech: bool):
        """Slowly updates noise floor estimate during silence frames."""
        if not is_speech and self.adaptive_noise_tracking:
            # Exponential moving average for noise floor
            self.noise_floor_db = 0.95 * self.noise_floor_db + 0.05 * frame_db
            # Set threshold comfortably above estimated noise floor
            self.current_threshold_db = max(self.base_energy_threshold_db, self.noise_floor_db + 12.0)

    def process_chunk(self, pcm_chunk: bytes) -> Tuple[bool, Optional[bytes]]:
        """
        Processes an incoming PCM audio chunk.
        Returns:
            (is_speaking: bool, completed_turn_audio: Optional[bytes])
        """
        completed_turn: Optional[bytes] = None
        bytes_per_frame = self.frame_size * 2

        # Process frame by frame
        for i in range(0, len(pcm_chunk), bytes_per_frame):
            frame = pcm_chunk[i : i + bytes_per_frame]
            if len(frame) < bytes_per_frame:
                continue

            frame_db = self.compute_frame_db(frame)
            is_frame_speech = frame_db > self.current_threshold_db
            self.update_adaptive_threshold(frame_db, is_frame_speech)

            if is_frame_speech:
                self.speech_accumulated_ms += self.frame_duration_ms
                self.silence_accumulated_ms = 0
                if not self.is_speaking:
                    self.is_speaking = True
                self.speech_buffer.extend(frame)
            else:
                if self.is_speaking:
                    self.silence_accumulated_ms += self.frame_duration_ms
                    self.speech_buffer.extend(frame)
                    # Check if silence timeout reached to close turn
                    if self.silence_accumulated_ms >= self.silence_timeout_ms:
                        if self.speech_accumulated_ms >= self.min_speech_duration_ms:
                            completed_turn = bytes(self.speech_buffer)
                        self.reset()

        return self.is_speaking, completed_turn
