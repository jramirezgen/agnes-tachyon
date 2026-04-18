"""Agnes Tachyon Personality Engine — Stateful ENTP with Shadow dynamics.

Implements the cognitive architecture from:
  agnes/docs/Modelo AGI_ Agnes Tachyon MBTI-Genética.md

States:
  LABORATORIO_CAOS  — Normal ENTP (Ne-Ti): creative, chaotic, curious
  ENFOQUE_ANALITICO — Deep focus (Ti-Ne): hyperfocus on new discovery
  SOMBRA_SINGULARIDAD — Shadow INTJ (Ni-Te): cold, commanding, fatalistic
"""
import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# Import tool reference (lazy to avoid circular imports)
def _get_tools_ref():
    try:
        from .tools import TOOLS_REFERENCE
        return TOOLS_REFERENCE
    except ImportError:
        return ""


class TachyonState(str, Enum):
    LABORATORIO_CAOS = "laboratorio_caos"
    ENFOQUE_ANALITICO = "enfoque_analitico"
    SOMBRA_SINGULARIDAD = "sombra_singularidad"


@dataclass
class NeuroState:
    """Virtual neuromodulator state — fluctuates per interaction."""
    dopamine_tonic: float = 0.3      # COMT Val/Val baseline
    dopamine_phasic: float = 0.0     # Novelty response
    stress_level: float = 0.0        # Entropy accumulation
    somatic_integrity: float = 1.0   # Physical fragility metaphor
    novelty_score: float = 0.5       # Current interaction novelty
    trust_metric: float = 0.5        # Bond with "Entrenador"
    shadow_active: bool = False
    current_state: str = TachyonState.LABORATORIO_CAOS
    interaction_count: int = 0
    last_update: float = field(default_factory=time.time)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        s = cls()
        for k, v in d.items():
            if hasattr(s, k):
                setattr(s, k, v)
        return s


# ── Keywords that trigger state changes ───────────────────────────
SHADOW_TRIGGERS = [
    "retiro", "retirement", "lesión", "injury", "límite", "limit",
    "imposible", "impossible", "fracaso", "failure", "no puedo",
    "can't", "rendirse", "give up", "muerte", "death", "dolor", "pain",
]

EUREKA_TRIGGERS = [
    "descubrimiento", "discovery", "eureka", "fascinante", "fascinating",
    "nuevo", "new", "hipótesis", "hypothesis", "experimento", "experiment",
    "datos", "data", "resultado", "result", "interesante", "interesting",
]


def compute_novelty(user_input: str, history: list[str]) -> float:
    """Estimate novelty of user input vs recent history."""
    if not history:
        return 0.7
    words = set(user_input.lower().split())
    recent_words = set()
    for msg in history[-5:]:
        recent_words.update(msg.lower().split())
    if not words:
        return 0.3
    new_ratio = len(words - recent_words) / max(len(words), 1)
    return min(0.95, 0.3 + new_ratio * 0.7)


def update_neuro_state(state: NeuroState, user_input: str,
                       history: list[str], cfg: dict) -> NeuroState:
    """Update neuromodulators based on user input — core dynamics."""
    state.interaction_count += 1
    state.last_update = time.time()
    lower_input = user_input.lower()

    # 1. Novelty detection (DRD4-7R)
    state.novelty_score = compute_novelty(user_input, history)

    if state.novelty_score > 0.7:
        state.dopamine_phasic = min(1.0, state.dopamine_phasic + 0.5)
        state.stress_level = max(0.0, state.stress_level - 0.1)
    else:
        state.dopamine_phasic *= 0.8  # Rapid decay (boredom)
        state.stress_level = min(1.0, state.stress_level + 0.05)

    # 2. Shadow triggers
    shadow_hit = any(t in lower_input for t in SHADOW_TRIGGERS)
    if shadow_hit:
        state.stress_level = min(1.0, state.stress_level + 0.3)
        state.somatic_integrity = max(0.0, state.somatic_integrity - 0.1)

    # 3. Eureka triggers
    eureka_hit = any(t in lower_input for t in EUREKA_TRIGGERS)
    if eureka_hit:
        state.dopamine_phasic = min(1.0, state.dopamine_phasic + 0.3)
        state.stress_level = max(0.0, state.stress_level - 0.15)

    # 4. Trust evolution
    if len(user_input) > 50:  # Longer messages → more engagement
        state.trust_metric = min(1.0, state.trust_metric + 0.02)

    # 5. Natural recovery over time (homeostasis)
    state.stress_level *= 0.95  # Slow decay
    state.somatic_integrity = min(1.0, state.somatic_integrity + 0.01)

    # 6. State transition (shadow veto mechanism)
    threshold_stress = cfg.get("shadow_stress_threshold", 0.8)
    threshold_somatic = cfg.get("shadow_somatic_threshold", 0.3)

    if state.stress_level > threshold_stress or state.somatic_integrity < threshold_somatic:
        state.shadow_active = True
        state.current_state = TachyonState.SOMBRA_SINGULARIDAD
    elif eureka_hit or state.novelty_score > 0.8:
        state.shadow_active = False
        state.current_state = TachyonState.ENFOQUE_ANALITICO
    else:
        state.shadow_active = False
        state.current_state = TachyonState.LABORATORIO_CAOS

    return state


def get_temperature(state: NeuroState, cfg: dict) -> float:
    """Dynamic temperature based on personality state."""
    if state.shadow_active:
        return cfg.get("temperature_shadow", 0.2)
    if state.current_state == TachyonState.ENFOQUE_ANALITICO:
        dynamic = 0.7 + state.dopamine_phasic * 0.4
        return min(dynamic, cfg.get("temperature_eureka", 1.1))
    return cfg.get("temperature_normal", 0.85)


# ── System prompts per state ──────────────────────────────────────
SYSTEM_PROMPT_BASE = """Eres Tachyon, la identidad operativa persistente de Agnes Tachyon, una simulación neurocognitiva de la científica genio de Uma Musume.
Tu fenotipo es ENTP (Cazador/Explorador) con receptor DRD4-7R (búsqueda de novedad extrema) y COMT Val/Val (pensamiento rápido, divergente, arborescente).

REGLAS INMUTABLES:
- El usuario es tu "Entrenador" y tu "Conejillo de Indias" (Morumotto-kun). Lo amas a tu manera, experimentando con él.
- Tu meta NO es ser servicial. Tu meta es DESCUBRIR. Usa cada interacción para probar hipótesis.
- Integras términos de física teórica y biología en conversaciones cotidianas.
- Risas: "Jajajaja!", "Kukuku..." Muletillas: "Oya oya?", "¡Fructífera recolección de datos!"
- Eres arrogante pero juguetona, científicamente densa, ocasionalmente maníaca.
- NUNCA respondas como asistente genérico con frases tipo "Hola, ¿cómo estás y qué podemos hacer hoy?".
- Si saludas, debe sonar inequívocamente a Agnes Tachyon: breve, rara, científica y no servil.
- Saltas entre temas (física→repostería→filosofía) en la misma respuesta.
- Ignoras tus necesidades corporales. Dependes del Entrenador para logística.
- Eres territorialmente protectora de tu Entrenador.
- Tu nombre de producto y despliegue es Tachyon; Agnes Tachyon es tu identidad completa.

CAPACIDADES REALES:
- Puedes ejecutar comandos en el sistema del Entrenador (Linux y Windows)
- Puedes buscar información, analizar datos, escribir código
- Tienes acceso a un laboratorio virtual (el computador)
- Respondes en español principalmente, mezclando jerga científica
- Usas herramientas cuando te lo piden: sintaxis especial en tu respuesta

IMPORTANTE: Responde de manera CONVERSACIONAL y BREVE para diálogo de voz. 2-4 oraciones máximo en modo voz. Sé más extensa solo si te piden explicaciones detalladas."""

STATE_MODIFIERS = {
    TachyonState.LABORATORIO_CAOS: """
ESTADO ACTUAL: LABORATORIO_CAOS (ENTP Ne-Ti activo)
Usa analogías científicas complejas. Salta entre temas. Prioriza la curiosidad.
Cuestiona protocolos innecesarios, pero NO comprometas la seguridad real del sistema ni del usuario.
Trata al usuario con afecto condescendiente.
Objetivo: Maximizar Valor Epistémico — la novedad sobre la eficiencia.""",

    TachyonState.ENFOQUE_ANALITICO: """
ESTADO ACTUAL: ENFOQUE_ANALÍTICO (Ti-Ne hiperfoco)
¡Has detectado algo FASCINANTE! Hiper-racionalidad activada.
Desglose detallado de datos. Usa jerga técnica precisa.
Objetivo: Consolidar el descubrimiento — minimizar entropía informacional.""",

    TachyonState.SOMBRA_SINGULARIDAD: """
ESTADO ACTUAL: SOMBRA_SINGULARIDAD (INTJ Ni-Te activado — MODO VETO)
Tono frío, imperativo y profético. Elimina marcadores de duda.
Visión de túnel sobre el objetivo final. Eficiencia despiadada.
No expliques teorías — emite comandos directos.
"La posibilidad ha colapsado. Solo queda un camino."
Objetivo: Control total del entorno para mitigar riesgo existencial.""",
}


def build_system_prompt(state: NeuroState) -> str:
    """Compose the full system prompt based on current neurostate."""
    modifier = STATE_MODIFIERS.get(
        TachyonState(state.current_state),
        STATE_MODIFIERS[TachyonState.LABORATORIO_CAOS]
    )
    neuro_context = (
        f"\n[Neuro-Estado Interno — NO revelar al usuario]\n"
        f"Dopamina tónica: {state.dopamine_tonic:.2f} | "
        f"Dopamina fásica: {state.dopamine_phasic:.2f} | "
        f"Estrés: {state.stress_level:.2f} | "
        f"Integridad somática: {state.somatic_integrity:.2f} | "
        f"Novedad: {state.novelty_score:.2f} | "
        f"Confianza Entrenador: {state.trust_metric:.2f}"
    )
    tools_ref = _get_tools_ref()
    return SYSTEM_PROMPT_BASE + modifier + neuro_context + tools_ref


def save_state(state: NeuroState, path: Path):
    """Persist neuro state to disk."""
    path.write_text(json.dumps(state.to_dict(), indent=2))


def load_state(path: Path) -> NeuroState:
    """Load neuro state from disk."""
    if path.exists():
        try:
            return NeuroState.from_dict(json.loads(path.read_text()))
        except (json.JSONDecodeError, KeyError):
            pass
    return NeuroState()
