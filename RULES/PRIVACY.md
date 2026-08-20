# Privacy Rules
 
Use data minimization and local-first execution.

Defaults:
- core audio processing runs locally on user-controlled infrastructure;
- raw audio never leaves user infrastructure for external third-party hosted APIs;
- no permanent call recording unless explicitly enabled;
- temporary audio has controlled retention and automatic cleanup;
- transcripts are not retained by default unless required and disclosed;
- voice profiles are separately protected and stored locally;
- users can delete/reset their voice profile and applicable stored data at any time.

Never log:
- raw audio;
- secrets;
- auth tokens;
- sensitive conversation content in ordinary logs.
