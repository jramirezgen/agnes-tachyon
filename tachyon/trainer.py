"""ms-swift Training Pipeline — Fine-tune Qwen with LoRA/QLoRA.

This replaces the old TinyLlama librarian_learn.py with a unified
Qwen training pipeline using ModelScope ms-swift.

Usage:
    python -m tachyon.trainer [--dataset PATH] [--steps N]
"""
import argparse
import importlib.util
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import config
from .persona_dataset import build_persona_dataset

log = logging.getLogger("tachyon.trainer")


def resolve_swift_command() -> list[str]:
    """Resolve how to invoke ms-swift CLI in this environment.

    Priority:
    1. Installed python module: python -m swift.cli.main
    2. Local repo checkout: python -m swift.cli.main + PYTHONPATH al repo
    3. Binary in PATH: swift
    """
    if importlib.util.find_spec("swift") is not None:
        return [sys.executable, "-m", "swift.cli.main"]

    local_cli = config.MSSWIFT_DIR / "swift" / "cli" / "main.py"
    if local_cli.exists():
        return [sys.executable, "-m", "swift.cli.main"]

    swift_bin = shutil.which("swift")
    if swift_bin:
        return [swift_bin]

    raise RuntimeError(
        "No se encontro ms-swift. Instala el paquete o verifica el repo en "
        f"{config.MSSWIFT_DIR}"
    )


def build_training_command(
    dataset: str = None,
    max_steps: int = 100,
    model: str = None,
    output_dir: str = None,
) -> list[str]:
    """Build the ms-swift training command."""
    model = model or config.TRAIN_MODEL
    output_dir = output_dir or str(config.TRAIN_OUTPUT)
    dataset = dataset or "AI-ModelScope/alpaca-gpt4-data-zh#500 AI-ModelScope/alpaca-gpt4-data-en#500"
    swift_cmd = resolve_swift_command()

    cmd = [
        *swift_cmd, "sft",
        "--model", model,
        "--use_hf", "true",
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
        "--output_dir", output_dir,
        "--max_steps", str(max_steps),
        "--logging_steps", "5",
        "--save_steps", str(max(max_steps // 5, 10)),
        "--per_device_train_batch_size", "1",
        "--gradient_accumulation_steps", "4",
        "--learning_rate", "1e-4",
        "--warmup_ratio", "0.05",
        "--torch_dtype", "bfloat16",
        "--max_length", "1024",
        # Avoid optional TensorBoard dependency issues in minimal envs.
        "--report_to", "none",
    ]
    return cmd


def find_latest_checkpoint(output_dir: str | Path) -> str:
    """Find the newest checkpoint directory produced by ms-swift."""
    output_path = Path(output_dir)
    checkpoints = [p for p in output_path.rglob("checkpoint-*") if p.is_dir()]
    if not checkpoints:
        raise FileNotFoundError(f"No se encontraron checkpoints en {output_path}")
    checkpoints.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(checkpoints[0])


def export_merged_model(adapters_dir: str, output_dir: str) -> int:
    """Export and merge LoRA adapters into a full HF model using ms-swift."""
    swift_cmd = resolve_swift_command()
    cmd = [
        *swift_cmd, "export",
        "--adapters", adapters_dir,
        "--output_dir", output_dir,
        "--merge_lora", "true",
        "--use_hf", "true",
        # Keep export single-threaded to avoid RAM/swap spikes in WSL.
        "--thread_count", os.getenv("SWIFT_EXPORT_THREAD_COUNT", "1"),
    ]
    log.info("Exporting merged model from %s -> %s", adapters_dir, output_dir)
    env = {**os.environ}
    ms_swift_path = str(config.MSSWIFT_DIR)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{ms_swift_path}:{existing_pythonpath}"
        if existing_pythonpath
        else ms_swift_path
    )
    env.setdefault("TORCHINDUCTOR_COMPILE_THREADS", os.getenv("TORCHINDUCTOR_COMPILE_THREADS", "1"))
    env.setdefault("OMP_NUM_THREADS", os.getenv("OMP_NUM_THREADS", "4"))
    env.setdefault("MKL_NUM_THREADS", os.getenv("MKL_NUM_THREADS", "4"))
    env.setdefault("NUMEXPR_NUM_THREADS", os.getenv("NUMEXPR_NUM_THREADS", "4"))
    result = subprocess.run(cmd, env=env)
    return result.returncode


def build_custom_dataset(conversations: list[dict], output_path: Path) -> str:
    """Build a custom JSONL dataset from conversation memory for training.

    Takes conversation pairs and formats them for ms-swift SFT.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = []

    for i in range(0, len(conversations) - 1, 2):
        user_msg = conversations[i]
        if i + 1 < len(conversations):
            assistant_msg = conversations[i + 1]
            if user_msg.get("role") == "user" and assistant_msg.get("role") == "assistant":
                records.append({
                    "messages": [
                        {"role": "system", "content": "Eres Agnes Tachyon, científica genio ENTP."},
                        {"role": "user", "content": user_msg["content"]},
                        {"role": "assistant", "content": assistant_msg["content"]},
                    ]
                })

    if not records:
        log.warning("No valid conversation pairs for training.")
        return ""

    with open(output_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    log.info("Built custom dataset: %d samples → %s", len(records), output_path)
    return str(output_path)


def run_training(
    dataset: str = None,
    max_steps: int = 100,
    model: str = None,
    output_dir: str = None,
    blocking: bool = True,
):
    """Run ms-swift QLoRA training."""
    cmd = build_training_command(dataset, max_steps, model, output_dir)
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": "0"}
    ms_swift_path = str(config.MSSWIFT_DIR)
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{ms_swift_path}:{existing_pythonpath}"
        if existing_pythonpath
        else ms_swift_path
    )

    log.info("Starting ms-swift training:")
    log.info("  Model: %s", model or config.TRAIN_MODEL)
    log.info("  Dataset: %s", dataset)
    log.info("  Steps: %d", max_steps)
    log.info("  Command: %s", " ".join(cmd[:10]) + "...")

    logfile = config.DATA_DIR / "train.log"

    if blocking:
        result = subprocess.run(
            cmd, env=env,
            stdout=open(logfile, "w"),
            stderr=subprocess.STDOUT,
        )
        log.info("Training finished with exit code %d", result.returncode)
        return result.returncode
    else:
        proc = subprocess.Popen(
            cmd, env=env,
            stdout=open(logfile, "w"),
            stderr=subprocess.STDOUT,
        )
        log.info("Training started in background (PID %d)", proc.pid)
        return proc


def main():
    parser = argparse.ArgumentParser(description="Tachyon ms-swift Trainer")
    parser.add_argument("--dataset", default=None, help="Dataset spec")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--persona-docs", action="store_true",
                        help="Build persona dataset from Agnes docs")
    parser.add_argument("--export-merged", action="store_true",
                        help="Export merged HF model after training")
    parser.add_argument("--export-dir", default=None,
                        help="Output dir for merged export")
    parser.add_argument("--from-memory", action="store_true",
                        help="Build dataset from conversation memory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    dataset = args.dataset
    if args.persona_docs:
        dataset_path = config.PERSONA_OUTPUT / "tachyon_persona_docs.jsonl"
        dataset = build_persona_dataset(dataset_path)

    if args.from_memory:
        from .memory import ConversationMemory
        mem = ConversationMemory()
        if mem.count < 10:
            log.error("Not enough conversation data (%d messages). Need at least 10.", mem.count)
            sys.exit(1)
        dataset_path = config.DATA_DIR / "custom_train.jsonl"
        dataset = build_custom_dataset(mem.messages, dataset_path)
        if not dataset:
            sys.exit(1)

    rc = run_training(
        dataset=dataset,
        max_steps=args.steps,
        model=args.model,
        output_dir=args.output_dir,
    )
    if rc == 0 and args.export_merged:
        checkpoint = find_latest_checkpoint(args.output_dir or config.TRAIN_OUTPUT)
        export_dir = args.export_dir or str(config.TRAIN_OUTPUT / "merged")
        rc = export_merged_model(checkpoint, export_dir)
    sys.exit(rc)


if __name__ == "__main__":
    main()
