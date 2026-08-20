#!/usr/bin/env bash
# ==============================================================================
# VoiceBridge Local AI OS — Restart Script
# ==============================================================================

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "🔄 Restarting VoiceBridge Local Platform..."
./stop.sh
sleep 1
./start.sh
