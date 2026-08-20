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
    app_name: str = Field(default="Personal Voice Translation AI OS", description="Application name")
    app_version: str = Field(default="3.0.0", description="Application semantic version")
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
        description="Debug mode toggle",
    )
    host: str = Field(
        default_factory=lambda: os.getenv("HOST", "0.0.0.0"),
        description="Server host address",
    )
    port: int = Field(
        default_factory=lambda: int(os.getenv("PORT", "8000")),
        description="Server listening port",
    )
    
    # Security
    jwt_secret: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET", "pvt-development-secret-key-32-bytes-long!"),
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT hashing algorithm")
    session_token_expire_minutes: int = Field(default=120, description="Session token validity duration")
    
    # Audio & Processing Defaults
    audio_sample_rate: int = Field(default=16000, description="Audio sample rate in Hz (16 kHz mono standard)")
    audio_channels: int = Field(default=1, description="Number of audio channels (mono)")
    chunk_size_ms: int = Field(default=100, description="Streaming chunk buffer size in milliseconds")
    silence_threshold_ms: int = Field(default=600, description="Silence duration in ms to trigger end of turn")
    
    # Provider Settings (Pluggable: local | mock | whisper | gemini | elevenlabs)
    stt_provider: str = Field(
        default_factory=lambda: os.getenv("STT_PROVIDER", "local"),
        description="Active Speech-to-Text provider (local | mock | whisper)",
    )
    translation_provider: str = Field(
        default_factory=lambda: os.getenv("TRANSLATION_PROVIDER", "local"),
        description="Active translation provider (local | mock | gemini)",
    )
    tts_provider: str = Field(
        default_factory=lambda: os.getenv("TTS_PROVIDER", "local"),
        description="Active voice synthesizer provider (local | mock | elevenlabs)",
    )

    # Strict Local / Offline Mode (Enforces Zero External Network Access)
    offline_mode: bool = Field(
        default_factory=lambda: os.getenv("OFFLINE_MODE", "true").lower() == "true",
        description="Strict offline mode rejecting outbound third-party AI calls",
    )
    local_only: bool = Field(
        default_factory=lambda: os.getenv("LOCAL_ONLY", "true").lower() == "true",
        description="Enforces local execution only",
    )
    
    # Target Latency (ms) for observability
    target_latency_budget_ms: int = Field(default=1500, description="Target roundtrip latency ceiling in milliseconds")
    
    # Privacy / Retention
    retain_session_transcripts: bool = Field(default=False, description="Persist session transcripts")
    retain_call_audio: bool = Field(default=False, description="Persist raw call audio")
    auto_cleanup_temp_audio: bool = Field(default=True, description="Automatically purge temporary audio files")


settings = AppSettings()
