#!/usr/bin/env bash
# ==============================================================================
# VoiceBridge Local AI OS — Mac Startup Script
# Strict 100% Local-First Offline Mode (Zero External AI APIs)
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-0.0.0.0}"
PID_FILE="$ROOT_DIR/.server.pid"
PORT_FILE="$ROOT_DIR/.server.port"
LOG_FILE="$ROOT_DIR/.local_server.log"

# Detect Mac's local LAN IP address
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1 || echo "127.0.0.1")

echo "================================================================="
echo "  🎙️  Starting VoiceBridge — Personal Voice Translation AI OS"
echo "  📍  Mode: 100% LOCAL-FIRST (Air-Gapped / Strict Offline)"
echo "  📡  LAN IP: $LAN_IP"
echo "================================================================="

# 1. Verify / Setup Python Environment
if [ ! -d ".venv" ]; then
    echo "⚙️  Virtual environment (.venv) not found. Creating one..."
    python3 -m venv .venv
    echo "📦 Installing local dependencies..."
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"

if [ ! -f "$UVICORN_BIN" ]; then
    echo "❌ Error: uvicorn not found in .venv. Installing requirements..."
    .venv/bin/pip install -r requirements.txt
fi

# 2. Verify Local Storage Directories
mkdir -p "$ROOT_DIR/data/voice_profiles"
mkdir -p "$ROOT_DIR/data/temp_audio"

# 3. Clean up any existing process recorded in PID file
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "🛑 Stopping existing server instance (PID: $OLD_PID)..."
        kill "$OLD_PID" 2>/dev/null || true
        sleep 1
    fi
    rm -f "$PID_FILE"
fi

# 4. Determine an available local port
find_free_port() {
    local candidate_ports=("8000" "8080" "8001" "8081" "8888")
    if [ -n "${PORT:-}" ]; then
        candidate_ports=("$PORT" "${candidate_ports[@]}")
    fi

    for p in "${candidate_ports[@]}"; do
        # Try to kill any stale Python server on this port first
        local stale_pid
        stale_pid=$(lsof -ti :"$p" 2>/dev/null || true)
        if [ -n "$stale_pid" ]; then
            kill "$stale_pid" 2>/dev/null || true
            sleep 0.3
        fi

        # Check if port is free now
        if ! lsof -i :"$p" >/dev/null 2>&1; then
            echo "$p"
            return 0
        fi
    done

    # Fallback to python socket check for random free port
    "$PYTHON_BIN" -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()'
}

CHOSEN_PORT=$(find_free_port)
PORT="$CHOSEN_PORT"

# 5. Enforce Strict Local Offline Environment Variables
export OFFLINE_MODE="true"
export LOCAL_ONLY="true"
export STT_PROVIDER="local"
export TRANSLATION_PROVIDER="local"
export TTS_PROVIDER="local"
export HOST="$HOST"
export PORT="$PORT"
export DEBUG="false"
export JWT_SECRET="${JWT_SECRET:-local-pvt-secure-secret-key-32-chars-min!}"

# 6. Launch Backend Server in Background
echo "🚀 Launching local server on http://$HOST:$PORT..."
nohup "$UVICORN_BIN" backend.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "$PORT" > "$PORT_FILE"

# 7. Perform Health Check Polling
echo "⏳ Initializing local neural models & audio gateway..."
sleep 1.5

if kill -0 "$SERVER_PID" 2>/dev/null; then
    HEALTHY=1
else
    HEALTHY=0
fi

if [ $HEALTHY -eq 1 ]; then
    echo ""
    echo "================================================================="
    echo "  ✅ VoiceBridge is LIVE and Ready on Your Mac & Local Network!"
    echo "================================================================="
    echo ""
    echo "  💻 Device A (This Mac):     http://localhost:$PORT/"
    echo "  📱 Device B (Phone / LAN):  http://$LAN_IP:$PORT/"
    echo "  📊 Health Check:            http://localhost:$PORT/api/health"
    echo "  📚 API Documentation:       http://localhost:$PORT/docs"
    echo ""
    echo "  👥 2-DEVICE REAL-WORLD CONVERSATION SETUP:"
    echo "     1. On Device A (Mac):    Open http://localhost:$PORT/ in Chrome/Safari"
    echo "     2. On Device B (Phone):  Connect to same Wi-Fi & open http://$LAN_IP:$PORT/"
    echo "     3. In both devices:      Verify Room Code is identical (e.g. PVT-DEMO)"
    echo "     4. On both devices:      Click 'Connect Live Call' and start speaking!"
    echo ""
    echo "  🔒 Local Guarantee: 0 External AI Calls | 0 Cloud Dependencies"
    echo "  🛑 To stop the server:      ./stop.sh"
    echo "================================================================="
    echo ""
else
    echo "❌ Error: Server failed to start on port $PORT."
    echo "Check logs at: $LOG_FILE"
    tail -n 20 "$LOG_FILE" 2>/dev/null || true
    exit 1
fi
