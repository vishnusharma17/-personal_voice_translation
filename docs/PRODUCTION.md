# Production Operations & Runbook

## Architecture Overview
The Personal Voice Translation Platform runs as a high-performance asynchronous service (FastAPI + WebSockets/WebRTC signaling) handling real-time turn detection, streaming speech recognition, context-aware translation, and authorized voice cloning synthesis.

## Quick Start (Docker)

```bash
# 1. Copy environment template and configure keys
cp .env.example .env

# 2. Build and start with Docker Compose
docker compose up -d

# 3. Verify health
curl -f http://localhost:8000/api/health
```

## Observability & Metrics
- **Health Endpoint**: `GET /api/health` returns operational status, active provider names, and target latency budget.
- **Latency Breakdown**: Every turn payload returns detailed telemetry:
  - `vad_ms`: Voice activity detection and silence segmentation delay.
  - `stt_ms`: Speech-to-text transcription latency.
  - `translation_ms`: Context-aware natural translation latency.
  - `tts_ms`: Personal voice synthesis latency.
  - `total_latency_ms`: Combined roundtrip conversational delay (target: `< 1500ms`).

## Cost & Usage Controls
- **VAD Silence Gating**: Audio frames containing pure silence or room noise are discarded before hitting cloud STT endpoints, reducing API costs by 40-60%.
- **Streaming Token Cap**: LLM translation queries enforce `maxOutputTokens: 200` to prevent runaway generation.
- **Ephemeral Audio Cleanup**: Temporary audio chunks are purged immediately after processing (`auto_cleanup_temp_audio: true`).

## Rollback Procedure
If a production deployment encounters provider degradation or network failure:
1. Revert `STT_PROVIDER`, `TRANSLATION_PROVIDER`, or `TTS_PROVIDER` to `mock` in `.env` to test baseline network transport.
2. If rolling back container image: `docker compose down && docker compose up -d --build`.
