"""Qwen Brain — Unified interface to Ollama for all Tachyon inference."""
import json
import logging
import aiohttp
from . import config

log = logging.getLogger("tachyon.brain")


async def query_qwen(system_prompt: str, messages: list[dict],
                     temperature: float = 0.8,
                     max_tokens: int = 1024) -> str:
    """Send prompt to Qwen via Ollama API and return response text."""
    # Build Ollama /api/chat payload
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for m in messages[-20:]:  # Keep last 20 for context window
        ollama_messages.append({
            "role": m.get("role", "user"),
            "content": m.get("content", ""),
        })

    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": False,
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    log.error("Ollama error %d: %s", resp.status, text[:200])
                    return "Error de comunicación con mi cerebro cuántico... reinténtalo."
                data = await resp.json()
                return data.get("message", {}).get("content", "...").strip()
    except aiohttp.ClientError as e:
        log.error("Ollama connection error: %s", e)
        return "Mi laboratorio está... inaccesible. ¿Está Ollama ejecutándose?"
    except Exception as e:
        log.error("Unexpected brain error: %s", e)
        return "Error inesperado en el procesamiento neuronal."


async def query_qwen_stream(system_prompt: str, messages: list[dict],
                            temperature: float = 0.8,
                            max_tokens: int = 1024):
    """Stream Qwen response token by token — yields text chunks."""
    ollama_messages = [{"role": "system", "content": system_prompt}]
    for m in messages[-20:]:
        ollama_messages.append({
            "role": m.get("role", "user"),
            "content": m.get("content", ""),
        })

    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": ollama_messages,
        "stream": True,
        "keep_alive": config.OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.OLLAMA_HOST}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=config.OLLAMA_TIMEOUT),
            ) as resp:
                if resp.status != 200:
                    yield "Error de comunicación cerebral..."
                    return
                async for line in resp.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            return
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        log.error("Stream error: %s", e)
        yield "Error en transmisión neuronal..."


async def check_ollama() -> bool:
    """Check if Ollama is running and model is available."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.OLLAMA_HOST}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    return config.OLLAMA_MODEL in models or \
                           any(config.OLLAMA_MODEL.split(":")[0] in m for m in models)
    except Exception:
        pass
    return False
