"""Tachyon Server — FastAPI + WebSocket for voice & text interaction.

Endpoints:
  GET  /                → Frontend HTML
  GET  /health          → System health check
  GET  /state           → Current personality state
  POST /chat            → Text chat (JSON)
  WS   /ws              → Real-time voice + text WebSocket
  GET  /voices           → Available TTS voices
  POST /train/start     → Start ms-swift training (background)
  GET  /train/status    → Training status
"""
import asyncio
import base64
import json
import logging
import os
import signal
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

from . import config
from .personality import (
    NeuroState, TachyonState, build_system_prompt,
    update_neuro_state, get_temperature, save_state, load_state,
)
from .brain import query_qwen, query_qwen_stream, check_ollama
from .memory import ConversationMemory
from .voice import transcribe_audio, synthesize_speech, preload_whisper
from .tools import execute_tool_calls, has_tool_calls
from .intent import detect_intent_and_run, summarize_pc_diagnostic

log = logging.getLogger("tachyon.server")

# ── Global state ──────────────────────────────────────────────────
neuro_state: NeuroState = NeuroState()
memory: ConversationMemory = ConversationMemory()
training_process: subprocess.Popen | None = None
start_time: float = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown."""
    global neuro_state
    log.info("═══ Agnes Tachyon — Activating cognitive systems ═══")

    # Load persisted state
    neuro_state = load_state(config.STATE_FILE)
    log.info("Neuro state: %s (stress=%.2f, shadow=%s)",
             neuro_state.current_state, neuro_state.stress_level,
             neuro_state.shadow_active)

    # Preload Whisper in background
    preload_whisper()

    # Check Ollama
    ollama_ok = await check_ollama()
    if ollama_ok:
        log.info("✓ Qwen brain online via Ollama (%s)", config.OLLAMA_MODEL)
    else:
        log.warning("✗ Ollama/Qwen not detected — text brain offline!")

    log.info("✓ Memory: %d messages loaded", memory.count)
    log.info("✓ Tachyon listening on %s:%d", config.HOST, config.PORT)
    log.info("═══ 'La perfección es un estado estático, y por lo tanto, muerto.' ═══")

    yield

    # Shutdown
    save_state(neuro_state, config.STATE_FILE)
    memory.save()
    log.info("═══ Agnes Tachyon — Cognitive systems suspended ═══")


app = FastAPI(title="Agnes Tachyon", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"


# ── Models ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    voice: bool = False  # If true, return TTS audio


class ChatResponse(BaseModel):
    response: str
    state: str
    audio_b64: str | None = None
    neuro: dict


# ── Core chat logic ───────────────────────────────────────────────
async def process_message(user_text: str, want_audio: bool = False) -> dict:
    """Full Tachyon processing pipeline: state → brain → memory → voice."""
    global neuro_state

    # 1. Update personality state
    history = memory.get_history_texts()
    neuro_state = update_neuro_state(
        neuro_state, user_text, history, config.PERSONALITY
    )

    # 2. Build system prompt
    system_prompt = build_system_prompt(neuro_state)
    mem_context = memory.get_memory_context()
    if mem_context:
        system_prompt += mem_context

    # 3. Add user message to memory
    memory.add("user", user_text, neuro_state.current_state)

    # 3b. Intent-based tool pre-execution (for small models that don't follow tool syntax)
    pre_tool_context = ""
    pre_tool_results = await detect_intent_and_run(user_text)
    if pre_tool_results:
        log.info("Pre-executed %d intent tool(s)", len(pre_tool_results))
        pre_tool_context = "\n\nYa ejecuté estos comandos por ti. Responde usando estos datos REALES:\n"
        for t in pre_tool_results:
            pre_tool_context += f"[{t['tool']}: {t['cmd']}]\n{t['output']}\n\n"

    # 4. Query Qwen
    temperature = get_temperature(neuro_state, config.PERSONALITY)
    context = memory.get_context(n=20)
    if pre_tool_context:
        # Replace last user message in context with enriched version
        # so the model sees the data right next to the question
        enriched_user_msg = user_text + pre_tool_context
        # Update the last user message in context
        for i in range(len(context) - 1, -1, -1):
            if context[i]["role"] == "user":
                context[i] = {"role": "user", "content": enriched_user_msg}
                break

    # Fast path for deterministic PC diagnosis to avoid LLM timeouts
    diagnostic_result = next(
        (item for item in pre_tool_results if item.get("cmd") == "pc_diagnostic"),
        None,
    )
    if diagnostic_result:
        response_text = summarize_pc_diagnostic(diagnostic_result["output"])
    else:
        response_text = await query_qwen(
            system_prompt, context,
            temperature=temperature,
            max_tokens=512 if want_audio else 1024,
        )

    # 5. Execute tool calls if any (Linux/Windows commands)
    tool_results = []
    if has_tool_calls(response_text):
        response_text, tool_results = await execute_tool_calls(response_text)
        if tool_results:
            log.info("Executed %d tool(s)", len(tool_results))
            # Second pass: ask Qwen to synthesize a clean spoken response
            # only if voice mode (keep it short for TTS)
            if want_audio:
                tool_summary = "\n".join(
                    f"- {t['tool']}: {t['output'][:200]}" for t in tool_results
                )
                synth_msgs = memory.get_context(n=10) + [
                    {"role": "user", "content":
                     f"Resultado de las herramientas ejecutadas:\n{tool_summary}\n"
                     "Resume en 1-2 oraciones conversacionales qué hiciste y el resultado."
                    }
                ]
                spoken = await query_qwen(
                    build_system_prompt(neuro_state), synth_msgs,
                    temperature=0.7, max_tokens=180,
                )
                response_text = spoken if spoken else response_text

    # 6. Save assistant response
    memory.add("assistant", response_text, neuro_state.current_state)
    save_state(neuro_state, config.STATE_FILE)

    # 7. TTS if requested
    audio_b64 = None
    if want_audio and response_text:
        try:
            audio_bytes = await synthesize_speech(response_text)
            audio_b64 = base64.b64encode(audio_bytes).decode()
        except Exception as e:
            log.error("TTS error: %s", e)

    return {
        "response": response_text,
        "state": neuro_state.current_state,
        "audio_b64": audio_b64,
        "neuro": {
            "dopamine_phasic": round(neuro_state.dopamine_phasic, 2),
            "stress": round(neuro_state.stress_level, 2),
            "novelty": round(neuro_state.novelty_score, 2),
            "trust": round(neuro_state.trust_metric, 2),
            "somatic": round(neuro_state.somatic_integrity, 2),
            "shadow": neuro_state.shadow_active,
        },
    }


# ── HTTP Endpoints ────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text())
    return HTMLResponse("<h1>Agnes Tachyon — Frontend not found</h1>")


@app.get("/health")
async def health():
    ollama_ok = await check_ollama()
    return {
        "status": "alive",
        "uptime_s": round(time.time() - start_time),
        "ollama": ollama_ok,
        "model": config.OLLAMA_MODEL,
        "state": neuro_state.current_state,
        "memory_messages": memory.count,
        "shadow_active": neuro_state.shadow_active,
    }


@app.get("/state")
async def get_state():
    return {
        "state": neuro_state.current_state,
        "neuro": neuro_state.to_dict(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    result = await process_message(req.message, want_audio=req.voice)
    return ChatResponse(**result)


@app.get("/voices")
async def voices():
    from .voice import list_voices
    return await list_voices("es")


# ── Training endpoints ────────────────────────────────────────────
@app.post("/train/start")
async def train_start(request: Request):
    global training_process
    if training_process and training_process.poll() is None:
        return JSONResponse({"error": "Training already running"}, 409)

    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    dataset = body.get("dataset", "AI-ModelScope/alpaca-gpt4-data-zh#500")

    cmd = [
        sys.executable, "-m", "swift.cli.main", "sft",
        "--model", config.TRAIN_MODEL,
        "--tuner_type", "lora",
        "--quant_method", "bnb",
        "--quant_bits", str(config.TRAIN_QUANT_BITS),
        "--bnb_4bit_compute_dtype", "bfloat16",
        "--bnb_4bit_quant_type", "nf4",
        "--bnb_4bit_use_double_quant", "true",
        "--dataset", dataset,
        "--lora_rank", str(config.TRAIN_LORA_RANK),
        "--lora_alpha", str(config.TRAIN_LORA_ALPHA),
        "--target_modules", "all-linear",
        "--output_dir", str(config.TRAIN_OUTPUT),
        "--max_steps", "100",
        "--logging_steps", "5",
        "--report_to", "none",
    ]

    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
    ms_swift_path = str(config.MSSWIFT_DIR)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{ms_swift_path}:{existing_pythonpath}"
        if existing_pythonpath
        else ms_swift_path
    )

    training_process = subprocess.Popen(
        cmd,
        stdout=open(config.DATA_DIR / "train.log", "w"),
        stderr=subprocess.STDOUT,
        env=env,
    )
    return {"status": "started", "pid": training_process.pid}


@app.get("/train/status")
async def train_status():
    if training_process is None:
        return {"status": "idle"}
    rc = training_process.poll()
    if rc is None:
        # Read last lines of log
        logfile = config.DATA_DIR / "train.log"
        tail = ""
        if logfile.exists():
            lines = logfile.read_text().splitlines()
            tail = "\n".join(lines[-10:])
        return {"status": "running", "pid": training_process.pid, "log_tail": tail}
    return {"status": "finished", "exit_code": rc}


# ── WebSocket — Real-time voice + text ────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    log.info("WebSocket client connected")
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "text")

            if msg_type == "text":
                # Text message
                result = await process_message(
                    msg.get("content", ""),
                    want_audio=msg.get("voice", False),
                )
                await ws.send_text(json.dumps({
                    "type": "response",
                    **result,
                }))

            elif msg_type == "audio":
                # Audio message — base64 WAV
                audio_b64 = msg.get("audio", "")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)

                    # STT
                    await ws.send_text(json.dumps({
                        "type": "status",
                        "status": "transcribing",
                    }))
                    transcription = await transcribe_audio(audio_bytes)

                    if not transcription.strip():
                        await ws.send_text(json.dumps({
                            "type": "status",
                            "status": "no_speech",
                        }))
                        continue

                    # Show transcription
                    await ws.send_text(json.dumps({
                        "type": "transcription",
                        "text": transcription,
                    }))

                    # Process through Tachyon
                    await ws.send_text(json.dumps({
                        "type": "status",
                        "status": "thinking",
                    }))
                    result = await process_message(transcription, want_audio=True)
                    await ws.send_text(json.dumps({
                        "type": "response",
                        **result,
                    }))

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected")
    except Exception as e:
        log.error("WebSocket error: %s", e)


# ── Entry point ───────────────────────────────────────────────────
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    uvicorn.run(
        "tachyon.server:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
