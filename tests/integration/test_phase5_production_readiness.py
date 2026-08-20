"""
Integration Tests: Phase 5 Production Readiness, Health, and Environment Sanity
"""

from pathlib import Path
import pytest
import httpx
from backend.config import settings
from backend.main import app


@pytest.mark.asyncio
async def test_production_health_check_payload():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "target_latency_budget_ms" in data
        assert "providers" in data
        assert "stt" in data["providers"]
        assert "translation" in data["providers"]
        assert "tts" in data["providers"]


def test_production_deployment_artifacts_exist():
    base_dir = Path(__file__).resolve().parent.parent.parent
    assert (base_dir / "Dockerfile").exists()
    assert (base_dir / "docker-compose.yml").exists()
    assert (base_dir / ".env.example").exists()
    assert (base_dir / "docs" / "PRODUCTION.md").exists()


def test_configuration_defaults_safety():
    assert settings.target_latency_budget_ms <= 1500
    assert settings.retain_call_audio is False  # Privacy default
    assert settings.auto_cleanup_temp_audio is True  # Cost & disk safety
