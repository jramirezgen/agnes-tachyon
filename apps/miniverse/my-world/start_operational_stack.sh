#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [ -z "${NVM_DIR:-}" ]; then
  export NVM_DIR="$HOME/.nvm"
fi
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
fi

if ! command -v node >/dev/null 2>&1; then
  echo "[ERROR] node no esta disponible."
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
export TACHYON_URL="${TACHYON_URL:-http://localhost:7777}"
mkdir -p "$AGNES_DATA_DIR/models"

# Asegurar libstdc++ de miniconda solo para procesos Python de entrenamiento
PYTHON_LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
if [ -d "$HOME/miniconda3/lib" ]; then
  PYTHON_LD_LIBRARY_PATH="$HOME/miniconda3/lib${PYTHON_LD_LIBRARY_PATH:+:$PYTHON_LD_LIBRARY_PATH}"
fi

RUNTIME_ROOT="${MINIVERSE_RUNTIME_ROOT:-$ROOT/../my-miniverse}"
RUNTIME_SCRIPT="$RUNTIME_ROOT/agents/runtime.py"
if [ ! -f "$RUNTIME_SCRIPT" ]; then
  echo "[ERROR] no se encontro el runtime en $RUNTIME_SCRIPT"
  exit 1
fi

if ! curl -fsS "$TACHYON_URL/health" >/dev/null 2>&1; then
  echo "[stack] tachyon no esta activo, iniciando servicio..."
  nohup "$HOME/.local/bin/tachyon" start > generated/tachyon.log 2>&1 &
  for _ in $(seq 1 30); do
    if curl -fsS "$TACHYON_URL/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl -fsS "$TACHYON_URL/health" >/dev/null 2>&1; then
  echo "[ERROR] Tachyon no quedo disponible en $TACHYON_URL"
  exit 1
fi

mkdir -p generated
PID_FILE="generated/operational_stack.pids"

if [ -f "$PID_FILE" ]; then
  ./stop_operational_stack.sh >/dev/null 2>&1 || true
fi

PORT="${PORT:-$($MINIVERSE_PYTHON - <<'PY'
import socket

def free(port):
    for probe in (port, port + 1):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", probe))
        except OSError:
            sock.close()
            return False
        sock.close()
    return True

candidate = 4331
for _ in range(100):
    if free(candidate):
        print(candidate)
        break
    candidate += 10
else:
    raise SystemExit("No se encontro un par libre de puertos")
PY
)}"

SERVER_URL="http://localhost:${PORT}"

PORT="$PORT" node server.js > generated/world_server.log 2>&1 &
SERVER_PID=$!

READY=0
for _ in $(seq 1 30); do
  if curl -fsS "$SERVER_URL/" >/dev/null 2>&1 && curl -fsS "$SERVER_URL/api/agents" >/dev/null 2>&1; then
    READY=1
    break
  fi
  if ! kill -0 "$SERVER_PID" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "[ERROR] el servidor oficial no quedo disponible. Revisa generated/world_server.log"
  exit 1
fi

# Lanzar bibliotecaria en modo aprendizaje (background, independiente)
LEARN_SCRIPT="${RUNTIME_ROOT}/agents/librarian_learn_swift.py"
if [ ! -f "$LEARN_SCRIPT" ]; then
  LEARN_SCRIPT="${RUNTIME_ROOT}/agents/librarian_learn.py"
fi
ENABLE_LIBRARIAN_LEARNER="${ENABLE_LIBRARIAN_LEARNER:-1}"
if [ "$ENABLE_LIBRARIAN_LEARNER" = "1" ]; then
  if [ -f "$LEARN_SCRIPT" ]; then
    LD_LIBRARY_PATH="$PYTHON_LD_LIBRARY_PATH" MINIVERSE_SERVER_URL="$SERVER_URL" TACHYON_URL="$TACHYON_URL" AGNES_TRAINER_PYTHON="$MINIVERSE_PYTHON" AGNES_HOME="$AGNES_HOME" AGNES_DATA_DIR="$AGNES_DATA_DIR" LIBRARIAN_SWIFT_EXPORT_MERGED="${LIBRARIAN_SWIFT_EXPORT_MERGED:-1}" LIBRARIAN_MERGE_INTERVAL_SEC="${LIBRARIAN_MERGE_INTERVAL_SEC:-10800}" "$MINIVERSE_PYTHON" -u "$LEARN_SCRIPT" > generated/librarian_learn.log 2>&1 &
    LEARN_PID=$!
    echo "[stack] bibliotecaria aprendiendo PID=$LEARN_PID (log: generated/librarian_learn.log)"
  else
    LEARN_PID=""
    echo "[stack] WARN: librarian_learn.py no encontrado"
  fi
else
  LEARN_PID=""
  echo "[stack] aprendizaje continuo desactivado (ENABLE_LIBRARIAN_LEARNER=0)"
fi

PYTHONNOUSERSITE=1 LD_LIBRARY_PATH="$PYTHON_LD_LIBRARY_PATH" MINIVERSE_SERVER_URL="$SERVER_URL" TACHYON_URL="$TACHYON_URL" MINIVERSE_LAUNCH_LEARNER=0 AGNES_HOME="$AGNES_HOME" AGNES_DATA_DIR="$AGNES_DATA_DIR" "$MINIVERSE_PYTHON" -u "$RUNTIME_SCRIPT" > generated/agents_runtime.log 2>&1 &
AGENTS_PID=$!

sleep 2
if ! kill -0 "$AGENTS_PID" >/dev/null 2>&1; then
  echo "[ERROR] el runtime no se mantuvo en ejecucion. Revisa generated/agents_runtime.log"
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  exit 1
fi

cat > "$PID_FILE" <<EOF
PORT=$PORT
SERVER_PID=$SERVER_PID
AGENTS_PID=$AGENTS_PID
LEARN_PID=${LEARN_PID:-}
SERVER_URL=$SERVER_URL
RUNTIME_ROOT=$RUNTIME_ROOT
EOF

echo "[stack] mundo oficial: $SERVER_URL"
echo "[stack] server PID=$SERVER_PID"
echo "[stack] agents PID=$AGENTS_PID"
echo "[stack] agnes data dir: $AGNES_DATA_DIR"
echo "[stack] python: $MINIVERSE_PYTHON"
echo "[stack] logs: generated/world_server.log y generated/agents_runtime.log"