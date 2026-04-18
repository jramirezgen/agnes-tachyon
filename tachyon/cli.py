"""Standard CLI for Agnes Tachyon."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = REPO_ROOT / "bin"
WORLD_DIR = REPO_ROOT / "apps" / "miniverse" / "my-world"
PORTABLE_SCRIPTS_DIR = REPO_ROOT / ".github" / "skills" / "agnes-tachyon-portable" / "scripts"


def _default_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("AGNES_HOME", str(REPO_ROOT))
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def _http_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = response.read().decode()
    return json.loads(raw) if raw else {}


def _run(cmd: list[str], *, replace: bool = False) -> int:
    env = _default_env()
    if replace:
        os.execvpe(cmd[0], cmd, env)
        return 0
    return subprocess.call(cmd, env=env)


def cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def cmd_server(args: argparse.Namespace) -> int:
    os.environ["AGNES_HOME"] = str(REPO_ROOT)
    if args.port:
        os.environ["TACHYON_PORT"] = str(args.port)
    from .server import main as server_main
    server_main()
    return 0


def cmd_watchdog(_args: argparse.Namespace) -> int:
    os.environ["AGNES_HOME"] = str(REPO_ROOT)
    from .watchdog import main as watchdog_main
    watchdog_main()
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    port = args.port or os.environ.get("TACHYON_PORT", "7777")
    try:
        data = _http_json(f"http://localhost:{port}/health")
    except urllib.error.URLError as exc:
        print(f"Health check failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def cmd_diagnose(args: argparse.Namespace) -> int:
    port = args.port or os.environ.get("TACHYON_PORT", "7777")
    payload = {
        "message": "genera un diagnóstico técnico completo y breve de mi PC y detecta cuellos de botella actuales",
        "voice": False,
    }
    try:
        data = _http_json(f"http://localhost:{port}/chat", method="POST", payload=payload)
    except urllib.error.URLError as exc:
        print(f"Diagnose request failed: {exc}", file=sys.stderr)
        return 1
    print(data.get("response", "Sin respuesta"))
    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    port = str(args.port or os.environ.get("TACHYON_PORT", "7777"))
    patterns = ["tachyon.server", "tachyon.watchdog", "tachyon.miniverse_bridge"]
    for pattern in patterns:
        subprocess.run(["pkill", "-f", pattern], check=False)
    subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Agnes Tachyon systems suspended.")
    return 0


def cmd_train(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "tachyon.trainer"]
    if args.dataset:
        cmd.extend(["--dataset", args.dataset])
    if args.steps is not None:
        cmd.extend(["--steps", str(args.steps)])
    if args.model:
        cmd.extend(["--model", args.model])
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.from_memory:
        cmd.append("--from-memory")
    return _run(cmd, replace=True)


def cmd_stack_start(_args: argparse.Namespace) -> int:
    return _run([str(WORLD_DIR / "start_operational_stack.sh")], replace=True)


def cmd_stack_stop(_args: argparse.Namespace) -> int:
    return _run([str(WORLD_DIR / "stop_operational_stack.sh")], replace=True)


def cmd_portable_export(args: argparse.Namespace) -> int:
    cmd = [str(PORTABLE_SCRIPTS_DIR / "export_agnes_tachyon_bundle.sh"), "--profile", args.profile]
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    return _run(cmd, replace=True)


def cmd_portable_restore(args: argparse.Namespace) -> int:
    cmd = [str(PORTABLE_SCRIPTS_DIR / "restore_agnes_tachyon_bundle.sh"), args.bundle]
    if args.destination:
        cmd.append(args.destination)
    return _run(cmd, replace=True)


def cmd_portable_verify(args: argparse.Namespace) -> int:
    cmd = [str(PORTABLE_SCRIPTS_DIR / "verify_restored_stack.sh"), args.path]
    return _run(cmd, replace=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agnes-tachyon", description="Agnes Tachyon standard CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    version_parser = subparsers.add_parser("version", help="Show package version")
    version_parser.set_defaults(func=cmd_version)

    server_parser = subparsers.add_parser("server", help="Start the FastAPI backend server")
    server_parser.add_argument("--port", type=int, default=None, help="Override backend port")
    server_parser.set_defaults(func=cmd_server)

    watchdog_parser = subparsers.add_parser("watchdog", help="Start the watchdog supervisor")
    watchdog_parser.set_defaults(func=cmd_watchdog)

    health_parser = subparsers.add_parser("health", help="Query backend health endpoint")
    health_parser.add_argument("--port", type=int, default=None, help="Override backend port")
    health_parser.set_defaults(func=cmd_health)

    diagnose_parser = subparsers.add_parser("diagnose", help="Ask Tachyon for a live local diagnosis")
    diagnose_parser.add_argument("--port", type=int, default=None, help="Override backend port")
    diagnose_parser.set_defaults(func=cmd_diagnose)

    stop_parser = subparsers.add_parser("stop", help="Stop backend-related Tachyon processes")
    stop_parser.add_argument("--port", type=int, default=None, help="Override backend port")
    stop_parser.set_defaults(func=cmd_stop)

    train_parser = subparsers.add_parser("train", help="Run the training pipeline")
    train_parser.add_argument("--dataset", default=None)
    train_parser.add_argument("--steps", type=int, default=100)
    train_parser.add_argument("--model", default=None)
    train_parser.add_argument("--output-dir", default=None)
    train_parser.add_argument("--from-memory", action="store_true")
    train_parser.set_defaults(func=cmd_train)

    stack_parser = subparsers.add_parser("stack", help="Operate the integrated Miniverse stack")
    stack_subparsers = stack_parser.add_subparsers(dest="stack_command", required=True)
    stack_start_parser = stack_subparsers.add_parser("start", help="Start integrated stack")
    stack_start_parser.set_defaults(func=cmd_stack_start)
    stack_stop_parser = stack_subparsers.add_parser("stop", help="Stop integrated stack")
    stack_stop_parser.set_defaults(func=cmd_stack_stop)

    portable_parser = subparsers.add_parser("portable", help="Portable bundle workflows")
    portable_subparsers = portable_parser.add_subparsers(dest="portable_command", required=True)

    portable_export_parser = portable_subparsers.add_parser("export", help="Export a portable bundle")
    portable_export_parser.add_argument("--profile", default="code-only", choices=["code-only", "with-datasets", "full-portable"])
    portable_export_parser.add_argument("--output-dir", default=None)
    portable_export_parser.set_defaults(func=cmd_portable_export)

    portable_restore_parser = portable_subparsers.add_parser("restore", help="Restore a portable bundle")
    portable_restore_parser.add_argument("bundle")
    portable_restore_parser.add_argument("destination", nargs="?", default=None)
    portable_restore_parser.set_defaults(func=cmd_portable_restore)

    portable_verify_parser = portable_subparsers.add_parser("verify", help="Verify a restored stack")
    portable_verify_parser.add_argument("path")
    portable_verify_parser.set_defaults(func=cmd_portable_verify)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
