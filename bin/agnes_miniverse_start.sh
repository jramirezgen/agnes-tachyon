#!/usr/bin/env bash
set -euo pipefail

AGNES_HOME="${AGNES_HOME:-$HOME/agnes}"
AGNES_DATA_DIR="${AGNES_DATA_DIR:-$AGNES_HOME/data}"
AGNES_APP_ROOT="${AGNES_APP_ROOT:-$AGNES_HOME/apps/miniverse}"

SRC_WORLD="${SRC_WORLD:-$HOME/skills/miniverse/my-world}"
SRC_RUNTIME="${SRC_RUNTIME:-$HOME/skills/miniverse/my-miniverse}"

DST_WORLD="$AGNES_APP_ROOT/my-world"
DST_RUNTIME="$AGNES_APP_ROOT/my-miniverse"

if ! command -v rsync >/dev/null 2>&1; then
  echo "[agnes] ERROR: rsync no disponible. Instala rsync para sincronizacion segura."
  exit 1
fi

mkdir -p "$AGNES_DATA_DIR/models" "$AGNES_HOME/tools/bin" "$AGNES_APP_ROOT"

# Sincroniza codigo operativo dentro de Agnes (biblioteca ejecutable).
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'generated/' \
  --exclude '.venv/' \
  "$SRC_WORLD/" "$DST_WORLD/"

rsync -a --delete \
  --exclude '.git/' \
  --exclude 'node_modules/' \
  --exclude 'generated/' \
  --exclude 'models/' \
  --exclude '.venv/' \
  "$SRC_RUNTIME/" "$DST_RUNTIME/"

# Tools usados por runtime: copiar wrappers al arbol Agnes.
if [ -f "$HOME/.local/bin/oc_ollama_qwen.sh" ]; then
  cp "$HOME/.local/bin/oc_ollama_qwen.sh" "$AGNES_HOME/tools/bin/oc_ollama_qwen.sh"
  chmod +x "$AGNES_HOME/tools/bin/oc_ollama_qwen.sh"
fi
if [ -f "$HOME/.local/bin/oc_ollama_qwen_windows.sh" ]; then
  cp "$HOME/.local/bin/oc_ollama_qwen_windows.sh" "$AGNES_HOME/tools/bin/oc_ollama_qwen_windows.sh"
  chmod +x "$AGNES_HOME/tools/bin/oc_ollama_qwen_windows.sh"
fi
if [ -f "$HOME/.local/bin/oc_windows_exec.sh" ]; then
  cp "$HOME/.local/bin/oc_windows_exec.sh" "$AGNES_HOME/tools/bin/oc_windows_exec.sh"
  chmod +x "$AGNES_HOME/tools/bin/oc_windows_exec.sh"
fi

# Mantener compatibilidad de ruta models dentro del runtime clonado.
rm -rf "$DST_RUNTIME/models"
ln -s "$AGNES_DATA_DIR/models" "$DST_RUNTIME/models"

# Dependencias Node del world clonado.
if [ ! -d "$DST_WORLD/node_modules" ]; then
  (cd "$DST_WORLD" && npm install)
fi

export AGNES_HOME
export AGNES_DATA_DIR
export MINIVERSE_RUNTIME_ROOT="$DST_RUNTIME"

echo "[agnes] runtime root: $MINIVERSE_RUNTIME_ROOT"
echo "[agnes] data dir: $AGNES_DATA_DIR"

cd "$DST_WORLD"
./start_operational_stack.sh
