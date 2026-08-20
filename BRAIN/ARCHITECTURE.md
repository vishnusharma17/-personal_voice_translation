# Architecture Brain — How

## End-to-end flow

Speaker A
→ microphone/audio capture
→ VAD/turn detection
→ streaming speech recognition
→ language detection
→ context and intent
→ natural translation
→ prosody planning
→ authorized personal voice synthesis
→ streamed audio
→ Speaker B

The reverse direction uses the same pipeline.

## Major components

1. Web application / call UI
2. WebRTC realtime transport
3. Realtime session gateway
4. Audio/VAD layer
5. Speech recognition adapter
6. Language/context engine
7. Translation adapter
8. Naturalness/prosody layer
9. Voice synthesis adapter
10. Session state
11. Authentication/authorization
12. Privacy/data-retention controls
13. Observability
14. Automated QA

## Architecture principles

- Provider integrations must sit behind stable interfaces (`SpeechRecognizer`, `Translator`, `VoiceSynthesizer`, `LanguageDetector`, `VoiceProfileService`).
- Local-first & self-hosted by design: Core processing runs locally on user-controlled infrastructure without external third-party API dependencies.
- CPU/GPU fallback: Models must run efficiently on standard CPU and Apple Silicon / CUDA GPUs.
- Low-memory footprint: Pipeline optimized to run concurrently on resource-constrained 8GB RAM machines.
- Temporary processing data must be separated from persistent user data.
- Prefer streaming over full-turn blocking processing.
- Make interruption, timeout, retry, and fallback behavior explicit.
- Isolate voice identity data and authorize every access.
- Never leak audio across sessions.
- Keep components independently testable.

## Local Open-Source Stack Strategy

1. **Local STT**: Faster-Whisper / Whisper.cpp / Vosk (quantized `tiny`/`base` models for CPU & low memory footprint ~150-300MB RAM).
2. **Local Translation**: MarianMT / NLLB-200 / Quantized Llama-3.2-1B / Qwen-2.5-1.5B (quantized INT4/INT8 ~800MB-1.2GB RAM).
3. **Local Personal Voice Cloning & TTS**: Piper TTS / Coqui TTS / ChatTTS / OpenVoice (low-resource localized voice synthesis with speaker embedding modulation).
4. **Local Voice Profile & Consent**: Local cryptographic hashing, SNR signal analysis, and local file storage.

## Realtime direction

WebRTC is the primary browser audio transport.

The processing pipeline supports streaming chunks, cancellation of stale generations, interruption handling, reconnection, and network adaptation.

## Latency target

Long-term target: conversational perceived latency around the sub-1.5-second range where technically achievable on local hardware.

Never claim a latency target is achieved without measurement.

