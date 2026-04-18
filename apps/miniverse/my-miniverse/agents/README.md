# Multiagentes Operativos (OpenClaw + Miniverse)

Este runtime levanta 4 roles en paralelo:
- boss-agent (Jefe orquestador)
- accountant-agent (Contador)
- librarian-agent (Bibliotecaria)
- auditor-agent (Auditor)

Todos reportan estado al servidor Miniverse y colaboran por mensajes internos.

Implementacion principal en este entorno:
- Python: `runtime.py`, `submit_task.py`, `demo.py`, `start_stack.sh`

Implementacion alternativa (si tienes Node/npm):
- JS: `runtime.mjs`, `submit-task.mjs`, `demo.mjs`

## Arranque automatico

Con `agents/start_stack.sh` se inician:
- servidor Miniverse
- runtime multiagente Python

Si usas Node/npm en tu entorno, tambien puedes usar `npm run dev` (vite + server + runtime JS).

## Scripts utiles (Python)

- `python3 agents/runtime.py` -> arranca runtime multiagente
- `python3 agents/submit_task.py "tu solicitud"` -> envia tarea al jefe
- `python3 agents/demo.py` -> envia dos tareas en paralelo para demo
- `agents/start_stack.sh` -> arranque conjunto server + agentes

## Scripts utiles (Node/npm, opcional)

- `npm run agents`
- `npm run agents:task -- "tu solicitud"`
- `npm run agents:demo`

## Flujo

1. El jefe recibe la tarea y la clasifica (finance / knowledge / windows_action).
2. Asigna a contador o bibliotecaria.
3. El agente produce resultado consultando a Tachyon como cerebro único.
4. El auditor valida calidad.
5. El jefe cierra la tarea y notifica estado.

## Artefactos

Los resultados se guardan en:
- `generated/boss-agent/`
- `generated/accountant-agent/`
- `generated/librarian-agent/`
- `generated/auditor-agent/`

## Variables opcionales

- `MINIVERSE_SERVER_URL` (default: http://localhost:4321)
- `MINIVERSE_HEARTBEAT_SEC` (default: 20, runtime Python)
- `MINIVERSE_POLL_SEC` (default: 3, runtime Python)
- `MINIVERSE_HEARTBEAT_MS` (default: 20000, runtime JS)
- `MINIVERSE_POLL_MS` (default: 3000, runtime JS)
- `MINIVERSE_BOOTSTRAP_DEMO` (default: 1)
- `TACHYON_URL` (default: http://localhost:7777)
