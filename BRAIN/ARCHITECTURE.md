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

- Provider integrations must sit behind stable interfaces.
- Realtime transport must remain independent of any one AI provider.
- Temporary processing data must be separated from persistent user data.
- Prefer streaming over full-turn blocking processing.
- Make interruption, timeout, retry, and fallback behavior explicit.
- Isolate voice identity data and authorize every access.
- Never leak audio across sessions.
- Keep components independently testable.

## Suggested provider interfaces

SpeechRecognizer
Translator
VoiceSynthesizer
LanguageDetector
VoiceProfileService

Providers can be replaced without rewriting the session engine.

## Realtime direction

WebRTC is the primary browser audio transport.

The processing pipeline should support streaming chunks, cancellation of stale generations, interruption handling, reconnection, and network adaptation.

## Latency target

Long-term target: conversational perceived latency around the sub-1.5-second range where technically achievable.

Never claim a latency target is achieved without measurement.
