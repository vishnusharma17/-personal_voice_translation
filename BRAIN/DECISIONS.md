# Permanent Decisions

This is the single source of truth for durable architectural/product decisions.

## DECISION-001 — Real-time browser communication
Status: Approved

Decision:
Use WebRTC as the primary browser audio transport for live conversations.

Reason:
The product requires low-latency two-way audio.

## DECISION-002 — Provider abstraction
Status: Approved

Decision:
Keep STT, translation, language detection, voice synthesis, and voice-profile services behind internal interfaces.

Reason:
Avoid provider lock-in and make quality/cost optimization possible.

## DECISION-003 — Consent-first voice
Status: Approved

Decision:
Personal voice synthesis is limited to an explicitly authorized/consented voice.

Reason:
Voice identity is sensitive and must not become an arbitrary impersonation feature.

Add new permanent decisions here. Do not duplicate them in other brain files.
