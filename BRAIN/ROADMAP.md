# Roadmap (Local-First Open-Source AI Architecture)

## Phase 0 — Foundation
- [x] Initialize repository/app
- [x] Lock technical stack (Python / FastAPI / WebSockets / WebRTC)
- [x] Define provider interfaces (`SpeechRecognizer`, `LanguageDetector`, `Translator`, `VoiceSynthesizer`, `VoiceProfileService`)
- [x] Define auth/session model
- [x] Define voice onboarding model
- [x] Establish testing infrastructure

## Phase 1 — Voice (Local & Consented)
- [x] Voice onboarding
- [x] Consent/authorization
- [x] Voice quality validation (SNR / clipping / noise floor)
- [x] Secure voice profile (local storage & cryptographic hash)
- [x] Voice deletion/reset

## Phase 2 — Translation (Local Open-Source Pipeline)
- [x] Local streaming STT adapter (Faster-Whisper / Whisper.cpp / Vosk)
- [x] Local Hinglish & Hindi ↔ English normalizer & translator (MarianMT / NLLB / Tiny Llama/Qwen / Rule Engine)
- [x] Local personal voice synthesizer (Piper / Coqui / Mel-spectrogram & speaker timbre modulation)
- [x] Translation quality and semantic fidelity evaluation
- [x] Low-memory CPU/GPU optimization (<8GB RAM compatibility)

## Phase 3 — Realtime
- [x] WebRTC sessions
- [x] Adaptive turn detection
- [x] Streaming synthesis
- [x] Interruption handling
- [x] Reconnect behavior
- [x] Session isolation

## Phase 4 — Quality & Safety
- [x] Voice similarity evaluation
- [x] Translation evaluation
- [x] Latency measurement on local hardware
- [x] Reliability testing
- [x] Security audit
- [x] Privacy audit
- [x] Abuse prevention

## Phase 5 — Production
- [x] Self-hosted deployment (Docker / CPU & GPU)
- [x] Observability
- [x] Production QA
- [x] Rollback procedure
- [x] Resource & memory usage controls

## Later
- [ ] More languages
- [ ] Meeting integrations
- [ ] Group conversations
- [ ] Business/customer-support mode
- [ ] SDK/API

Do not silently jump to later phases.
