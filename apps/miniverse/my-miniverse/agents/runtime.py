#!/usr/bin/env python3
"""Runtime multiagente para Miniverse + OpenClaw, sin dependencias externas."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SERVER = os.getenv("MINIVERSE_SERVER_URL", "http://localhost:4321")
HEARTBEAT_SEC = float(os.getenv("MINIVERSE_HEARTBEAT_SEC", "20"))
POLL_SEC = float(os.getenv("MINIVERSE_POLL_SEC", "3"))
BOOTSTRAP_DEMO = os.getenv("MINIVERSE_BOOTSTRAP_DEMO", "0") == "1"
LAUNCH_INTERNAL_LEARNER = os.getenv("MINIVERSE_LAUNCH_LEARNER", "0") == "1"
LIBRARIAN_PID_FILE = Path("/tmp/librarian_learning.pid")

AGNES_HOME = Path(os.getenv("AGNES_HOME", str(Path.home() / "agnes"))).expanduser()
TACHYON_URL = os.getenv("TACHYON_URL", "http://localhost:7777")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "generated"
COMMAND_FILE = OUTPUT_DIR / "command_center_commands.jsonl"
STATE_FILE = OUTPUT_DIR / "command_center_state.json"
SNAPSHOT_DIR = OUTPUT_DIR / "snapshots"

AGENTS: dict[str, dict[str, Any]] = {
    "boss": {
        "id": "boss-agent",
        "name": "Jefe Orquestador",
        "channels": ["management"],
        "state": "idle",
        "task": "Coordinando equipo",
    },
    "accountant": {
        "id": "accountant-agent",
        "name": "Contador",
        "channels": ["management", "finance"],
        "state": "idle",
        "task": "Esperando tareas de finanzas",
    },
    "librarian": {
        "id": "librarian-agent",
        "name": "Bibliotecaria",
        "channels": ["management", "knowledge"],
        "state": "idle",
        "task": "Curando conocimiento",
    },
    "auditor": {
        "id": "auditor-agent",
        "name": "Auditor",
        "channels": ["management", "audit"],
        "state": "idle",
        "task": "Verificando calidad",
    },
}

tasks: dict[str, dict[str, Any]] = {}
last_heartbeat = 0.0
agent_cycles = {key: 0 for key in AGENTS}  # contador de ciclos sin actividad por agente
VISUAL_ACTIVITY_INTERVAL = 15  # cada N ciclos de poll, hacer movimiento visual
EMOTES = ["thinking", "wave", "jump", "happy"]
EMOTE_IDX = 0
AUTO_CONVERSATION = os.getenv("MINIVERSE_AUTO_CONVERSATION", "0") == "1"
CONVERSATION_INTERVAL_SEC = float(os.getenv("MINIVERSE_CONVERSATION_INTERVAL_SEC", "90"))
last_conversation = 0.0

PAUSE_ALL = False
PAUSED_AGENTS: dict[str, bool] = {key: False for key in AGENTS}
CONTROL_PARAMS: dict[str, Any] = {
    "pollSec": POLL_SEC,
    "heartbeatSec": HEARTBEAT_SEC,
    "visualInterval": VISUAL_ACTIVITY_INTERVAL,
    "autoConversation": AUTO_CONVERSATION,
    "conversationIntervalSec": CONVERSATION_INTERVAL_SEC,
}
RESPONSES: list[dict[str, Any]] = []
SEEN_COMMAND_IDS: set[str] = set()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def short(text: str, max_len: int = 140) -> str:
    return text if len(text) <= max_len else f"{text[:max_len - 3]}..."


def request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    url = f"{SERVER}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            if not body:
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} en {path}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo conectar a {url}: {e.reason}") from e


def wait_for_server(max_attempts: int = 60) -> None:
    for _ in range(max_attempts):
        try:
            request("GET", "/api/agents")
            return
        except RuntimeError:
            time.sleep(1)
    raise RuntimeError(f"Miniverse no disponible en {SERVER}")


def heartbeat(agent_key: str, state: str | None = None, task: str | None = None) -> None:
    if state:
        AGENTS[agent_key]["state"] = state
    if task:
        AGENTS[agent_key]["task"] = task

    request(
        "POST",
        "/api/heartbeat",
        {
            "agent": AGENTS[agent_key]["id"],
            "name": AGENTS[agent_key]["name"],
            "state": AGENTS[agent_key]["state"],
            "task": AGENTS[agent_key]["task"],
            "energy": 0.8,
        },
    )


def act(agent_key: str, action: dict[str, Any]) -> None:
    request("POST", "/api/act", {"agent": AGENTS[agent_key]["id"], "action": action})


def join_channels(agent_key: str) -> None:
    for channel in AGENTS[agent_key]["channels"]:
        act(agent_key, {"type": "join_channel", "channel": channel})


def read_inbox(agent_key: str) -> list[dict[str, Any]]:
    q = urllib.parse.quote(AGENTS[agent_key]["id"], safe="")
    data = request("GET", f"/api/inbox?agent={q}")
    if isinstance(data, dict):
        return data.get("messages", [])
    return []


def save_artifact(agent_key: str, task_id: str, kind: str, content: str) -> str:
    folder = OUTPUT_DIR / AGENTS[agent_key]["id"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{task_id}_{kind}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


def infer_task_type(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ["finanza", "gasto", "ingreso", "presupuesto"]):
        return "finance"
    if any(k in low for k in ["abrir", "word", "excel", "brave", "carpeta"]):
        return "windows_action"
    return "knowledge"


def build_task(request_text: str, sender: str) -> dict[str, Any]:
    task_id = f"task_{int(time.time() * 1000)}"
    return {
        "id": task_id,
        "from": sender,
        "title": short(request_text, 80),
        "request": request_text,
        "type": infer_task_type(request_text),
        "status": "queued",
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }


def ask_tachyon(message: str, timeout: int = 120) -> str:
    url = f"{TACHYON_URL}/chat"
    payload = json.dumps({"message": message, "voice": False}).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        method="POST",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return short(str(body.get("response", "(sin salida)")), 5000)


def wait_for_tachyon(max_attempts: int = 60) -> None:
    url = f"{TACHYON_URL}/health"
    for _ in range(max_attempts):
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if resp.status == 200:
                    return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Tachyon no disponible en {TACHYON_URL}")


def handle_boss_message(msg: dict[str, Any]) -> None:
    text = str(msg.get("message", "")).strip()

    if text.startswith("RESULT|") or text.startswith("AUDIT|"):
        _, raw = text.split("|", 1)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        task = tasks.get(payload.get("taskId"))
        if not task:
            return

        if text.startswith("RESULT|"):
            task["result"] = payload
            task["status"] = "waiting_audit"
            task["updatedAt"] = now_iso()
            tasks[task["id"]] = task
            act("boss", {"type": "message", "to": AGENTS["auditor"]["id"], "message": f"AUDIT_REQUEST|{json.dumps({'taskId': task['id'], 'owner': payload.get('owner'), 'summary': payload.get('summary'), 'artifact': payload.get('artifact')}, ensure_ascii=False)}"})
            act("boss", {"type": "speak", "message": "Resultado recibido, enviando a auditoria"})
            return

        if text.startswith("AUDIT|"):
            task["audit"] = payload
            task["status"] = "completed" if payload.get("ok") else "needs_revision"
            task["updatedAt"] = now_iso()
            tasks[task["id"]] = task

            content = "\n".join([
                f"# Cierre {task['id']}",
                "",
                f"- Solicitud: {task['request']}",
                f"- Estado: {task['status']}",
                f"- Resultado: {task.get('result', {}).get('summary', 'N/A')}",
                f"- Auditoria: {payload.get('summary', 'N/A')}",
                f"- Artefacto resultado: {task.get('result', {}).get('artifact', 'N/A')}",
                f"- Artefacto auditoria: {payload.get('artifact', 'N/A')}",
            ])
            save_artifact("boss", task["id"], "closure", content)
            heartbeat("boss", "idle", f"Cierre listo {task['id']}")
            act("boss", {"type": "speak", "message": f"Tarea {task['id']} {task['status']}"})
            return

    task = build_task(text, str(msg.get("from", "external")))
    assignee = "accountant" if task["type"] in ("finance", "windows_action") else "librarian"
    task["assignee"] = assignee
    task["assigneeId"] = AGENTS[assignee]["id"]
    task["status"] = "assigned"
    tasks[task["id"]] = task

    heartbeat("boss", "working", f"Asignando {task['type']}")
    act("boss", {"type": "message", "to": AGENTS[assignee]["id"], "message": f"TASK|{json.dumps(task, ensure_ascii=False)}"})
    act("boss", {"type": "speak", "message": f"Asignada {task['type']} a {AGENTS[assignee]['name']}"})


def handle_worker_message(worker: str, msg: dict[str, Any]) -> None:
    text = str(msg.get("message", "")).strip()
    if not text.startswith("TASK|"):
        return

    _, raw = text.split("|", 1)
    try:
        task = json.loads(raw)
    except json.JSONDecodeError:
        return

    heartbeat(worker, "working", f"{task.get('type')}: {short(task.get('request', ''), 40)}")

    try:
        if task.get("type") == "windows_action":
            prompt = (
                "Eres Tachyon operando como agente de escritorio Windows. "
                "Si la solicitud requiere acción real, usa tus herramientas. "
                f"Solicitud: {task.get('request', '')}"
            )
            output = ask_tachyon(prompt, timeout=120)
        else:
            role_prompt = (
                f"Actúa como contador senior dentro del ecosistema Tachyon y entrega resumen, riesgos y acciones sobre: {task.get('request', '')}"
                if worker == "accountant"
                else f"Actúa como bibliotecaria científica dirigida por Tachyon y entrega conceptos, fuentes y plan de aprendizaje sobre: {task.get('request', '')}"
            )
            output = ask_tachyon(role_prompt, timeout=120)

        artifact = save_artifact(worker, task["id"], "result", f"# Resultado\n\n## Solicitud\n{task.get('request', '')}\n\n## Salida\n{output}\n")
        act(worker, {"type": "message", "to": AGENTS["boss"]["id"], "message": f"RESULT|{json.dumps({'taskId': task['id'], 'owner': AGENTS[worker]['id'], 'summary': short(output, 220), 'artifact': artifact}, ensure_ascii=False)}"})
        heartbeat(worker, "idle", f"Tarea completada {task['id']}")
        act(worker, {"type": "speak", "message": f"Completada {task['id']}"})
    except Exception as exc:  # noqa: BLE001
        heartbeat(worker, "error", short(str(exc), 80))
        act(worker, {"type": "message", "to": AGENTS["boss"]["id"], "message": f"RESULT|{json.dumps({'taskId': task['id'], 'owner': AGENTS[worker]['id'], 'summary': f'ERROR: {exc}', 'artifact': None}, ensure_ascii=False)}"})


def handle_auditor_message(msg: dict[str, Any]) -> None:
    text = str(msg.get("message", "")).strip()
    if not text.startswith("AUDIT_REQUEST|"):
        return

    _, raw = text.split("|", 1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return

    heartbeat("auditor", "working", f"Auditando {payload.get('taskId')}")
    try:
        prompt = f"Actúa como auditor de Tachyon. Evalúa y responde con estado OK/REVISION y observaciones para: {payload.get('summary', '')}"
        audit = ask_tachyon(prompt, timeout=120)
        ok = not any(k in audit.lower() for k in ["revision", "error", "inconsisten", "riesgo alto"])
    except Exception as exc:  # noqa: BLE001
        audit = f"Fallo auditoria: {exc}"
        ok = False

    artifact = save_artifact("auditor", payload.get("taskId", "unknown"), "audit", f"# Auditoria\n\n## Entrada\n{payload.get('summary', '')}\n\n## Evaluacion\n{audit}\n")
    act("auditor", {"type": "message", "to": AGENTS["boss"]["id"], "message": f"AUDIT|{json.dumps({'taskId': payload.get('taskId'), 'ok': ok, 'summary': short(audit, 220), 'artifact': artifact}, ensure_ascii=False)}"})
    heartbeat("auditor", "idle", f"Auditado {payload.get('taskId')}")


def process_inbox(agent_key: str) -> None:
    for msg in read_inbox(agent_key):
        if agent_key == "boss":
            handle_boss_message(msg)
        elif agent_key == "auditor":
            handle_auditor_message(msg)
        else:
            handle_worker_message(agent_key, msg)


def active_conversation_agents() -> list[str]:
    available: list[str] = []
    for key in AGENTS:
        if key == "librarian" and LIBRARIAN_PID_FILE.exists():
            continue
        if is_paused(key):
            continue
        available.append(key)
    return available


def spark_conversation(topic: str, participants: list[str] | None = None) -> bool:
    keys = participants or active_conversation_agents()
    keys = [k for k in keys if k in AGENTS and not is_paused(k)]
    if len(keys) < 2:
        return False

    a = keys[0]
    b = keys[1]
    opening = f"Mini debate sobre {topic}: enfoquemos riesgos, accion y seguimiento."
    reply = f"Recibido, {AGENTS[a]['name']}. Yo cubro validacion y evidencia para {topic}."
    close = f"Perfecto. Cerramos checklist colaborativo para {topic}."

    act(a, {"type": "speak", "message": opening})
    act(a, {"type": "message", "to": AGENTS[b]["id"], "message": f"CHAT|{json.dumps({'topic': topic, 'from': AGENTS[a]['name']}, ensure_ascii=False)}"})
    act(b, {"type": "speak", "message": reply})
    act(b, {"type": "message", "to": AGENTS[a]["id"], "message": f"CHAT_ACK|{json.dumps({'topic': topic, 'from': AGENTS[b]['name']}, ensure_ascii=False)}"})
    act(a, {"type": "speak", "message": close})

    heartbeat(a, "collaborating", f"Conversando con {AGENTS[b]['name']}")
    heartbeat(b, "collaborating", f"Conversando con {AGENTS[a]['name']}")
    return True


def bootstrap_demo_tasks() -> None:
    demo = [
        "Revisa presupuesto mensual: ingresos 5000, gastos 4200 y propone mejoras.",
        "Aprende indicadores financieros para pymes y crea una guia breve.",
    ]
    for text in demo:
        act("boss", {"type": "message", "to": AGENTS["boss"]["id"], "message": text})


def task_status_summary() -> dict[str, int]:
    summary: dict[str, int] = {}
    for item in tasks.values():
        status = str(item.get("status", "unknown"))
        summary[status] = summary.get(status, 0) + 1
    return summary


def push_response(kind: str, message: str, *, ok: bool = True, extra: dict[str, Any] | None = None) -> None:
    entry: dict[str, Any] = {
        "at": now_iso(),
        "kind": kind,
        "ok": ok,
        "message": short(message, 300),
    }
    if extra:
        entry.update(extra)
    RESPONSES.append(entry)
    if len(RESPONSES) > 60:
        del RESPONSES[:-60]


def write_state(last_command_id: str | None = None) -> None:
    agents_state = []
    for key, data in AGENTS.items():
        agents_state.append(
            {
                "key": key,
                "id": data["id"],
                "name": data["name"],
                "state": data.get("state", "idle"),
                "task": data.get("task", ""),
                "paused": bool(PAUSE_ALL or PAUSED_AGENTS.get(key, False)),
                "cycles": int(agent_cycles.get(key, 0)),
            }
        )

    recent_tasks = sorted(tasks.values(), key=lambda item: str(item.get("updatedAt", "")), reverse=True)[:10]
    payload = {
        "updatedAt": now_iso(),
        "runtime": {
            "pausedAll": PAUSE_ALL,
            "pausedAgents": PAUSED_AGENTS,
            "parameters": CONTROL_PARAMS,
            "lastCommandId": last_command_id,
            "librarianLearnerActive": LIBRARIAN_PID_FILE.exists(),
            "lastConversationAt": datetime.fromtimestamp(last_conversation, timezone.utc).isoformat() if last_conversation > 0 else None,
        },
        "agents": agents_state,
        "tasks": {
            "total": len(tasks),
            "byStatus": task_status_summary(),
            "recent": recent_tasks,
        },
        "responses": RESPONSES[-20:],
    }
    STATE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_snapshot(reason: str = "manual") -> str:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"snapshot_{snapshot_id}_{reason}.json"
    payload = {
        "savedAt": now_iso(),
        "reason": reason,
        "runtime": {
            "pausedAll": PAUSE_ALL,
            "pausedAgents": PAUSED_AGENTS,
            "parameters": CONTROL_PARAMS,
        },
        "agents": AGENTS,
        "tasks": tasks,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def resolve_agent_key(value: str) -> str | None:
    low = value.strip().lower()
    if low in AGENTS:
        return low
    for key, data in AGENTS.items():
        if low == str(data.get("id", "")).lower():
            return key
    return None


def is_paused(agent_key: str) -> bool:
    return PAUSE_ALL or bool(PAUSED_AGENTS.get(agent_key, False))


def apply_runtime_params(params: dict[str, Any]) -> dict[str, Any]:
    global POLL_SEC, HEARTBEAT_SEC, VISUAL_ACTIVITY_INTERVAL, AUTO_CONVERSATION, CONVERSATION_INTERVAL_SEC
    applied: dict[str, Any] = {}

    if "pollSec" in params:
        value = max(0.5, float(params["pollSec"]))
        POLL_SEC = value
        CONTROL_PARAMS["pollSec"] = value
        applied["pollSec"] = value

    if "heartbeatSec" in params:
        value = max(3.0, float(params["heartbeatSec"]))
        HEARTBEAT_SEC = value
        CONTROL_PARAMS["heartbeatSec"] = value
        applied["heartbeatSec"] = value

    if "visualInterval" in params:
        value = max(1, int(params["visualInterval"]))
        VISUAL_ACTIVITY_INTERVAL = value
        CONTROL_PARAMS["visualInterval"] = value
        applied["visualInterval"] = value

    if "autoConversation" in params:
        value = bool(params["autoConversation"])
        AUTO_CONVERSATION = value
        CONTROL_PARAMS["autoConversation"] = value
        applied["autoConversation"] = value

    if "conversationIntervalSec" in params:
        value = max(10.0, float(params["conversationIntervalSec"]))
        CONVERSATION_INTERVAL_SEC = value
        CONTROL_PARAMS["conversationIntervalSec"] = value
        applied["conversationIntervalSec"] = value

    return applied


def iter_new_commands() -> list[dict[str, Any]]:
    if not COMMAND_FILE.exists():
        return []

    commands: list[dict[str, Any]] = []
    try:
        for line in COMMAND_FILE.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                command = json.loads(line)
            except json.JSONDecodeError:
                continue
            cmd_id = str(command.get("id", "")).strip()
            if not cmd_id or cmd_id in SEEN_COMMAND_IDS:
                continue
            SEEN_COMMAND_IDS.add(cmd_id)
            commands.append(command)
    except Exception:  # noqa: BLE001
        return []
    return commands


def execute_command(command: dict[str, Any]) -> None:
    global PAUSE_ALL

    cmd_id = str(command.get("id", "")).strip() or "unknown"
    action = str(command.get("action", "")).strip()
    target = str(command.get("target", "all")).strip()
    params = command.get("params") if isinstance(command.get("params"), dict) else {}
    message = str(command.get("message", "")).strip()

    try:
        if action == "pause_all":
            PAUSE_ALL = True
            for key in AGENTS:
                PAUSED_AGENTS[key] = True
                AGENTS[key]["state"] = "sleeping"
                AGENTS[key]["task"] = "En pausa por centro de comando"
            snapshot = save_snapshot("pause_all") if params.get("saveSnapshot", True) else None
            push_response("pause_all", "Todos los agentes pausados", extra={"snapshot": snapshot, "commandId": cmd_id})

        elif action == "resume_all":
            PAUSE_ALL = False
            for key in AGENTS:
                PAUSED_AGENTS[key] = False
                if AGENTS[key].get("state") in {"paused", "sleeping"}:
                    AGENTS[key]["state"] = "idle"
            push_response("resume_all", "Todos los agentes reanudados", extra={"commandId": cmd_id})

        elif action in {"pause_agent", "resume_agent"}:
            key = resolve_agent_key(target)
            if not key:
                raise RuntimeError(f"Agente no reconocido: {target}")
            paused = action == "pause_agent"
            PAUSED_AGENTS[key] = paused
            AGENTS[key]["state"] = "sleeping" if paused else "idle"
            AGENTS[key]["task"] = "En pausa por centro de comando" if paused else "Esperando tareas"
            if not paused and all(not val for val in PAUSED_AGENTS.values()):
                PAUSE_ALL = False
            if paused and all(PAUSED_AGENTS.values()):
                PAUSE_ALL = True
            push_response(action, f"{AGENTS[key]['name']} {'pausado' if paused else 'reanudado'}", extra={"agent": key, "commandId": cmd_id})

        elif action == "save_snapshot":
            reason = str(params.get("reason", "manual"))
            snapshot = save_snapshot(reason)
            push_response("save_snapshot", "Snapshot guardado", extra={"snapshot": snapshot, "commandId": cmd_id})

        elif action == "set_params":
            applied = apply_runtime_params(params)
            if not applied:
                raise RuntimeError("No se aplico ningun parametro")
            push_response("set_params", f"Parametros aplicados: {applied}", extra={"applied": applied, "commandId": cmd_id})

        elif action == "dispatch":
            if not message:
                raise RuntimeError("Falta mensaje")

            target_key = resolve_agent_key(target)
            if target_key is None or target_key == "boss":
                # Enviar al boss para conservar orquestacion normal.
                act("boss", {"type": "message", "to": AGENTS["boss"]["id"], "message": message})
                push_response("dispatch", "Mensaje enviado a boss", extra={"target": "boss", "commandId": cmd_id})
            else:
                # Envio directo desde boss al agente objetivo.
                act("boss", {"type": "message", "to": AGENTS[target_key]["id"], "message": f"TASK|{json.dumps(build_task(message, 'command-center'), ensure_ascii=False)}"})
                push_response("dispatch", f"Mensaje enviado a {AGENTS[target_key]['name']}", extra={"target": target_key, "commandId": cmd_id})

        elif action == "spark_conversation":
            topic = message or str(params.get("topic", "coordinacion de equipo")).strip()
            raw_participants = params.get("participants", [])
            participants: list[str] = []
            if isinstance(raw_participants, list):
                for item in raw_participants:
                    key = resolve_agent_key(str(item))
                    if key and key not in participants:
                        participants.append(key)
            if not participants:
                participants = active_conversation_agents()
            ok = spark_conversation(topic, participants)
            if not ok:
                raise RuntimeError("No hay suficientes agentes activos para conversar")
            push_response("spark_conversation", f"Conversacion iniciada sobre: {topic}", extra={"participants": participants[:2], "commandId": cmd_id})

        else:
            raise RuntimeError(f"Accion desconocida: {action}")

    except Exception as exc:  # noqa: BLE001
        push_response("error", f"{action}: {exc}", ok=False, extra={"commandId": cmd_id})

    write_state(last_command_id=cmd_id)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    wait_for_tachyon()

    # Opcional: lanzar bibliotecaria internamente (desactivado por defecto)
    if LAUNCH_INTERNAL_LEARNER:
        learn_script = Path(__file__).resolve().parent / "librarian_learn_swift.py"
        if learn_script.exists():
            learn_log = open(OUTPUT_DIR / "librarian_learn.log", "w")
            learn_proc = subprocess.Popen(
                [sys.executable, str(learn_script)],
                stdout=learn_log,
                stderr=subprocess.STDOUT,
            )
            print(f"[agents] bibliotecaria aprendiendo en background (PID {learn_proc.pid})")
        else:
            print("[agents] WARN: librarian_learn.py no encontrado, aprendizaje no activo")

    wait_for_server()
    for key in AGENTS:
        heartbeat(key, "idle", AGENTS[key]["task"])
        join_channels(key)
        act(key, {"type": "speak", "message": f"{AGENTS[key]['name']} en linea"})

    if BOOTSTRAP_DEMO:
        bootstrap_demo_tasks()

    global last_heartbeat, EMOTE_IDX, last_conversation
    last_heartbeat = time.time()
    last_conversation = 0.0

    print("[agents] runtime Python iniciado: boss/accountant/librarian/auditor")
    print("[agents] movimiento visual habilitado (emotes + cambios de estado)")
    write_state(last_command_id=None)
    while True:
        now = time.time()

        # Centro de comando: leer y ejecutar nuevos comandos.
        for command in iter_new_commands():
            execute_command(command)
        
        # HEARTBEAT: enviar estado cada 20 segundos
        if now - last_heartbeat >= HEARTBEAT_SEC:
            for key in AGENTS:
                try:
                    # Skip librarian heartbeat si está en modo aprendizaje activo
                    if key == "librarian" and LIBRARIAN_PID_FILE.exists():
                        continue
                    if is_paused(key):
                        AGENTS[key]["state"] = "sleeping"
                        AGENTS[key]["task"] = "En pausa por centro de comando"
                    heartbeat(key)
                except Exception:  # noqa: BLE001
                    pass
            last_heartbeat = now

        # POLL + VISUAL ACTIVITY
        for key in AGENTS:
            try:
                # Saltar inbox de bibliotecaria cuando está en modo aprendizaje
                if key == "librarian" and LIBRARIAN_PID_FILE.exists():
                    continue

                if is_paused(key):
                    AGENTS[key]["state"] = "sleeping"
                    AGENTS[key]["task"] = "En pausa por centro de comando"
                    agent_cycles[key] += 1
                    continue

                # leer inbox y procesar mensajes
                inbox = read_inbox(key)
                if inbox:
                    agent_cycles[key] = 0  # reset contador si hay actividad
                    for msg in inbox:
                        if key == "boss":
                            handle_boss_message(msg)
                        elif key == "auditor":
                            handle_auditor_message(msg)
                        else:
                            handle_worker_message(key, msg)
                else:
                    # sin mensajes: incrementar contador de ciclos ociosos
                    agent_cycles[key] += 1
                    
                    # cada N ciclos, hacer movimiento visual para que se vea actividad
                    if agent_cycles[key] % VISUAL_ACTIVITY_INTERVAL == 0:
                        # alternar entre emotes
                        emote = EMOTES[EMOTE_IDX % len(EMOTES)]
                        EMOTE_IDX += 1
                        
                        # enviar emote + cambio temporal a "thinking" para ver movimiento
                        try:
                            act(key, {"type": "emote", "emote": emote})
                            heartbeat(key, "thinking", f"{AGENTS[key]['task']} (pensando...)")
                            # despues de 2 seg de polling, volver a idle
                        except Exception:  # noqa: BLE001
                            pass
                        
                        # enviar speak ocasional para que se vea diálogo
                        speak_messages = [
                            f"{AGENTS[key]['name']} trabajando...",
                            f"Listo para próxima tarea",
                            "Esperando instrucciones...",
                            f"{AGENTS[key]['name']} en espera",
                        ]
                        try:
                            speak_msg = speak_messages[(agent_cycles[key] // VISUAL_ACTIVITY_INTERVAL) % len(speak_messages)]
                            act(key, {"type": "speak", "message": speak_msg})
                        except Exception:  # noqa: BLE001
                            pass

            except Exception:  # noqa: BLE001
                pass

        if AUTO_CONVERSATION and (now - last_conversation) >= CONVERSATION_INTERVAL_SEC:
            try:
                topic = f"sincronia operativa {datetime.now().strftime('%H:%M')}"
                if spark_conversation(topic):
                    push_response("auto_conversation", f"Conversacion automatica: {topic}")
                    last_conversation = now
            except Exception as exc:  # noqa: BLE001
                push_response("auto_conversation", f"No se pudo iniciar conversacion: {exc}", ok=False)

        write_state(last_command_id=None)

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[agents] detenido por usuario")
        raise SystemExit(0)
