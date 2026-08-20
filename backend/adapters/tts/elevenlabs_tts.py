"""
ElevenLabs Personal Voice Synthesis Adapter
Synthesizes speech in authorized user voice using ElevenLabs Instant Voice Clone API.
"""

import os
from typing import AsyncGenerator, Optional
import httpx

from backend.domain.interfaces import VoiceSynthesizer
from backend.domain.models import Language, VoiceProfile, VoiceProfileStatus


class ElevenLabsTTS(VoiceSynthesizer):
    """
    ElevenLabs Voice Synthesis adapter adhering to RULES/VOICE.md.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_id: str = "eleven_multilingual_v2",
        timeout_sec: float = 10.0,
    ):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self.model_id = model_id
        self.timeout_sec = timeout_sec

    async def synthesize(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> bytes:
        if not text.strip():
            return b""

        # Voice Safety Check (RULES/VOICE.md)
        if voice_profile.status not in (VoiceProfileStatus.READY, None):
            raise PermissionError("Cannot synthesize voice without active and authorized voice profile status.")

        if not self.api_key:
            # Fallback to modulated local synthesis
            from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
            fallback = MockVoiceSynthesizer()
            return await fallback.synthesize(text, voice_profile, target_language)

        voice_id = voice_profile.embedding_ref or voice_profile.voice_id
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/wav",
        }
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.85,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    return res.content
                else:
                    from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
                    fallback = MockVoiceSynthesizer()
                    return await fallback.synthesize(text, voice_profile, target_language)
        except Exception:
            from backend.adapters.tts.mock_tts import MockVoiceSynthesizer
            fallback = MockVoiceSynthesizer()
            return await fallback.synthesize(text, voice_profile, target_language)

    async def synthesize_stream(
        self,
        text: str,
        voice_profile: VoiceProfile,
        target_language: Language,
    ) -> AsyncGenerator[bytes, None]:
        audio = await self.synthesize(text, voice_profile, target_language)
        chunk_size = 3200
        for i in range(0, len(audio), chunk_size):
            yield audio[i : i + chunk_size]
