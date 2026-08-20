#!/usr/bin/env bash
# ==============================================================================
# VoiceBridge Local AI OS — Stop Script
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.server.pid"
PORT_FILE="$ROOT_DIR/.server.port"

echo "🛑 Stopping VoiceBridge Local Server..."

STOPPED=0

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        echo "Sending termination signal to PID $PID..."
        kill "$PID" 2>/dev/null || true
        
        # Wait up to 5 seconds for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                STOPPED=1
                break
            fi
            sleep 0.5
        done
        
        if [ $STOPPED -eq 0 ]; then
            echo "Force killing PID $PID..."
            kill -9 "$PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PID_FILE"
fi

if [ -f "$PORT_FILE" ]; then
    RECORDED_PORT=$(cat "$PORT_FILE" 2>/dev/null || true)
    if [ -n "$RECORDED_PORT" ]; then
        PORT_PID=$(lsof -ti :"$RECORDED_PORT" 2>/dev/null || true)
        if [ -n "$PORT_PID" ]; then
            kill "$PORT_PID" 2>/dev/null || true
        fi
    fi
    rm -f "$PORT_FILE"
fi

echo "✅ VoiceBridge local server stopped cleanly."
