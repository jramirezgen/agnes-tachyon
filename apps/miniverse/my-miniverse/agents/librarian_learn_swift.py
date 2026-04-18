#!/usr/bin/env python3
"""Bibliotecaria sobre ms-swift + Qwen para aprendizaje continuo bajo Tachyon."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from librarian_learn import (  # type: ignore[import-not-found]
    AGENT_ID,
    AGENT_NAME,
    AGNES_DATA_DIR,
    HeartbeatThread,
    TOPIC_ORDER,
    TOPICS,
    build_wiki_examples,
    heartbeat,
    speak,
)

AGNES_HOME = Path(os.getenv("AGNES_HOME", str(Path.home() / "agnes"))).expanduser()
TRAINER_PYTHON = os.getenv("AGNES_TRAINER_PYTHON", sys.executable)
STEPS_PER_TOPIC = int(os.getenv("LIBRARIAN_SWIFT_STEPS", "60"))
PAUSE_BETWEEN_TOPICS = int(os.getenv("LIBRARIAN_SWIFT_PAUSE_SEC", "30"))
TRAIN_MODEL = os.getenv("LIBRARIAN_SWIFT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
EXPORT_MERGED = os.getenv("LIBRARIAN_SWIFT_EXPORT_MERGED", "0") == "1"
MAX_ROUNDS = int(os.getenv("LIBRARIAN_SWIFT_MAX_ROUNDS", "1"))
KEEP_RUNS = int(os.getenv("LIBRARIAN_SWIFT_KEEP_RUNS", "3"))
KEEP_MERGED = int(os.getenv("LIBRARIAN_SWIFT_KEEP_MERGED", "2"))

MODELS_ROOT = AGNES_DATA_DIR / "models"
SWIFT_ROOT = MODELS_ROOT / "librarian_swift"
DATASET_ROOT = SWIFT_ROOT / "datasets"
RUNS_ROOT = SWIFT_ROOT / "runs"
MERGED_ROOT = SWIFT_ROOT / "merged"
LATEST_MERGED_FILE = SWIFT_ROOT / "LATEST_MERGED_MODEL.txt"
PID_FILE = Path("/tmp/librarian_learning.pid")

LIBRARIAN_SYSTEM = (
    "Eres la bibliotecaria científica de Tachyon. Enseñas física, matemáticas y estructura conceptual "
    "con claridad rigurosa, sin perder precisión formal."
)


def _safe_name(topic: str) -> str:
    return topic.replace(" ", "_").replace("/", "-").lower()


def _topic_records(topic: str) -> list[dict]:
    info = TOPICS[topic]
    curated = list(info.get("curated", []))
    wiki = build_wiki_examples(topic, info.get("wiki_pages", []))
    examples = curated + wiki
    records = []
    for example in examples:
        records.append({
            "messages": [
                {"role": "system", "content": LIBRARIAN_SYSTEM},
                {"role": "user", "content": example["instruction"]},
                {"role": "assistant", "content": example["output"]},
            ]
        })
    return records


def _write_dataset(topic: str) -> Path:
    DATASET_ROOT.mkdir(parents=True, exist_ok=True)
    dataset_path = DATASET_ROOT / f"{_safe_name(topic)}.jsonl"
    with dataset_path.open("w", encoding="utf-8") as handle:
        for record in _topic_records(topic):
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return dataset_path


def _run_topic(topic: str, hb: HeartbeatThread) -> str | None:
    dataset_path = _write_dataset(topic)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = RUNS_ROOT / f"{_safe_name(topic)}_{stamp}"
    export_dir = MERGED_ROOT / f"merged_from_{_safe_name(topic)}_{stamp}"
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    MERGED_ROOT.mkdir(parents=True, exist_ok=True)

    hb.update("working", f"Swift/Qwen aprendiendo {topic}")
    speak(f"Aprendiendo {topic} con ms-swift")

    cmd = [
        TRAINER_PYTHON,
        "-m",
        "tachyon.trainer",
        "--dataset",
        str(dataset_path),
        "--steps",
        str(STEPS_PER_TOPIC),
        "--model",
        TRAIN_MODEL,
        "--output-dir",
        str(output_dir),
    ]
    if EXPORT_MERGED:
        cmd.extend([
            "--export-merged",
            "--export-dir",
            str(export_dir),
        ])
    env = {**os.environ, "PYTHONPATH": str(AGNES_HOME)}
    # El entrenamiento puede depender de paquetes instalados en user-site.
    # Si el stack global usa PYTHONNOUSERSITE=1, lo desactivamos solo para esta llamada.
    env.pop("PYTHONNOUSERSITE", None)
    result = subprocess.run(cmd, env=env)
    if result.returncode == 0:
        target_path = export_dir if EXPORT_MERGED else output_dir
        LATEST_MERGED_FILE.write_text(str(target_path), encoding="utf-8")
        hb.update("speaking", f"Conocimiento consolidado: {target_path.name}")
        speak(f"Consolidación completa en {target_path.name}")
        return str(target_path)

    hb.update("idle", f"Fallo ms-swift en {topic}")
    speak(f"Entrenamiento falló en {topic}")
    return None


def _cleanup(*_args) -> None:
    PID_FILE.unlink(missing_ok=True)
    sys.exit(0)


def _prune_old_dirs(root: Path, pattern: str, keep: int) -> None:
    if keep < 1:
        return
    if not root.exists():
        return
    dirs = sorted((p for p in root.glob(pattern) if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in dirs[keep:]:
        try:
            for node in sorted(stale.rglob("*"), reverse=True):
                if node.is_file() or node.is_symlink():
                    node.unlink(missing_ok=True)
                elif node.is_dir():
                    node.rmdir()
            stale.rmdir()
        except Exception:
            # Best-effort cleanup only.
            pass


def main() -> int:
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    signal.signal(signal.SIGINT, _cleanup)
    signal.signal(signal.SIGTERM, _cleanup)

    hb = HeartbeatThread()
    hb.start()
    print(f"[librarian-swift] Modelo base: {TRAIN_MODEL}")
    print(f"[librarian-swift] Trainer python: {TRAINER_PYTHON}")
    print(f"[librarian-swift] Root: {SWIFT_ROOT}")
    heartbeat("working", "Bibliotecaria ms-swift iniciada")

    rounds = 0
    try:
        while True:
            rounds += 1
            for topic in TOPIC_ORDER:
                _run_topic(topic, hb)
                _prune_old_dirs(RUNS_ROOT, "*", KEEP_RUNS)
                _prune_old_dirs(MERGED_ROOT, "merged_from_*", KEEP_MERGED)
                time.sleep(PAUSE_BETWEEN_TOPICS)
            if MAX_ROUNDS > 0 and rounds >= MAX_ROUNDS:
                hb.update("idle", "Ciclo de aprendizaje completado")
                break
    finally:
        hb.stop()
        PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())