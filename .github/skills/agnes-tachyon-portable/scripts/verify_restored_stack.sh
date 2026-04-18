#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT="${1:-$PWD}"
STACK_DIR="$TARGET_ROOT/apps/miniverse/my-world"

if [[ ! -d "$STACK_DIR" ]]; then
  echo "[ERROR] no se encontró stack dir en $STACK_DIR" >&2
  exit 1
fi

cd "$STACK_DIR"

if ! curl -fsS http://localhost:4331/api/agents >/dev/null 2>&1; then
  echo "[verify] API no responde en 4331; intentando arrancar stack base"
  ENABLE_LIBRARIAN_LEARNER=0 ./start_operational_stack.sh >/tmp/verify_restored_stack.log 2>&1 || true
fi

curl -fsS http://localhost:4331/api/agents >/dev/null
echo "[verify] api-ok"

curl -fsS http://localhost:4331/ >/dev/null
echo "[verify] frontend-ok"

ps aux | grep -E 'runtime.py|node server.js' | grep -v grep >/dev/null
echo "[verify] processes-ok"

echo "[verify] verificación base completada"