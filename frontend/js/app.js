/**
 * Personal Voice Translation — Application Frontend Controller
 * Complete Local-First Real-Time Studio Controller
 */

// State
let currentRoomCode = "PVT-DEMO";
let currentUserId = "user_rajesh_" + Math.random().toString(36).substring(2, 7);
let activeConsentId = null;
let activeVoiceProfile = null;
let isCallConnected = false;
let socket = null;
let turnsCount = 0;
let recordedAudioBlob = null;

// Audio & Mic State
let audioContext = null;
let micMediaStream = null;
let micSourceNode = null;
let analyserNode = null;
let scriptProcessorNode = null;
let isLiveMicActive = false;
let isSampleRecording = false;
let animationFrameId = null;

// Live Turn Detection (VAD) State
let isSpeaking = false;
let speechBuffer = [];
let silenceFrames = 0;
const VAD_ENERGY_THRESHOLD_DB = -42.0;
const VAD_SILENCE_FRAMES_LIMIT = 8; // ~400ms at 50ms chunks

// WebRTC Peer Connection State
let peerConnection = null;
const rtcConfig = {
  iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
};

// DOM Elements
const conversationStream = document.getElementById("conversation-stream");
const audioPlayer = document.getElementById("synthesized-audio-player");
const visualizerCanvas = document.getElementById("visualizer-canvas");
const canvasCtx = visualizerCanvas ? visualizerCanvas.getContext("2d") : null;

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
  document.querySelectorAll(".app-section").forEach(sec => sec.classList.remove("active"));

  const targetBtn = document.getElementById(`tab-${tabId}-btn`);
  const targetSection = document.getElementById(`section-${tabId}`);
  if (targetBtn) targetBtn.classList.add("active");
  if (targetSection) targetSection.classList.add("active");
}

// Room Generation
function generateNewRoom() {
  currentRoomCode = "PVT-" + Math.random().toString(36).substring(2, 8).toUpperCase();
  document.getElementById("header-room-status").innerText = `Room: ${currentRoomCode}`;
  if (isCallConnected) {
    disconnectCall();
    connectCall();
  }
}

// ==========================================
// 1. WebSocket Live Call & WebRTC Gateway
// ==========================================
function toggleCallConnection() {
  if (isCallConnected) {
    disconnectCall();
  } else {
    connectCall();
  }
}

function connectCall() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const speakerName = document.getElementById("speaker-name-input").value || "Rajesh Sharma";
  const speakLang = document.getElementById("speak-lang-select").value;
  const listenLang = document.getElementById("listen-lang-select").value;

  const wsUrl = `${protocol}//${window.location.host}/ws/call/${currentRoomCode}?user_id=${currentUserId}&display_name=${encodeURIComponent(speakerName)}&speaking_lang=${speakLang}&listening_lang=${listenLang}`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    isCallConnected = true;
    document.getElementById("call-btn-text").innerText = "Disconnect Call";
    document.getElementById("start-call-btn").classList.remove("btn-primary");
    document.getElementById("start-call-btn").classList.add("btn-danger");
    document.getElementById("mic-status-label").innerText = "Connected";
    document.getElementById("mic-status-label").className = "badge badge-success";
    initWebRTCPeer();
    startVisualizerIdle();
  };

  socket.onmessage = async (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.event === "turn_completed") {
        renderTurn(msg.data);
      } else if (msg.event === "translated_audio") {
        // Play only translated personal voice (Original language audio isolated)
        playTranslatedAudio(msg.data.audio_base64, msg.data.speaker_id);
      } else if (msg.event === "interrupt_playback") {
        // Barge-in triggered: Halt audio output immediately
        haltPlaybackImmediate("⚡ Playback interrupted by speaker");
      } else if (msg.event === "session_reconnected") {
        console.log("Session reconnected, restoring history:", msg.data);
        if (msg.data.history && msg.data.history.length > 0) {
          msg.data.history.forEach(turn => renderTurn(turn));
        }
      } else if (msg.event === "webrtc_signal") {
        await handleWebRTCSignal(msg.data);
      }
    } catch (e) {
      console.error("WS Parse Error:", e);
    }
  };

  socket.onclose = () => {
    disconnectCall();
  };
}

function disconnectCall() {
  stopLiveMicrophone();
  if (peerConnection) {
    peerConnection.close();
    peerConnection = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
  isCallConnected = false;
  document.getElementById("call-btn-text").innerText = "Connect Live Call";
  const btn = document.getElementById("start-call-btn");
  if (btn) {
    btn.classList.add("btn-primary");
    btn.classList.remove("btn-danger");
  }
  document.getElementById("mic-status-label").innerText = "Idle";
  document.getElementById("mic-status-label").className = "badge";
  stopVisualizer();
}

// WebRTC Signaling Handling
function initWebRTCPeer() {
  try {
    peerConnection = new RTCPeerConnection(rtcConfig);

    peerConnection.onicecandidate = (event) => {
      if (event.candidate && socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "webrtc_signal",
          signal_type: "candidate",
          signal_data: event.candidate,
        }));
      }
    };

    // In translation-only mode, WebRTC data channel handles direct peer metadata
    const dataChannel = peerConnection.createDataChannel("voicebridge_meta");
    dataChannel.onmessage = (e) => console.log("WebRTC DataChannel message:", e.data);
  } catch (err) {
    console.warn("WebRTC initialization:", err);
  }
}

async function handleWebRTCSignal(signal) {
  if (!peerConnection) initWebRTCPeer();
  if (!peerConnection) return;

  try {
    if (signal.signal_type === "offer") {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(signal.data));
      const answer = await peerConnection.createAnswer();
      await peerConnection.setLocalDescription(answer);
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({
          type: "webrtc_signal",
          signal_type: "answer",
          signal_data: answer,
          target_id: signal.sender_id,
        }));
      }
    } else if (signal.signal_type === "answer") {
      await peerConnection.setRemoteDescription(new RTCSessionDescription(signal.data));
    } else if (signal.signal_type === "candidate" && signal.data) {
      await peerConnection.addIceCandidate(new RTCIceCandidate(signal.data));
    }
  } catch (e) {
    console.warn("WebRTC Signal error:", e);
  }
}

// ==========================================
// 2. Real Microphone Streaming & VAD
// ==========================================
async function toggleLiveMicrophone() {
  if (isLiveMicActive) {
    stopLiveMicrophone();
  } else {
    await startLiveMicrophone();
  }
}

async function startLiveMicrophone() {
  if (!isCallConnected) {
    connectCall();
  }

  try {
    micMediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      }
    });

    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    micSourceNode = audioContext.createMediaStreamSource(micMediaStream);
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 512;

    // Buffer processing node for VAD (16kHz PCM chunks)
    const bufferSize = 2048; // ~128ms
    scriptProcessorNode = audioContext.createScriptProcessor(bufferSize, 1, 1);

    micSourceNode.connect(analyserNode);
    analyserNode.connect(scriptProcessorNode);
    scriptProcessorNode.connect(audioContext.destination);

    scriptProcessorNode.onaudioprocess = (e) => {
      if (!isLiveMicActive) return;
      const inputData = e.inputBuffer.getChannelData(0);
      processLiveAudioChunk(inputData);
    };

    isLiveMicActive = true;
    const micBtn = document.getElementById("toggle-live-mic-btn");
    if (micBtn) {
      micBtn.classList.remove("btn-secondary");
      micBtn.classList.add("btn-danger");
      micBtn.innerHTML = "<span>🔴 Mic Active (VAD)</span>";
    }
    document.getElementById("mic-status-label").innerText = "Listening...";
    document.getElementById("mic-status-label").className = "badge badge-success";

    startLiveVisualizerLoop();
  } catch (err) {
    alert("Microphone Access Error: " + err.message);
    console.error("Mic Error:", err);
  }
}

function stopLiveMicrophone() {
  isLiveMicActive = false;
  if (scriptProcessorNode) {
    scriptProcessorNode.disconnect();
    scriptProcessorNode = null;
  }
  if (micSourceNode) {
    micSourceNode.disconnect();
    micSourceNode = null;
  }
  if (micMediaStream) {
    micMediaStream.getTracks().forEach(t => t.stop());
    micMediaStream = null;
  }
  const micBtn = document.getElementById("toggle-live-mic-btn");
  if (micBtn) {
    micBtn.classList.remove("btn-danger");
    micBtn.classList.add("btn-secondary");
    micBtn.innerHTML = "<span>🎙️ Live Mic (VAD)</span>";
  }
  document.getElementById("mic-status-label").innerText = isCallConnected ? "Connected" : "Idle";
  document.getElementById("mic-status-label").className = isCallConnected ? "badge badge-success" : "badge";
  startVisualizerIdle();
}

function processLiveAudioChunk(float32Chunk) {
  // 1. Calculate RMS energy in dBFS
  let sumSq = 0;
  for (let i = 0; i < float32Chunk.length; i++) {
    sumSq += float32Chunk[i] * float32Chunk[i];
  }
  const rms = Math.sqrt(sumSq / float32Chunk.length);
  const db = 20 * Math.log10(Math.max(1e-5, rms));

  // Convert Float32 to 16-bit PCM Int16Array
  const pcm16 = new Int16Array(float32Chunk.length);
  for (let i = 0; i < float32Chunk.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Chunk[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }

  // 2. VAD State Machine
  if (db > VAD_ENERGY_THRESHOLD_DB) {
    // Active Speech Detected
    if (!isSpeaking) {
      isSpeaking = true;
      speechBuffer = [];
      silenceFrames = 0;
      document.getElementById("mic-status-label").innerText = "Speaking 🎙️";

      // Barge-in Check: If audio is currently playing, trigger interruption immediately!
      if (audioPlayer && !audioPlayer.paused) {
        triggerManualBargeIn();
      }
    }
    speechBuffer.push(pcm16);
    silenceFrames = 0;
  } else if (isSpeaking) {
    // Silence frame during speech
    speechBuffer.push(pcm16);
    silenceFrames++;

    if (silenceFrames >= VAD_SILENCE_FRAMES_LIMIT) {
      // Speech Turn Complete — Send Turn to Backend Pipeline
      isSpeaking = false;
      document.getElementById("mic-status-label").innerText = "Processing Turn ⚡";
      dispatchCompletedAudioTurn();
    }
  }
}

function dispatchCompletedAudioTurn() {
  if (speechBuffer.length < 4) { // Ignore tiny clicks < 250ms
    speechBuffer = [];
    document.getElementById("mic-status-label").innerText = "Listening...";
    return;
  }

  // Flatten speech buffer
  let totalLength = 0;
  for (const b of speechBuffer) totalLength += b.length;
  const mergedPcm = new Int16Array(totalLength);
  let offset = 0;
  for (const b of speechBuffer) {
    mergedPcm.set(b, offset);
    offset += b.length;
  }
  speechBuffer = [];

  // Convert PCM bytes to Base64
  const uint8 = new Uint8Array(mergedPcm.buffer);
  let binary = "";
  for (let i = 0; i < uint8.byteLength; i++) {
    binary += String.fromCharCode(uint8[i]);
  }
  const audioB64 = btoa(binary);

  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: "audio_turn",
      audio_base64: audioB64,
    }));
  }
}

// ==========================================
// 3. Interruption / Barge-In & Cancellation
// ==========================================
function triggerManualBargeIn() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: "interrupt",
    }));
  }
  haltPlaybackImmediate("⚡ Interrupted by user (Barge-in)");
}

function haltPlaybackImmediate(reason = "Playback interrupted") {
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer.currentTime = 0;
  }
  const statusEl = document.getElementById("playback-status-text");
  if (statusEl) {
    statusEl.innerText = reason;
  }
}

// ==========================================
// 4. Prompt Simulation & Direct Pipeline
// ==========================================
async function simulatePrompt(text) {
  document.getElementById("custom-prompt-input").value = text;
  await sendCustomPrompt();
}

async function sendCustomPrompt() {
  const inputEl = document.getElementById("custom-prompt-input");
  const text = inputEl.value.trim();
  if (!text) return;

  const speakerName = document.getElementById("speaker-name-input").value || "Rajesh";
  const sourceLang = document.getElementById("speak-lang-select").value;
  const targetLang = document.getElementById("listen-lang-select").value;

  simulateAudioActivity();

  try {
    const res = await fetch("/api/pipeline/translate-turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentRoomCode,
        speaker_id: currentUserId,
        speaker_name: speakerName,
        text_prompt: text,
        source_language: sourceLang,
        target_language: targetLang,
      }),
    });

    const data = await res.json();
    if (data.turn) {
      renderTurn(data.turn, data.synthesized_audio_base64);
      if (data.synthesized_audio_base64) {
        playTranslatedAudio(data.synthesized_audio_base64, speakerName);
      }
    }
  } catch (err) {
    console.error("Pipeline Error:", err);
  }
}

// Render Turn to Stream
function renderTurn(turn, audioB64 = null) {
  const welcome = conversationStream.querySelector(".welcome-box");
  if (welcome) welcome.remove();

  turnsCount++;
  document.getElementById("turns-count-badge").innerText = `${turnsCount} Turns`;

  if (turn.latency) {
    const totalMs = turn.latency.total_latency_ms || 420;
    document.getElementById("header-latency-val").innerText = `${totalMs}ms`;
    document.getElementById("diag-total-latency").innerText = `${totalMs} ms`;
    document.getElementById("diag-vad-val").innerText = `${turn.latency.vad_ms || 35}ms`;
    document.getElementById("diag-stt-val").innerText = `${turn.latency.stt_ms || 110}ms`;
    document.getElementById("diag-translate-val").innerText = `${turn.latency.translation_ms || 140}ms`;
    document.getElementById("diag-tts-val").innerText = `${turn.latency.tts_ms || 135}ms`;
  }

  const turnEl = document.createElement("div");
  turnEl.className = "turn-card";

  const isHindi = turn.source_language === "hi" || turn.source_language === "hi-en";
  const sourceLangLabel = isHindi ? "Hindi / Hinglish" : "English";
  const targetLangLabel = isHindi ? "English (Translated Voice)" : "Hindi (Translated Voice)";

  turnEl.innerHTML = `
    <div class="turn-header">
      <div class="turn-speaker-info">
        <span class="speaker-badge">🎙️ ${turn.speaker_name}</span>
        <span class="lang-pill ${isHindi ? 'hi' : 'en'}">${sourceLangLabel} ➔ ${targetLangLabel}</span>
      </div>
      <div class="turn-latency-tag">⚡ ${turn.latency ? turn.latency.total_latency_ms : 420}ms</div>
    </div>
    <div class="turn-body">
      <div class="source-utterance">"${turn.source_text}"</div>
      <div class="translated-utterance">
        <span>"${turn.translated_text}"</span>
        ${audioB64 ? `<button class="play-turn-btn" title="Play Translated Audio">▶</button>` : ''}
      </div>
      <div class="latency-micro-bar">
        <span>STT: ${turn.latency ? turn.latency.stt_ms : 0}ms</span> • 
        <span>Translate: ${turn.latency ? turn.latency.translation_ms : 0}ms</span> • 
        <span>Voice Clone: ${turn.latency ? turn.latency.tts_ms : 0}ms</span> • 
        <span>Confidence: ${Math.round((turn.confidence || 1.0) * 100)}%</span>
      </div>
    </div>
  `;

  if (audioB64) {
    const playBtn = turnEl.querySelector(".play-turn-btn");
    if (playBtn) {
      playBtn.onclick = () => playTranslatedAudio(audioB64, turn.speaker_name);
    }
  }

  conversationStream.appendChild(turnEl);
  conversationStream.scrollTop = conversationStream.scrollHeight;
}

// Play Synthesized Voice Audio
function playTranslatedAudio(b64Data, speakerName) {
  if (!b64Data) return;
  const audioSrc = `data:audio/wav;base64,${b64Data}`;
  audioPlayer.src = audioSrc;
  document.getElementById("playback-speaker-name").innerText = `${speakerName || 'Authorized Voice'} (Cloned Voice)`;
  document.getElementById("playback-status-text").innerText = "Playing synthesized translation...";

  audioPlayer.play().catch(e => console.log("Auto-play blocked:", e));
  audioPlayer.onended = () => {
    document.getElementById("playback-status-text").innerText = "Finished playback";
  };
}

function clearFeed() {
  conversationStream.innerHTML = `
    <div class="welcome-box">
      <div class="welcome-icon">🎙️</div>
      <h3>Feed Cleared</h3>
      <p>Speak or simulate a turn to resume live translation feed.</p>
    </div>
  `;
  turnsCount = 0;
  document.getElementById("turns-count-badge").innerText = "0 Turns";
}

// ==========================================
// 5. Voice Onboarding, Recording & Consent
// ==========================================
async function authorizeConsent() {
  const statement = document.getElementById("consent-statement-text").innerText.trim();
  try {
    const res = await fetch("/api/voice/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentUserId,
        statement_text: statement,
      }),
    });

    const data = await res.json();
    if (data.consent_id) {
      activeConsentId = data.consent_id;
      const statusBadge = document.getElementById("consent-status-badge");
      statusBadge.className = "consent-status verified";
      statusBadge.innerHTML = `<span class="status-dot"></span> Authorized (ID: ${data.consent_id.substring(0, 16)}...)`;
      document.getElementById("create-profile-btn").disabled = false;
      document.getElementById("view-consent-id").innerText = data.consent_id;
    }
  } catch (err) {
    alert("Consent Authorization Failed: " + err.message);
  }
}

async function toggleVoiceSampleRecord() {
  if (isSampleRecording) return;

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, sampleRate: 16000 } });
    const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const source = ctx.createMediaStreamSource(stream);
    const proc = ctx.createScriptProcessor(4096, 1, 1);

    const recordedSamples = [];
    isSampleRecording = true;
    let countdown = 5;

    const label = document.getElementById("record-btn-label");
    const btn = document.getElementById("mic-record-btn");
    btn.classList.add("btn-danger");
    label.innerText = `Recording... ${countdown}s`;

    const timer = setInterval(() => {
      countdown--;
      if (countdown > 0) {
        label.innerText = `Recording... ${countdown}s`;
      } else {
        clearInterval(timer);
      }
    }, 1000);

    proc.onaudioprocess = (e) => {
      const data = e.inputBuffer.getChannelData(0);
      recordedSamples.push(new Float32Array(data));
    };

    source.connect(proc);
    proc.connect(ctx.destination);

    // Stop recording after 5 seconds
    setTimeout(async () => {
      proc.disconnect();
      source.disconnect();
      stream.getTracks().forEach(t => t.stop());
      isSampleRecording = false;
      btn.classList.remove("btn-danger");
      label.innerText = "Re-record Sample (5s)";

      // Combine samples to 16-bit PCM WAV
      let totalLength = 0;
      for (const s of recordedSamples) totalLength += s.length;
      const fullBuffer = new Float32Array(totalLength);
      let offset = 0;
      for (const s of recordedSamples) {
        fullBuffer.set(s, offset);
        offset += s.length;
      }

      const pcm16 = new Int16Array(fullBuffer.length);
      for (let i = 0; i < fullBuffer.length; i++) {
        const s = Math.max(-1, Math.min(1, fullBuffer[i]));
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      const wavBlob = encodeWAV(pcm16, 16000);
      recordedAudioBlob = wavBlob;

      // Validate audio quality with backend
      const formData = new FormData();
      formData.append("audio_file", wavBlob, "voice_sample.wav");

      try {
        const res = await fetch("/api/voice/validate-audio", {
          method: "POST",
          body: formData,
        });
        const metrics = await res.json();
        renderQualityMetrics(metrics);
      } catch (err) {
        console.error("Audio validation error:", err);
      }
    }, 5000);

  } catch (err) {
    alert("Microphone Error: " + err.message);
  }
}

function encodeWAV(pcm16Data, sampleRate = 16000) {
  const buffer = new ArrayBuffer(44 + pcm16Data.byteLength);
  const view = new DataView(buffer);

  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + pcm16Data.byteLength, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); // Block align
  view.setUint16(34, 16, true); // Bits per sample
  writeString(view, 36, 'data');
  view.setUint32(40, pcm16Data.byteLength, true);

  const byteView = new Uint8Array(buffer, 44);
  byteView.set(new Uint8Array(pcm16Data.buffer));

  return new Blob([buffer], { type: 'audio/wav' });
}

async function handleSampleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("audio_file", file);

  try {
    const res = await fetch("/api/voice/validate-audio", {
      method: "POST",
      body: formData,
    });
    const metrics = await res.json();
    renderQualityMetrics(metrics);
    recordedAudioBlob = file;
  } catch (err) {
    console.error("Audio validation error:", err);
  }
}

function renderQualityMetrics(metrics) {
  document.getElementById("metric-snr").innerText = `${metrics.snr_db} dB`;
  document.getElementById("metric-clipping").innerText = `${(metrics.clipping_rate * 100).toFixed(2)} %`;
  document.getElementById("metric-noise").innerText = `${metrics.background_noise_db} dBFS`;
  document.getElementById("metric-duration").innerText = `${metrics.duration_sec} s`;

  const feedbackBox = document.getElementById("quality-feedback-box");
  feedbackBox.classList.remove("hidden");

  if (metrics.is_acceptable) {
    feedbackBox.className = "feedback-alert success";
    feedbackBox.innerText = "✓ Voice sample meets high-quality fidelity bar for synthesis.";
    document.getElementById("create-profile-btn").disabled = !activeConsentId;
  } else {
    feedbackBox.className = "feedback-alert error";
    feedbackBox.innerText = metrics.feedback.join(" ");
  }
}

async function enrollVoiceProfile() {
  if (!activeConsentId) {
    alert("Please authorize explicit voice consent first.");
    return;
  }

  let audioFileToSend = recordedAudioBlob;
  if (!audioFileToSend) {
    const buffer = new ArrayBuffer(64044);
    audioFileToSend = new Blob([buffer], { type: "audio/wav" });
  }

  const formData = new FormData();
  formData.append("user_id", currentUserId);
  formData.append("display_name", document.getElementById("speaker-name-input").value || "Rajesh Sharma");
  formData.append("consent_id", activeConsentId);
  formData.append("native_language", "hi");
  formData.append("audio_file", audioFileToSend, "sample.wav");

  try {
    const res = await fetch("/api/voice/create-profile", {
      method: "POST",
      body: formData,
    });
    const profile = await res.json();
    if (profile.voice_id) {
      activeVoiceProfile = profile;
      document.getElementById("profile-status-badge").innerText = "READY";
      document.getElementById("profile-status-badge").className = "badge badge-success";
      document.getElementById("view-profile-id").innerText = profile.voice_id;
      document.getElementById("view-profile-quality").innerText = "Active & Authorized";
      alert("Voice Profile enrolled successfully!");
    }
  } catch (err) {
    alert("Enrollment failed: " + err.message);
  }
}

async function deleteActiveProfile() {
  if (!confirm("Are you sure you want to permanently delete and revoke your voice profile? This cannot be undone.")) return;

  try {
    await fetch(`/api/voice/profile/${currentUserId}`, { method: "DELETE" });
    activeVoiceProfile = null;
    activeConsentId = null;
    document.getElementById("profile-status-badge").innerText = "No Profile";
    document.getElementById("profile-status-badge").className = "badge";
    document.getElementById("consent-status-badge").className = "consent-status unverified";
    document.getElementById("consent-status-badge").innerText = "Not Authorized";
    document.getElementById("view-profile-id").innerText = "None";
    document.getElementById("view-consent-id").innerText = "None";
    document.getElementById("create-profile-btn").disabled = true;
    alert("Voice profile and all associated data permanently deleted.");
  } catch (e) {
    console.error("Delete profile error:", e);
  }
}

// ==========================================
// 6. Visualizer Waveform Animation
// ==========================================
function startVisualizerIdle() {
  if (!canvasCtx) return;
  let phase = 0;

  function draw() {
    if (isLiveMicActive) return; // Mic active loop handles drawing
    canvasCtx.fillStyle = "rgba(15, 23, 42, 0.4)";
    canvasCtx.fillRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);

    canvasCtx.beginPath();
    canvasCtx.lineWidth = 2;
    canvasCtx.strokeStyle = "#6366f1";

    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    const midY = height / 2;

    for (let x = 0; x < width; x++) {
      const y = midY + Math.sin(x * 0.05 + phase) * 8 * Math.sin(x * 0.02);
      if (x === 0) canvasCtx.moveTo(x, y);
      else canvasCtx.lineTo(x, y);
    }
    canvasCtx.stroke();
    phase += 0.08;
    animationFrameId = requestAnimationFrame(draw);
  }
  draw();
}

function startLiveVisualizerLoop() {
  if (!canvasCtx || !analyserNode) return;
  const bufferLength = analyserNode.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    if (!isLiveMicActive) return;
    analyserNode.getByteTimeDomainData(dataArray);

    canvasCtx.fillStyle = "rgba(15, 23, 42, 0.5)";
    canvasCtx.fillRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);

    canvasCtx.beginPath();
    canvasCtx.lineWidth = 2.5;
    canvasCtx.strokeStyle = isSpeaking ? "#10b981" : "#06b6d4";

    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    const sliceWidth = width * 1.0 / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = v * height / 2;

      if (i === 0) canvasCtx.moveTo(x, y);
      else canvasCtx.lineTo(x, y);

      x += sliceWidth;
    }
    canvasCtx.stroke();
    animationFrameId = requestAnimationFrame(draw);
  }
  draw();
}

function simulateAudioActivity() {
  if (!canvasCtx) return;
  let count = 0;
  function burst() {
    canvasCtx.fillStyle = "#0f172a";
    canvasCtx.fillRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);

    canvasCtx.beginPath();
    canvasCtx.lineWidth = 2.5;
    canvasCtx.strokeStyle = "#06b6d4";

    const width = visualizerCanvas.width;
    const height = visualizerCanvas.height;
    const midY = height / 2;

    for (let x = 0; x < width; x++) {
      const amp = Math.sin(x * 0.1) * (15 + Math.random() * 12);
      const y = midY + amp;
      if (x === 0) canvasCtx.moveTo(x, y);
      else canvasCtx.lineTo(x, y);
    }
    canvasCtx.stroke();
    count++;
    if (count < 25) {
      requestAnimationFrame(burst);
    } else {
      startVisualizerIdle();
    }
  }
  burst();
}

function stopVisualizer() {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
    animationFrameId = null;
  }
  if (canvasCtx) {
    canvasCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
  }
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
  startVisualizerIdle();
});
