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
BOOTSTRAP_DEMO = os.getenv("MINIVERSE_BOOTSTRAP_DEMO", "1") == "1"
LAUNCH_INTERNAL_LEARNER = os.getenv("MINIVERSE_LAUNCH_LEARNER", "0") == "1"
LIBRARIAN_PID_FILE = Path("/tmp/librarian_learning.pid")

AGNES_HOME = Path(os.getenv("AGNES_HOME", str(Path.home() / "agnes"))).expanduser()
TACHYON_URL = os.getenv("TACHYON_URL", "http://localhost:7777")

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "generated"

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


def bootstrap_demo_tasks() -> None:
    demo = [
        "Revisa presupuesto mensual: ingresos 5000, gastos 4200 y propone mejoras.",
        "Aprende indicadores financieros para pymes y crea una guia breve.",
    ]
    for text in demo:
        act("boss", {"type": "message", "to": AGENTS["boss"]["id"], "message": text})


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
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

    global last_heartbeat, EMOTE_IDX
    last_heartbeat = time.time()

    print("[agents] runtime Python iniciado: boss/accountant/librarian/auditor")
    print("[agents] movimiento visual habilitado (emotes + cambios de estado)")
    while True:
        now = time.time()
        
        # HEARTBEAT: enviar estado cada 20 segundos
        if now - last_heartbeat >= HEARTBEAT_SEC:
            for key in AGENTS:
                try:
                    # Skip librarian heartbeat si está en modo aprendizaje activo
                    if key == "librarian" and LIBRARIAN_PID_FILE.exists():
                        continue
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

        time.sleep(POLL_SEC)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[agents] detenido por usuario")
        raise SystemExit(0)
