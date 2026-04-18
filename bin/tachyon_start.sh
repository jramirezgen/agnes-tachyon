#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  Agnes Tachyon — Master Launcher
#  "La perfección es un estado estático, y por lo tanto, muerto."
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGNES_HOME="$(dirname "$SCRIPT_DIR")"
export AGNES_HOME
export PYTHONPATH="$AGNES_HOME"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${PURPLE}"
echo "═══════════════════════════════════════════════════════════"
echo "  🔬 Agnes Tachyon — Cognitive Systems Activation"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"

# ── Conda activation ──────────────────────────────────────────────
if [[ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate base 2>/dev/null || true
fi

# ── Check Ollama ──────────────────────────────────────────────────
echo -e "${CYAN}[1/4] Checking Ollama...${NC}"
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Ollama already running${NC}"
else
    echo -e "  Starting Ollama..."
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    sleep 3
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Ollama started${NC}"
    else
        echo -e "${RED}  ✗ Ollama failed to start${NC}"
        echo "    Check: ollama serve"
    fi
fi

# ── Check Qwen model ─────────────────────────────────────────────
echo -e "${CYAN}[2/4] Checking Qwen model...${NC}"
QWEN_MODEL="${OLLAMA_MODEL:-tachyon:latest}"
BASE_MODEL="${OLLAMA_BASE_MODEL:-qwen2.5:7b-instruct}"
MODELFILE="$AGNES_HOME/tachyon/Modelfile.tachyon"
if ollama list 2>/dev/null | grep -q "^${QWEN_MODEL%%:*}:latest\|^${QWEN_MODEL}$"; then
    echo -e "${GREEN}  ✓ Model '${QWEN_MODEL}' available${NC}"
else
    echo -e "  Preparing canonical model '${QWEN_MODEL}' from ${BASE_MODEL}..."
    if ! ollama list 2>/dev/null | grep -q "^${BASE_MODEL%%:*}:\|^${BASE_MODEL}$"; then
        ollama pull "${BASE_MODEL}"
    fi
    ollama create "${QWEN_MODEL%%:*}" -f "$MODELFILE"
fi

# ── Mode selection ────────────────────────────────────────────────
MODE="${1:-server}"

case "$MODE" in
    server)
        echo -e "${CYAN}[3/4] Starting Tachyon server...${NC}"
        echo -e "${GREEN}  ✓ Frontend: http://localhost:${TACHYON_PORT:-7777}${NC}"
        echo -e "${GREEN}  ✓ Open in Windows browser for voice interaction${NC}"
        echo ""
        exec python3 -m tachyon.server
        ;;

    watchdog)
        echo -e "${CYAN}[3/4] Starting Tachyon watchdog (24/7 mode)...${NC}"
        echo -e "${GREEN}  ✓ All services will auto-restart on crash${NC}"
        echo ""
        exec python3 -m tachyon.watchdog
        ;;

    train)
        echo -e "${CYAN}[3/4] Starting ms-swift training...${NC}"
        DATASET="${2:-}"
        STEPS="${3:-100}"
        if [[ -n "$DATASET" ]]; then
            exec python3 -m tachyon.trainer --dataset "$DATASET" --steps "$STEPS"
        else
            exec python3 -m tachyon.trainer --steps "$STEPS"
        fi
        ;;

    train-memory)
        echo -e "${CYAN}[3/4] Training from conversation memory...${NC}"
        STEPS="${2:-100}"
        exec python3 -m tachyon.trainer --from-memory --steps "$STEPS"
        ;;

    *)
        echo "Usage: $0 {server|watchdog|train [dataset] [steps]|train-memory [steps]}"
        echo ""
        echo "  server       — Start Tachyon server (default)"
        echo "  watchdog     — Start 24/7 watchdog (auto-restart)"
        echo "  train        — Run ms-swift QLoRA training"
        echo "  train-memory — Train from conversation history"
        exit 1
        ;;
esac
