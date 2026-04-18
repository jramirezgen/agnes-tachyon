#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: restore_agnes_tachyon_bundle.sh /ruta/al/bundle.tar.gz [destino]" >&2
  exit 1
fi

BUNDLE_PATH="$(realpath "$1")"
DEST_ROOT="${2:-$HOME/restore-agnes}"

if [[ ! -f "$BUNDLE_PATH" ]]; then
  echo "[ERROR] bundle no encontrado: $BUNDLE_PATH" >&2
  exit 1
fi

mkdir -p "$DEST_ROOT"
tar -xzf "$BUNDLE_PATH" -C "$DEST_ROOT"

RESTORE_ROOT="$(find "$DEST_ROOT" -maxdepth 2 -type d -name portable_bundle | head -n 1)"
if [[ -z "$RESTORE_ROOT" ]]; then
  echo "[ERROR] no se encontró portable_bundle tras extraer" >&2
  exit 1
fi

REPO_ROOT="$RESTORE_ROOT/repo/agnes"
if [[ ! -d "$REPO_ROOT" ]]; then
  echo "[ERROR] no se encontró el repositorio restaurado en $REPO_ROOT" >&2
  exit 1
fi

cat > "$RESTORE_ROOT/env/restore-paths.env" <<EOF
RESTORE_ROOT=$RESTORE_ROOT
RESTORED_AGNES_REPO=$REPO_ROOT
RESTORED_STACK_DIR=$REPO_ROOT/apps/miniverse/my-world
RESTORED_RUNTIME_DIR=$REPO_ROOT/apps/miniverse/my-miniverse
EOF

echo "[restore] bundle extraído en: $RESTORE_ROOT"
echo "[restore] repo restaurado: $REPO_ROOT"
echo "[restore] usa restore-paths.env para exportar rutas base"