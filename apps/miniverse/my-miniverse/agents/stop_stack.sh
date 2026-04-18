#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PID_FILE="generated/stack.pids"

if [ ! -f "$PID_FILE" ]; then
  echo "[stack] no hay archivo de PIDs en generated/stack.pids"
  exit 0
fi

SERVER_PID="$(awk -F= '/^SERVER_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
AGENTS_PID="$(awk -F= '/^AGENTS_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
UI_PID="$(awk -F= '/^UI_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
SERVER_STARTED_BY_SCRIPT="$(awk -F= '/^SERVER_STARTED_BY_SCRIPT=/{print $2}' "$PID_FILE" 2>/dev/null || true)"

if [ -n "$AGENTS_PID" ] && kill -0 "$AGENTS_PID" >/dev/null 2>&1; then
  kill "$AGENTS_PID" >/dev/null 2>&1 || true
  echo "[stack] detenido AGENTS_PID=$AGENTS_PID"
else
  echo "[stack] AGENTS_PID no activo"
fi

if [ "${SERVER_STARTED_BY_SCRIPT:-0}" = "1" ] && [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" >/dev/null 2>&1; then
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  echo "[stack] detenido SERVER_PID=$SERVER_PID"
else
  echo "[stack] SERVER_PID externo o no activo"
fi

if [ -n "$UI_PID" ] && kill -0 "$UI_PID" >/dev/null 2>&1; then
  kill "$UI_PID" >/dev/null 2>&1 || true
  echo "[stack] detenido UI_PID=$UI_PID"
else
  echo "[stack] UI_PID externo o no activo"
fi

rm -f "$PID_FILE"
echo "[stack] stack detenido"
