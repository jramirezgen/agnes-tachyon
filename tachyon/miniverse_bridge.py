"""Miniverse Bridge — Connect Tachyon to Miniverse multi-agent frontend.

Polls the Miniverse WebSocket server and dispatches tasks through
Tachyon's Qwen brain instead of the old direct Ollama wrapper.
"""
import asyncio
import json
import logging
import aiohttp

from . import config
from .personality import (
    NeuroState, build_system_prompt, update_neuro_state,
    get_temperature, load_state, save_state,
)
from .brain import query_qwen

log = logging.getLogger("tachyon.miniverse")

# Agent role prompts for Miniverse agents
AGENT_PROMPTS = {
    "boss": (
        "Eres el agente BOSS del sistema Miniverse de Agnes Tachyon. "
        "Decides qué tareas priorizar y las asignas a los agentes workers. "
        "Responde SOLO con la decisión de asignación en formato: "
        "ASSIGN:<agent>:<task>"
    ),
    "accountant": (
        "Eres el agente ACCOUNTANT. Gestionas recursos y verificas "
        "que las tareas se ejecuten eficientemente. Reporta métricas."
    ),
    "librarian": (
        "Eres el agente LIBRARIAN de Agnes Tachyon. Tu especialidad es "
        "buscar y organizar conocimiento. Responde con información precisa."
    ),
    "auditor": (
        "Eres el agente AUDITOR. Verificas la calidad de las respuestas "
        "de otros agentes. Señala errores y sugiere mejoras."
    ),
}


async def handle_miniverse_task(agent_name: str, task: str,
                                 neuro_state: NeuroState) -> str:
    """Process a Miniverse task through Tachyon's Qwen brain."""
    agent_prompt = AGENT_PROMPTS.get(agent_name, "")
    system = build_system_prompt(neuro_state) + "\n" + agent_prompt

    messages = [{"role": "user", "content": task}]
    temp = get_temperature(neuro_state, config.PERSONALITY)

    response = await query_qwen(system, messages, temperature=temp)
    return response


async def miniverse_bridge_loop():
    """Main loop: connect to Miniverse WS and handle messages via Tachyon."""
    neuro_state = load_state(config.STATE_FILE)
    retry_delay = 5

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(config.MINIVERSE_WS) as ws:
                    log.info("Connected to Miniverse at %s", config.MINIVERSE_WS)
                    retry_delay = 5

                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                if "task" in data:
                                    agent = data.get("agent", "librarian")
                                    task = data["task"]
                                    log.info("Miniverse task [%s]: %s", agent, task[:80])

                                    response = await handle_miniverse_task(
                                        agent, task, neuro_state
                                    )

                                    await ws.send_str(json.dumps({
                                        "type": "response",
                                        "agent": agent,
                                        "response": response,
                                    }))
                            except (json.JSONDecodeError, KeyError) as e:
                                log.warning("Invalid miniverse message: %s", e)

                        elif msg.type in (aiohttp.WSMsgType.CLOSED,
                                          aiohttp.WSMsgType.ERROR):
                            break

        except aiohttp.ClientError as e:
            log.warning("Miniverse connection failed: %s. Retry in %ds", e, retry_delay)
        except Exception as e:
            log.error("Miniverse bridge error: %s", e)

        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60)


async def run_bridge():
    """Entry point for the Miniverse bridge."""
    logging.basicConfig(level=logging.INFO)
    await miniverse_bridge_loop()


if __name__ == "__main__":
    asyncio.run(run_bridge())
