"""Tachyon Configuration — Single source of truth."""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────
AGNES_HOME = Path(os.environ.get("AGNES_HOME", Path.home() / "agnes"))
TACHYON_DIR = AGNES_HOME / "tachyon"
DATA_DIR = TACHYON_DIR / "data"
MEMORY_FILE = DATA_DIR / "memory.json"
STATE_FILE = DATA_DIR / "state.json"
AUDIO_DIR = DATA_DIR / "audio"

# ── Qwen / Ollama ─────────────────────────────────────────────────
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "tachyon:latest")
OLLAMA_BASE_MODEL = os.environ.get("OLLAMA_BASE_MODEL", "qwen2.5:7b-instruct")
OLLAMA_TIMEOUT = 120  # seconds
OLLAMA_KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "30m")

# ── Voice ──────────────────────────────────────────────────────────
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "base")  # tiny/base/small
WHISPER_DEVICE = "cpu"  # GPU is used by Ollama
WHISPER_COMPUTE = "int8"
TTS_VOICE = os.environ.get("TTS_VOICE", "es-MX-DaliaNeural")  # Spanish female
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

# ── Server ─────────────────────────────────────────────────────────
HOST = "0.0.0.0"
PORT = int(os.environ.get("TACHYON_PORT", "7777"))
CORS_ORIGINS = ["*"]  # WSL→Windows browser

# ── Miniverse bridge ──────────────────────────────────────────────
MINIVERSE_WS = os.environ.get("MINIVERSE_WS", "ws://localhost:4341")

# ── Personality parameters (from docs) ────────────────────────────
PERSONALITY = {
    "name": "Agnes Tachyon",
    "type": "ENTP",
    # Neuromodulator baseline values (Table 1 from docs)
    "stability_bias": 0.3,       # COMT Val/Val → low sustained attention
    "learning_rate_phasic": 0.9, # DRD4-7R → extreme novelty reaction
    "precision_weight": 0.5,     # Noradrenaline → variable
    "social_adherence": 0.3,     # OXTR → low social compliance
    "systemizing_index": 0.85,   # AR → high objectification
    # State thresholds
    "shadow_stress_threshold": 0.8,
    "shadow_somatic_threshold": 0.3,
    # Dynamic ranges
    "temperature_normal": 0.85,
    "temperature_shadow": 0.2,
    "temperature_eureka": 1.1,
}

# ── ms-swift training ─────────────────────────────────────────────
MSSWIFT_DIR = Path.home() / "skills" / "ms-swift"
TRAIN_MODEL = "Qwen/Qwen2.5-7B-Instruct"
TRAIN_OUTPUT = DATA_DIR / "training"
PERSONA_OUTPUT = DATA_DIR / "persona"
TRAIN_LORA_RANK = 8
TRAIN_LORA_ALPHA = 32
TRAIN_QUANT_BITS = 4  # QLoRA 4-bit for RTX 3060 12GB

# ── Memory ─────────────────────────────────────────────────────────
MAX_MEMORY_MESSAGES = 200  # Keep last N messages in active memory
MEMORY_SUMMARY_INTERVAL = 50  # Summarize every N messages

# Ensure directories exist
for d in [DATA_DIR, AUDIO_DIR, TRAIN_OUTPUT, PERSONA_OUTPUT]:
    d.mkdir(parents=True, exist_ok=True)
