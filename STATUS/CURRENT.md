# Current Status — Single Source of Truth

## Overall
Phase 0 & Phase 1 Complete. Phase 2 Architecture Refactored to Local-First Open-Source AI.

## Phase
Phase 2 — Transitioning to Local-First Open-Source Pipeline (Self-Hosted, No External AI APIs).

## Architecture Audit & Decision
Per `DECISION-004`, the platform is strictly local-first and self-hosted. External paid AI APIs (Whisper API, Gemini API, ElevenLabs API) are optional legacy fallbacks, not required runtime dependencies.

### 1. External Dependencies Audit
| Component | Current Hosted Adapter | External Dependency | Local-First Replacement | Memory Footprint |
| :--- | :--- | :--- | :--- | :--- |
| **STT** | `WhisperSTT` | `api.openai.com` (`OPENAI_API_KEY`) | `Faster-Whisper` / `whisper.cpp` (INT8 `tiny`/`base`) | ~180 MB RAM |
| **Translation** | `GeminiTranslator` | `generativelanguage.googleapis.com` | `MarianMT` (`opus-mt-hi-en`/`en-hi`) / `NLLB-200` / Quantized `Llama-3.2-1B` | ~350 MB RAM |
| **TTS / Voice** | `ElevenLabsTTS` | `api.elevenlabs.io` (`ELEVENLABS_API_KEY`) | `Piper TTS` (Fast ONNX) + Voice Timbre Modulator / `Coqui XTTS` | ~80 MB RAM |
| **VAD / Audio** | `EnergyVAD` | None (Local Signal Processing) | `EnergyVAD` (Noise-Adaptive) + WebRTC VAD | ~5 MB RAM |
| **Voice Profile** | `SecureVoiceProfileService` | None (Local SHA-256 + SNR) | Local filesystem + cryptographic hashing | ~10 MB RAM |

**Total Local Memory Footprint**: ~625 MB RAM (Runs effortlessly on an 8GB RAM machine with zero network calls).

### 2. Expected Local Hardware & Latency Profile (8GB Mac / CPU)
- **VAD Turn Detection**: 30 – 50 ms
- **Local STT (Faster-Whisper INT8)**: 150 – 280 ms
- **Local Translation (MarianMT / INT4)**: 80 – 180 ms
- **Local Voice Synthesis (Piper / Local Vocoder)**: 90 – 160 ms
- **Total Local Roundtrip Latency**: **~350 – 670 ms** (Well below the 1500ms budget).

### 3. Migration Order
1. **Preserve Interfaces**: Keep `SpeechRecognizer`, `Translator`, `VoiceSynthesizer`, and `VoiceProfileService` intact.
2. **Local STT Adapter**: Add `LocalWhisperSTT` (CTranslate2/ONNX INT8 runtime with CPU & Metal acceleration).
3. **Local Translation Adapter**: Add `LocalTranslationAdapter` (MarianMT / NLLB-200 / lightweight GGUF LLM + Hinglish dictionary).
4. **Local TTS Adapter**: Add `LocalVoiceSynthesizer` (Piper ONNX / speaker timbre modulation).
5. **Provider Factory Defaults**: Set `factory.py` defaults to `local` with zero requirement for API keys.
6. **Offline Verification**: Verify the entire end-to-end pipeline in strict sandbox mode without network access.

## Blocker
None. Awaiting user review of the audit and migration strategy before executing the local provider adapter implementation.
