#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
PROFILE="code-only"
OUT_DIR="${ROOT_DIR}/dist/portable"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_NAME="agnes-tachyon-${STAMP}"
WORK_DIR="${OUT_DIR}/${BUNDLE_NAME}"
PAYLOAD_DIR="${WORK_DIR}/portable_bundle"

usage() {
  cat <<'EOF'
Uso:
  export_agnes_tachyon_bundle.sh [--profile code-only|with-datasets|full-portable] [--output-dir PATH]

Perfiles:
  code-only      Solo código, scripts y snapshots de entorno.
  with-datasets  Incluye data ligera, excluyendo modelos y runs.
  full-portable  Igual que with-datasets, añadiendo referencias del modelo base actual.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="$2"
      shift 2
      ;;
    --output-dir)
      OUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] argumento no reconocido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$PROFILE" in
  code-only|with-datasets|full-portable) ;;
  *)
    echo "[ERROR] perfil inválido: $PROFILE" >&2
    exit 1
    ;;
esac

mkdir -p "$OUT_DIR" "$PAYLOAD_DIR/repo" "$PAYLOAD_DIR/env" "$PAYLOAD_DIR/meta"

if ! command -v rsync >/dev/null 2>&1; then
  echo "[ERROR] rsync es requerido para exportar el bundle" >&2
  exit 1
fi

RSYNC_EXCLUDES=(
  --exclude=.git
  --exclude=.venv
  --exclude=venv
  --exclude=__pycache__
  --exclude=.pytest_cache
  --exclude=.mypy_cache
  --exclude=node_modules
  --exclude=generated
  --exclude=dist/portable
  --exclude='*.pyc'
  --exclude='*.pyo'
)

DATA_EXCLUDES=(
  --exclude=data/models
  --exclude=data/**/runs
  --exclude=data/**/merged
  --exclude=data/**/checkpoints
  --exclude=data/**/cache
  --exclude=data/**/tmp
)

if [[ "$PROFILE" == "code-only" ]]; then
  DATA_EXCLUDES+=(--exclude=data)
fi

echo "[bundle] exportando repositorio desde $ROOT_DIR"
rsync -a \
  "${RSYNC_EXCLUDES[@]}" \
  "${DATA_EXCLUDES[@]}" \
  "$ROOT_DIR/" "$PAYLOAD_DIR/repo/agnes/"

if [[ ! -d "$PAYLOAD_DIR/repo/agnes" ]]; then
  echo "[ERROR] no se exportó el repositorio" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python3 --version > "$PAYLOAD_DIR/env/python-version.txt" 2>&1 || true
fi

if command -v node >/dev/null 2>&1; then
  node --version > "$PAYLOAD_DIR/env/node-version.txt" 2>&1 || true
fi

if command -v npm >/dev/null 2>&1; then
  npm --version > "$PAYLOAD_DIR/env/npm-version.txt" 2>&1 || true
fi

if [[ -x "$HOME/miniconda3/envs/miniverse-gpu/bin/python" ]]; then
  "$HOME/miniconda3/envs/miniverse-gpu/bin/python" -m pip freeze > "$PAYLOAD_DIR/env/miniverse-gpu-pip-freeze.txt" 2>&1 || true
fi

if command -v conda >/dev/null 2>&1; then
  conda env export -n miniverse-gpu > "$PAYLOAD_DIR/env/miniverse-gpu-conda-env.yml" 2>&1 || true
  conda list -n miniverse-gpu --explicit > "$PAYLOAD_DIR/env/miniverse-gpu-conda-explicit.txt" 2>&1 || true
fi

python3 - <<'PY' > "$PAYLOAD_DIR/env/model-reference.txt"
import sys
from pathlib import Path

root = Path("/home/kaitokid/agnes")
sys.path.insert(0, str(root))

try:
  from tachyon import config
    print(f"TRAIN_MODEL={config.TRAIN_MODEL}")
    print(f"OLLAMA_MODEL={config.OLLAMA_MODEL}")
    print(f"OLLAMA_BASE_MODEL={config.OLLAMA_BASE_MODEL}")
except Exception as exc:
    print(f"MODEL_REFERENCE_ERROR={exc}")
PY

cat > "$PAYLOAD_DIR/env/optimized-learner.env" <<'EOF'
ENABLE_LIBRARIAN_LEARNER=1
LIBRARIAN_SWIFT_MAX_ROUNDS=999
LIBRARIAN_SWIFT_KEEP_RUNS=3
LIBRARIAN_SWIFT_KEEP_MERGED=2
LIBRARIAN_SWIFT_EXPORT_MERGED=0
EOF

cat > "$PAYLOAD_DIR/meta/export-metadata.txt" <<EOF
bundle_name=${BUNDLE_NAME}
created_utc=${STAMP}
profile=${PROFILE}
include_trained_models=0
root_dir=${ROOT_DIR}
hostname=$(hostname 2>/dev/null || echo unknown)
user=$(whoami 2>/dev/null || echo unknown)
target_platform=linux-wsl-backend-with-frontend
EOF

(cd "$PAYLOAD_DIR" && find . -type f | sort) > "$WORK_DIR/file-manifest.txt"

if command -v sha256sum >/dev/null 2>&1; then
  (cd "$PAYLOAD_DIR" && find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$WORK_DIR/SHA256SUMS.txt"
fi

tar -czf "$OUT_DIR/${BUNDLE_NAME}.tar.gz" -C "$WORK_DIR" portable_bundle file-manifest.txt SHA256SUMS.txt

echo "[bundle] listo: $OUT_DIR/${BUNDLE_NAME}.tar.gz"
echo "[bundle] manifiesto: $WORK_DIR/file-manifest.txt"
if [[ -f "$WORK_DIR/SHA256SUMS.txt" ]]; then
  echo "[bundle] checksums: $WORK_DIR/SHA256SUMS.txt"
fi