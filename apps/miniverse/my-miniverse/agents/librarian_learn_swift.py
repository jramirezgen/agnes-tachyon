#!/usr/bin/env python3
"""Bibliotecaria sobre ms-swift + Qwen para aprendizaje continuo bajo Tachyon."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
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
EXPORT_MERGED = os.getenv("LIBRARIAN_SWIFT_EXPORT_MERGED", "1") == "1"
MAX_ROUNDS = int(os.getenv("LIBRARIAN_SWIFT_MAX_ROUNDS", "1"))
KEEP_RUNS = int(os.getenv("LIBRARIAN_SWIFT_KEEP_RUNS", "3"))
KEEP_MERGED = int(os.getenv("LIBRARIAN_SWIFT_KEEP_MERGED", "2"))
EVAL_ON_MERGE = os.getenv("LIBRARIAN_SWIFT_EVAL_ON_MERGE", "1") == "1"
EVAL_CASES = int(os.getenv("LIBRARIAN_SWIFT_EVAL_CASES", "6"))
EVAL_TIMEOUT_SEC = int(os.getenv("LIBRARIAN_SWIFT_EVAL_TIMEOUT_SEC", "90"))
EVAL_RETRIES = int(os.getenv("LIBRARIAN_SWIFT_EVAL_RETRIES", "2"))
EVAL_RETRY_BACKOFF_SEC = float(os.getenv("LIBRARIAN_SWIFT_EVAL_RETRY_BACKOFF_SEC", "4"))
EVAL_MAX_TOKENS = int(os.getenv("LIBRARIAN_SWIFT_EVAL_MAX_TOKENS", "256"))
EVAL_WARMUP_SEC = int(os.getenv("LIBRARIAN_SWIFT_EVAL_WARMUP_SEC", "6"))
EVAL_MIN_DELTA = float(os.getenv("LIBRARIAN_SWIFT_EVAL_MIN_DELTA", "0.03"))
EVAL_CANDIDATE_MODEL = os.getenv("LIBRARIAN_SWIFT_EVAL_CANDIDATE_MODEL", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_ACTIVE_MODEL = os.getenv("OLLAMA_MODEL", "tachyon:latest")
MERGE_INTERVAL_SEC = int(os.getenv("LIBRARIAN_MERGE_INTERVAL_SEC", "10800"))  # 3 horas
SYNC_SKILLS = os.getenv("LIBRARIAN_SYNC_SKILLS", "1") == "1"
SYNC_REPO = os.getenv("LIBRARIAN_SYNC_REPO", "1") == "1"
SKILLS_DIR = Path.home() / "skills" / "miniverse"

MODELS_ROOT = AGNES_DATA_DIR / "models"
SWIFT_ROOT = MODELS_ROOT / "librarian_swift"
DATASET_ROOT = SWIFT_ROOT / "datasets"
RUNS_ROOT = SWIFT_ROOT / "runs"
MERGED_ROOT = SWIFT_ROOT / "merged"
REPORTS_ROOT = SWIFT_ROOT / "reports"
LATEST_MERGED_FILE = SWIFT_ROOT / "LATEST_MERGED_MODEL.txt"
LATEST_REPORT_FILE = REPORTS_ROOT / "LATEST_EVAL_REPORT.txt"
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


def _normalize_tokens(text: str) -> set[str]:
    cleaned = []
    for char in text.lower():
        cleaned.append(char if char.isalnum() or char.isspace() else " ")
    return {tok for tok in "".join(cleaned).split() if len(tok) > 2}


def _keyword_recall(reference: str, prediction: str) -> float:
    ref_tokens = _normalize_tokens(reference)
    if not ref_tokens:
        return 0.0
    pred_tokens = _normalize_tokens(prediction)
    common = len(ref_tokens.intersection(pred_tokens))
    return common / max(len(ref_tokens), 1)


def _ask_ollama(model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "stream": False,
        "options": {
            "num_predict": EVAL_MAX_TOKENS,
            "temperature": 0.2,
        },
        "messages": [
            {"role": "system", "content": LIBRARIAN_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }
    last_error = ""
    attempts = max(EVAL_RETRIES + 1, 1)
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            f"{OLLAMA_HOST}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=EVAL_TIMEOUT_SEC) as response:
                raw = response.read().decode("utf-8")
            parsed = json.loads(raw)
            return parsed.get("message", {}).get("content", "")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            last_error = str(exc)
            if attempt < attempts:
                time.sleep(EVAL_RETRY_BACKOFF_SEC * attempt)
            continue
    raise TimeoutError(last_error or "ollama request failed")


def _wait_for_ollama() -> None:
    request = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10):
            return
    except Exception:
        # Best effort warm-up only.
        pass


def _resolved_merged_artifact(output_dir: Path, export_dir: Path) -> Path:
    if export_dir.exists() and any(export_dir.iterdir()):
        return export_dir

    merged_candidates = sorted(
        [p for p in output_dir.rglob("checkpoint-*-merged") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if merged_candidates:
        return merged_candidates[0]

    return export_dir


def _benchmark_cases(topic: str) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for record in _topic_records(topic)[: max(EVAL_CASES, 1)]:
        messages = record.get("messages", [])
        if len(messages) < 3:
            continue
        cases.append({
            "prompt": messages[1].get("content", ""),
            "expected": messages[2].get("content", ""),
        })
    return cases


def _evaluate_model(model: str, topic: str) -> dict:
    started = time.time()
    cases = _benchmark_cases(topic)
    if not cases:
        return {
            "model": model,
            "cases": 0,
            "avg_keyword_recall": 0.0,
            "avg_latency_sec": 0.0,
            "status": "no_cases",
            "details": [],
        }

    details = []
    recalls = []
    latencies = []
    error_count = 0
    for case in cases:
        t0 = time.time()
        try:
            output = _ask_ollama(model, case["prompt"])
            status = "ok"
            error = ""
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            output = ""
            status = "error"
            error = str(exc)
            error_count += 1
        latency = time.time() - t0
        recall = _keyword_recall(case["expected"], output) if status == "ok" else 0.0
        recalls.append(recall)
        latencies.append(latency)
        details.append({
            "prompt": case["prompt"],
            "expected": case["expected"],
            "output": output,
            "keyword_recall": recall,
            "latency_sec": latency,
            "status": status,
            "error": error,
        })

    return {
        "model": model,
        "topic": topic,
        "cases": len(cases),
        "avg_keyword_recall": sum(recalls) / len(recalls),
        "avg_latency_sec": sum(latencies) / len(latencies),
        "error_count": error_count,
        "error_rate": error_count / len(cases),
        "elapsed_sec": time.time() - started,
        "status": "ok",
        "details": details,
    }


def _last_report_score() -> float | None:
    if not REPORTS_ROOT.exists():
        return None
    reports = sorted(REPORTS_ROOT.glob("merge_eval_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for report in reports:
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        candidate = payload.get("candidate_eval") or {}
        active = payload.get("active_eval") or {}
        score = candidate.get("avg_keyword_recall") if candidate else active.get("avg_keyword_recall")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _write_report(report: dict) -> None:
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = REPORTS_ROOT / f"merge_eval_{stamp}.json"
    md_path = REPORTS_ROOT / f"merge_eval_{stamp}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    candidate_eval = report.get("candidate_eval") or {}
    summary = [
        "# Librarian Merge Evaluation",
        "",
        f"- timestamp_utc: {report['timestamp_utc']}",
        f"- topic: {report['topic']}",
        f"- merged_artifact: {report['merged_artifact']}",
        f"- active_model: {report['active_model']}",
        f"- candidate_model: {report.get('candidate_model') or 'n/a'}",
        f"- decision: {report['decision']}",
        f"- reason: {report['reason']}",
        "",
        "## Metrics",
        f"- active_avg_keyword_recall: {report['active_eval'].get('avg_keyword_recall', 0.0):.4f}",
        f"- active_avg_latency_sec: {report['active_eval'].get('avg_latency_sec', 0.0):.3f}",
        f"- candidate_avg_keyword_recall: {candidate_eval.get('avg_keyword_recall', 0.0):.4f}",
        f"- active_error_rate: {report['active_eval'].get('error_rate', 0.0):.4f}",
        f"- candidate_error_rate: {candidate_eval.get('error_rate', 0.0):.4f}",
        f"- delta_vs_previous_report: {report.get('delta_vs_previous_report', 0.0):.4f}",
    ]
    md_path.write_text("\n".join(summary) + "\n", encoding="utf-8")
    LATEST_REPORT_FILE.write_text(str(json_path), encoding="utf-8")


def _evaluate_after_merge(topic: str, merged_artifact: Path) -> None:
    if not EVAL_ON_MERGE:
        return

    if EVAL_WARMUP_SEC > 0:
        time.sleep(EVAL_WARMUP_SEC)
    _wait_for_ollama()

    previous_score = _last_report_score()
    active_eval = _evaluate_model(OLLAMA_ACTIVE_MODEL, topic)
    candidate_eval = None
    if EVAL_CANDIDATE_MODEL:
        candidate_eval = _evaluate_model(EVAL_CANDIDATE_MODEL, topic)

    current_score = (
        candidate_eval.get("avg_keyword_recall", 0.0)
        if candidate_eval
        else active_eval.get("avg_keyword_recall", 0.0)
    )
    delta = current_score - previous_score if previous_score is not None else 0.0

    if candidate_eval:
        active_score = active_eval.get("avg_keyword_recall", 0.0)
        candidate_score = candidate_eval.get("avg_keyword_recall", 0.0)
        gain = candidate_score - active_score
        if gain >= EVAL_MIN_DELTA:
            decision = "promote_candidate"
            reason = f"candidate beats active by {gain:.4f}"
        else:
            decision = "hold"
            reason = f"candidate gain {gain:.4f} below threshold {EVAL_MIN_DELTA:.4f}"
    else:
        decision = "await_candidate_model"
        reason = "no candidate model configured for direct A/B"

    report = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "topic": topic,
        "merged_artifact": str(merged_artifact),
        "active_model": OLLAMA_ACTIVE_MODEL,
        "candidate_model": EVAL_CANDIDATE_MODEL or "",
        "active_eval": active_eval,
        "candidate_eval": candidate_eval,
        "delta_vs_previous_report": delta,
        "decision": decision,
        "reason": reason,
    }
    _write_report(report)


def _sync_skills_dir() -> None:
    """Sincroniza código operativo de vuelta a ~/skills/miniverse/."""
    if not SYNC_SKILLS:
        return
    if not SKILLS_DIR.exists():
        print("[librarian-swift] skills/miniverse no existe, saltando sync")
        return
    src = str(AGNES_HOME / "apps" / "miniverse") + "/"
    dst = str(SKILLS_DIR) + "/"
    result = subprocess.run(
        [
            "rsync", "-a", "--delete",
            "--exclude=.git/", "--exclude=node_modules/",
            "--exclude=generated/", "--exclude=models/",
            "--exclude=__pycache__/", "--exclude=dist/",
            src, dst,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("[librarian-swift] Skills local sincronizada")
    else:
        print(f"[librarian-swift] rsync skills falló: {result.stderr[:300]}")


def _sync_tachyon_repo(topic: str) -> None:
    """Hace git add+commit+push en AGNES_HOME."""
    if not SYNC_REPO:
        return
    repo = str(AGNES_HOME)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    msg = f"librarian: merge+eval {_safe_name(topic)} @ {stamp}"
    subprocess.run(["git", "-C", repo, "add", "-A"], capture_output=True)
    r_commit = subprocess.run(
        ["git", "-C", repo, "commit", "-m", msg],
        capture_output=True,
        text=True,
    )
    if "nothing to commit" in r_commit.stdout or "nothing to commit" in r_commit.stderr:
        print("[librarian-swift] repo sin cambios nuevos, skip push")
        return
    r_push = subprocess.run(
        ["git", "-C", repo, "push"],
        capture_output=True,
        text=True,
    )
    if r_push.returncode == 0:
        print(f"[librarian-swift] Repo Tachyon actualizado: {msg}")
    else:
        print(f"[librarian-swift] push falló: {r_push.stderr[:300]}")


def _post_merge_sync(topic: str, hb: HeartbeatThread) -> None:
    """Sincroniza skills y repo tras cada merge programado."""
    hb.update("working", "Sincronizando skills y repositorio...")
    speak("Actualizando skills local y repositorio Tachyon")
    try:
        _sync_skills_dir()
    except Exception as exc:
        print(f"[librarian-swift] sync skills falló: {exc}")
    try:
        _sync_tachyon_repo(topic)
    except Exception as exc:
        print(f"[librarian-swift] sync repo falló: {exc}")
    hb.update("idle", f"Ciclo de merge completo: {topic}")
    speak("Ciclo de merge y sync completo")


def _run_topic(topic: str, hb: HeartbeatThread, force_export: bool = False) -> str | None:
    dataset_path = _write_dataset(topic)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = RUNS_ROOT / f"{_safe_name(topic)}_{stamp}"
    export_dir = MERGED_ROOT / f"merged_from_{_safe_name(topic)}_{stamp}"
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)
    MERGED_ROOT.mkdir(parents=True, exist_ok=True)

    do_export = EXPORT_MERGED or force_export

    hb.update("working", f"Swift/Qwen aprendiendo {topic}{'  [merge]' if force_export else ''}")
    speak(f"Aprendiendo {topic} con ms-swift{'  [merge programado]' if force_export else ''}")

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
    if do_export:
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
        target_path = _resolved_merged_artifact(output_dir, export_dir) if do_export else output_dir
        LATEST_MERGED_FILE.write_text(str(target_path), encoding="utf-8")
        if do_export:
            try:
                _evaluate_after_merge(topic, target_path)
            except Exception as exc:
                print(f"[librarian-swift] Post-merge evaluation failed: {exc}")
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
    # Forzar primer merge al iniciar (last_merge_time=0 garantiza que el primer topic dispare)
    last_merge_time: float = time.time() - MERGE_INTERVAL_SEC
    print(f"[librarian-swift] Intervalo de merge: {MERGE_INTERVAL_SEC}s ({MERGE_INTERVAL_SEC // 3600}h)")
    try:
        while True:
            rounds += 1
            for topic in TOPIC_ORDER:
                now = time.time()
                force_merge = (now - last_merge_time) >= MERGE_INTERVAL_SEC
                merged = _run_topic(topic, hb, force_export=force_merge)
                if force_merge and merged:
                    _post_merge_sync(topic, hb)
                    last_merge_time = time.time()
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