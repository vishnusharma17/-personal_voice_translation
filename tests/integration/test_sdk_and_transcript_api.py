"""
Integration Test for Transcript Export API & Python SDK
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from sdk.python.voicebridge_client import VoiceBridgeClient

client = TestClient(app)


def test_transcript_export_endpoint():
    response = client.get("/api/session/sess_test_123/transcript?format=json")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "history" in data

    vtt_resp = client.get("/api/session/sess_test_123/transcript?format=vtt")
    assert vtt_resp.status_code == 200
    assert "WEBVTT" in vtt_resp.text


def test_sdk_instantiation():
    sdk = VoiceBridgeClient(base_url="http://localhost:8000")
    assert sdk.base_url == "http://localhost:8000"
