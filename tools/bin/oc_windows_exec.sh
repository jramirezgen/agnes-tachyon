#!/bin/bash
# Wrapper seguro para ejecutar comandos en Windows desde WSL
# Uso: oc_windows_exec.sh "comando PowerShell"

LOGFILE="$HOME/.openclaw/logs/windows_exec.log"
CMD="$1"

# Comandos peligrosos bloqueados
if [[ "$CMD" =~ (Remove-Item\s+C:\\|Format-Volume) ]]; then
  echo "Comando bloqueado por seguridad" | tee -a "$LOGFILE"
  exit 1
fi

# Ejecutar comando en Windows via powershell.exe
{
  echo "[$(date)] CMD: $CMD" >> "$LOGFILE"
  timeout 30s powershell.exe -Command "$CMD" 2>&1 | tee -a "$LOGFILE"
}