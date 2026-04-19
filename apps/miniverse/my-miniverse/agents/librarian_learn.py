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
    "Cosmología y Astrofísica": {
        "wiki_pages": [
            "Big Bang",
            "Dark matter",
            "Dark energy",
            "Black hole",
            "Stellar evolution",
        ],
        "curated": [
            {
                "instruction": "Explica el modelo cosmológico estándar ΛCDM",
                "output": (
                    "El modelo ΛCDM (Lambda-Cold Dark Matter) es el modelo estándar de cosmología:\n"
                    "- Λ (Lambda): constante cosmológica = energía oscura, ~68% del universo\n"
                    "- CDM: materia oscura fría = ~27% del universo\n"
                    "- Materia bariónica (visible): ~5%\n\n"
                    "El universo se originó hace ~13.8 Ga en el Big Bang y se expande aceleradamente. "
                    "La expansión sigue la ecuación de Friedmann: (ȧ/a)² = 8πGρ/3 - kc²/a² + Λc²/3, "
                    "donde a(t) es el factor de escala. "
                    "La energía oscura actúa como presión negativa (p = -ρc²), causando expansión acelerada. "
                    "La materia oscura no interactúa electromagnéticamente pero sí gravitacionalmente; "
                    "forma el andamiaje gravitacional de la estructura a gran escala del universo."
                ),
            },
            {
                "instruction": "Describe la termodinámica y la física de los agujeros negros",
                "output": (
                    "Los agujeros negros son regiones donde el escape gravitacional supera c. "
                    "El radio de Schwarzschild: rs = 2GM/c².\n\n"
                    "Termodinámica de agujeros negros (Bekenstein-Hawking):\n"
                    "- Temperatura de Hawking: T_H = ℏc³/(8πGMkB)\n"
                    "- Entropía: S = kB·A/(4l_P²), donde A es el área del horizonte y l_P = √(ℏG/c³) es la longitud de Planck\n"
                    "- Primera ley: dM = T_H·dS + ΩdJ + ΦdQ\n\n"
                    "Un agujero negro de masa M irradia como cuerpo negro a T_H y se evapora en tiempo "
                    "t_evap ∝ M³. Para el Sol: T_H ~ 10⁻⁷ K y t_evap ~ 10⁶⁶ años. "
                    "La paradoja de la información (Hawking) cuestiona si la información cae al singularity o se codifica en la radiación."
                ),
            },
        ],
    },
    "Mecánica Estadística y Fenómenos Críticos": {
        "wiki_pages": [
            "Statistical mechanics",
            "Partition function (statistical mechanics)",
            "Phase transition",
            "Ising model",
            "Renormalization group",
        ],
        "curated": [
            {
                "instruction": "Explica la función de partición y su rol en la mecánica estadística",
                "output": (
                    "La función de partición Z resume completamente el comportamiento termodinámico de un sistema:\n"
                    "Z = Σᵢ e^(-βEᵢ)  donde β = 1/(kB·T)\n\n"
                    "De Z se derivan todas las cantidades termodinámicas:\n"
                    "- Energía libre de Helmholtz: F = -kBT·ln(Z)\n"
                    "- Energía interna: U = -∂ln(Z)/∂β\n"
                    "- Entropía: S = kB(ln(Z) + βU)\n"
                    "- Presión: p = kBT·∂ln(Z)/∂V\n"
                    "- Calor específico: CV = kBβ²·∂²ln(Z)/∂β²\n\n"
                    "Para un gas ideal monoatómico: Z = (V/λ_th³)^N/N!, donde λ_th = h/√(2πmkBT) "
                    "es la longitud de onda térmica de de Broglie. La mecánica estadística cuántica "
                    "distingue bosones (Bose-Einstein) de fermiones (Fermi-Dirac)."
                ),
            },
            {
                "instruction": "¿Qué son las transiciones de fase y el grupo de renormalización?",
                "output": (
                    "Las transiciones de fase ocurren cuando los parámetros del sistema cruzan valores críticos.\n"
                    "Cerca del punto crítico (Tc), las propiedades escalan como potencias:\n"
                    "- ξ ~ |T-Tc|^(-ν) (longitud de correlación diverge)\n"
                    "- CV ~ |T-Tc|^(-α)\n"
                    "- m ~ |T-Tc|^β (parámetro de orden)\n"
                    "- χ ~ |T-Tc|^(-γ) (susceptibilidad)\n\n"
                    "Los exponentes críticos son universales — independientes de los detalles microscópicos. "
                    "El grupo de renormalización (Wilson, 1971-1982, Nobel 1982) explica esta universalidad: "
                    "a diferentes escalas espaciales, el sistema fluye hacia puntos fijos en el espacio "
                    "de parámetros. Solo los grados de libertad de largo alcance importan en el punto crítico."
                ),
            },
        ],
    },
    "Teoría Cuántica de Campos": {
        "wiki_pages": [
            "Quantum field theory",
            "Feynman diagram",
            "Renormalization",
            "Path integral formulation",
            "Gauge theory",
        ],
        "curated": [
            {
                "instruction": "¿Qué es la formulación de integral de camino de Feynman?",
                "output": (
                    "La formulación de integral de camino (Feynman, 1948) reformula la mecánica cuántica:\n"
                    "La amplitud de probabilidad de ir de x_i a x_f es la suma sobre TODOS los caminos posibles:\n"
                    "⟨x_f|e^(-iHt/ℏ)|x_i⟩ = ∫𝒟[x(t)] · e^(iS[x]/ℏ)\n"
                    "donde S[x] = ∫dt L(x,ẋ) es la acción y la integral es sobre todas las trayectorias.\n\n"
                    "En el límite clásico (ℏ→0), las contribuciones de caminos lejanos al camino clásico "
                    "se cancelan por interferencia, recuperando la mecánica clásica (principio de mínima acción).\n\n"
                    "En TQC, la integral de camino genera todas las amplitudes de Feynman: "
                    "Z = ∫𝒟[φ] · e^(iS[φ]/ℏ), donde φ(x,t) son los campos cuánticos."
                ),
            },
            {
                "instruction": "Explica el concepto de renormalización en teoría cuántica de campos",
                "output": (
                    "En TQC, los cálculos perturbativos producen divergencias (integrales que van al infinito) "
                    "en bucles de Feynman. La renormalización es el procedimiento para extraer predicciones finitas.\n\n"
                    "Pasos de renormalización:\n"
                    "1. Regularización: introducir un cutoff UV Λ o usar dimensiones D=4-ε (Dim. Reg.)\n"
                    "2. Absorber divergencias en redefiniciones de los parámetros (masa, carga, campo)\n"
                    "3. Fijar condiciones de renormalización a escala μ\n\n"
                    "La ecuación del grupo de renormalización (Callan-Symanzik):\n"
                    "[μ∂/∂μ + β(g)∂/∂g + γ(g)]G^(n) = 0\n"
                    "describe cómo las constantes de acoplamiento varían con la escala energética. "
                    "El correr de acoplamiento (running coupling) explica la libertad asintótica en QCD: "
                    "los quarks interactúan débilmente a alta energía (αs→0 cuando Q→∞)."
                ),
            },
        ],
    },
    "Teoría de la Información y Computación": {
        "wiki_pages": [
            "Information theory",
            "Shannon entropy",
            "Quantum information",
            "Quantum computing",
            "Kolmogorov complexity",
        ],
        "curated": [
            {
                "instruction": "Explica la entropía de Shannon y su relación con la física",
                "output": (
                    "La entropía de Shannon (Claude Shannon, 1948) mide la información de una fuente:\n"
                    "H(X) = -Σᵢ pᵢ log₂(pᵢ)  [bits]\n\n"
                    "Propiedades:\n"
                    "- H es máxima cuando la distribución es uniforme (máxima incertidumbre)\n"
                    "- H = 0 cuando un evento tiene probabilidad 1 (cero incertidumbre)\n"
                    "- H es concava: la mezcla no reduce información\n\n"
                    "Conexión con física: H = -(1/ln2)·S_Boltzmann/kB cuando pᵢ = e^(-βEᵢ)/Z. "
                    "El principio de Landauer establece que borrar 1 bit genera al menos kBT·ln2 de calor. "
                    "La información cuántica generaliza: entropía de von Neumann S(ρ) = -Tr(ρ log ρ), "
                    "donde ρ es la matriz densidad del estado cuántico."
                ),
            },
            {
                "instruction": "¿Qué es la computación cuántica y cuáles son sus ventajas sobre la clásica?",
                "output": (
                    "La computación cuántica usa qubits |ψ⟩ = α|0⟩ + β|1⟩ (superposición) en lugar de bits clásicos.\n\n"
                    "Ventajas cuánticas clave:\n"
                    "- Algoritmo de Shor (1994): factorización en tiempo O(log³N) vs. exponencial clásico\n"
                    "- Algoritmo de Grover (1996): búsqueda en O(√N) vs. O(N) clásico\n"
                    "- Simulación cuántica: simular sistemas cuánticos exponencialmente más eficiente\n\n"
                    "El entrelazamiento cuántico: |ψ⟩ = (|00⟩+|11⟩)/√2 (estado de Bell) es un recurso "
                    "sin análogo clásico. La decoherencia — interacción del qubit con el entorno — "
                    "destruye la superposición (tiempo de coherencia T₂). La corrección de errores cuánticos "
                    "requiere O(1000) qubits físicos por qubit lógico para tolerancia a fallos."
                ),
            },
        ],
    },
    "Química Cuántica y Materia Condensada": {
        "wiki_pages": [
            "Density functional theory",
            "Superconductivity",
            "Chemical bond",
            "Molecular orbital theory",
            "Band theory",
        ],
        "curated": [
            {
                "instruction": "Explica la teoría de funcional de densidad (DFT)",
                "output": (
                    "La DFT (Hohenberg-Kohn 1964, Kohn-Sham 1965) reformula el problema de N electrones "
                    "en términos de la densidad electrónica ρ(r⃗):\n\n"
                    "Teorema de Hohenberg-Kohn: la energía del estado fundamental es un funcional único "
                    "de la densidad electrónica: E[ρ] = T[ρ] + V_ext[ρ] + V_Hartree[ρ] + E_xc[ρ]\n\n"
                    "Las ecuaciones de Kohn-Sham:\n"
                    "[-ℏ²/(2m)∇² + V_eff(r⃗)]φᵢ(r⃗) = εᵢφᵢ(r⃗)\n"
                    "donde V_eff = V_ext + V_Hartree + V_xc es el potencial efectivo de un electron.\n\n"
                    "DFT reduce el problema de 3N dimensiones (N electrones) a 3 dimensiones (densidad). "
                    "Es el método dominante en química computacional y ciencia de materiales, "
                    "calculando geometrías moleculares, espectros vibracionales, y propiedades electrónicas."
                ),
            },
            {
                "instruction": "Explica la superconductividad y la teoría BCS",
                "output": (
                    "La superconductividad (Kamerlingh Onnes, 1911) ocurre cuando la resistividad eléctrica "
                    "cae exactamente a cero bajo temperatura crítica Tc.\n\n"
                    "Teoría BCS (Bardeen-Cooper-Schrieffer, 1957, Nobel 1972):\n"
                    "- Los electrones se emparejan en Pares de Cooper mediante fononos (vibración de red)\n"
                    "- El par Cooper tiene spin total 0 (bosón) y condensa en un estado coherente de muchos cuerpos\n"
                    "- Gap de energía: Δ ~ 2ℏωD·e^(-1/N(0)V)\n"
                    "- Efecto Meissner: expulsión perfecta del campo magnético B⃗ = 0 dentro del superconductor\n"
                    "- Temperatura crítica: kBTc ≈ 1.13ℏωD·e^(-1/N(0)V)\n\n"
                    "Los superconductores de alta temperatura (cuprates, HgBa₂CuO₄, Tc~133K) "
                    "no se explican completamente por BCS — son un problema abierto de materia condensada."
                ),
            },
        ],
    },
    "Biofísica y Sistemas Complejos": {
        "wiki_pages": [
            "Biophysics",
            "DNA replication",
            "Protein folding",
            "Complex system",
            "Emergence",
        ],
        "curated": [
            {
                "instruction": "Explica el problema del plegamiento de proteínas y sus principios físicos",
                "output": (
                    "Las proteínas son cadenas de aminoácidos que se pliegan espontáneamente a su "
                    "estructura nativa en microsegundos a segundos. La paradoja de Levinthal:\n"
                    "Si una proteína de 100 aminoácidos probara todas las conformaciones posibles a "
                    "10¹³ conf/s, tardaría 10²⁷ años — más que la edad del universo.\n\n"
                    "Solución: el embudo de plegamiento energético (Wolynes, Dill):\n"
                    "- El paisaje energético tiene forma de embudo hacia el estado nativo (mínimo global)\n"
                    "- La energía libre G = H - TS equilibra estabilidad y entropía conformacional\n"
                    "- Fuerzas dominantes: efecto hidrofóbico, puentes de hidrógeno, interacciones van der Waals\n\n"
                    "AlphaFold2 (DeepMind, 2021) predice estructuras con precisión atómica usando "
                    "atención multi-cabeza sobre evolutionary couplings — revolucionando la biología estructural."
                ),
            },
            {
                "instruction": "¿Qué son los sistemas complejos y la emergencia?",
                "output": (
                    "Los sistemas complejos presentan comportamiento colectivo que no puede predecirse "
                    "sumando las partes individuales (emergencia).\n\n"
                    "Características:\n"
                    "- Muchos agentes interactivos con retroalimentación no lineal\n"
                    "- Auto-organización sin control centralizado\n"
                    "- Propiedades emergentes (ej: temperatura emerge de velocidades moleculares)\n"
                    "- Comportamiento crítico y transiciones de fase\n\n"
                    "Ejemplos físico-biológicos:\n"
                    "- Murmuración de estorninos (bandadas): reglas locales → comportamiento global\n"
                    "- Sincronización de luciérnagas: osciladores acoplados → fase colectiva (Kuramoto)\n"
                    "- Neuronas → conciencia: ~86×10⁹ neuronas con 10¹⁴ sinapsis generan cognición\n"
                    "- Mercados financieros: agentes racionales → volatilidad en clusters (Mandelbrot)\n\n"
                    "La ciencia de la complejidad usa herramientas como teoría de redes, autómatas celulares, "
                    "y dinámica no lineal para entender estos fenómenos."
                ),
            },
        ],
    },
    "Gravedad Cuántica y Física Teórica Avanzada": {
        "wiki_pages": [
            "Loop quantum gravity",
            "String theory",
            "AdS/CFT correspondence",
            "Holographic principle",
            "Planck length",
        ],
        "curated": [
            {
                "instruction": "Explica el principio holográfico y la correspondencia AdS/CFT",
                "output": (
                    "El principio holográfico (t'Hooft, Susskind, 1993-1995):\n"
                    "Toda la información contenida en un volumen de espacio puede codificarse "
                    "en su frontera bidimensional. Análogo al holograma: imagen 3D en placa 2D.\n\n"
                    "Motivación: la entropía de un agujero negro S = A/(4l_P²) escala con el ÁREA, "
                    "no el volumen — sugiere que la gravedad es fundamentalmente bidimensional.\n\n"
                    "AdS/CFT (Maldacena, 1997): dualidad holográfica concreta:\n"
                    "- Teoría de gravedad en espacio Anti-de Sitter (AdS) en D+1 dimensiones\n"
                    "- ≡ Teoría conforme de campos (CFT) cuántica sin gravedad en D dimensiones (frontera)\n"
                    "Aplicaciones: cálculo de viscosidad en plasma quark-gluón (QGP), "
                    "sistemas de materia condensada fuertemente correlacionados, "
                    "y la paradoja de la información de agujeros negros."
                ),
            },
            {
                "instruction": "¿Qué es la escala de Planck y por qué es fundamental?",
                "output": (
                    "La escala de Planck surge combinando las tres constantes fundamentales:\n"
                    "G (gravedad), ℏ (cuántica), c (relatividad):\n\n"
                    "- Longitud de Planck: l_P = √(ℏG/c³) ≈ 1.616×10⁻³⁵ m\n"
                    "- Tiempo de Planck: t_P = √(ℏG/c⁵) ≈ 5.39×10⁻⁴⁴ s\n"
                    "- Masa de Planck: m_P = √(ℏc/G) ≈ 2.18×10⁻⁸ kg ≈ 10¹⁹ GeV/c²\n"
                    "- Temperatura de Planck: T_P = m_P·c²/kB ≈ 1.42×10³² K\n\n"
                    "Por debajo de l_P, la noción clásica de espaciotiempo se rompe: "
                    "las fluctuaciones cuánticas de la geometría (espuma cuántica) dominan. "
                    "Una teoría completa de gravedad cuántica (quantum gravity) debe describir esta escala. "
                    "Candidatos: Teoría de cuerdas, Gravedad cuántica de bucles (LQG), Causal Dynamical Triangulations."
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
