#!/usr/bin/env python3
"""
Bibliotecaria — Aprendizaje continuo por fine-tuning sobre leyes fundamentales del universo.
Usa QLoRA (4-bit) + LoRA sobre TinyLlama-1.1B con CUDA cuando está disponible.
Reporta progreso a Miniverse en tiempo real (heartbeat) para visualización.

Dependencias (auto-instaladas): transformers, peft, bitsandbytes, accelerate, datasets
"""
from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Rutas ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
LEGACY_MODELS_ROOT = SCRIPT_DIR.parent / "models"
AGNES_HOME = Path(os.getenv("AGNES_HOME", str(Path.home() / "agnes"))).expanduser()
AGNES_DATA_DIR = Path(os.getenv("AGNES_DATA_DIR", str(AGNES_HOME / "data"))).expanduser()

# Compatibilidad: si no se configuró AGNES_DATA_DIR y existe el árbol legacy,
# mantener ruta anterior hasta que se complete la migración.
if "AGNES_DATA_DIR" not in os.environ and not (AGNES_DATA_DIR / "models").exists() and LEGACY_MODELS_ROOT.exists():
    MODELS_ROOT = LEGACY_MODELS_ROOT
else:
    MODELS_ROOT = AGNES_DATA_DIR / "models"

MODELS_DIR = MODELS_ROOT / "librarian"
MERGED_MODELS_DIR = MODELS_ROOT / "librarian_merged"
SNAPSHOTS_DIR = MODELS_ROOT / "librarian_snapshots"
LATEST_MERGED_FILE = MODELS_ROOT / "LATEST_MERGED_MODEL.txt"
PID_FILE = Path("/tmp/librarian_learning.pid")

# ── Config Miniverse ────────────────────────────────────────────────────────
SERVER = os.getenv("MINIVERSE_SERVER_URL", "http://localhost:4321")
AGENT_ID = "librarian-agent"
AGENT_NAME = "Bibliotecaria"

# ── Config modelo ────────────────────────────────────────────────────────────
BASE_MODEL = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
LORA_RANK = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
MAX_SEQ_LEN = 512
BATCH_SIZE = 4
EPOCHS_PER_TOPIC = 3
HEARTBEAT_INTERVAL = 15  # segundos entre heartbeats durante entrenamiento
MERGE_INTERVAL_HOURS = int(os.getenv("LIBRARIAN_MERGE_INTERVAL_HOURS", "8"))
MERGE_INTERVAL_SECONDS = MERGE_INTERVAL_HOURS * 3600
KEEP_MERGED_MODELS = int(os.getenv("LIBRARIAN_KEEP_MERGED_MODELS", "2"))
KEEP_SNAPSHOTS = int(os.getenv("LIBRARIAN_KEEP_SNAPSHOTS", "2"))

# ── Corpus de leyes fundamentales ───────────────────────────────────────────
TOPICS: dict[str, dict[str, Any]] = {
    "Mecánica Clásica": {
        "wiki_pages": [
            "Newton's laws of motion",
            "Conservation of energy",
            "Newton's law of universal gravitation",
            "Momentum",
            "Classical mechanics",
        ],
        "curated": [
            {
                "instruction": "Explica la primera ley de Newton (ley de inercia)",
                "output": (
                    "La primera ley de Newton, o ley de inercia, establece: "
                    "Todo cuerpo permanece en su estado de reposo o de movimiento rectilíneo uniforme "
                    "a menos que sobre él actúe una fuerza neta no nula. "
                    "Matemáticamente: si ΣF = 0, entonces dv/dt = 0. "
                    "Esta ley define los sistemas de referencia inerciales y establece que el movimiento "
                    "no requiere una causa continua — solo el cambio de movimiento la requiere."
                ),
            },
            {
                "instruction": "Explica la segunda ley de Newton con su forma matemática",
                "output": (
                    "La segunda ley de Newton establece que la fuerza neta sobre un cuerpo "
                    "es igual al producto de su masa por su aceleración: F = ma. "
                    "En forma vectorial: ΣF⃗ = ma⃗ = m(d²r⃗/dt²). "
                    "La forma más general es ΣF⃗ = dp⃗/dt, donde p⃗ = mv⃗ es el momento lineal. "
                    "Esta ley es válida en sistemas de referencia inerciales y es la base "
                    "de toda la mecánica clásica."
                ),
            },
            {
                "instruction": "Explica la tercera ley de Newton y su significado físico",
                "output": (
                    "La tercera ley de Newton establece: para cada acción existe una reacción igual y opuesta. "
                    "Si el cuerpo A ejerce una fuerza F⃗_AB sobre B, entonces B ejerce F⃗_BA = -F⃗_AB sobre A. "
                    "Estas fuerzas actúan sobre cuerpos diferentes, son simultáneas, iguales en magnitud "
                    "y opuestas en dirección. Esta ley implica la conservación del momento lineal en sistemas aislados: "
                    "d/dt(p₁ + p₂) = F₁₂ + F₂₁ = 0."
                ),
            },
            {
                "instruction": "Describe la ley de gravitación universal de Newton",
                "output": (
                    "La ley de gravitación universal establece que dos masas m₁ y m₂ separadas una "
                    "distancia r se atraen con una fuerza: F = G·m₁·m₂/r². "
                    "Donde G = 6.674×10⁻¹¹ N·m²/kg² es la constante de gravitación universal. "
                    "En forma vectorial: F⃗₁₂ = -G·m₁·m₂/r³ · r⃗₁₂. "
                    "Esta ley describe desde la caída libre hasta las órbitas planetarias, y fue unificada "
                    "con la relatividad general por Einstein en 1915."
                ),
            },
            {
                "instruction": "¿Qué es la conservación de energía mecánica?",
                "output": (
                    "En un sistema conservativo (sin fricción), la energía mecánica total E = T + V es constante: "
                    "dE/dt = 0, donde T = ½mv² es la energía cinética y V es la energía potencial. "
                    "Para la gravedad cerca de la Tierra: V = mgh. Para el campo gravitacional: V = -GMm/r. "
                    "Para un resorte (fuerza de Hooke, F = -kx): V = ½kx². "
                    "La conservación de energía es consecuencia del teorema de Noether: la invarianza "
                    "temporal de las leyes físicas implica la conservación de energía."
                ),
            },
        ],
    },
    "Electromagnetismo": {
        "wiki_pages": [
            "Maxwell's equations",
            "Gauss's law",
            "Faraday's law of induction",
            "Ampere's circuital law",
            "Electromagnetic wave equation",
        ],
        "curated": [
            {
                "instruction": "Escribe y explica las ecuaciones de Maxwell en forma diferencial",
                "output": (
                    "Las cuatro ecuaciones de Maxwell son el fundamento del electromagnetismo clásico:\n"
                    "1. Ley de Gauss (eléctrica): ∇·E⃗ = ρ/ε₀\n"
                    "   Las cargas eléctricas son la fuente de campo eléctrico.\n"
                    "2. Ley de Gauss (magnética): ∇·B⃗ = 0\n"
                    "   No existen monopolos magnéticos; las líneas de B⃗ son siempre cerradas.\n"
                    "3. Ley de Faraday: ∇×E⃗ = -∂B⃗/∂t\n"
                    "   Un campo magnético variable induce un campo eléctrico rotacional.\n"
                    "4. Ley de Ampère-Maxwell: ∇×B⃗ = μ₀J⃗ + μ₀ε₀·∂E⃗/∂t\n"
                    "   Las corrientes y campos eléctricos variables generan campo magnético.\n"
                    "De estas ecuaciones se deduce la velocidad de la luz: c = 1/√(μ₀ε₀) ≈ 3×10⁸ m/s."
                ),
            },
            {
                "instruction": "¿Cómo se derivan las ondas electromagnéticas de las ecuaciones de Maxwell?",
                "output": (
                    "Tomando el rotacional de la ley de Faraday y usando la ley de Ampère-Maxwell "
                    "en el vacío (ρ=0, J⃗=0):\n"
                    "∇×(∇×E⃗) = -∂/∂t(∇×B⃗) = -μ₀ε₀·∂²E⃗/∂t²\n"
                    "Usando la identidad vectorial ∇×(∇×E⃗) = ∇(∇·E⃗) - ∇²E⃗ y ∇·E⃗=0:\n"
                    "∇²E⃗ = μ₀ε₀·∂²E⃗/∂t²\n"
                    "Esta es la ecuación de onda con velocidad c = 1/√(μ₀ε₀). "
                    "La luz es una onda electromagnética que se autopropaga oscilando E⃗ y B⃗ "
                    "mutuamente perpendiculares y en fase."
                ),
            },
        ],
    },
    "Mecánica Cuántica": {
        "wiki_pages": [
            "Schrödinger equation",
            "Heisenberg uncertainty principle",
            "Wave function",
            "Quantum superposition",
            "Dirac equation",
        ],
        "curated": [
            {
                "instruction": "Escribe y explica la ecuación de Schrödinger dependiente del tiempo",
                "output": (
                    "La ecuación de Schrödinger dependiente del tiempo es:\n"
                    "iℏ·∂ψ/∂t = Ĥψ\n"
                    "Donde ψ(r⃗,t) es la función de onda, ℏ = h/(2π) es la constante de Planck reducida, "
                    "e Ĥ es el operador hamiltoniano: Ĥ = -ℏ²/(2m)·∇² + V(r⃗,t).\n"
                    "La función de onda |ψ|² da la densidad de probabilidad de encontrar la partícula. "
                    "Para sistemas estacionarios (V independiente de t): ψ(r⃗,t) = φ(r⃗)·e^(-iEt/ℏ), "
                    "y la ecuación se reduce a: Ĥφ = Eφ (eigenvalores de energía)."
                ),
            },
            {
                "instruction": "Explica el principio de incertidumbre de Heisenberg",
                "output": (
                    "El principio de incertidumbre de Heisenberg establece que no se pueden conocer "
                    "simultáneamente con precisión arbitraria la posición y el momento de una partícula:\n"
                    "Δx·Δpₓ ≥ ℏ/2\n"
                    "Esto no es una limitación técnica, sino una propiedad fundamental de la naturaleza. "
                    "Para energía y tiempo: ΔE·Δt ≥ ℏ/2.\n"
                    "Matemáticamente surge del álgebra de conmutadores: [x̂, p̂ₓ] = iℏ. "
                    "La desigualdad generalizada para dos observables Â, B̂ es: "
                    "ΔA·ΔB ≥ ½|⟨[Â,B̂]⟩|."
                ),
            },
            {
                "instruction": "¿Qué dice el postulado de Born sobre la función de onda?",
                "output": (
                    "La interpretación de Born (postulado de Born, 1926) establece que para una "
                    "partícula con función de onda ψ(r⃗,t):\n"
                    "P(r⃗,t) = |ψ(r⃗,t)|² = ψ*(r⃗,t)·ψ(r⃗,t)\n"
                    "es la densidad de probabilidad de encontrar la partícula en la posición r⃗ al tiempo t. "
                    "La función de onda debe ser normalizable: ∫|ψ|²d³r = 1. "
                    "La función de onda en sí no es observable — solo |ψ|² tiene significado físico directo. "
                    "Este postulado conecta el formalismo matemático con las mediciones experimentales."
                ),
            },
        ],
    },
    "Relatividad": {
        "wiki_pages": [
            "Special relativity",
            "General relativity",
            "Lorentz transformation",
            "Einstein field equations",
            "Spacetime",
        ],
        "curated": [
            {
                "instruction": "Explica los dos postulados de la relatividad especial de Einstein",
                "output": (
                    "La relatividad especial (Einstein, 1905) se basa en dos postulados:\n"
                    "1. Principio de relatividad: las leyes de la física son las mismas en todos "
                    "los sistemas de referencia inerciales.\n"
                    "2. Invariancia de la velocidad de la luz: la velocidad de la luz en el vacío "
                    "c ≈ 3×10⁸ m/s es la misma para todos los observadores, "
                    "independientemente del movimiento de la fuente o el observador.\n"
                    "Estas premisas llevan a la dilatación del tiempo: Δt' = γΔt, "
                    "contracción de longitudes: L' = L/γ, y equivalencia masa-energía: E = mc².\n"
                    "Donde γ = 1/√(1-v²/c²) es el factor de Lorentz."
                ),
            },
            {
                "instruction": "Escribe y explica las ecuaciones de campo de Einstein de la relatividad general",
                "output": (
                    "Las ecuaciones de campo de Einstein (1915) son:\n"
                    "Gμν + Λgμν = (8πG/c⁴)Tμν\n"
                    "Donde:\n"
                    "- Gμν = Rμν - ½gμνR es el tensor de Einstein (curvatura del espaciotiempo)\n"
                    "- Rμν es el tensor de Ricci\n"
                    "- R = gμνRμν es el escalar de Ricci\n"
                    "- gμν es el tensor métrico\n"
                    "- Λ es la constante cosmológica\n"
                    "- Tμν es el tensor energía-momento (fuente de curvatura)\n"
                    "- G es la constante gravitacional, c la velocidad de la luz\n"
                    "En palabras: 'la curvatura del espaciotiempo es proporcional a la distribución "
                    "de energía-momento'. La gravedad NO es una fuerza, sino curvatura del espaciotiempo."
                ),
            },
        ],
    },
    "Termodinámica": {
        "wiki_pages": [
            "Laws of thermodynamics",
            "Entropy",
            "Boltzmann constant",
            "Thermodynamic equilibrium",
            "Second law of thermodynamics",
        ],
        "curated": [
            {
                "instruction": "Enuncia y explica las cuatro leyes de la termodinámica",
                "output": (
                    "Las cuatro leyes de la termodinámica:\n\n"
                    "Ley Cero: Si dos sistemas A y B están en equilibrio térmico con C, "
                    "entonces A y B están en equilibrio entre sí. Define la temperatura.\n\n"
                    "Primera ley: La energía interna de un sistema aislado es constante: "
                    "ΔU = Q - W. Conservación de energía incluyendo calor.\n\n"
                    "Segunda ley: La entropía de un sistema aislado nunca disminuye: ΔS ≥ 0. "
                    "Los procesos espontáneos van hacia estados de mayor entropía. "
                    "Equivalentemente: no es posible convertir completamente calor en trabajo.\n\n"
                    "Tercera ley (Nernst): La entropía de un cristal perfecto a T=0K es cero: "
                    "S → 0 cuando T → 0. Es imposible alcanzar el cero absoluto en un número finito de pasos."
                ),
            },
            {
                "instruction": "Explica el significado estadístico de la entropía según Boltzmann",
                "output": (
                    "Ludwig Boltzmann demostró la conexión entre termodinámica y mecánica estadística:\n"
                    "S = kB · ln(Ω)\n"
                    "Donde:\n"
                    "- S es la entropía termodinámica\n"
                    "- kB = 1.380649×10⁻²³ J/K es la constante de Boltzmann\n"
                    "- Ω es el número de microestados compatibles con el macroestado\n"
                    "La entropía mide el desorden microscópico o la cantidad de información desconocida "
                    "sobre el microestado del sistema. Un sistema de alta entropía tiene muchas "
                    "configuraciones microscópicas posibles. La segunda ley se convierte en una ley "
                    "estadística: los estados de alta entropía son exponencialmente más probables."
                ),
            },
        ],
    },
    "Matemáticas Fundamentales": {
        "wiki_pages": [
            "Calculus",
            "Linear algebra",
            "Group theory",
            "Differential geometry",
            "Hilbert space",
        ],
        "curated": [
            {
                "instruction": "Explica el teorema de Noether y su importancia en física",
                "output": (
                    "El teorema de Noether (Emmy Noether, 1915) establece una correspondencia "
                    "fundamental entre simetrías y leyes de conservación:\n"
                    "Cada simetría continua de un sistema físico corresponde a una cantidad conservada.\n\n"
                    "Ejemplos fundamentales:\n"
                    "- Invarianza bajo traslación temporal → Conservación de energía\n"
                    "- Invarianza bajo traslación espacial → Conservación de momento lineal\n"
                    "- Invarianza bajo rotación → Conservación de momento angular\n"
                    "- Invarianza gauge U(1) → Conservación de carga eléctrica\n\n"
                    "Matemáticamente: si L(q,q̇,t) es el lagrangiano y δL=0 bajo q→q+εδq, "
                    "entonces J = Σᵢ(∂L/∂q̇ᵢ)·δqᵢ es una cantidad conservada."
                ),
            },
            {
                "instruction": "¿Qué es un espacio de Hilbert y por qué es fundamental en mecánica cuántica?",
                "output": (
                    "Un espacio de Hilbert H es un espacio vectorial complejo completo con producto interno. "
                    "Para dos vectores |φ⟩, |ψ⟩ ∈ H: ⟨φ|ψ⟩ ∈ ℂ satisface hermicidad, linealidad y positividad.\n\n"
                    "En mecánica cuántica:\n"
                    "- Los estados físicos son vectores normalizados |ψ⟩ en H\n"
                    "- Los observables son operadores autoadjuntos (hermitianos) Â = Â†\n"
                    "- Las mediciones son valores propios: Â|aₙ⟩ = aₙ|aₙ⟩\n"
                    "- La probabilidad de medir aₙ es |⟨aₙ|ψ⟩|²\n\n"
                    "La notación de Dirac |ψ⟩ (ket) y ⟨ψ| (bra) facilita el álgebra de operadores cuánticos. "
                    "Los espacios L²(ℝ³) de funciones de onda son el ejemplo más importante."
                ),
            },
        ],
    },
    "Física de Partículas y Modelo Estándar": {
        "wiki_pages": [
            "Standard Model",
            "Quantum field theory",
            "Higgs mechanism",
            "Quantum chromodynamics",
            "Feynman diagram",
        ],
        "curated": [
            {
                "instruction": "Describe el Modelo Estándar de la física de partículas",
                "output": (
                    "El Modelo Estándar (1970s) describe las partículas fundamentales y tres de las "
                    "cuatro fuerzas fundamentales (excepto gravedad):\n\n"
                    "Fermiones (materia, spin 1/2):\n"
                    "- Quarks: up, down, charm, strange, top, bottom (6 sabores, 3 colores c/u)\n"
                    "- Leptones: electrón, muón, tau y sus neutrinos (6)\n\n"
                    "Bosones de gauge (portadores de fuerza, spin 1):\n"
                    "- Fotón γ: fuerza electromagnética (U(1))\n"
                    "- W±, Z⁰: fuerza débil (SU(2))\n"
                    "- Gluones (8): fuerza fuerte (SU(3), QCD)\n\n"
                    "Bosón de Higgs (spin 0): mecanismo de Higgs, da masa a W,Z y fermiones.\n\n"
                    "La simetría de gauge del Modelo Estándar es: SU(3)_c × SU(2)_L × U(1)_Y"
                ),
            },
        ],
    },
}

TOPIC_ORDER = list(TOPICS.keys())
MERGE_MIN_TOPICS = int(os.getenv("LIBRARIAN_MERGE_MIN_TOPICS", str(max(1, len(TOPIC_ORDER)))))


# ── Miniverse API ────────────────────────────────────────────────────────────

def _api_request(method: str, path: str, payload: dict | None = None) -> Any:
    url = f"{SERVER}{path}"
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except Exception:
        return None


def heartbeat(state: str, task: str) -> None:
    _api_request("POST", "/api/heartbeat", {
        "agent": AGENT_ID,
        "name": AGENT_NAME,
        "state": state,
        "task": task,
        "energy": 0.9,
    })


def speak(message: str) -> None:
    _api_request("POST", "/api/act", {
        "agent": AGENT_ID,
        "action": {"type": "speak", "message": message},
    })


# ── Wikipedia fetcher ────────────────────────────────────────────────────────

def fetch_wikipedia_summary(title: str) -> str | None:
    """Fetches a Wikipedia article summary using the public REST API."""
    encoded = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "LibrarianLearnBot/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("extract", "")
    except Exception:
        return None


def build_wiki_examples(topic: str, pages: list[str]) -> list[dict[str, str]]:
    """Convert Wikipedia summaries into instruction-following training examples."""
    examples = []
    for page in pages:
        text = fetch_wikipedia_summary(page)
        if text and len(text) > 100:
            examples.append({
                "instruction": f"Explica en detalle el concepto científico: {page}",
                "output": text[:1200],
            })
    print(f"[librarian] Wikipedia: {len(examples)}/{len(pages)} artículos obtenidos para '{topic}'")
    return examples


# ── Deps auto-install ────────────────────────────────────────────────────────

def _install(packages: list[str]) -> None:
    for pkg in packages:
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-q", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.CalledProcessError:
            print(f"[librarian] WARN: no se pudo instalar {pkg}")


def ensure_deps() -> None:
    missing = []
    for pkg, import_name in [
        ("transformers", "transformers"),
        ("peft", "peft"),
        ("accelerate", "accelerate"),
        ("bitsandbytes", "bitsandbytes"),
    ]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[librarian] Instalando dependencias: {missing}")
        heartbeat("thinking", f"Instalando: {', '.join(missing)}")
        _install(missing)
        print("[librarian] Dependencias instaladas.")


# ── Heartbeat thread ─────────────────────────────────────────────────────────

class HeartbeatThread(threading.Thread):
    """Sends periodic heartbeats to Miniverse during long training operations."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.state = "working"
        self.task = "Aprendiendo..."
        self._stop = threading.Event()

    def update(self, state: str, task: str) -> None:
        self.state = state
        self.task = task
        heartbeat(state, task)

    def run(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL):
            heartbeat(self.state, self.task)

    def stop(self) -> None:
        self._stop.set()


# ── Formateador de prompts TinyLlama ─────────────────────────────────────────

SYSTEM_PROMPT = (
    "Eres una bibliotecaria científica especializada en física teórica, matemáticas y "
    "las leyes fundamentales del universo. Respondes con precisión, usando notación matemática "
    "cuando es necesario, y explicas tanto el significado físico como la estructura matemática."
)


def format_example(example: dict[str, str]) -> str:
    """Format as TinyLlama chat template."""
    return (
        f"<|system|>\n{SYSTEM_PROMPT}</s>\n"
        f"<|user|>\n{example['instruction']}</s>\n"
        f"<|assistant|>\n{example['output']}</s>"
    )


# ── Entrenamiento QLoRA ───────────────────────────────────────────────────────

def setup_model(hb: HeartbeatThread):
    """Load TinyLlama with optional 4-bit quantization and LoRA adapters."""
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import get_peft_model, LoraConfig, TaskType

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[librarian] Dispositivo: {device}")
    if device == "cpu":
        print("[librarian] ADVERTENCIA: CUDA no disponible. El entrenamiento será lento.")

    hb.update("thinking", f"Cargando modelo {BASE_MODEL}...")

    # Try 4-bit quantization if bitsandbytes+CUDA available
    use_4bit = device == "cuda"
    bnb_config = None
    if use_4bit:
        try:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
        except Exception:
            use_4bit = False

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_kwargs: dict = {"trust_remote_code": True}
    if bnb_config:
        load_kwargs["quantization_config"] = bnb_config
        load_kwargs["device_map"] = "auto"
    else:
        dtype = torch.float16 if device == "cuda" else torch.float32
        load_kwargs["torch_dtype"] = dtype
        load_kwargs["device_map"] = device

    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, **load_kwargs)

    # Apply LoRA
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_RANK,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer, device


def tokenize_examples(examples: list[dict[str, str]], tokenizer) -> list:
    """Tokenize training examples."""
    import torch
    texts = [format_example(ex) for ex in examples]
    encodings = []
    for text in texts:
        enc = tokenizer(
            text,
            max_length=MAX_SEQ_LEN,
            truncation=True,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids = enc["input_ids"].squeeze(0)
        # For causal LM: labels = input_ids (shifted internally by HF)
        encodings.append({
            "input_ids": input_ids,
            "labels": input_ids.clone(),
        })
    return encodings


def train_on_topic(
    model,
    tokenizer,
    examples: list[dict[str, str]],
    topic: str,
    hb: HeartbeatThread,
) -> float:
    """Train model on a set of examples for EPOCHS_PER_TOPIC epochs."""
    import torch
    from torch.optim import AdamW

    if not examples:
        print(f"[librarian] Sin ejemplos para '{topic}', saltando.")
        return 0.0

    device = next(model.parameters()).device
    encodings = tokenize_examples(examples, tokenizer)
    optimizer = AdamW(model.parameters(), lr=2e-4)

    model.train()
    total_loss = 0.0
    steps = 0

    for epoch in range(EPOCHS_PER_TOPIC):
        epoch_loss = 0.0
        # Mini-batch loop
        for i in range(0, len(encodings), BATCH_SIZE):
            batch = encodings[i:i + BATCH_SIZE]
            if not batch:
                continue

            input_ids = torch.stack([b["input_ids"] for b in batch]).to(device)
            labels = torch.stack([b["labels"] for b in batch]).to(device)

            optimizer.zero_grad()
            outputs = model(input_ids=input_ids, labels=labels)
            loss = outputs.loss

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            epoch_loss += loss.item()
            steps += 1

        avg_loss = epoch_loss / max(1, len(encodings) // BATCH_SIZE)
        total_loss += avg_loss
        msg = f"Aprendiendo: {topic} [época {epoch+1}/{EPOCHS_PER_TOPIC}, loss={avg_loss:.4f}]"
        print(f"[librarian] {msg}")
        hb.update("working", msg)

    return total_loss / EPOCHS_PER_TOPIC


def save_checkpoint(model, tokenizer, topic: str, hb: HeartbeatThread) -> str:
    """Save LoRA adapter weights."""
    safe_name = topic.replace(" ", "_").replace("/", "-").lower()
    checkpoint_dir = MODELS_DIR / safe_name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    hb.update("speaking", f"Guardando checkpoint: {safe_name}")
    model.save_pretrained(str(checkpoint_dir))
    tokenizer.save_pretrained(str(checkpoint_dir))

    # Write metadata
    meta = {
        "topic": topic,
        "base_model": BASE_MODEL,
        "lora_rank": LORA_RANK,
        "epochs": EPOCHS_PER_TOPIC,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    (checkpoint_dir / "train_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    speak(f"Checkpoint guardado: {safe_name}")
    return str(checkpoint_dir)


def _keep_newest_dirs(base_dir: Path, keep: int) -> None:
    """Delete old directories in base_dir, keeping newest 'keep' entries."""
    if keep < 1 or not base_dir.exists():
        return

    dirs = [p for p in base_dir.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in dirs[keep:]:
        try:
            shutil.rmtree(old)
            print(f"[librarian] Limpieza: eliminado {old}")
        except Exception as exc:
            print(f"[librarian] WARN limpieza falló en {old}: {exc}")


def maybe_merge_and_cleanup(adapter_dir: str, topic: str, hb: HeartbeatThread) -> str | None:
    """Merge latest LoRA adapter into a full model and prune old artifacts."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    import torch

    adapter_path = Path(adapter_dir)
    if not adapter_path.exists():
        print(f"[librarian] WARN: adapter no existe para merge: {adapter_path}")
        return None

    safe_topic = topic.replace(" ", "_").replace("/", "-").lower()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snapshot_dir = SNAPSHOTS_DIR / f"{safe_topic}_{stamp}"
    merged_dir = MERGED_MODELS_DIR / f"merged_from_{safe_topic}_{stamp}"

    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    hb.update("thinking", f"Fusionando conocimiento ({MERGE_INTERVAL_HOURS}h)")
    speak(f"Iniciando fusión de conocimiento: {topic}")

    try:
        # Snapshot del adapter para trazabilidad y rollback.
        shutil.copytree(adapter_path, snapshot_dir)

        use_cuda = torch.cuda.is_available()
        dtype = torch.float16 if use_cuda else torch.float32
        device_map = "auto" if use_cuda else "cpu"

        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            trust_remote_code=True,
            torch_dtype=dtype,
            device_map=device_map,
        )
        tokenizer = AutoTokenizer.from_pretrained(str(snapshot_dir), trust_remote_code=True)

        peft_model = PeftModel.from_pretrained(base_model, str(snapshot_dir), is_trainable=False)
        merged_model = peft_model.merge_and_unload()

        merged_model.save_pretrained(str(merged_dir), safe_serialization=True)
        tokenizer.save_pretrained(str(merged_dir))

        meta = {
            "merged_at": datetime.now(timezone.utc).isoformat(),
            "base_model": BASE_MODEL,
            "adapter_source": str(adapter_path),
            "adapter_snapshot": str(snapshot_dir),
            "topic": topic,
            "device_used": "cuda" if use_cuda else "cpu",
            "torch_version": torch.__version__,
            "merge_interval_hours": MERGE_INTERVAL_HOURS,
        }
        (merged_dir / "merge_meta.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        LATEST_MERGED_FILE.write_text(str(merged_dir), encoding="utf-8")

        # Retención para ahorrar espacio.
        _keep_newest_dirs(MERGED_MODELS_DIR, KEEP_MERGED_MODELS)
        _keep_newest_dirs(SNAPSHOTS_DIR, KEEP_SNAPSHOTS)

        hb.update("speaking", f"Fusión completada: {merged_dir.name}")
        speak(f"Fusión completada. Modelo consolidado: {merged_dir.name}")
        print(f"[librarian] Merge OK: {merged_dir}")
        return str(merged_dir)
    except Exception as exc:
        hb.update("idle", f"Merge falló: {exc}")
        print(f"[librarian] WARN merge falló: {exc}")
        return None
    finally:
        try:
            del merged_model  # type: ignore[name-defined]
        except Exception:
            pass
        try:
            del peft_model  # type: ignore[name-defined]
        except Exception:
            pass
        try:
            del base_model  # type: ignore[name-defined]
        except Exception:
            pass
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ── Main loop ────────────────────────────────────────────────────────────────

def wait_for_server(max_attempts: int = 60) -> None:
    for attempt in range(max_attempts):
        result = _api_request("GET", "/api/agents")
        if result is not None:
            return
        if attempt == 0:
            print("[librarian] Esperando al servidor Miniverse...")
        time.sleep(1)
    print("[librarian] WARN: servidor no disponible, continuando de todos modos.")


def write_pid() -> None:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def cleanup(signum=None, frame=None) -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass
    heartbeat("idle", "Aprendizaje pausado")
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    print("[librarian] === Bibliotecaria — Fine-Tuning Continuo ===")
    print(f"[librarian] Modelo: {BASE_MODEL}")
    print(f"[librarian] Data root Agnes: {AGNES_DATA_DIR}")
    print(f"[librarian] Checkpoints: {MODELS_DIR}")
    print(f"[librarian] Servidor: {SERVER}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    MERGED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    write_pid()

    # Wait for Miniverse server
    wait_for_server()
    heartbeat("thinking", "Iniciando sistema de aprendizaje...")
    speak("Sistema de aprendizaje continuo iniciado")

    # Auto-install dependencies
    ensure_deps()

    import torch
    print(f"[librarian] CUDA disponible: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"[librarian] GPU: {torch.cuda.get_device_name(0)}")
        print(f"[librarian] VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Setup heartbeat thread
    hb = HeartbeatThread()
    hb.update("thinking", "Cargando modelo de lenguaje...")
    hb.start()

    # Load model once (reused across topics)
    try:
        model, tokenizer, device = setup_model(hb)
        print(f"[librarian] Modelo cargado en {device}")
    except Exception as exc:
        hb.update("idle", f"Error cargando modelo: {exc}")
        print(f"[librarian] ERROR cargando modelo: {exc}")
        cleanup()
        return

    topic_idx = 0
    last_merge_ts = time.time()
    topics_since_merge = 0

    while True:
        topic = TOPIC_ORDER[topic_idx % len(TOPIC_ORDER)]
        topic_data = TOPICS[topic]

        print(f"\n[librarian] ══ Tópico: {topic} ══")

        # 1. Fetch Wikipedia data
        hb.update("thinking", f"Consultando Wikipedia: {topic}...")
        wiki_examples = build_wiki_examples(topic, topic_data["wiki_pages"])
        time.sleep(1)

        # 2. Combine with curated examples
        all_examples = topic_data["curated"] + wiki_examples
        hb.update("working", f"Corpus listo: {len(all_examples)} ejemplos — {topic}")
        print(f"[librarian] Total ejemplos: {len(all_examples)}")
        time.sleep(2)

        # 3. Train
        speak(f"Aprendiendo: {topic} ({len(all_examples)} ejemplos)")
        try:
            avg_loss = train_on_topic(model, tokenizer, all_examples, topic, hb)
            print(f"[librarian] Entrenamiento completado — loss promedio: {avg_loss:.4f}")
        except Exception as exc:
            print(f"[librarian] ERROR durante entrenamiento: {exc}")
            hb.update("idle", f"Error en {topic}: {exc}")
            time.sleep(10)
            topic_idx += 1
            continue

        # 4. Save checkpoint
        try:
            ckpt_path = save_checkpoint(model, tokenizer, topic, hb)
            print(f"[librarian] Checkpoint: {ckpt_path}")
            topics_since_merge += 1
        except Exception as exc:
            print(f"[librarian] ERROR guardando checkpoint: {exc}")

        # 4.1 Merge periódico + limpieza de artefactos
        elapsed = time.time() - last_merge_ts
        if elapsed >= MERGE_INTERVAL_SECONDS and topics_since_merge >= MERGE_MIN_TOPICS:
            try:
                merged_path = maybe_merge_and_cleanup(ckpt_path, topic, hb)
                if merged_path:
                    last_merge_ts = time.time()
                    topics_since_merge = 0
                    print(f"[librarian] Modelo consolidado activo: {merged_path}")
            except Exception as exc:
                print(f"[librarian] WARN merge periódico falló: {exc}")

        # 5. Rest and rotate topic
        next_topic = TOPIC_ORDER[(topic_idx + 1) % len(TOPIC_ORDER)]
        hb.update("idle", f"Tópico completado: {topic}. Próximo: {next_topic}")
        speak(f"Completé: {topic}. Próximo: {next_topic}")
        time.sleep(5)

        topic_idx += 1


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
