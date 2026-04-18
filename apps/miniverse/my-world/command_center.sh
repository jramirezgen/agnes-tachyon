#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PID_FILE="generated/operational_stack.pids"

if [ ! -f "$PID_FILE" ]; then
  echo "[cc] stack no detectado. iniciando stack operativo..."
  ./start_operational_stack.sh
fi

if [ ! -f "$PID_FILE" ]; then
  echo "[cc] no se pudo detectar operational_stack.pids"
  exit 1
fi

SERVER_URL="$(awk -F= '/^SERVER_URL=/{print $2}' "$PID_FILE")"
if [ -z "$SERVER_URL" ]; then
  PORT="$(awk -F= '/^PORT=/{print $2}' "$PID_FILE")"
  SERVER_URL="http://localhost:${PORT:-4331}"
fi

API_URL="$SERVER_URL/api/command-center/command"

send_cmd() {
  local action="$1"
  local target="${2:-all}"
  local message="${3:-}"

  local payload
  if [ -n "$message" ]; then
    local msg_json
    msg_json="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$message")"
    payload=$(printf '{"action":"%s","target":"%s","message":%s,"source":"cli"}' "$action" "$target" "$msg_json")
  else
    payload=$(printf '{"action":"%s","target":"%s","source":"cli"}' "$action" "$target")
  fi

  curl -fsS -X POST "$API_URL" -H 'Content-Type: application/json' -d "$payload" >/dev/null
  echo "[cc] comando enviado: $action target=$target"
}

case "${1:-open}" in
  open)
    URL="$SERVER_URL/?cc=1"
    echo "[cc] abriendo: $URL"
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$URL" >/dev/null 2>&1 || true
    fi
    echo "$URL"
    ;;
  pause-all)
    send_cmd "pause_all" "all"
    ;;
  resume-all)
    send_cmd "resume_all" "all"
    ;;
  save)
    send_cmd "save_snapshot" "all"
    ;;
  pause)
    send_cmd "pause_agent" "${2:-boss}"
    ;;
  resume)
    send_cmd "resume_agent" "${2:-boss}"
    ;;
  dispatch)
    if [ -z "${2:-}" ] || [ -z "${3:-}" ]; then
      echo "Uso: $0 dispatch <boss|accountant|librarian|auditor> \"mensaje\""
      exit 1
    fi
    send_cmd "dispatch" "$2" "$3"
    ;;
  *)
    cat <<'HELP'
Uso:
  ./command_center.sh open
  ./command_center.sh pause-all
  ./command_center.sh resume-all
  ./command_center.sh save
  ./command_center.sh pause <agent>
  ./command_center.sh resume <agent>
  ./command_center.sh dispatch <agent> "mensaje"
HELP
    exit 1
    ;;
esac
