"""
Application Configuration
Defines environment variables, system constants, and runtime defaults.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VOICE_PROFILES_DIR = DATA_DIR / "voice_profiles"
TEMP_AUDIO_DIR = DATA_DIR / "temp_audio"

# Ensure runtime directories exist
VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)
TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    app_name: str = "Personal Voice Translation AI OS"
    app_version: str = "3.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # Security
    jwt_secret: str = os.getenv("JWT_SECRET", "pvt-development-secret-key-32-bytes-long!")
    jwt_algorithm: str = "HS256"
    session_token_expire_minutes: int = 120
    
    # Audio & Processing Defaults
    audio_sample_rate: int = 16000  # 16 kHz mono standard for speech
    audio_channels: int = 1
    chunk_size_ms: int = 100        # 100ms streaming chunks
    silence_threshold_ms: int = 600 # Silence duration to trigger end-of-turn
    
    # Provider Settings (Pluggable)
    stt_provider: str = os.getenv("STT_PROVIDER", "mock")  # mock | whisper | deepgram
    translation_provider: str = os.getenv("TRANSLATION_PROVIDER", "mock")  # mock | gemini | openai
    tts_provider: str = os.getenv("TTS_PROVIDER", "mock")  # mock | elevenlabs | xtts
    
    # Target Latency (ms) for observability
    target_latency_budget_ms: int = 1500
    
    # Privacy / Retention
    retain_session_transcripts: bool = False
    retain_call_audio: bool = False
    auto_cleanup_temp_audio: bool = True


settings = AppSettings()
