#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PID_FILE="generated/operational_stack.pids"

if [ ! -f "$PID_FILE" ]; then
  echo "[stack] no hay stack operativo registrado"
  exit 0
fi

SERVER_PID="$(awk -F= '/^SERVER_PID=/{print $2}' "$PID_FILE")"
AGENTS_PID="$(awk -F= '/^AGENTS_PID=/{print $2}' "$PID_FILE")"
LEARN_PID="$(awk -F= '/^LEARN_PID=/{print $2}' "$PID_FILE")"

LEARN_SCRIPT_PATH="$(cd "$ROOT/../my-miniverse/agents" && pwd)/librarian_learn.py"
RUNTIME_SCRIPT_PATH="$(cd "$ROOT/../my-miniverse/agents" && pwd)/runtime.py"

kill_pid_if_running() {
  local pid="$1"
  if [ -n "$pid" ] && kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
  fi
}

# Detener procesos registrados
kill_pid_if_running "$LEARN_PID"
kill_pid_if_running "$AGENTS_PID"
kill_pid_if_running "$SERVER_PID"

# Limpiar huérfanos del stack (sesiones antiguas sin PID_FILE válido)
pkill -f "python3 .*librarian_learn.py" >/dev/null 2>&1 || true
pkill -f "python3 .*librarian_learn_swift.py" >/dev/null 2>&1 || true
pkill -f "python3 .*runtime.py" >/dev/null 2>&1 || true
pkill -f "swift/cli/export.py" >/dev/null 2>&1 || true
pkill -f "swift.cli.main export" >/dev/null 2>&1 || true

rm -f "$PID_FILE"
echo "[stack] stack operativo detenido"