"""Intent-based tool pre-execution.

For small models that don't reliably follow custom tool syntax,
this module detects system-action intents from the user's message
and pre-executes the appropriate tool, injecting results into context.
"""
import asyncio
import logging
import re
from pathlib import Path

from .tools import exec_linux, exec_windows

log = logging.getLogger("tachyon.intent")


def summarize_pc_diagnostic(raw: str) -> str:
    """Build a concise deterministic summary from the PC diagnostic output."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]

    load_line = next((line for line in lines if "load average:" in line), None)
    mem_line = next((line for line in lines if line.startswith("Mem:")), None)
    swap_line = next((line for line in lines if line.startswith("Swap:")), None)
    disk_line = next((line for line in lines if line.startswith("/dev/")), None)
    gpu_line = next((line for line in lines if "NVIDIA" in line or "nvidia-smi" in line), None)

    top_processes = []
    in_cpu_block = False
    for line in lines:
        if line == "=== TOP CPU ===":
            in_cpu_block = True
            continue
        if line.startswith("===") and line != "=== TOP CPU ===":
            in_cpu_block = False
        if not in_cpu_block:
            continue
        if line.startswith("PID ") or line.startswith("PID"):
            continue
        if line and line[0].isdigit():
            top_processes.append(line)
        if len(top_processes) >= 4:
            break

    findings = []
    if load_line:
        findings.append(f"Carga actual: {load_line}")
    if mem_line:
        findings.append(f"Memoria: {mem_line}")
    if swap_line:
        findings.append(f"Swap: {swap_line}")
    if disk_line:
        findings.append(f"Disco raíz: {disk_line}")
    if gpu_line:
        findings.append(f"GPU: {gpu_line}")

    if top_processes:
        findings.append("Procesos más pesados ahora:")
        findings.extend(f"- {line}" for line in top_processes)

    recommendations = []
    joined = "\n".join(top_processes)
    if "librarian_learn.py" in joined:
        recommendations.append("Hay entrenamiento activo de librarian_learn.py consumiendo bastante CPU/RAM.")
    if "ollama runner" in joined:
        recommendations.append("Ollama/Qwen está cargado y consume CPU o VRAM mientras Tachyon responde.")
    if swap_line and not swap_line.endswith("0B") and " 0B" not in swap_line:
        recommendations.append("Hay uso de swap; eso puede introducir lentitud si varias cargas pesadas coinciden.")

    response = "Diagnóstico rápido del PC:\n\n" + "\n".join(findings)
    if recommendations:
        response += "\n\nCuellos de botella detectados:\n" + "\n".join(f"- {item}" for item in recommendations)
    return response

# ── Intent patterns → auto-action ────────────────────────────────
# Each entry: (regex_pattern, async_fn_to_call, description)

_FILE_LIST_RE = re.compile(
    r'(qué hay|lista|muestra|archivos|carpeta|directorio|ver|archivos de)',
    re.IGNORECASE
)
_EXEC_EXPLICIT_RE = re.compile(
    r'(ejecuta|corre|lanza|run|execute|haz un ls|haz pwd|muestra los procesos)',
    re.IGNORECASE
)
_SYSTEM_INFO_RE = re.compile(
    r'(cuánta memoria|ram|cpu|disco|espacio|uso de|sistema|gpu|temperatura|recursos)',
    re.IGNORECASE
)
_WIN_INFO_RE = re.compile(
    r'(windows|escritorio de windows|programa.*windows|proceso.*windows|escritorio)',
    re.IGNORECASE
)
_PS_LIST_RE = re.compile(
    r'(procesos|process|ps aux|qué corre|qué está corriendo|top)',
    re.IGNORECASE
)
_DATE_TIME_RE = re.compile(
    r'(qué hora|fecha|cuándo|time|date|hora)',
    re.IGNORECASE
)
_PC_DIAG_RE = re.compile(
    r'(diagn[oó]stic|diagnostico|diagnóstico|pc|computadora|ordenador|equipo|lenta|lento|rendimiento|optimiza|optimizar|performance)',
    re.IGNORECASE
)


async def detect_intent_and_run(user_text: str) -> list[dict]:
    """Detect tool intents from user message and pre-run them."""
    results = []
    text = user_text.strip()
    lower_text = text.lower()

    # Date/time — always fast and useful
    if _DATE_TIME_RE.search(text):
        out = await exec_linux("date '+%A %d %B %Y — %H:%M:%S'")
        results.append({"tool": "EXEC_LINUX", "cmd": "date", "output": out})

    # Full PC diagnostic / performance triage
    if _PC_DIAG_RE.search(text):
        cmd = (
            "echo '=== RESUMEN ===' && uptime && "
            "echo '=== MEMORIA ===' && free -h && "
            "echo '=== DISCO ===' && df -h / && "
            "echo '=== TOP CPU ===' && ps -eo pid,ppid,%cpu,%mem,etime,cmd --sort=-%cpu | head -12 && "
            "echo '=== TOP RAM ===' && ps -eo pid,ppid,%cpu,%mem,etime,cmd --sort=-%mem | head -12 && "
            "echo '=== GPU ===' && (nvidia-smi --query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu --format=csv,noheader 2>/dev/null || echo 'nvidia-smi no disponible')"
        )
        out = await exec_linux(cmd, timeout=30)
        results.append({"tool": "EXEC_LINUX", "cmd": "pc_diagnostic", "output": out})

    # System resources
    elif _SYSTEM_INFO_RE.search(text):
        cmd = (
            "echo '=== CPU ===' && grep 'model name' /proc/cpuinfo | head -1 && "
            "echo '=== RAM ===' && free -h | grep Mem && "
            "echo '=== DISCO ===' && df -h / | tail -1 && "
            "echo '=== GPU ===' && (nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu "
            "--format=csv,noheader 2>/dev/null || echo 'nvidia-smi no disponible')"
        )
        out = await exec_linux(cmd)
        results.append({"tool": "EXEC_LINUX", "cmd": "sysinfo", "output": out})

    # Process list
    elif _PS_LIST_RE.search(text) and not _SYSTEM_INFO_RE.search(text):
        out = await exec_linux("ps aux --sort=-%mem | head -12")
        results.append({"tool": "EXEC_LINUX", "cmd": "ps aux", "output": out})

    # File listing — extract path if mentioned
    if _FILE_LIST_RE.search(text):
        # Try to extract a path from the message
        path_match = re.search(r'(/[\w/.\-_~]+)', text)
        if path_match:
            path = path_match.group(1)
        else:
            # Default to agnes/tachyon or home
            if 'tachyon' in lower_text:
                path = str(Path.home() / 'agnes' / 'tachyon')
            elif 'agnes' in lower_text:
                path = str(Path.home() / 'agnes')
            elif 'proyecto' in lower_text or 'project' in lower_text:
                path = str(Path.home() / 'projects')
            else:
                path = str(Path.home())
        out = await exec_linux(f"ls -la '{path}' 2>&1 | head -30")
        results.append({"tool": "EXEC_LINUX", "cmd": f"ls {path}", "output": out})

    # Explicit execution request — extract command after trigger word
    if _EXEC_EXPLICIT_RE.search(text):
        # Look for quoted or backtick command
        cmd_match = re.search(r'[`\'"]([^`\'"]{3,150})[`\'"]', text)
        if cmd_match:
            cmd = cmd_match.group(1)
            out = await exec_linux(cmd)
            results.append({"tool": "EXEC_LINUX", "cmd": cmd, "output": out})

    # Windows info request
    if _WIN_INFO_RE.search(text):
        out = await exec_windows(
            "Get-Process | Sort-Object CPU -Descending | Select-Object -First 8 Name,CPU,WorkingSet | Format-Table -AutoSize"
        )
        results.append({"tool": "EXEC_WIN", "cmd": "Get-Process top8", "output": out})

    return results
