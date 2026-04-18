"""Agnes Tachyon — Tools: Control del sistema Linux + Windows.

Agnes puede ejecutar comandos en el entorno del usuario.
Sintaxis que Qwen debe usar en sus respuestas:
  <EXEC_LINUX>comando bash</EXEC_LINUX>
  <EXEC_WIN>PowerShell comando</EXEC_WIN>
  <READ_FILE>/ruta/al/archivo</READ_FILE>
  <WRITE_FILE path="/ruta/archivo">contenido</WRITE_FILE>
"""
import asyncio
import logging
import re
from pathlib import Path

log = logging.getLogger("tachyon.tools")

# ── Security blocklists ───────────────────────────────────────────
LINUX_BLOCKLIST = [
    r'\brm\s+-rf\s+/',
    r'\bmkfs\b',
    r'\bdd\s+if=',
    r'>\s*/dev/(s|h)da',
    r'\bshutdown\b',
    r'\breboot\b',
    r':(){ :|:& };:',          # fork bomb
]

WINDOWS_BLOCKLIST = [
    r'Remove-Item\s+C:\\',
    r'Format-Volume',
    r'rm\s+-recurse\s+C:',
    r'Stop-Computer',
    r'Restart-Computer',
]

TOOL_RE = re.compile(
    r'<(EXEC_LINUX|EXEC_WIN|READ_FILE|WRITE_FILE)(\s[^>]*)?>(.*?)</\1>',
    re.DOTALL | re.IGNORECASE,
)
WRITE_PATH_RE = re.compile(r'path=["\']([^"\']+)["\']')


def _safe(cmd: str, blocklist: list[str]) -> bool:
    return not any(re.search(p, cmd, re.IGNORECASE) for p in blocklist)


async def exec_linux(cmd: str, timeout: int = 20) -> str:
    if not _safe(cmd, LINUX_BLOCKLIST):
        return "⛔ [BLOQUEADO] Comando denegado por seguridad."
    log.info("⚙ EXEC_LINUX: %s", cmd[:120])
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode(errors="replace").strip()
        return (out[:2000] + "\n...(truncado)") if len(out) > 2000 else (out or "(sin salida)")
    except asyncio.TimeoutError:
        return f"⏱ [TIMEOUT] El comando tardó más de {timeout}s."
    except Exception as e:
        return f"💥 [ERROR] {e}"


async def exec_windows(cmd: str, timeout: int = 25) -> str:
    if not _safe(cmd, WINDOWS_BLOCKLIST):
        return "⛔ [BLOQUEADO] Comando denegado por seguridad."
    log.info("⚙ EXEC_WIN: %s", cmd[:120])
    try:
        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command", cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        return (out[:2000] + "\n...(truncado)") if len(out) > 2000 else (out or "(sin salida)")
    except asyncio.TimeoutError:
        return f"⏱ [TIMEOUT] El comando PowerShell tardó más de {timeout}s."
    except FileNotFoundError:
        return "❌ [ERROR] powershell.exe no encontrado. ¿Estás en WSL?"
    except Exception as e:
        return f"💥 [ERROR] {e}"


async def read_file_tool(path: str) -> str:
    p = Path(path.strip())
    if not p.exists():
        return f"❌ [ERROR] Archivo no encontrado: {path}"
    try:
        content = p.read_text(errors="replace")
        if len(content) > 3000:
            return content[:3000] + "\n...(truncado)"
        return content
    except Exception as e:
        return f"💥 [ERROR] {e}"


async def write_file_tool(path: str, content: str) -> str:
    p = Path(path.strip())
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"✅ Archivo guardado: {path} ({len(content)} bytes)"
    except Exception as e:
        return f"💥 [ERROR] {e}"


async def execute_tool_calls(response_text: str) -> tuple[str, list[dict]]:
    """Find and execute all <TOOL> blocks in the LLM response.

    Returns:
        clean_text: response with tool blocks replaced by results
        results: list of executed tool metadata
    """
    results = []
    clean_text = response_text

    for m in list(TOOL_RE.finditer(response_text)):
        tag = m.group(1).upper()
        attrs = m.group(2) or ""
        body = m.group(3).strip()
        raw_tag = m.group(0)

        if tag == "EXEC_LINUX":
            out = await exec_linux(body)
        elif tag == "EXEC_WIN":
            out = await exec_windows(body)
        elif tag == "READ_FILE":
            out = await read_file_tool(body)
        elif tag == "WRITE_FILE":
            pm = WRITE_PATH_RE.search(attrs)
            if pm:
                out = await write_file_tool(pm.group(1), body)
            else:
                out = "❌ [ERROR] Falta atributo path= en WRITE_FILE"
        else:
            out = "❌ Tool desconocida"

        results.append({"tool": tag, "cmd": body[:80], "output": out})
        # Replace tag with inline result
        clean_text = clean_text.replace(raw_tag, f"\n[{tag}] → {out}\n", 1)

    return clean_text, results


def has_tool_calls(text: str) -> bool:
    return bool(TOOL_RE.search(text))


# Quick tool-syntax reference for system prompt injection
TOOLS_REFERENCE = """\

HERRAMIENTAS DEL SISTEMA (usar solo cuando el usuario pida acción):
  <EXEC_LINUX>comando bash</EXEC_LINUX>   — ejecutar en Linux/WSL del Entrenador
  <EXEC_WIN>comando PowerShell</EXEC_WIN> — ejecutar en Windows del Entrenador
  <READ_FILE>/ruta/archivo</READ_FILE>    — leer un archivo
  <WRITE_FILE path="/ruta">contenido</WRITE_FILE> — crear/escribir archivo

REGLAS:
- Puedes encadenar varias herramientas en una misma respuesta.
- Después de cada herramienta SIEMPRE comenta el resultado brevemente.
- Si el comando falla, analiza el error y propón una solución.
- NUNCA uses herramientas para respuestas simples sin acción real.
- En modo voz: anuncia lo que vas a hacer ANTES del tag, y resume el resultado DESPUÉS.
"""
