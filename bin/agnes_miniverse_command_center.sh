#!/usr/bin/env bash
set -euo pipefail

AGNES_HOME="${AGNES_HOME:-$HOME/agnes}"
WORLD_DIR="${AGNES_HOME}/apps/miniverse/my-world"

if [ ! -d "$WORLD_DIR" ]; then
  echo "[agnes] no existe $WORLD_DIR"
  echo "[agnes] primero ejecuta: $AGNES_HOME/bin/agnes_miniverse_start.sh"
  exit 1
fi

cd "$WORLD_DIR"
./command_center.sh "$@"
