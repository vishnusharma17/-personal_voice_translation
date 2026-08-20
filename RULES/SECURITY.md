# Security Rules

Protect:
- authentication;
- session tokens;
- API keys;
- voice profiles;
- raw audio;
- transcripts;
- participant identity.

Requirements:
- no secrets in source control;
- authenticated and authorized access to voice profiles;
- strict session isolation;
- input validation;
- rate limiting where appropriate;
- auditable privileged access;
- safe error handling;
- security review before production.

Critical security issues block release.
