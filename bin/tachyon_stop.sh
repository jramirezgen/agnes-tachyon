#!/usr/bin/env bash
# Stop all Tachyon processes
echo "Stopping Agnes Tachyon..."

# Kill by known ports/patterns
pkill -f "tachyon.server" 2>/dev/null && echo "  ✓ Server stopped" || true
pkill -f "tachyon.watchdog" 2>/dev/null && echo "  ✓ Watchdog stopped" || true
pkill -f "tachyon.miniverse_bridge" 2>/dev/null && echo "  ✓ Bridge stopped" || true

# Kill any process on Tachyon port
TACHYON_PORT="${TACHYON_PORT:-7777}"
fuser -k "${TACHYON_PORT}/tcp" 2>/dev/null && echo "  ✓ Port ${TACHYON_PORT} freed" || true

echo "Agnes Tachyon systems suspended."
