"""
VoiceBridge Python SDK Client
Lightweight SDK for interacting with Personal Voice Translation API endpoints.
"""

import base64
import json
import urllib.request
import urllib.parse


class VoiceBridgeClient:
    """
    Python SDK Client for VoiceBridge Real-Time Personal Voice Translation Platform.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def create_room(self, host_user_id: str, room_code: str | None = None) -> dict:
        url = f"{self.base_url}/api/rooms/create"
        payload = json.dumps({"host_user_id": host_user_id, "room_code": room_code}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def translate_turn(
        self,
        speaker_id: str,
        speaker_name: str,
        text_prompt: str,
        source_language: str = "hi",
        target_language: str = "en",
        session_id: str = "demo_session",
    ) -> dict:
        url = f"{self.base_url}/api/pipeline/translate-turn"
        payload = json.dumps({
            "session_id": session_id,
            "speaker_id": speaker_id,
            "speaker_name": speaker_name,
            "text_prompt": text_prompt,
            "source_language": source_language,
            "target_language": target_language,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))

    def get_transcript(self, session_id: str, format_type: str = "json") -> dict | str:
        url = f"{self.base_url}/api/session/{session_id}/transcript?format={format_type}"
        with urllib.request.urlopen(url) as response:
            res_bytes = response.read()
            if format_type == "json":
                return json.loads(res_bytes.decode("utf-8"))
            return res_bytes.decode("utf-8")
