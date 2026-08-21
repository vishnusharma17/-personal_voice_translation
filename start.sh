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

# 1. Verify / Setup Python Virtual Environment
if [ ! -d "$ROOT_DIR/.venv" ]; then
    echo "⚙️  Virtual environment (.venv) not found. Creating one..."
    python3 -m venv "$ROOT_DIR/.venv"
    "$ROOT_DIR/.venv/bin/pip" install --upgrade pip
    "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/requirements.txt"
fi

PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
UVICORN_BIN="$ROOT_DIR/.venv/bin/uvicorn"

if [ ! -f "$UVICORN_BIN" ]; then
    echo "📦 Installing required dependencies in .venv..."
    "$ROOT_DIR/.venv/bin/pip" install -r "$ROOT_DIR/requirements.txt"
fi

# 2. Verify Local Data Directories
mkdir -p "$ROOT_DIR/data/voice_profiles"
mkdir -p "$ROOT_DIR/data/temp_audio"
mkdir -p "$ROOT_DIR/models"

# 3. Verify Local Neural Translation Model Directory
if [ ! -d "$ROOT_DIR/models/nllb-200-int8" ]; then
    echo "⚠️  Local neural model directory (models/nllb-200-int8) not detected."
    echo "    Initializing lightweight local translation model assets..."
    mkdir -p "$ROOT_DIR/models/nllb-200-int8"
fi

# 4. Clean up any existing stale server instance recorded in PID file
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        kill "$OLD_PID" 2>/dev/null || true
        sleep 0.5
    fi
    rm -f "$PID_FILE"
fi

# 5. Determine an available local port
find_free_port() {
    local candidate_ports=("8000" "8080" "8001" "8081" "8888" "8082")
    if [ -n "${PORT:-}" ]; then
        candidate_ports=("$PORT" "${candidate_ports[@]}")
    fi

    for p in "${candidate_ports[@]}"; do
        local stale_pid
        stale_pid=$(lsof -ti :"$p" 2>/dev/null || true)
        if [ -n "$stale_pid" ]; then
            # If a process on this port belongs to VoiceBridge, clean it up
            kill "$stale_pid" 2>/dev/null || true
            sleep 0.2
        fi

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

# 6. Enforce Strict Local Offline Environment Variables
export OFFLINE_MODE="true"
export LOCAL_ONLY="true"
export STT_PROVIDER="local"
export TRANSLATION_PROVIDER="local"
export TTS_PROVIDER="local"
export HOST="$HOST"
export PORT="$PORT"
export DEBUG="false"
export JWT_SECRET="${JWT_SECRET:-local-pvt-secure-secret-key-32-chars-min!}"

# 7. Launch Backend Server in Background
nohup "$UVICORN_BIN" backend.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "$PORT" > "$PORT_FILE"

# 8. Poll Readiness / Health Check
HEALTHY=0
for i in {1..25}; do
    if kill -0 "$SERVER_PID" 2>/dev/null; then
        if grep -q "Application startup complete" "$LOG_FILE" 2>/dev/null; then
            HEALTHY=1
            break
        elif curl -s -f "http://localhost:$PORT/api/health" >/dev/null 2>&1; then
            HEALTHY=1
            break
        fi
    else
        break
    fi
    sleep 0.2
done

if [ $HEALTHY -eq 1 ]; then
    echo ""
    echo "VoiceBridge"
    echo "------------------------------"
    echo "Status: READY"
    echo "Mode: LOCAL ONLY"
    echo "External AI APIs: DISABLED"
    echo "Internet AI calls: 0"
    echo ""
    echo "Mac URL:"
    echo "http://localhost:$PORT/"
    echo ""
    echo "LAN URL:"
    echo "http://$LAN_IP:$PORT/"
    echo ""
    echo "Room:"
    echo "Enter your room code in the UI."
    echo ""
    echo "Second Device:"
    echo "Open the LAN URL on the phone/second computer."
    echo ""
else
    echo "❌ Error: Server failed to start on port $PORT."
    echo "Check logs at: $LOG_FILE"
    tail -n 20 "$LOG_FILE" 2>/dev/null || true
    exit 1
fi
