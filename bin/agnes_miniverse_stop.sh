#!/usr/bin/env bash
set -euo pipefail

AGNES_HOME="${AGNES_HOME:-$HOME/agnes}"
AGNES_APP_ROOT="${AGNES_APP_ROOT:-$AGNES_HOME/apps/miniverse}"
DST_WORLD="$AGNES_APP_ROOT/my-world"

if [ ! -d "$DST_WORLD" ]; then
  echo "[agnes] WARN: no existe runtime clonado en $DST_WORLD"
  exit 0
fi

cd "$DST_WORLD"
./stop_operational_stack.sh
