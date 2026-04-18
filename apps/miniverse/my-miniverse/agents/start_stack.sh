#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Carga nvm en shells no interactivos para que miniverse (npm global) exista en PATH
if [ -z "${NVM_DIR:-}" ]; then
  export NVM_DIR="$HOME/.nvm"
fi
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

if ! command -v miniverse >/dev/null 2>&1; then
  echo "[ERROR] miniverse no esta instalado en este entorno."
  echo "Instala miniverse/node y vuelve a ejecutar este script."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 no esta disponible."
  exit 1
fi

MINIVERSE_PYTHON_DEFAULT="$HOME/miniconda3/envs/miniverse-gpu/bin/python"
MINIVERSE_PYTHON="${MINIVERSE_PYTHON:-$MINIVERSE_PYTHON_DEFAULT}"
if [ ! -x "$MINIVERSE_PYTHON" ]; then
  echo "[ERROR] no se encontro python GPU en $MINIVERSE_PYTHON"
  echo "        Exporta MINIVERSE_PYTHON con un interprete valido."
  exit 1
fi

AGNES_HOME_DEFAULT="$HOME/agnes"
export AGNES_HOME="${AGNES_HOME:-$AGNES_HOME_DEFAULT}"
export AGNES_DATA_DIR="${AGNES_DATA_DIR:-$AGNES_HOME/data}"
mkdir -p "$AGNES_DATA_DIR/models"

mkdir -p generated
PID_FILE="generated/stack.pids"
SERVER_URL="${MINIVERSE_SERVER_URL:-http://localhost:4321}"
UI_PORT="${MINIVERSE_UI_PORT:-7777}"
UI_URL="http://localhost:${UI_PORT}"

if [ -f "$PID_FILE" ]; then
  OLD_SERVER_PID="$(awk -F= '/^SERVER_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
  OLD_AGENTS_PID="$(awk -F= '/^AGENTS_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
  OLD_UI_PID="$(awk -F= '/^UI_PID=/{print $2}' "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_SERVER_PID" ] && kill -0 "$OLD_SERVER_PID" >/dev/null 2>&1; then
    kill "$OLD_SERVER_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$OLD_AGENTS_PID" ] && kill -0 "$OLD_AGENTS_PID" >/dev/null 2>&1; then
    kill "$OLD_AGENTS_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "$OLD_UI_PID" ] && kill -0 "$OLD_UI_PID" >/dev/null 2>&1; then
    kill "$OLD_UI_PID" >/dev/null 2>&1 || true
  fi
fi

SERVER_STARTED_BY_SCRIPT=0

if curl -fsS "$SERVER_URL/api/info" >/dev/null 2>&1; then
  echo "[stack] detectado servidor existente en $SERVER_URL, se reutiliza"
  SERVER_PID=""
else
  echo "[stack] iniciando servidor miniverse..."
  miniverse --no-browser > generated/miniverse_server.log 2>&1 &
  SERVER_PID=$!
  SERVER_STARTED_BY_SCRIPT=1
fi

sleep 2

echo "[stack] iniciando runtime multiagente..."
PYTHONNOUSERSITE=1 AGNES_HOME="$AGNES_HOME" AGNES_DATA_DIR="$AGNES_DATA_DIR" "$MINIVERSE_PYTHON" agents/runtime.py > generated/agents_runtime.log 2>&1 &
AGENTS_PID=$!

if curl -fsS "$UI_URL" >/dev/null 2>&1; then
  echo "[stack] detectado UI server existente en $UI_URL, se reutiliza"
  UI_PID=""
else
  echo "[stack] iniciando UI server en puerto ${UI_PORT}..."
  PYTHONNOUSERSITE=1 MINIVERSE_UI_PORT="$UI_PORT" AGNES_HOME="$AGNES_HOME" AGNES_DATA_DIR="$AGNES_DATA_DIR" "$MINIVERSE_PYTHON" agents/serve_ui.py > generated/ui_server.log 2>&1 &
  UI_PID=$!
fi

echo "SERVER_PID=$SERVER_PID" > "$PID_FILE"
echo "AGENTS_PID=$AGENTS_PID" >> "$PID_FILE"
echo "UI_PID=$UI_PID" >> "$PID_FILE"
echo "SERVER_STARTED_BY_SCRIPT=$SERVER_STARTED_BY_SCRIPT" >> "$PID_FILE"

sleep 2

if [ "$SERVER_STARTED_BY_SCRIPT" -eq 1 ]; then
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    if ! curl -fsS "$SERVER_URL/api/info" >/dev/null 2>&1; then
      echo "[ERROR] el servidor miniverse no se mantuvo en ejecucion. Revisa generated/miniverse_server.log"
      exit 1
    fi
  fi
fi

if ! kill -0 "$AGENTS_PID" >/dev/null 2>&1; then
  echo "[ERROR] el runtime de agentes no se mantuvo en ejecucion. Revisa generated/agents_runtime.log"
  exit 1
fi

if [ -n "${UI_PID:-}" ]; then
  if ! kill -0 "$UI_PID" >/dev/null 2>&1; then
    if ! curl -fsS "$UI_URL" >/dev/null 2>&1; then
      echo "[ERROR] el UI server no se mantuvo en ejecucion. Revisa generated/ui_server.log"
      exit 1
    fi
  fi
fi

echo "[stack] server PID=${SERVER_PID:-external}, agents PID=$AGENTS_PID"
echo "[stack] ui PID=${UI_PID:-external}, URL=$UI_URL"
echo "[stack] agnes data dir: $AGNES_DATA_DIR"
echo "[stack] python: $MINIVERSE_PYTHON"
echo "[stack] logs: generated/miniverse_server.log, generated/agents_runtime.log y generated/ui_server.log"
if [ -n "${SERVER_PID:-}" ]; then
  if [ -n "${UI_PID:-}" ]; then
    echo "[stack] iniciado en background. Para detener: kill $SERVER_PID $AGENTS_PID $UI_PID"
  else
    echo "[stack] iniciado en background. Para detener: kill $SERVER_PID $AGENTS_PID"
  fi
else
  if [ -n "${UI_PID:-}" ]; then
    echo "[stack] iniciado en background. Para detener agentes/UI: kill $AGENTS_PID $UI_PID"
  else
    echo "[stack] iniciado en background. Para detener agentes: kill $AGENTS_PID"
  fi
fi
