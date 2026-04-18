"""Tachyon Watchdog — Keeps the system alive 24/7.

Monitors all Tachyon processes and restarts them if they crash.
Manages: Ollama, Tachyon Server, Miniverse Bridge.
"""
import asyncio
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from . import config

log = logging.getLogger("tachyon.watchdog")

PROCESSES: dict[str, dict] = {}
RUNNING = True


def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        import urllib.request
        req = urllib.request.urlopen(f"{config.OLLAMA_HOST}/api/tags", timeout=3)
        return req.status == 200
    except Exception:
        return False


def start_ollama():
    """Start Ollama serve if not running."""
    if check_ollama():
        log.info("✓ Ollama already running")
        return

    log.info("Starting Ollama serve...")
    proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    PROCESSES["ollama"] = {"proc": proc, "restarts": 0}
    time.sleep(3)

    if check_ollama():
        log.info("✓ Ollama started (PID %d)", proc.pid)
    else:
        log.warning("✗ Ollama failed to start")


def start_tachyon_server():
    """Start the Tachyon FastAPI server."""
    log.info("Starting Tachyon server on port %d...", config.PORT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "tachyon.server"],
        env={**os.environ, "PYTHONPATH": str(config.AGNES_HOME)},
    )
    PROCESSES["server"] = {"proc": proc, "restarts": 0}
    log.info("✓ Tachyon server started (PID %d)", proc.pid)
    return proc


def start_miniverse_bridge():
    """Start the Miniverse bridge."""
    log.info("Starting Miniverse bridge...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "tachyon.miniverse_bridge"],
        env={**os.environ, "PYTHONPATH": str(config.AGNES_HOME)},
    )
    PROCESSES["miniverse"] = {"proc": proc, "restarts": 0}
    log.info("✓ Miniverse bridge started (PID %d)", proc.pid)
    return proc


def check_and_restart():
    """Check all processes and restart dead ones."""
    for name, info in list(PROCESSES.items()):
        proc = info["proc"]
        if proc.poll() is not None:
            rc = proc.returncode
            restarts = info["restarts"]
            log.warning("Process '%s' died (exit=%d, restarts=%d)",
                        name, rc, restarts)

            if restarts > 10:
                log.error("Process '%s' exceeded restart limit!", name)
                continue

            # Restart
            time.sleep(2)
            if name == "ollama":
                start_ollama()
            elif name == "server":
                start_tachyon_server()
            elif name == "miniverse":
                start_miniverse_bridge()

            if name in PROCESSES:
                PROCESSES[name]["restarts"] = restarts + 1


def signal_handler(sig, frame):
    global RUNNING
    log.info("Shutdown signal received. Stopping all processes...")
    RUNNING = False
    for name, info in PROCESSES.items():
        proc = info["proc"]
        if proc.poll() is None:
            log.info("Stopping %s (PID %d)...", name, proc.pid)
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    log.info("All processes stopped. Goodbye!")
    sys.exit(0)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [WATCHDOG] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    log.info("═══════════════════════════════════════════════")
    log.info("  Agnes Tachyon — Watchdog v1.0")
    log.info("  'El laboratorio nunca duerme.'")
    log.info("═══════════════════════════════════════════════")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start all services
    start_ollama()
    time.sleep(2)
    start_tachyon_server()
    time.sleep(2)
    start_miniverse_bridge()

    log.info("All systems online. Watchdog monitoring...")
    log.info("Frontend URL: http://localhost:%d", config.PORT)

    # Main monitoring loop
    while RUNNING:
        time.sleep(10)
        check_and_restart()


if __name__ == "__main__":
    main()
