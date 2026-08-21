"""
Integration Tests: FastAPI HTTP Endpoints, Security Headers & ICE Configuration
"""

import httpx
import pytest

from backend.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert data["target_latency_budget_ms"] == 1500


@pytest.mark.asyncio
async def test_security_headers_middleware():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        assert res.headers.get("x-content-type-options") == "nosniff"
        assert res.headers.get("x-frame-options") == "DENY"
        assert res.headers.get("x-xss-protection") == "1; mode=block"
        assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_ice_servers_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/config/ice-servers")
        assert res.status_code == 200
        data = res.json()
        assert "iceServers" in data
        assert len(data["iceServers"]) >= 1
        assert "urls" in data["iceServers"][0]


@pytest.mark.asyncio
async def test_auth_token_generation():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/auth/token",
            json={"user_id": "test_user_raj", "display_name": "Raj Sharma"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user_id"] == "test_user_raj"


@pytest.mark.asyncio
async def test_voice_consent_and_validation_routes():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Record Consent
        res = await client.post(
            "/api/voice/consent",
            json={
                "user_id": "api_user_1",
                "statement_text": "I hereby consent and authorize personal voice synthesis for real-time translation calls.",
            },
        )
        assert res.status_code == 200
        consent_data = res.json()
        assert consent_data["consent_id"].startswith("consent_api_user_1_")

        # 2. Validate Audio Sample
        fake_audio_wav = b"RIFF" + b"\x00" * 40 + (b"\x10\x00" * 32000)
        files = {"audio_file": ("test_sample.wav", fake_audio_wav, "audio/wav")}
        res = await client.post("/api/voice/validate-audio", files=files)
        assert res.status_code == 200
        val_data = res.json()
        assert "is_acceptable" in val_data


@pytest.mark.asyncio
async def test_direct_pipeline_translate_endpoint():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/pipeline/translate-turn",
            json={
                "speaker_id": "spk_1",
                "speaker_name": "Rajesh",
                "text_prompt": "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga.",
                "source_language": "hi",
                "target_language": "en",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["turn"]["source_text"] == "Kal 11 baje meeting rakh lete hain, main demo bhi dikha dunga."
        trans_out = data["turn"]["translated_text"].lower()
        assert "meeting" in trans_out and ("11" in trans_out or "eleven" in trans_out)
        assert len(data["synthesized_audio_base64"]) > 0
