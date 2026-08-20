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
- [ ] Local streaming STT adapter (Faster-Whisper / Whisper.cpp / Vosk)
- [ ] Local Hinglish & Hindi ↔ English normalizer & translator (MarianMT / NLLB / Tiny Llama/Qwen / Rule Engine)
- [ ] Local personal voice synthesizer (Piper / Coqui / Mel-spectrogram & speaker timbre modulation)
- [ ] Translation quality and semantic fidelity evaluation
- [ ] Low-memory CPU/GPU optimization (<8GB RAM compatibility)

## Phase 3 — Realtime
- [ ] WebRTC sessions
- [ ] Adaptive turn detection
- [ ] Streaming synthesis
- [ ] Interruption handling
- [ ] Reconnect behavior
- [ ] Session isolation

## Phase 4 — Quality & Safety
- [ ] Voice similarity evaluation
- [ ] Translation evaluation
- [ ] Latency measurement on local hardware
- [ ] Reliability testing
- [ ] Security audit
- [ ] Privacy audit
- [ ] Abuse prevention

## Phase 5 — Production
- [ ] Self-hosted deployment (Docker / CPU & GPU)
- [ ] Observability
- [ ] Production QA
- [ ] Rollback procedure
- [ ] Resource & memory usage controls

## Later
- [ ] More languages
- [ ] Meeting integrations
- [ ] Group conversations
- [ ] Business/customer-support mode
- [ ] SDK/API

Do not silently jump to later phases.
